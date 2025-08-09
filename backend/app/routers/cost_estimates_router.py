"""
Cost Estimates API Router
RESTful API endpoints for cost estimation functionality
Provides comprehensive TCO analysis and cost calculation endpoints
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from ..services.session_manager import session_manager
from ..services.cost_estimates_service import cost_estimates_service
from ..services.aws_pricing_service import AWSRegionConfig
from ..models.core_models import (
    TCOParameters, 
    CostEstimatesAnalysis, 
    VMCostEstimate,
    CostSummary,
    PaginatedResponse,
    ErrorResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/cost-estimates", tags=["Cost Estimates"])

@router.post("/analyze/{session_id}")
async def analyze_cost_estimates(
    session_id: str,
    tco_parameters: Optional[TCOParameters] = None
) -> CostEstimatesAnalysis:
    """
    Perform comprehensive cost analysis for VM inventory
    
    **Parameters:**
    - session_id: Unique session identifier
    - tco_parameters: TCO calculation parameters (optional, uses defaults if not provided)
    
    **Returns:**
    - Complete cost estimates analysis with detailed VM costs and summary
    
    **Example:**
    ```json
    {
        "target_region": "us-east-1",
        "production_ri_years": 3,
        "include_network": true,
        "include_observability": true,
        "network_cost_percentage": 10.0,
        "observability_cost_percentage": 5.0
    }
    ```
    """
    try:
        logger.info(f"Starting cost analysis for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        if not session.vm_inventory:
            raise HTTPException(status_code=400, detail="No VM inventory data found in session")
        
        # Use default parameters if not provided
        if tco_parameters is None:
            tco_parameters = TCOParameters()
        
        # Perform cost analysis
        analysis = await cost_estimates_service.analyze_cost_estimates(
            session_id=session_id,
            vm_inventory=session.vm_inventory,
            tco_parameters=tco_parameters
        )
        
        # Update session with cost analysis results
        session_manager.update_session_data(session_id, "cost_estimates_analysis", analysis.dict())
        
        # Advance session to next phase
        session_manager.advance_phase(session_id)
        
        logger.info(f"Cost analysis completed for session {session_id}: ${analysis.cost_summary.total_monthly_cost:.2f}/month")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost analysis failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Cost analysis failed: {str(e)}")

@router.get("/detailed/{session_id}")
async def get_detailed_cost_estimates(
    session_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    search: Optional[str] = Query(None, description="Search VM names"),
    instance_family: Optional[str] = Query(None, description="Filter by instance family"),
    pricing_plan: Optional[str] = Query(None, description="Filter by pricing plan"),
    sort_by: str = Query("total_monthly_cost", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
) -> PaginatedResponse:
    """
    Get detailed cost estimates with pagination, search, and filtering
    
    **Parameters:**
    - session_id: Session identifier
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 1000)
    - search: Search VM names (optional)
    - instance_family: Filter by instance family (optional)
    - pricing_plan: Filter by pricing plan (optional)
    - sort_by: Sort field (default: total_monthly_cost)
    - sort_order: Sort order - asc or desc (default: desc)
    
    **Returns:**
    - Paginated list of detailed VM cost estimates
    """
    try:
        logger.info(f"Getting detailed cost estimates for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get cost analysis from session data
        cost_analysis_data = session_manager.get_session_data(session_id, "cost_estimates_analysis")
        if not cost_analysis_data:
            raise HTTPException(status_code=404, detail="Cost analysis not found. Run analysis first.")
        
        # Parse cost analysis
        analysis = CostEstimatesAnalysis(**cost_analysis_data)
        detailed_estimates = analysis.detailed_estimates
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            detailed_estimates = [
                estimate for estimate in detailed_estimates
                if search_lower in estimate.vm_name.lower()
            ]
        
        # Apply instance family filter
        if instance_family:
            detailed_estimates = [
                estimate for estimate in detailed_estimates
                if estimate.recommended_instance_family == instance_family
            ]
        
        # Apply pricing plan filter
        if pricing_plan:
            detailed_estimates = [
                estimate for estimate in detailed_estimates
                if estimate.pricing_plan == pricing_plan
            ]
        
        # Sort results
        reverse_sort = sort_order == "desc"
        if sort_by == "vm_name":
            detailed_estimates.sort(key=lambda x: x.vm_name, reverse=reverse_sort)
        elif sort_by == "total_monthly_cost":
            detailed_estimates.sort(key=lambda x: x.total_monthly_cost, reverse=reverse_sort)
        elif sort_by == "ec2_monthly_cost":
            detailed_estimates.sort(key=lambda x: x.ec2_monthly_cost, reverse=reverse_sort)
        elif sort_by == "recommended_instance_size":
            detailed_estimates.sort(key=lambda x: x.recommended_instance_size, reverse=reverse_sort)
        
        # Calculate pagination
        total_count = len(detailed_estimates)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_items = detailed_estimates[start_idx:end_idx]
        
        logger.info(f"Retrieved {len(paginated_items)} detailed estimates (page {page}/{total_pages})")
        
        return PaginatedResponse(
            items=paginated_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get detailed estimates for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get detailed estimates: {str(e)}")

@router.get("/summary/{session_id}")
async def get_cost_summary(session_id: str) -> Dict:
    """
    Get cost summary and breakdowns for a session
    
    **Returns:**
    - Cost summary with breakdowns by workload type and instance family
    """
    try:
        logger.info(f"Getting cost summary for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get cost analysis from session data
        cost_analysis_data = session_manager.get_session_data(session_id, "cost_estimates_analysis")
        if not cost_analysis_data:
            raise HTTPException(status_code=404, detail="Cost analysis not found. Run analysis first.")
        
        # Parse cost analysis
        analysis = CostEstimatesAnalysis(**cost_analysis_data)
        
        # Get breakdowns
        workload_breakdown = cost_estimates_service.get_cost_breakdown_by_workload(analysis)
        family_breakdown = cost_estimates_service.get_cost_breakdown_by_instance_family(analysis)
        
        summary = {
            "session_id": session_id,
            "cost_summary": analysis.cost_summary.dict(),
            "tco_parameters": analysis.tco_parameters.dict(),
            "total_vms_analyzed": analysis.total_vms_analyzed,
            "workload_breakdown": workload_breakdown,
            "instance_family_breakdown": family_breakdown,
            "analysis_timestamp": session.updated_at.isoformat()
        }
        
        logger.info(f"Cost summary retrieved for session {session_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cost summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost summary: {str(e)}")

@router.put("/parameters/{session_id}")
async def update_tco_parameters(
    session_id: str,
    tco_parameters: TCOParameters
) -> CostEstimatesAnalysis:
    """
    Update TCO parameters and recalculate costs
    
    **Parameters:**
    - session_id: Session identifier
    - tco_parameters: New TCO parameters
    
    **Returns:**
    - Updated cost estimates analysis
    """
    try:
        logger.info(f"Updating TCO parameters for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get existing cost analysis
        cost_analysis_data = session_manager.get_session_data(session_id, "cost_estimates_analysis")
        if not cost_analysis_data:
            raise HTTPException(status_code=404, detail="Cost analysis not found. Run analysis first.")
        
        # Parse existing analysis
        existing_analysis = CostEstimatesAnalysis(**cost_analysis_data)
        
        # Recalculate with new parameters
        updated_analysis = await cost_estimates_service.recalculate_with_parameters(
            session_id=session_id,
            existing_analysis=existing_analysis,
            new_parameters=tco_parameters
        )
        
        # Update session with new analysis
        session_manager.update_session_data(session_id, "cost_estimates_analysis", updated_analysis.dict())
        
        logger.info(f"TCO parameters updated for session {session_id}: ${updated_analysis.cost_summary.total_monthly_cost:.2f}/month")
        return updated_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update TCO parameters for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update TCO parameters: {str(e)}")

@router.get("/export/{session_id}")
async def export_cost_estimates(
    session_id: str,
    format: str = Query("json", regex="^(json|csv)$", description="Export format")
) -> JSONResponse:
    """
    Export cost estimates data
    
    **Parameters:**
    - session_id: Session identifier
    - format: Export format - json or csv (default: json)
    
    **Returns:**
    - Exported cost estimates data
    """
    try:
        logger.info(f"Exporting cost estimates for session: {session_id} in {format} format")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get cost analysis from session data
        cost_analysis_data = session_manager.get_session_data(session_id, "cost_estimates_analysis")
        if not cost_analysis_data:
            raise HTTPException(status_code=404, detail="Cost analysis not found. Run analysis first.")
        
        # Parse cost analysis
        analysis = CostEstimatesAnalysis(**cost_analysis_data)
        
        if format == "json":
            export_data = {
                "session_id": session_id,
                "export_timestamp": session.updated_at.isoformat(),
                "cost_summary": analysis.cost_summary.dict(),
                "tco_parameters": analysis.tco_parameters.dict(),
                "detailed_estimates": [estimate.dict() for estimate in analysis.detailed_estimates],
                "total_vms_analyzed": analysis.total_vms_analyzed
            }
            
            return JSONResponse(
                content=export_data,
                headers={"Content-Disposition": f"attachment; filename=cost_estimates_{session_id}.json"}
            )
        
        elif format == "csv":
            # Create enhanced CSV content with Operating System and Pricing Plan
            csv_lines = []
            csv_lines.append("VM Name,CPU Cores,Memory (GB),Storage (GB),Recommended Instance Type,Instance Cost ($),Storage Cost ($),Total Monthly Cost ($),Pricing Plan,Operating System,Environment")
            
            for estimate in analysis.detailed_estimates:
                # Determine environment based on workload type
                environment = "Production" if estimate.workload_type.lower() == "production" else "Non-Production"
                
                # Get operating system from VM data if available
                operating_system = "Linux"  # Default
                
                # Try to get the actual OS from the original VM data
                try:
                    # Get the original VM data from session
                    vm_inventory = session.vm_inventory
                    matching_vm = next((vm for vm in vm_inventory if vm.get('vm_name') == estimate.vm_name), None)
                    
                    if matching_vm:
                        # Use the OS detection logic from cost estimates service
                        from ..services.cost_estimates_service import cost_estimates_service
                        operating_system = cost_estimates_service._detect_vm_os_type(matching_vm)
                        
                        # Convert OS type to display format
                        os_display_map = {
                            'linux': 'Linux',
                            'windows': 'Windows',
                            'rhel': 'Red Hat Enterprise Linux',
                            'suse': 'SUSE Linux',
                            'ubuntu_pro': 'Ubuntu Pro'
                        }
                        operating_system = os_display_map.get(operating_system, operating_system.title())
                        
                except Exception as e:
                    logger.warning(f"Could not determine OS for VM {estimate.vm_name}: {e}")
                    operating_system = "Linux"  # Fallback
                
                csv_lines.append(
                    f"{estimate.vm_name},{estimate.current_cpu},{estimate.current_ram_gb},"
                    f"{estimate.current_storage_gb},{estimate.recommended_instance_size},"
                    f"{estimate.ec2_monthly_cost:.2f},{estimate.storage_monthly_cost:.2f},"
                    f"{estimate.total_monthly_cost:.2f},{estimate.pricing_plan},{operating_system},{environment}"
                )
            
            csv_content = "\n".join(csv_lines)
            
            return JSONResponse(
                content={"csv_data": csv_content},
                headers={"Content-Disposition": f"attachment; filename=vm-cost-estimates-{session_id}.csv"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export cost estimates for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export cost estimates: {str(e)}")

@router.get("/pricing-info/{region}")
async def get_pricing_info(
    region: str,
    instance_types: Optional[str] = Query(None, description="Comma-separated instance types")
) -> Dict:
    """
    Get current AWS pricing information for specific region and instance types
    
    **Parameters:**
    - region: AWS region code
    - instance_types: Comma-separated list of instance types (optional)
    
    **Returns:**
    - Current pricing information
    """
    try:
        logger.info(f"Getting pricing info for region: {region}")
        
        if instance_types:
            # Get pricing for specific instance types
            instance_type_list = [t.strip() for t in instance_types.split(",")]
            pricing_data = await cost_estimates_service.pricing_service.get_multiple_instance_pricing(
                instance_type_list, region
            )
            
            pricing_info = {}
            for instance_type, pricing in pricing_data.items():
                pricing_info[instance_type] = {
                    "on_demand_hourly": pricing.on_demand_hourly,
                    "reserved_1yr_hourly": pricing.reserved_1yr_hourly,
                    "reserved_3yr_hourly": pricing.reserved_3yr_hourly,
                    "vcpu": pricing.vcpu,
                    "memory_gb": pricing.memory_gb,
                    "currency": pricing.currency
                }
        else:
            # Get general pricing information
            storage_pricing = await cost_estimates_service.pricing_service.get_storage_pricing("gp3", region)
            
            pricing_info = {
                "region": region,
                "storage_pricing": {
                    "gp3_per_gb_month": storage_pricing.price_per_gb_month,
                    "currency": storage_pricing.currency
                },
                "cache_stats": cost_estimates_service.pricing_service.get_cache_stats()
            }
        
        logger.info(f"Pricing info retrieved for region {region}")
        return pricing_info
        
    except Exception as e:
        logger.error(f"Failed to get pricing info for region {region}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pricing info: {str(e)}")

@router.get("/health")
async def cost_estimates_health() -> Dict:
    """
    Health check endpoint for cost estimates service
    
    **Returns:**
    - Service health status and statistics
    """
    try:
        # Test AWS pricing service connection
        test_pricing = await cost_estimates_service.pricing_service.get_instance_pricing("m5.large", "us-east-1")
        
        health_status = {
            "service": "cost_estimates",
            "status": "healthy",
            "timestamp": session_manager._get_current_time().isoformat(),
            "aws_pricing_service": "connected" if test_pricing else "disconnected",
            "cache_stats": cost_estimates_service.pricing_service.get_cache_stats(),
            "instance_families": len(cost_estimates_service.recommendation_service.get_instance_families_summary())
        }
        
        logger.info("Cost estimates service health check passed")
        return health_status
        
    except Exception as e:
        logger.error(f"Cost estimates service health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@router.get("/regions")
def get_supported_regions():
    """
    Get all supported AWS regions for cost estimation
    
    **Returns:**
    - List of all supported AWS regions with metadata
    """
    try:
        logger.info("Fetching supported AWS regions (simple version)")
        
        # Simple hardcoded regions list for immediate fix
        regions = [
            {"code": "us-east-1", "name": "US East (N. Virginia)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "us-east-2", "name": "US East (Ohio)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "us-west-1", "name": "US West (N. California)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "us-west-2", "name": "US West (Oregon)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "eu-west-1", "name": "Europe (Ireland)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "eu-west-2", "name": "Europe (London)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "eu-west-3", "name": "Europe (Paris)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "eu-central-1", "name": "Europe (Frankfurt)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "eu-north-1", "name": "Europe (Stockholm)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "ap-northeast-1", "name": "Asia Pacific (Tokyo)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "ap-northeast-2", "name": "Asia Pacific (Seoul)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "ap-southeast-1", "name": "Asia Pacific (Singapore)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "ap-southeast-2", "name": "Asia Pacific (Sydney)", "pricing_tier": "premium", "supports_savings_plans": True},
            {"code": "ap-south-1", "name": "Asia Pacific (Mumbai)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "ca-central-1", "name": "Canada (Central)", "pricing_tier": "standard", "supports_savings_plans": True},
            {"code": "sa-east-1", "name": "South America (São Paulo)", "pricing_tier": "premium", "supports_savings_plans": True}
        ]
        
        logger.info(f"Retrieved {len(regions)} supported regions")
        return {
            "regions": regions,
            "total_count": len(regions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get supported regions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve regions: {str(e)}")

# Add router tags and metadata
router.tags = ["Cost Estimates"]
