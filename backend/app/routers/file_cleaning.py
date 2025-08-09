"""
File Cleaning API Router
Production-grade REST API endpoints for RVTool file cleaning functionality
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
import os
from pathlib import Path

from ..models.cleaning_models import (
    CleaningSession, HeaderValidationRequest, DataValidationRequest,
    CleanupRequest, CleaningSessionResponse, ValidationResponse,
    CleanupResponse, ErrorResponse, CleaningConfig
)
from ..services.file_cleaning_service import file_cleaning_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/cleaning",
    tags=["File Cleaning"],
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


def validate_file_upload(file: UploadFile) -> None:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in CleaningConfig.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Supported: {CleaningConfig.SUPPORTED_EXTENSIONS}"
        )
    
    # Check file size (if available)
    if hasattr(file, 'size') and file.size and file.size > CleaningConfig.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {CleaningConfig.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )


@router.options("/upload")
async def upload_options():
    """Handle CORS preflight for upload endpoint"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/upload", response_model=CleaningSessionResponse)
async def upload_file_for_cleaning(file: UploadFile = File(...)):
    """
    Upload a file for cleaning and validation
    Creates a new cleaning session
    """
    try:
        # Validate file
        validate_file_upload(file)
        
        # Read file content
        file_content = await file.read()
        
        # Additional size check after reading
        if len(file_content) > CleaningConfig.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {CleaningConfig.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        # Create cleaning session
        session = file_cleaning_service.create_session(file.filename, file_content)
        
        logger.info(f"File uploaded for cleaning: {file.filename} (Session: {session.session_id})")
        
        return CleaningSessionResponse(
            session=session,
            message=f"File '{file.filename}' uploaded successfully. Ready for validation."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.options("/validate-headers")
async def validate_headers_options():
    """Handle CORS preflight for validate-headers endpoint"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/validate-headers", response_model=ValidationResponse)
async def validate_headers(request: HeaderValidationRequest):
    """
    Validate column headers against required TCO calculation columns
    """
    try:
        session = file_cleaning_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Perform header validation
        header_result = file_cleaning_service.validate_headers(request.session_id)
        
        message = "Header validation completed successfully"
        if not header_result.is_valid:
            message = f"Header validation failed. Missing columns: {', '.join(header_result.missing_headers)}"
        
        return ValidationResponse(
            session_id=request.session_id,
            header_validation=header_result,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating headers for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Header validation failed: {str(e)}")


@router.options("/validate-data")
async def validate_data_options():
    """Handle CORS preflight for validate-data endpoint"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.post("/validate-data", response_model=ValidationResponse)
async def validate_data(request: DataValidationRequest):
    """
    Perform comprehensive data validation
    Checks for duplicates, null values, zero values, and logical constraints
    """
    try:
        session = file_cleaning_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if headers are valid first
        if not session.header_validation or not session.header_validation.is_valid:
            raise HTTPException(
                status_code=400, 
                detail="Header validation must pass before data validation"
            )
        
        # Perform data validation
        data_result = file_cleaning_service.validate_data(
            session_id=request.session_id,
            validate_duplicates=request.validate_duplicates,
            validate_null_values=request.validate_null_values,
            validate_zero_values=request.validate_zero_values,
            validate_logical_constraints=request.validate_logical_constraints
        )
        
        issues_count = len(data_result.issues)
        critical_count = data_result.critical_issues_count
        
        if issues_count == 0:
            message = "Data validation completed successfully. No issues found."
        else:
            message = f"Data validation completed. Found {issues_count} issues ({critical_count} critical)."
        
        # Create response with proper CORS headers
        response_data = ValidationResponse(
            session_id=request.session_id,
            data_validation=data_result,
            message=message
        )
        
        return JSONResponse(
            content=response_data.dict(),
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating data for session {request.session_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={"error": f"Data validation failed: {str(e)}"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS", 
                "Access-Control-Allow-Headers": "*",
            }
        )


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_data(request: CleanupRequest):
    """
    Perform data cleanup based on user selections
    Removes problematic records and generates cleaned file
    """
    try:
        session = file_cleaning_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if data validation was performed
        if not session.data_validation:
            raise HTTPException(
                status_code=400,
                detail="Data validation must be performed before cleanup"
            )
        
        # Perform cleanup
        cleanup_result = file_cleaning_service.cleanup_data(
            session_id=request.session_id,
            cleanup_selection=request.cleanup_selection
        )
        
        # Generate download URL
        cleaned_file_url = f"/api/cleaning/download/{request.session_id}"
        
        removed_count = cleanup_result.removed_record_count
        remaining_count = cleanup_result.cleaned_record_count
        
        message = f"Cleanup completed successfully. Removed {removed_count} records, {remaining_count} records remaining."
        
        return CleanupResponse(
            session_id=request.session_id,
            cleanup_result=cleanup_result,
            cleaned_file_url=cleaned_file_url,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning data for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data cleanup failed: {str(e)}")


@router.get("/download/{session_id}")
async def download_cleaned_file(session_id: str):
    """
    Download the cleaned file
    """
    try:
        session = file_cleaning_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.cleaned_file_path:
            raise HTTPException(status_code=404, detail="Cleaned file not available")
        
        cleaned_file_path = session.cleaned_file_path
        if not os.path.exists(cleaned_file_path):
            raise HTTPException(status_code=404, detail="Cleaned file not found on disk")
        
        # Determine media type
        if session.cleaned_filename.endswith('.csv'):
            media_type = 'text/csv'
        else:
            media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return FileResponse(
            path=cleaned_file_path,
            filename=session.cleaned_filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/download-removed/{session_id}")
async def download_removed_data(session_id: str):
    """
    Download the removed data file with cleanup reasons
    """
    try:
        session = file_cleaning_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        removed_file_path = file_cleaning_service.get_removed_data_file_path(session_id)
        if not removed_file_path or not os.path.exists(removed_file_path):
            raise HTTPException(status_code=404, detail="Removed data file not available")
        
        # Generate filename for removed data
        removed_filename = f"removed_data_{session.original_filename}"
        
        # Determine media type
        if session.original_filename.endswith('.csv'):
            media_type = 'text/csv'
        else:
            media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return FileResponse(
            path=removed_file_path,
            filename=removed_filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading removed data for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/session/{session_id}", response_model=CleaningSessionResponse)
async def get_session_status(session_id: str):
    """
    Get current status of a cleaning session
    """
    try:
        session = file_cleaning_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return CleaningSessionResponse(
            session=session,
            message=f"Session status: {session.status}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a cleaning session and associated files
    """
    try:
        session = file_cleaning_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clean up files and session
        file_cleaning_service.cleanup_expired_sessions(hours=0)  # Force cleanup for this session
        
        return JSONResponse(
            content={"message": f"Session {session_id} deleted successfully"},
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the cleaning service
    """
    try:
        # Basic health check
        active_sessions = len(file_cleaning_service.sessions)
        
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "file_cleaning",
                "active_sessions": active_sessions,
                "max_file_size_mb": CleaningConfig.MAX_FILE_SIZE / (1024 * 1024),
                "supported_extensions": CleaningConfig.SUPPORTED_EXTENSIONS
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=500
        )


@router.post("/cleanup-expired")
async def cleanup_expired_sessions():
    """
    Manually trigger cleanup of expired sessions
    Admin endpoint for maintenance
    """
    try:
        file_cleaning_service.cleanup_expired_sessions()
        
        return JSONResponse(
            content={"message": "Expired sessions cleaned up successfully"},
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# Export router
file_cleaning_router = router
