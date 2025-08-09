"""
Modernization API Router
RESTful API endpoints for modernization opportunities analysis
Provides comprehensive modernization recommendations and cost impact analysis
"""

import logging
import sys
import os
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..services.session_manager import session_manager
from ..services.modernization_analysis_service import modernization_service
from ..models.core_models import (
    ModernizationAnalysis,
    ModernizationOpportunity,
    ModernizationType,
    PaginatedResponse,
    ErrorResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/modernization", tags=["Modernization"])

@router.post("/analyze/{session_id}")
async def analyze_modernization_opportunities(session_id: str) -> ModernizationAnalysis:
    """
    Analyze modernization opportunities for VM inventory
    
    **Parameters:**
    - session_id: Unique session identifier
    
    **Returns:**
    - Complete modernization analysis with opportunities and cost impact
    
    **Prerequisites:**
    - Session must have VM inventory data
    - Cost estimates analysis must be completed first
    
    **Modernization Types Detected:**
    - **Managed Database**: RDS, DocumentDB, Aurora Serverless
    - **Containerization**: ECS, EKS, AWS Batch
    - **Serverless**: Lambda, API Gateway, EventBridge
    - **Managed Services**: Various AWS managed services
    """
    try:
        logger.info(f"Starting modernization analysis for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        if not session.vm_inventory:
            raise HTTPException(status_code=400, detail="No VM inventory data found in session")
        
        # Get cost estimates (required for modernization analysis)
        cost_estimates_data = session_manager.get_session_data(session_id, "cost_estimates_analysis")
        if not cost_estimates_data:
            raise HTTPException(
                status_code=400, 
                detail="Cost estimates analysis required. Please run cost analysis first."
            )
        
        # Extract cost estimates for modernization analysis
        cost_estimates = cost_estimates_data.get("detailed_estimates", [])
        
        # Perform modernization analysis
        analysis = modernization_service.analyze_modernization_opportunities(
            session_id=session_id,
            vm_inventory=session.vm_inventory,
            cost_estimates=cost_estimates
        )
        
        # Update session with modernization analysis results
        session_manager.update_session_data(session_id, "modernization_analysis", analysis.dict())
        
        # Advance session to next phase
        session_manager.advance_phase(session_id)
        
        logger.info(f"Modernization analysis completed for session {session_id}: {analysis.total_opportunities} opportunities found")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modernization analysis failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Modernization analysis failed: {str(e)}")

@router.get("/opportunities/{session_id}")
async def get_modernization_opportunities(
    session_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    modernization_type: Optional[str] = Query(None, description="Filter by modernization type"),
    complexity: Optional[str] = Query(None, description="Filter by implementation complexity"),
    min_savings: Optional[float] = Query(None, description="Minimum monthly savings filter"),
    search: Optional[str] = Query(None, description="Search VM names"),
    sort_by: str = Query("monthly_savings", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
) -> PaginatedResponse:
    """
    Get modernization opportunities with pagination, search, and filtering
    
    **Parameters:**
    - session_id: Session identifier
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 1000)
    - modernization_type: Filter by type (managed_database, containerization, serverless, managed_services)
    - complexity: Filter by complexity (low, medium, high)
    - min_savings: Minimum monthly savings filter
    - search: Search VM names (optional)
    - sort_by: Sort field (default: monthly_savings)
    - sort_order: Sort order - asc or desc (default: desc)
    
    **Returns:**
    - Paginated list of modernization opportunities
    """
    try:
        logger.info(f"Getting modernization opportunities for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get modernization analysis from session data
        modernization_data = session_manager.get_session_data(session_id, "modernization_analysis")
        if not modernization_data:
            raise HTTPException(status_code=404, detail="Modernization analysis not found. Run analysis first.")
        
        # Parse modernization analysis
        analysis = ModernizationAnalysis(**modernization_data)
        opportunities = analysis.opportunities
        
        # Apply filters
        if modernization_type:
            try:
                mod_type = ModernizationType(modernization_type)
                opportunities = [opp for opp in opportunities if opp.modernization_type == mod_type]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid modernization type: {modernization_type}")
        
        if complexity:
            if complexity not in ["low", "medium", "high"]:
                raise HTTPException(status_code=400, detail=f"Invalid complexity level: {complexity}")
            opportunities = [opp for opp in opportunities if opp.implementation_complexity == complexity]
        
        if min_savings is not None:
            opportunities = [opp for opp in opportunities if opp.monthly_savings >= min_savings]
        
        if search:
            search_lower = search.lower()
            opportunities = [
                opp for opp in opportunities
                if search_lower in opp.vm_name.lower() or search_lower in opp.target_aws_service.lower()
            ]
        
        # Sort results
        reverse_sort = sort_order == "desc"
        if sort_by == "vm_name":
            opportunities.sort(key=lambda x: x.vm_name, reverse=reverse_sort)
        elif sort_by == "monthly_savings":
            opportunities.sort(key=lambda x: x.monthly_savings, reverse=reverse_sort)
        elif sort_by == "annual_savings":
            opportunities.sort(key=lambda x: x.annual_savings, reverse=reverse_sort)
        elif sort_by == "implementation_complexity":
            complexity_order = {"low": 1, "medium": 2, "high": 3}
            opportunities.sort(
                key=lambda x: complexity_order.get(x.implementation_complexity, 2), 
                reverse=reverse_sort
            )
        elif sort_by == "modernization_type":
            opportunities.sort(key=lambda x: x.modernization_type.value, reverse=reverse_sort)
        
        # Calculate pagination
        total_count = len(opportunities)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_items = opportunities[start_idx:end_idx]
        
        logger.info(f"Retrieved {len(paginated_items)} modernization opportunities (page {page}/{total_pages})")
        
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
        logger.error(f"Failed to get modernization opportunities for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get modernization opportunities: {str(e)}")

@router.get("/summary/{session_id}")
async def get_modernization_summary(session_id: str) -> Dict:
    """
    Get modernization summary and statistics
    
    **Returns:**
    - Comprehensive modernization summary with cost impact and breakdowns
    """
    try:
        logger.info(f"Getting modernization summary for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get modernization analysis from session data
        modernization_data = session_manager.get_session_data(session_id, "modernization_analysis")
        if not modernization_data:
            raise HTTPException(status_code=404, detail="Modernization analysis not found. Run analysis first.")
        
        # Parse modernization analysis
        analysis = ModernizationAnalysis(**modernization_data)
        
        # Get detailed summary
        summary = modernization_service.get_modernization_summary(analysis)
        
        # Add session and analysis metadata
        summary.update({
            "session_id": session_id,
            "cost_impact": analysis.cost_impact.dict(),
            "analysis_timestamp": session.updated_at.isoformat(),
            "total_vms_analyzed": len(session.vm_inventory)
        })
        
        logger.info(f"Modernization summary retrieved for session {session_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get modernization summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get modernization summary: {str(e)}")

@router.get("/opportunities/{session_id}/by-type")
async def get_opportunities_by_type(session_id: str) -> Dict[str, List[ModernizationOpportunity]]:
    """
    Get modernization opportunities grouped by type
    
    **Returns:**
    - Opportunities grouped by modernization type
    """
    try:
        logger.info(f"Getting opportunities by type for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get modernization analysis from session data
        modernization_data = session_manager.get_session_data(session_id, "modernization_analysis")
        if not modernization_data:
            raise HTTPException(status_code=404, detail="Modernization analysis not found. Run analysis first.")
        
        # Parse modernization analysis
        analysis = ModernizationAnalysis(**modernization_data)
        
        # Convert enum keys to strings for JSON serialization
        opportunities_by_type = {
            mod_type.value: opportunities 
            for mod_type, opportunities in analysis.opportunities_by_type.items()
        }
        
        logger.info(f"Opportunities by type retrieved for session {session_id}")
        return opportunities_by_type
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get opportunities by type for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get opportunities by type: {str(e)}")

@router.get("/cost-impact/{session_id}")
async def get_cost_impact_analysis(session_id: str) -> Dict:
    """
    Get detailed cost impact analysis for modernization
    
    **Returns:**
    - Detailed cost impact breakdown and projections
    """
    try:
        logger.info(f"Getting cost impact analysis for session: {session_id}")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get modernization analysis from session data
        modernization_data = session_manager.get_session_data(session_id, "modernization_analysis")
        if not modernization_data:
            raise HTTPException(status_code=404, detail="Modernization analysis not found. Run analysis first.")
        
        # Parse modernization analysis
        analysis = ModernizationAnalysis(**modernization_data)
        
        # Calculate detailed cost impact
        cost_impact = {
            "current_state": {
                "monthly_cost": analysis.cost_impact.current_aws_monthly_cost,
                "annual_cost": analysis.cost_impact.current_aws_monthly_cost * 12
            },
            "modernized_state": {
                "monthly_cost": analysis.cost_impact.modernized_aws_monthly_cost,
                "annual_cost": analysis.cost_impact.modernized_aws_monthly_cost * 12
            },
            "savings": {
                "monthly_savings": analysis.cost_impact.total_monthly_savings,
                "annual_savings": analysis.cost_impact.total_annual_savings,
                "savings_percentage": analysis.cost_impact.savings_percentage
            },
            "roi_analysis": {
                "payback_period_months": 6,  # Typical modernization payback
                "3_year_savings": analysis.cost_impact.total_annual_savings * 3,
                "5_year_savings": analysis.cost_impact.total_annual_savings * 5
            },
            "breakdown_by_type": {}
        }
        
        # Calculate savings by modernization type
        for mod_type, opportunities in analysis.opportunities_by_type.items():
            type_savings = sum(opp.monthly_savings for opp in opportunities)
            cost_impact["breakdown_by_type"][mod_type.value] = {
                "monthly_savings": type_savings,
                "annual_savings": type_savings * 12,
                "opportunity_count": len(opportunities)
            }
        
        logger.info(f"Cost impact analysis retrieved for session {session_id}")
        return cost_impact
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cost impact analysis for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost impact analysis: {str(e)}")

@router.get("/export/{session_id}")
async def export_modernization_analysis(
    session_id: str,
    format: str = Query("json", regex="^(json|csv)$", description="Export format")
) -> JSONResponse:
    """
    Export modernization analysis data
    
    **Parameters:**
    - session_id: Session identifier
    - format: Export format - json or csv (default: json)
    
    **Returns:**
    - Exported modernization analysis data
    """
    try:
        logger.info(f"Exporting modernization analysis for session: {session_id} in {format} format")
        
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Get modernization analysis from session data
        modernization_data = session_manager.get_session_data(session_id, "modernization_analysis")
        if not modernization_data:
            raise HTTPException(status_code=404, detail="Modernization analysis not found. Run analysis first.")
        
        # Parse modernization analysis
        analysis = ModernizationAnalysis(**modernization_data)
        
        if format == "json":
            export_data = {
                "session_id": session_id,
                "export_timestamp": session.updated_at.isoformat(),
                "cost_impact": analysis.cost_impact.dict(),
                "opportunities": [opp.dict() for opp in analysis.opportunities],
                "summary": modernization_service.get_modernization_summary(analysis),
                "total_opportunities": analysis.total_opportunities
            }
            
            return JSONResponse(
                content=export_data,
                headers={"Content-Disposition": f"attachment; filename=modernization_analysis_{session_id}.json"}
            )
        
        elif format == "csv":
            # Create CSV content
            csv_lines = []
            csv_lines.append("VM Name,Current Workload,Modernization Type,Target Service,Current Monthly Cost,Modernized Monthly Cost,Monthly Savings,Annual Savings,Implementation Complexity,Benefits")
            
            for opp in analysis.opportunities:
                benefits_str = "; ".join(opp.benefits)
                csv_lines.append(
                    f"{opp.vm_name},{opp.current_workload_type},{opp.modernization_type.value},"
                    f"{opp.target_aws_service},{opp.current_monthly_cost:.2f},"
                    f"{opp.modernized_monthly_cost:.2f},{opp.monthly_savings:.2f},"
                    f"{opp.annual_savings:.2f},{opp.implementation_complexity},\"{benefits_str}\""
                )
            
            csv_content = "\n".join(csv_lines)
            
            return JSONResponse(
                content={"csv_data": csv_content},
                headers={"Content-Disposition": f"attachment; filename=modernization_analysis_{session_id}.csv"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export modernization analysis for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export modernization analysis: {str(e)}")

@router.get("/health")
async def modernization_health() -> Dict:
    """
    Health check endpoint for modernization service
    
    **Returns:**
    - Service health status and statistics
    """
    try:
        health_status = {
            "service": "modernization",
            "status": "healthy",
            "timestamp": session_manager._get_current_time().isoformat(),
            "patterns_loaded": {
                "database_patterns": len(modernization_service.database_patterns),
                "containerization_patterns": len(modernization_service.containerization_patterns),
                "serverless_patterns": len(modernization_service.serverless_patterns)
            },
            "modernization_types": [mod_type.value for mod_type in ModernizationType]
        }
        
        logger.info("Modernization service health check passed")
        return health_status
        
    except Exception as e:
        logger.error(f"Modernization service health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# Add router tags and metadata
router.tags = ["Modernization"]
