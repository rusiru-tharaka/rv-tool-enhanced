"""
Migration Scope Router
API endpoints for migration scope analysis and blocker management
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import models and services
from ..models.core_models import (
        MigrationScopeAnalysis,
        MigrationBlocker,
        MigrationBlockerSeverity,
        PaginatedResponse
    )
from ..services.session_manager import session_manager
from ..services.migration_scope_service import migration_scope_service

# Create router
migration_scope_router = APIRouter(prefix="/api/migration-scope", tags=["Migration Scope"])

@migration_scope_router.post("/analyze/{session_id}")
async def analyze_migration_scope(session_id: str) -> MigrationScopeAnalysis:
    """
    Perform comprehensive migration scope analysis
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Complete migration scope analysis including blockers, insights, and classifications
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Perform migration scope analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        # Store analysis results for cross-phase integration
        analysis_dict = analysis.dict() if hasattr(analysis, 'dict') else analysis.__dict__
        session_manager.store_migration_scope_analysis(session_id, analysis_dict)
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze migration scope: {str(e)}"
        )

@migration_scope_router.get("/blockers/{session_id}")
async def get_migration_blockers(
    session_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for VM names or descriptions"),
    severity: Optional[MigrationBlockerSeverity] = Query(None, description="Filter by severity level")
) -> Dict[str, Any]:
    """
    Get paginated migration blockers with search and filtering
    
    Args:
        session_id: Analysis session identifier
        page: Page number (1-based)
        page_size: Number of items per page
        search: Optional search term
        severity: Optional severity filter
        
    Returns:
        Paginated list of migration blockers
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        blockers = analysis.migration_blockers
        
        # Apply severity filter
        if severity:
            blockers = [b for b in blockers if b.severity == severity]
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            blockers = [
                b for b in blockers 
                if search_lower in b.vm_name.lower() 
                or search_lower in b.description.lower()
                or search_lower in b.issue_type.lower()
                or search_lower in b.remediation.lower()
            ]
        
        # Apply pagination
        total_count = len(blockers)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_blockers = blockers[start_idx:end_idx]
        
        return {
            "blockers": paginated_blockers,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration blockers: {str(e)}"
        )

@migration_scope_router.get("/blockers/{session_id}/summary")
async def get_blockers_summary(session_id: str) -> Dict[str, Any]:
    """
    Get summary of migration blockers by severity
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Summary of blockers by severity level
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        # Count blockers by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for blocker in analysis.migration_blockers:
            severity_counts[blocker.severity.value] += 1
        
        return {
            "total_blockers": len(analysis.migration_blockers),
            "severity_breakdown": severity_counts,
            "complexity_score": analysis.complexity_score,
            "estimated_timeline_months": analysis.estimated_timeline_months
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get blockers summary: {str(e)}"
        )

@migration_scope_router.get("/out-of-scope/{session_id}")
async def get_out_of_scope_items(
    session_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category")
) -> Dict[str, Any]:
    """
    Get paginated out-of-scope items
    
    Args:
        session_id: Analysis session identifier
        page: Page number (1-based)
        page_size: Number of items per page
        category: Optional category filter
        
    Returns:
        Paginated list of out-of-scope items
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        out_of_scope_items = analysis.out_of_scope_items
        
        # Apply category filter
        if category:
            out_of_scope_items = [item for item in out_of_scope_items if item.category == category]
        
        # Apply pagination
        total_count = len(out_of_scope_items)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = out_of_scope_items[start_idx:end_idx]
        
        return {
            "items": paginated_items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get out-of-scope items: {str(e)}"
        )

@migration_scope_router.get("/workload-classifications/{session_id}")
async def get_workload_classifications(session_id: str) -> Dict[str, Any]:
    """
    Get workload classifications for the session
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Workload classifications with VM counts and percentages
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        return {
            "classifications": analysis.workload_classifications,
            "total_vms": analysis.total_vms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workload classifications: {str(e)}"
        )

@migration_scope_router.get("/infrastructure-insights/{session_id}")
async def get_infrastructure_insights(session_id: str) -> Dict[str, Any]:
    """
    Get infrastructure insights for the session
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Comprehensive infrastructure insights
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        return {
            "insights": analysis.infrastructure_insights,
            "total_vms": analysis.total_vms,
            "complexity_score": analysis.complexity_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get infrastructure insights: {str(e)}"
        )

@migration_scope_router.get("/export/{session_id}")
async def export_migration_scope_analysis(session_id: str) -> Dict[str, Any]:
    """
    Export complete migration scope analysis for reporting
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Complete migration scope analysis data
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration analysis
        analysis = await migration_scope_service.analyze_migration_scope(
            session_id, session.vm_inventory
        )
        
        return {
            "analysis": analysis,
            "export_timestamp": datetime.utcnow().isoformat(),
            "session_info": {
                "session_id": session_id,
                "created_at": session.created_at.isoformat(),
                "total_vms": len(session.vm_inventory)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export migration scope analysis: {str(e)}"
        )

@migration_scope_router.get("/health")
async def migration_scope_health() -> Dict[str, Any]:
    """
    Health check for migration scope service
    
    Returns:
        Service health status
    """
    try:
        return {
            "status": "healthy",
            "service": "migration_scope",
            "timestamp": datetime.utcnow().isoformat(),
            "features": [
                "blocker_detection",
                "workload_classification",
                "infrastructure_insights",
                "complexity_scoring",
                "timeline_estimation"
            ]
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "migration_scope",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@migration_scope_router.post("/store-results/{session_id}")
async def store_migration_scope_results(session_id: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store Migration Scope analysis results for cross-phase integration
    
    Args:
        session_id: Analysis session identifier
        analysis_data: Migration Scope analysis results from frontend
        
    Returns:
        Storage confirmation
    """
    try:
        # Store the analysis results
        success = session_manager.store_migration_scope_analysis(session_id, analysis_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "message": "Migration Scope analysis results stored successfully",
            "session_id": session_id,
            "stored_items": {
                "total_vms": analysis_data.get("total_vms", 0),
                "out_of_scope_items": len(analysis_data.get("out_of_scope_items", [])),
                "migration_blockers": len(analysis_data.get("migration_blockers", [])),
                "workload_classifications": len(analysis_data.get("workload_classifications", []))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store Migration Scope results: {str(e)}"
        )
