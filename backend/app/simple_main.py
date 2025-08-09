"""
Simplified FastAPI Application for RVTool Enhanced UX
Basic version that processes real RVTools data without complex dependencies
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import pandas as pd
import io
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for session data
session_storage: Dict[str, Dict[str, Any]] = {}

# Create FastAPI application
app = FastAPI(
    title="RVTool Enhanced UX API",
    description="AI-powered platform for analyzing VMware RVTools exports and providing AWS migration cost optimization recommendations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RVTool Enhanced UX API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for ECS health checks
    """
    try:
        # Basic health check without database dependency
        return {
            "status": "healthy",
            "version": "2.0.0",
            "platform": "enhanced_ux",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "api": "healthy",
                "database": "configured" if os.getenv("DATABASE_HOST") else "not_configured",
                "s3": "configured" if os.getenv("S3_BUCKET_NAME") else "not_configured"
            },
            "config": {
                "database_host": os.getenv("DATABASE_HOST", "not_set"),
                "database_username": "configured" if os.getenv("DATABASE_USERNAME") else "not_set",
                "database_password": "configured" if os.getenv("DATABASE_PASSWORD") else "not_set",
                "s3_bucket": os.getenv("S3_BUCKET_NAME", "not_set"),
                "redis_host": os.getenv("REDIS_HOST", "not_set"),
                "aws_region": os.getenv("AWS_DEFAULT_REGION", "not_set")
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "version": "2.0.0",
            "platform": "enhanced_ux",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/health")
async def api_health_check():
    """Alternative health check endpoint"""
    return await health_check()

# ============================================================================
# RVTOOLS DATA PROCESSING
# ============================================================================

def process_rvtools_data(file_content: bytes) -> List[Dict[str, Any]]:
    """Process RVTools Excel file and extract VM data"""
    try:
        # Read Excel file
        excel_data = pd.read_excel(io.BytesIO(file_content), sheet_name='vInfo')
        
        vm_inventory = []
        for _, row in excel_data.iterrows():
            # Handle different possible column names for storage
            storage_mb = 0
            if 'Provisioned MiB' in excel_data.columns:
                storage_mb = float(row.get('Provisioned MiB', 50000))
            elif 'Provisioned MB' in excel_data.columns:
                storage_mb = float(row.get('Provisioned MB', 50000))
            elif 'Total disk capacity MiB' in excel_data.columns:
                storage_mb = float(row.get('Total disk capacity MiB', 50000))
            else:
                storage_mb = 50000  # Default fallback
            
            vm_data = {
                "vm_name": str(row.get('VM', 'Unknown')),
                "current_cpu": int(row.get('CPUs', 2)),
                "current_memory_gb": float(row.get('Memory', 4096)) / 1024,  # Convert MB to GB
                "current_storage_gb": storage_mb / 1024,  # Convert MiB to GB
                "operating_system": str(row.get('OS', 'linux')).lower(),
                "power_state": str(row.get('Powerstate', 'poweredOn')),
                "cluster": str(row.get('Cluster', 'default')),
                "host": str(row.get('Host', 'unknown'))
            }
            vm_inventory.append(vm_data)
        
        logger.info(f"Processed {len(vm_inventory)} VMs from RVTools file")
        return vm_inventory
        
    except Exception as e:
        logger.error(f"Error processing RVTools file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error processing RVTools file: {str(e)}")

def calculate_aws_costs(vm_inventory: List[Dict[str, Any]], tco_parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate AWS costs for VM inventory with proper RI and production/non-production handling"""
    
    # AWS instance type mapping based on CPU/Memory with RI pricing
    def get_instance_pricing(cpu: int, memory_gb: float, is_production: bool, ri_years: int = 3) -> tuple:
        """Get instance type and pricing based on production status and RI settings"""
        
        # Determine instance type based on CPU/Memory
        if cpu <= 1 and memory_gb <= 2:
            instance_type = "t3.micro"
            on_demand_hourly = 0.0104
        elif cpu <= 1 and memory_gb <= 4:
            instance_type = "t3.small"
            on_demand_hourly = 0.0208
        elif cpu <= 2 and memory_gb <= 8:
            instance_type = "t3.medium"
            on_demand_hourly = 0.0416
        elif cpu <= 2 and memory_gb <= 16:
            instance_type = "m5.large"
            on_demand_hourly = 0.096
        elif cpu <= 4 and memory_gb <= 16:
            instance_type = "m5.xlarge"
            on_demand_hourly = 0.192
        elif cpu <= 8 and memory_gb <= 32:
            instance_type = "m5.2xlarge"
            on_demand_hourly = 0.384
        elif cpu <= 16 and memory_gb <= 64:
            instance_type = "m5.4xlarge"
            on_demand_hourly = 0.768
        else:
            instance_type = "m5.8xlarge"
            on_demand_hourly = 1.536
        
        # Calculate monthly cost
        monthly_hours = 24 * 30  # 720 hours per month
        on_demand_monthly = on_demand_hourly * monthly_hours
        
        # Apply Reserved Instance pricing for production VMs
        if is_production and tco_parameters.get("production_pricing_model") == "reserved_instance":
            # RI discount rates (approximate)
            ri_discount_rates = {1: 0.25, 3: 0.40, 5: 0.50}  # 25%, 40%, 50% discount
            discount = ri_discount_rates.get(ri_years, 0.40)
            monthly_cost = on_demand_monthly * (1 - discount)
            pricing_plan = f"{ri_years}-Year Reserved Instance"
        else:
            monthly_cost = on_demand_monthly
            pricing_plan = "On-Demand"
        
        return instance_type, monthly_cost, pricing_plan
    
    def normalize_vm_data(vm: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize VM data structure to handle different formats"""
        # Handle both RVTools direct format and frontend session format
        normalized = {
            "vm_name": vm.get("vm_name") or vm.get("VM") or vm.get("name", "Unknown"),
            "current_cpu": vm.get("current_cpu") or vm.get("CPUs") or vm.get("cpu", 2),
            "current_memory_gb": vm.get("current_memory_gb") or (vm.get("Memory", 4096) / 1024 if vm.get("Memory") else 4),
            "current_storage_gb": vm.get("current_storage_gb") or (vm.get("Provisioned MB", 50000) / 1024 if vm.get("Provisioned MB") else 50),
            "operating_system": str(vm.get("operating_system") or vm.get("OS", "linux")).lower(),
            "power_state": str(vm.get("power_state") or vm.get("Powerstate", "poweredOn")).lower(),
            "cluster": str(vm.get("cluster") or vm.get("Cluster", "default")),
            "host": str(vm.get("host") or vm.get("Host", "unknown"))
        }
        
        # Ensure numeric values are properly converted
        try:
            normalized["current_cpu"] = int(normalized["current_cpu"])
        except (ValueError, TypeError):
            normalized["current_cpu"] = 2
            
        try:
            normalized["current_memory_gb"] = float(normalized["current_memory_gb"])
        except (ValueError, TypeError):
            normalized["current_memory_gb"] = 4.0
            
        try:
            normalized["current_storage_gb"] = float(normalized["current_storage_gb"])
        except (ValueError, TypeError):
            normalized["current_storage_gb"] = 50.0
        
        return normalized
    
    def classify_vm_environment(vm_name: str) -> str:
        """Classify VM as production or non-production based on naming patterns"""
        vm_name_lower = vm_name.lower()
        
        # Non-production indicators
        non_prod_patterns = ['dev', 'test', 'uat', 'staging', 'demo', 'sandbox', 'dr']
        for pattern in non_prod_patterns:
            if pattern in vm_name_lower:
                return "non-production"
        
        # Production indicators (or default to production if no clear indicator)
        prod_patterns = ['prod', 'production', 'live', 'prd']
        for pattern in prod_patterns:
            if pattern in vm_name_lower:
                return "production"
        
        # Default to production for safety (conservative approach)
        return "production"
    
    detailed_estimates = []
    total_infrastructure_cost = 0
    total_storage_cost = 0
    production_count = 0
    non_production_count = 0
    
    ri_years = tco_parameters.get("production_ri_years", 3)
    
    for vm in vm_inventory:
        # Normalize VM data to handle different formats
        normalized_vm = normalize_vm_data(vm)
        
        if normalized_vm.get('power_state', '').lower() not in ['poweredon', 'powered_on']:
            continue  # Skip powered off VMs
        
        # Classify VM environment
        environment = classify_vm_environment(normalized_vm['vm_name'])
        is_production = (environment == "production")
        
        if is_production:
            production_count += 1
        else:
            non_production_count += 1
            
        instance_type, monthly_cost, pricing_plan = get_instance_pricing(
            normalized_vm['current_cpu'], 
            normalized_vm['current_memory_gb'],
            is_production,
            ri_years
        )
        
        storage_cost = normalized_vm['current_storage_gb'] * 0.10  # $0.10/GB/month for EBS gp3
        
        vm_estimate = {
            "vm_name": normalized_vm['vm_name'],
            "current_cpu": normalized_vm['current_cpu'],
            "current_memory_gb": normalized_vm['current_memory_gb'],
            "current_storage_gb": normalized_vm['current_storage_gb'],
            "recommended_instance_type": instance_type,
            "base_instance_cost": monthly_cost,
            "storage_cost": storage_cost,
            "projected_monthly_cost": monthly_cost + storage_cost,
            "pricing_plan": pricing_plan,
            "environment": environment,
            "operating_system": normalized_vm['operating_system'],
            "region": tco_parameters.get("target_region", "us-east-1")
        }
        
        detailed_estimates.append(vm_estimate)
        total_infrastructure_cost += monthly_cost
        total_storage_cost += storage_cost
    
    # Apply network and observability costs
    network_percentage = tco_parameters.get("network_cost_percentage", 10)
    observability_percentage = tco_parameters.get("observability_cost_percentage", 5)
    
    if tco_parameters.get("include_network", True):
        network_cost = total_infrastructure_cost * (network_percentage / 100)
    else:
        network_cost = 0
        
    if tco_parameters.get("include_observability", True):
        observability_cost = total_infrastructure_cost * (observability_percentage / 100)
    else:
        observability_cost = 0
    
    total_monthly_cost = total_infrastructure_cost + total_storage_cost + network_cost + observability_cost
    
    return {
        "detailed_estimates": detailed_estimates,
        "cost_summary": {
            "infrastructure_monthly_cost": total_infrastructure_cost,
            "storage_monthly_cost": total_storage_cost,
            "network_monthly_cost": network_cost,
            "observability_monthly_cost": observability_cost,
            "total_monthly_cost": total_monthly_cost,
            "total_annual_cost": total_monthly_cost * 12,
            "five_year_tco": total_monthly_cost * 12 * 5,
            "yearly_tco": [total_monthly_cost * 12] * 5,
            "production_vms": production_count,
            "non_production_vms": non_production_count
        },
        "total_vms_analyzed": len(detailed_estimates)
    }

@app.post("/api/upload-rvtools")
async def upload_rvtools(file: UploadFile = File(...)):
    """Upload and process RVTools Excel file"""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
        
        # Read file content
        file_content = await file.read()
        
        # Process RVTools data
        vm_inventory = process_rvtools_data(file_content)
        
        # Create session
        session_id = str(uuid.uuid4())
        session_storage[session_id] = {
            "vm_inventory": vm_inventory,
            "created_at": datetime.now().isoformat(),
            "filename": file.filename
        }
        
        logger.info(f"Created session {session_id} with {len(vm_inventory)} VMs")
        
        return {
            "success": True,
            "message": "RVTools file processed successfully",
            "session_id": session_id,
            "vm_count": len(vm_inventory),
            "filename": file.filename,
            "vm_inventory": vm_inventory  # Add this so frontend doesn't fall back to client-side parsing
        }
        
    except Exception as e:
        logger.error(f"Error uploading RVTools file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/phases/start-analysis")
async def start_analysis(request_data: Dict[str, Any]):
    """Start analysis session with VM inventory"""
    try:
        vm_inventory = request_data.get("vm_inventory", [])
        
        if not vm_inventory:
            raise HTTPException(status_code=400, detail="VM inventory is required")
        
        # Create session
        session_id = str(uuid.uuid4())
        session_storage[session_id] = {
            "vm_inventory": vm_inventory,
            "created_at": datetime.now().isoformat(),
            "phase": "migration_scope"
        }
        
        logger.info(f"Started analysis session {session_id} with {len(vm_inventory)} VMs")
        
        return {
            "session_id": session_id,
            "phase": "migration_scope",
            "vm_count": len(vm_inventory),
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cost-estimates/analyze/{session_id}")
async def analyze_cost_estimates(session_id: str, tco_parameters: Optional[Dict[str, Any]] = None):
    """Analyze cost estimates for a session using real VM data"""
    try:
        if session_id not in session_storage:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = session_storage[session_id]
        vm_inventory = session_data.get("vm_inventory", [])
        
        if not vm_inventory:
            raise HTTPException(status_code=400, detail="No VM inventory found for session")
        
        # Use default TCO parameters if none provided
        if not tco_parameters:
            tco_parameters = {
                "target_region": "us-east-1",
                "production_pricing_model": "on_demand",
                "non_production_pricing_model": "on_demand",
                "network_cost_percentage": 10,
                "observability_cost_percentage": 5
            }
        
        logger.info(f"Analyzing costs for session {session_id} with {len(vm_inventory)} VMs")
        
        # Calculate AWS costs
        cost_analysis = calculate_aws_costs(vm_inventory, tco_parameters)
        
        # Build response
        response = {
            "session_id": session_id,
            "tco_parameters": tco_parameters,
            "cost_summary": cost_analysis["cost_summary"],
            "detailed_estimates": cost_analysis["detailed_estimates"],
            "total_vms_analyzed": cost_analysis["total_vms_analyzed"],
            "analysis_timestamp": datetime.now().isoformat(),
            "pricing_source": "real_aws_pricing_calculation"
        }
        
        logger.info(f"Cost analysis complete for session {session_id}: ${cost_analysis['cost_summary']['total_monthly_cost']:.2f}/month")
        
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing cost estimates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cost-estimates/regions")
async def get_aws_regions():
    """Get available AWS regions for cost estimation"""
    return {
        "success": True,
        "message": "AWS regions loaded successfully",
        "regions": [
            {"code": "us-east-1", "name": "US East (N. Virginia)", "display": "US East (N. Virginia)"},
            {"code": "us-east-2", "name": "US East (Ohio)", "display": "US East (Ohio)"},
            {"code": "us-west-1", "name": "US West (N. California)", "display": "US West (N. California)"},
            {"code": "us-west-2", "name": "US West (Oregon)", "display": "US West (Oregon)"},
            {"code": "eu-west-1", "name": "Europe (Ireland)", "display": "Europe (Ireland)"},
            {"code": "eu-central-1", "name": "Europe (Frankfurt)", "display": "Europe (Frankfurt)"}
        ],
        "total_regions": 6,
        "service": "simple_backend_real_data",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/migration-scope/store-results/{session_id}")
async def store_migration_scope_results(session_id: str, results: Dict[str, Any]):
    """Store migration scope analysis results"""
    try:
        if session_id not in session_storage:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Store the migration scope results in the session
        session_storage[session_id]["migration_scope_results"] = results
        
        logger.info(f"Stored migration scope results for session {session_id}")
        
        return {
            "success": True,
            "message": "Migration scope results stored successfully",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error storing migration scope results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BASIC API ENDPOINTS
# ============================================================================

@app.get("/api/status")
async def get_status():
    """Get API status"""
    return {
        "api": "RVTool Enhanced UX",
        "status": "operational",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "api_health": "/api/health",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/api/info")
async def get_info():
    """Get application information"""
    return {
        "name": "RVTool Enhanced UX Platform",
        "description": "AI-powered platform for analyzing VMware RVTools exports and providing AWS migration cost optimization recommendations",
        "version": "2.0.0",
        "features": [
            "4-Phase Migration Analysis",
            "Cost Optimization Recommendations", 
            "Reserved Instance Planning",
            "Savings Plans Integration",
            "Spot Instance Analysis",
            "PDF Report Generation"
        ],
        "environment": {
            "database_configured": bool(os.getenv("DATABASE_HOST")),
            "s3_configured": bool(os.getenv("S3_BUCKET_NAME")),
            "redis_configured": bool(os.getenv("REDIS_HOST")),
            "aws_region": os.getenv("AWS_DEFAULT_REGION", "not_set")
        }
    }

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 RVTool Enhanced UX API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Database Host: {os.getenv('DATABASE_HOST', 'not_set')}")
    logger.info(f"S3 Bucket: {os.getenv('S3_BUCKET_NAME', 'not_set')}")
    logger.info(f"Redis Host: {os.getenv('REDIS_HOST', 'not_set')}")
    logger.info(f"AWS Region: {os.getenv('AWS_DEFAULT_REGION', 'not_set')}")
    logger.info("✅ RVTool Enhanced UX API startup complete!")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 RVTool Enhanced UX API shutting down...")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
