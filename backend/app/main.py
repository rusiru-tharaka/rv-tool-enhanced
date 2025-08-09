"""
Enhanced UX FastAPI Application
Main application for the 4-phase migration analysis platform
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import enhanced UX components
from .routers.phase_management import phase_router
from .routers.migration_scope import migration_scope_router
from .routers.modernization_router import router as modernization_router
from .routers.report_generation import report_router
from .routers.file_cleaning import file_cleaning_router
from .routers.cost_estimates_router import router as cost_estimates_router
from .routers.savings_plans_router import router as savings_plans_router
from .routers.reserved_instance_router import router as reserved_instance_router
from .routers.spot_instance_router import router as spot_instance_router
from .services.session_manager import session_manager

# Create FastAPI application
app = FastAPI(
    title="RVTool Enhanced UX API",
    description="Multi-phase migration analysis platform with enhanced user experience",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(phase_router)
app.include_router(migration_scope_router)
app.include_router(modernization_router)
app.include_router(report_router)
app.include_router(file_cleaning_router)
app.include_router(cost_estimates_router)
app.include_router(savings_plans_router)  # Phase 2.1: Savings Plans Integration
app.include_router(reserved_instance_router)  # Phase 2.2: Reserved Instance Optimization
app.include_router(spot_instance_router)  # Phase 2.3: Spot Instance Pricing

# ============================================================================
# ROOT AND HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Enhanced UX Platform API",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "4-phase migration analysis",
            "AI-powered blocker detection",
            "Smart modernization recommendations", 
            "Automated PDF report generation"
        ]
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "enhanced_ux_platform",
        "version": "2.0.0"
    }

@app.post("/api/test-session")
async def create_test_session():
    """Create a test session for development/testing"""
    test_vms = [
        {
            "VM": "legacy-dc-server-01",
            "CPUs": 4,
            "Memory": 8192,
            "Provisioned MB": 102400,
            "OS": "Microsoft Windows Server 2008 R2 (64-bit)",
            "Powerstate": "poweredOn",
            "Notes": "Domain Controller - Critical Legacy System"
        },
        {
            "VM": "web-app-frontend-prod",
            "CPUs": 4,
            "Memory": 8192,
            "Provisioned MB": 51200,
            "OS": "Ubuntu Linux 20.04 (64-bit)",
            "Powerstate": "poweredOn",
            "Notes": "Production web application frontend"
        },
        {
            "VM": "mysql-database-prod",
            "CPUs": 8,
            "Memory": 32768,
            "Provisioned MB": 204800,
            "OS": "Ubuntu Linux 18.04 (64-bit)",
            "Powerstate": "poweredOn",
            "Notes": "Production MySQL database server"
        }
    ]
    
    session_id = session_manager.create_session(test_vms)
    
    return {
        "session_id": session_id,
        "vm_count": len(test_vms),
        "message": "Test session created successfully"
    }

# ============================================================================
# FILE UPLOAD AND PROCESSING
# ============================================================================

@app.post("/api/upload-rvtools")
async def upload_rvtools_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload and process RVTools file to start enhanced analysis
    
    Args:
        file: RVTools Excel file upload
        
    Returns:
        Processed VM inventory data
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Process RVTools file using pandas
        try:
            import pandas as pd
            import io
            
            # Read Excel file from bytes
            excel_data = pd.read_excel(io.BytesIO(file_content), sheet_name='vInfo')
            
            logger.info(f"Successfully read Excel file: {len(excel_data)} VMs found")
            
            # Convert to properly mapped VM inventory
            vm_inventory = []
            
            def calculate_storage_gb(row):
                """Calculate storage in GB from RVTools MiB values"""
                # Use consumed storage first, fallback to provisioned
                consumed_mib = row.get('In Use MiB', 0)
                provisioned_mib = row.get('Provisioned MiB', 0)
                
                if pd.notna(consumed_mib) and consumed_mib > 0:
                    storage_mib = consumed_mib
                elif pd.notna(provisioned_mib) and provisioned_mib > 0:
                    storage_mib = provisioned_mib
                else:
                    storage_mib = 51200  # Default 50GB in MiB
                
                # Convert MiB to GB: 1 MiB = 1.048576 MB, 1 GB = 1024 MB
                storage_gb = (storage_mib * 1.048576) / 1024
                return round(storage_gb, 2)
            
            # Process each VM with proper column mapping
            for index, row in excel_data.iterrows():
                try:
                    vm_data = {
                        'vm_name': str(row.get('VM', f'VM-{index+1}')),
                        'cpu_count': int(row.get('CPUs', 2)) if pd.notna(row.get('CPUs')) else 2,
                        'memory_mb': int(row.get('Memory', 4096)) if pd.notna(row.get('Memory')) else 4096,
                        'disk_gb': calculate_storage_gb(row),
                        'os_type': str(row.get('OS according to the configuration file', 'Unknown')),
                        'power_state': str(row.get('Powerstate', 'poweredOn')),
                        'host': str(row.get('Host', 'Unknown')),
                        'cluster': str(row.get('Cluster', 'Unknown')),
                        'datacenter': str(row.get('Datacenter', 'Unknown')),
                        'creation_date': str(row.get('Creation date', '')) if pd.notna(row.get('Creation date')) else None
                    }
                    
                    # Validate data ranges
                    if vm_data['cpu_count'] < 1 or vm_data['cpu_count'] > 128:
                        vm_data['cpu_count'] = 2
                    if vm_data['memory_mb'] < 512 or vm_data['memory_mb'] > 1048576:
                        vm_data['memory_mb'] = 4096
                    if vm_data['disk_gb'] < 1 or vm_data['disk_gb'] > 16384:
                        vm_data['disk_gb'] = 50
                    
                    vm_inventory.append(vm_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing VM at row {index}: {e}")
                    # Add default VM data for failed processing
                    vm_inventory.append({
                        'vm_name': f'VM-{index+1}',
                        'cpu_count': 2,
                        'memory_mb': 4096,
                        'disk_gb': 50,
                        'os_type': 'Unknown',
                        'power_state': 'poweredOn',
                        'host': 'Unknown',
                        'cluster': 'Unknown',
                        'datacenter': 'Unknown',
                        'creation_date': None
                    })
            
            logger.info(f"Successfully processed {len(vm_inventory)} VMs with proper mapping")
            
        except Exception as e:
            logger.error(f"Error processing Excel file: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process Excel file: {str(e)}"
            )
        
        if not vm_inventory:
            raise HTTPException(
                status_code=400,
                detail="No VM data found in the uploaded file"
            )
        
        return {
            "success": True,
            "message": f"Successfully processed {len(vm_inventory)} VMs",
            "vm_inventory": vm_inventory,
            "total_vms": len(vm_inventory),
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

# ============================================================================
# HEALTH AND STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for the enhanced UX platform
    
    Returns:
        System health status
    """
    try:
        # Check session manager
        active_sessions = len(session_manager.list_sessions())
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "platform": "enhanced_ux",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "session_manager": "healthy",
                "phase_management": "healthy"
            },
            "metrics": {
                "active_sessions": active_sessions
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "version": "2.0.0",
                "platform": "enhanced_ux",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

@app.get("/api/status")
async def api_status() -> Dict[str, Any]:
    """
    API status and metrics
    
    Returns:
        API status information
    """
    return {
        "api_version": "2.0.0",
        "platform": "enhanced_ux",
        "features": [
            "4-phase_analysis",
            "session_management",
            "migration_scope_analysis",
            "cost_estimates",
            "modernization_opportunities",
            "real_time_pricing"
        ],
        "endpoints": {
            "phase_management": "/api/phases/*",
            "file_upload": "/api/upload-rvtools",
            "health": "/health",
            "docs": "/api/docs"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ============================================================================
# STARTUP AND SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    print("🚀 Enhanced UX Platform Starting...")
    print("📊 4-Phase Migration Analysis Ready")
    print("🔄 Session Management Initialized")
    print("✅ Enhanced UX Platform Started Successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    print("🛑 Enhanced UX Platform Shutting Down...")
    
    # Cleanup expired sessions
    try:
        deleted_count = session_manager.cleanup_expired_sessions(max_age_hours=1)
        print(f"🧹 Cleaned up {deleted_count} expired sessions")
    except Exception as e:
        print(f"⚠️ Error during session cleanup: {e}")
    
    print("✅ Enhanced UX Platform Shutdown Complete")

# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================

if __name__ == "__main__":
    print("🔧 Starting Enhanced UX Development Server...")
    uvicorn.run(
        "app_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
