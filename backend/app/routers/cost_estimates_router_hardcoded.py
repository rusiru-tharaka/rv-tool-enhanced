"""
Cost Estimates API Router - Hardcoded Parameters Version
Uses hardcoded 3-Year RI for Production and On-Demand 50% for Non-Production
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from ..services.session_manager import session_manager
# 🔧 HARDCODED: Use our hardcoded service instead of original
from ..services.cost_estimates_service_hardcoded import cost_estimates_service_hardcoded
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
router = APIRouter(prefix="/api/cost-estimates", tags=["Cost Estimates - Hardcoded"])

@router.post("/analyze/{session_id}")
async def analyze_cost_estimates_hardcoded(
    session_id: str,
    tco_parameters: Optional[TCOParameters] = None
) -> CostEstimatesAnalysis:
    """
    🔧 HARDCODED VERSION: Perform comprehensive cost analysis with hardcoded parameters
    - Production: 3-Year Reserved Instance (No Upfront)
    - Non-Production: On-Demand with 50% utilization
    """
    logger.info(f"🔧 HARDCODED: Starting cost analysis for session {session_id}")
    
    try:
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        if not session.vm_inventory:
            raise HTTPException(status_code=400, detail="No VM inventory data found in session")
        
        # Use default parameters if not provided (will be overridden by hardcoded values anyway)
        if tco_parameters is None:
            tco_parameters = TCOParameters()
        
        logger.info(f"🎯 HARDCODED: Processing {len(session.vm_inventory)} VMs with hardcoded parameters")
        
        # 🔧 HARDCODED: Use our hardcoded service
        analysis = await cost_estimates_service_hardcoded.analyze_cost_estimates(
            session_id=session_id,
            vm_inventory=session.vm_inventory,
            tco_parameters=tco_parameters  # Will be overridden with hardcoded values
        )
        
        # Store analysis in session
        session.cost_analysis = analysis
        session_manager.update_session(session_id, session)
        
        logger.info(f"✅ HARDCODED: Cost analysis completed for session {session_id}")
        logger.info(f"📊 Total Monthly Cost: ${analysis.cost_summary.total_monthly_cost:.2f}")
        logger.info(f"🏦 Parameters Used: {analysis.tco_parameters.pricing_model}, {analysis.tco_parameters.production_ri_years}yr RI")
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ HARDCODED: Cost analysis failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Cost analysis failed: {str(e)}")

@router.get("/summary/{session_id}")
async def get_cost_summary_hardcoded(session_id: str) -> Dict:
    """Get cost analysis summary with hardcoded parameters info"""
    
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        if not session.cost_analysis:
            raise HTTPException(status_code=404, detail="No cost analysis found for session")
        
        analysis = session.cost_analysis
        
        # Get breakdowns (simplified for hardcoded version)
        workload_breakdown = {}
        family_breakdown = {}
        
        # Calculate workload breakdown
        production_cost = sum(
            est.total_monthly_cost for est in analysis.detailed_estimates 
            if est.environment == 'Production'
        )
        non_production_cost = sum(
            est.total_monthly_cost for est in analysis.detailed_estimates 
            if est.environment == 'Non-Production'
        )
        
        workload_breakdown = {
            'Production': {
                'total_cost': production_cost,
                'vm_count': len([est for est in analysis.detailed_estimates if est.environment == 'Production']),
                'pricing_model': '3-Year Reserved Instance (Hardcoded)'
            },
            'Non-Production': {
                'total_cost': non_production_cost,
                'vm_count': len([est for est in analysis.detailed_estimates if est.environment == 'Non-Production']),
                'pricing_model': 'On-Demand 50% Utilization (Hardcoded)'
            }
        }
        
        # Calculate instance family breakdown
        family_costs = {}
        for est in analysis.detailed_estimates:
            family = est.recommended_instance_type.split('.')[0]  # e.g., 't3' from 't3.xlarge'
            if family not in family_costs:
                family_costs[family] = {'total_cost': 0, 'vm_count': 0}
            family_costs[family]['total_cost'] += est.total_monthly_cost
            family_costs[family]['vm_count'] += 1
        
        summary = {
            "session_id": session_id,
            "cost_summary": analysis.cost_summary.dict(),
            "tco_parameters": analysis.tco_parameters.dict(),
            "total_vms_analyzed": analysis.total_vms_analyzed,
            "workload_breakdown": workload_breakdown,
            "instance_family_breakdown": family_costs,
            "analysis_timestamp": session.updated_at.isoformat(),
            "hardcoded_info": {
                "production_pricing": "3-Year Reserved Instance (No Upfront)",
                "non_production_pricing": "On-Demand with 50% utilization",
                "note": "Parameters are hardcoded for consistent results"
            }
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cost summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost summary: {str(e)}")

@router.get("/export/{session_id}")
async def export_cost_estimates_hardcoded(
    session_id: str,
    format: str = Query("json", regex="^(json|csv)$")
):
    """Export cost estimates with hardcoded parameters info"""
    
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        if not session.cost_analysis:
            raise HTTPException(status_code=404, detail="No cost analysis found for session")
        
        analysis = session.cost_analysis
        
        if format == "csv":
            # Create CSV content with hardcoded info
            csv_content = "VM Name,CPU Cores,Memory (GB),Storage (GB),Recommended Instance Type,Instance Cost ($),Storage Cost ($),Total Monthly Cost ($),Pricing Plan,Operating System,Environment\n"
            
            for estimate in analysis.detailed_estimates:
                csv_content += f"{estimate.vm_name},{estimate.cpu_cores},{estimate.memory_gb},{estimate.storage_gb},{estimate.recommended_instance_type},{estimate.instance_cost:.2f},{estimate.storage_cost:.2f},{estimate.total_monthly_cost:.2f},{estimate.pricing_plan},{estimate.operating_system},{estimate.environment}\n"
            
            # Add hardcoded parameters info as comments
            csv_content += f"\n# HARDCODED PARAMETERS USED:\n"
            csv_content += f"# Production: 3-Year Reserved Instance (No Upfront)\n"
            csv_content += f"# Non-Production: On-Demand with 50% utilization\n"
            csv_content += f"# Total Monthly Cost: ${analysis.cost_summary.total_monthly_cost:.2f}\n"
            
            return JSONResponse(
                content=csv_content,
                headers={"Content-Disposition": f"attachment; filename=cost_estimates_hardcoded_{session_id}.csv"}
            )
        else:
            # JSON export
            export_data = {
                "session_id": session_id,
                "export_timestamp": session.updated_at.isoformat(),
                "cost_summary": analysis.cost_summary.dict(),
                "tco_parameters": analysis.tco_parameters.dict(),
                "detailed_estimates": [estimate.dict() for estimate in analysis.detailed_estimates],
                "total_vms_analyzed": analysis.total_vms_analyzed,
                "hardcoded_info": {
                    "production_pricing": "3-Year Reserved Instance (No Upfront)",
                    "non_production_pricing": "On-Demand with 50% utilization",
                    "note": "Parameters are hardcoded for consistent results"
                }
            }
            
            return JSONResponse(
                content=export_data,
                headers={"Content-Disposition": f"attachment; filename=cost_estimates_hardcoded_{session_id}.json"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export cost estimates for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/health")
async def health_check_hardcoded():
    """Health check for hardcoded cost estimates service"""
    
    try:
        # Test the hardcoded service
        health_status = {
            "status": "healthy",
            "service": "cost_estimates_hardcoded",
            "timestamp": session_manager._get_current_time().isoformat(),
            "hardcoded_parameters": {
                "production_pricing": "3-Year Reserved Instance (No Upfront)",
                "non_production_pricing": "On-Demand with 50% utilization",
                "pricing_service": "EnhancedLocalPricingService"
            },
            "database_records": "308 Singapore pricing records available"
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Add alias for backward compatibility
@router.post("/analyze-hardcoded/{session_id}")
async def analyze_cost_estimates_hardcoded_alias(
    session_id: str,
    tco_parameters: Optional[TCOParameters] = None
) -> CostEstimatesAnalysis:
    """Alias endpoint for hardcoded cost analysis"""
    return await analyze_cost_estimates_hardcoded(session_id, tco_parameters)
