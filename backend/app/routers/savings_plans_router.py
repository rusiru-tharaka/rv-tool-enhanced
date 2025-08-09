"""
Savings Plans API Router
Phase 2.1: Advanced Pricing Features - Savings Plans Integration
RESTful API endpoints for AWS Savings Plans analysis and recommendations
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from ..services.cost_estimates_service import cost_estimates_service
from ..services.savings_plans_service import savings_plans_service
from ..models.core_models import TCOParameters, VMCostEstimate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/savings-plans", tags=["Savings Plans"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SavingsPlansAnalysisRequest(BaseModel):
    """Request model for Savings Plans analysis"""
    session_id: str = Field(..., description="Analysis session ID")
    tco_parameters: TCOParameters = Field(..., description="TCO calculation parameters")
    detailed_estimates: Optional[List[Dict[str, Any]]] = Field(None, description="Existing cost estimates")
    analysis_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Analysis configuration options")

class SavingsPlansRecommendationRequest(BaseModel):
    """Request model for Savings Plans recommendations"""
    session_id: str = Field(..., description="Analysis session ID")
    current_monthly_spend: float = Field(..., gt=0, description="Current monthly AWS spend")
    workload_stability_score: Optional[float] = Field(80.0, ge=0, le=100, description="Workload stability score")
    risk_tolerance: Optional[str] = Field("medium", description="Risk tolerance: low, medium, high")
    commitment_preference: Optional[str] = Field("1_year", description="Preferred commitment term")

class SavingsPlansComparisonRequest(BaseModel):
    """Request model for Savings Plans comparison"""
    session_id: str = Field(..., description="Analysis session ID")
    plan_scenarios: List[Dict[str, Any]] = Field(..., description="Savings Plans scenarios to compare")
    comparison_metrics: Optional[List[str]] = Field(default_factory=lambda: ["savings", "risk", "flexibility"], description="Metrics to compare")

class SavingsPlansResponse(BaseModel):
    """Response model for Savings Plans analysis"""
    success: bool
    session_id: str
    analysis_timestamp: datetime
    current_monthly_spend: float
    total_potential_annual_savings: float
    potential_savings_percentage: float
    savings_portfolio: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    implementation_roadmap: Optional[Dict[str, Any]] = None

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=SavingsPlansResponse)
async def analyze_savings_plans_opportunities(
    request: SavingsPlansAnalysisRequest,
    background_tasks: BackgroundTasks
) -> SavingsPlansResponse:
    """
    Analyze Savings Plans opportunities for existing cost estimates
    
    This endpoint provides comprehensive Savings Plans analysis including:
    - Compute Savings Plans recommendations
    - EC2 Instance Savings Plans recommendations  
    - Portfolio optimization
    - Risk assessment
    - Implementation roadmap
    """
    logger.info(f"Starting Savings Plans analysis for session {request.session_id}")
    
    try:
        # Validate session and get existing cost estimates
        if not request.detailed_estimates:
            raise HTTPException(
                status_code=400,
                detail="Detailed cost estimates required for Savings Plans analysis"
            )
        
        # Convert request estimates to VMCostEstimate objects
        detailed_estimates = []
        for est_data in request.detailed_estimates:
            try:
                # Create VMCostEstimate from dictionary data
                estimate = VMCostEstimate(**est_data)
                detailed_estimates.append(estimate)
            except Exception as e:
                logger.warning(f"Failed to parse cost estimate: {e}")
                continue
        
        if not detailed_estimates:
            raise HTTPException(
                status_code=400,
                detail="No valid cost estimates found for analysis"
            )
        
        # Perform Savings Plans analysis
        analysis_result = await cost_estimates_service.analyze_savings_plans_opportunities(
            request.session_id,
            detailed_estimates,
            request.tco_parameters
        )
        
        # Generate implementation roadmap
        implementation_roadmap = await _generate_implementation_roadmap(
            analysis_result["savings_portfolio"],
            analysis_result["recommendations"]
        )
        
        # Schedule background optimization analysis
        background_tasks.add_task(
            _perform_background_optimization,
            request.session_id,
            analysis_result
        )
        
        return SavingsPlansResponse(
            success=True,
            session_id=request.session_id,
            analysis_timestamp=analysis_result["analysis_timestamp"],
            current_monthly_spend=analysis_result["current_monthly_spend"],
            total_potential_annual_savings=analysis_result["total_potential_annual_savings"],
            potential_savings_percentage=analysis_result["potential_savings_percentage"],
            savings_portfolio=analysis_result["savings_portfolio"].__dict__,
            recommendations=analysis_result["recommendations"],
            risk_assessment=analysis_result["savings_analysis"]["risk_assessment"],
            implementation_roadmap=implementation_roadmap
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Savings Plans analysis failed for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Savings Plans analysis failed: {str(e)}"
        )

@router.post("/recommendations")
async def get_savings_plans_recommendations(
    request: SavingsPlansRecommendationRequest
) -> JSONResponse:
    """
    Get tailored Savings Plans recommendations based on specific criteria
    
    Provides customized recommendations based on:
    - Current spend patterns
    - Workload stability
    - Risk tolerance
    - Commitment preferences
    """
    logger.info(f"Generating Savings Plans recommendations for session {request.session_id}")
    
    try:
        # Create mock VM inventory based on spend (for demonstration)
        estimated_vm_count = max(1, int(request.current_monthly_spend / 100))  # Estimate VMs
        mock_vm_inventory = _create_mock_vm_inventory(estimated_vm_count, request.current_monthly_spend)
        
        # Create basic TCO parameters
        tco_parameters = TCOParameters(
            target_region="us-east-1",
            pricing_model="mixed",
            production_ri_years=1 if request.commitment_preference == "1_year" else 3
        )
        
        # Analyze Savings Plans opportunities
        savings_portfolio = await savings_plans_service.analyze_savings_opportunities(
            mock_vm_inventory,
            tco_parameters,
            request.current_monthly_spend
        )
        
        # Filter recommendations based on risk tolerance
        filtered_recommendations = _filter_recommendations_by_risk(
            savings_portfolio,
            request.risk_tolerance,
            request.workload_stability_score
        )
        
        return JSONResponse(content={
            "success": True,
            "session_id": request.session_id,
            "recommendations": filtered_recommendations,
            "portfolio_summary": {
                "total_annual_savings": savings_portfolio.total_annual_savings,
                "savings_percentage": savings_portfolio.overall_savings_percentage,
                "portfolio_risk_score": savings_portfolio.portfolio_risk_score,
                "diversification_score": savings_portfolio.diversification_score
            },
            "next_steps": _generate_next_steps(filtered_recommendations, request.risk_tolerance)
        })
        
    except Exception as e:
        logger.error(f"Failed to generate Savings Plans recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Recommendations generation failed: {str(e)}"
        )

@router.post("/compare")
async def compare_savings_plans_scenarios(
    request: SavingsPlansComparisonRequest
) -> JSONResponse:
    """
    Compare different Savings Plans scenarios
    
    Provides side-by-side comparison of:
    - Different commitment terms
    - Payment options
    - Plan types (Compute vs EC2 Instance)
    - Risk/return profiles
    """
    logger.info(f"Comparing Savings Plans scenarios for session {request.session_id}")
    
    try:
        comparison_results = []
        
        for i, scenario in enumerate(request.plan_scenarios):
            scenario_name = scenario.get("name", f"Scenario {i+1}")
            
            # Analyze each scenario
            scenario_analysis = await _analyze_scenario(scenario, request.comparison_metrics)
            scenario_analysis["scenario_name"] = scenario_name
            
            comparison_results.append(scenario_analysis)
        
        # Generate comparison summary
        comparison_summary = _generate_comparison_summary(comparison_results, request.comparison_metrics)
        
        # Recommend best scenario
        best_scenario = _recommend_best_scenario(comparison_results)
        
        return JSONResponse(content={
            "success": True,
            "session_id": request.session_id,
            "comparison_results": comparison_results,
            "comparison_summary": comparison_summary,
            "recommended_scenario": best_scenario,
            "analysis_timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Savings Plans scenario comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Scenario comparison failed: {str(e)}"
        )

@router.get("/portfolio/{session_id}")
async def get_savings_plans_portfolio(session_id: str) -> JSONResponse:
    """
    Get current Savings Plans portfolio for a session
    
    Returns:
    - Current Savings Plans commitments
    - Utilization metrics
    - Performance tracking
    - Optimization opportunities
    """
    logger.info(f"Retrieving Savings Plans portfolio for session {session_id}")
    
    try:
        # In a real implementation, this would fetch from database
        # For now, return a mock portfolio structure
        portfolio = {
            "session_id": session_id,
            "portfolio_status": "active",
            "total_commitments": {
                "monthly": 2500.0,
                "annual": 30000.0
            },
            "current_utilization": {
                "compute_savings_plans": 85.2,
                "ec2_instance_savings_plans": 92.1,
                "overall": 88.7
            },
            "performance_metrics": {
                "actual_monthly_savings": 1200.0,
                "projected_monthly_savings": 1350.0,
                "savings_realization": 88.9
            },
            "active_plans": [
                {
                    "plan_type": "compute",
                    "commitment_term": "1_year",
                    "hourly_commitment": 3.47,
                    "utilization_percentage": 85.2,
                    "monthly_savings": 800.0
                },
                {
                    "plan_type": "ec2_instance",
                    "instance_family": "m5",
                    "commitment_term": "1_year",
                    "hourly_commitment": 1.39,
                    "utilization_percentage": 92.1,
                    "monthly_savings": 400.0
                }
            ],
            "optimization_opportunities": [
                {
                    "type": "increase_commitment",
                    "description": "Increase Compute Savings Plans commitment by 20%",
                    "potential_additional_savings": 200.0,
                    "confidence": "high"
                }
            ]
        }
        
        return JSONResponse(content={
            "success": True,
            "portfolio": portfolio,
            "last_updated": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve Savings Plans portfolio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Portfolio retrieval failed: {str(e)}"
        )

@router.get("/utilization/{session_id}")
async def get_savings_plans_utilization(
    session_id: str,
    days: Optional[int] = 30
) -> JSONResponse:
    """
    Get Savings Plans utilization metrics over time
    
    Returns:
    - Historical utilization data
    - Trends and patterns
    - Optimization recommendations
    """
    logger.info(f"Retrieving Savings Plans utilization for session {session_id}")
    
    try:
        # Mock utilization data (in real implementation, fetch from monitoring service)
        utilization_data = {
            "session_id": session_id,
            "period_days": days,
            "average_utilization": 87.3,
            "utilization_trend": "stable",
            "daily_utilization": [
                {"date": "2025-07-01", "compute": 85.2, "ec2_instance": 89.1, "overall": 87.2},
                {"date": "2025-07-02", "compute": 87.1, "ec2_instance": 91.3, "overall": 89.2},
                # ... more daily data would be here
            ],
            "utilization_insights": [
                {
                    "insight": "Compute Savings Plans utilization is consistently above 85%",
                    "impact": "positive",
                    "recommendation": "Consider increasing commitment level"
                },
                {
                    "insight": "Weekend utilization drops to 70%",
                    "impact": "neutral",
                    "recommendation": "Normal pattern for business workloads"
                }
            ],
            "optimization_score": 85.0
        }
        
        return JSONResponse(content={
            "success": True,
            "utilization_data": utilization_data,
            "analysis_timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve utilization data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Utilization data retrieval failed: {str(e)}"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _generate_implementation_roadmap(savings_portfolio: Any, recommendations: List[Dict]) -> Dict[str, Any]:
    """Generate implementation roadmap for Savings Plans"""
    
    roadmap = {
        "phase_1": {
            "title": "Initial Implementation (Month 1)",
            "actions": [
                "Implement highest-value Compute Savings Plans",
                "Monitor utilization patterns",
                "Establish baseline metrics"
            ],
            "expected_savings": savings_portfolio.total_monthly_savings * 0.6,
            "risk_level": "low"
        },
        "phase_2": {
            "title": "Optimization (Months 2-3)",
            "actions": [
                "Add EC2 Instance Savings Plans for stable workloads",
                "Fine-tune commitment levels",
                "Implement monitoring and alerting"
            ],
            "expected_savings": savings_portfolio.total_monthly_savings * 0.3,
            "risk_level": "medium"
        },
        "phase_3": {
            "title": "Advanced Optimization (Months 4-6)",
            "actions": [
                "Consider 3-year commitments for stable workloads",
                "Optimize payment options",
                "Implement automated optimization"
            ],
            "expected_savings": savings_portfolio.total_monthly_savings * 0.1,
            "risk_level": "medium"
        }
    }
    
    return roadmap

async def _perform_background_optimization(session_id: str, analysis_result: Dict[str, Any]):
    """Perform background optimization analysis"""
    logger.info(f"Performing background optimization for session {session_id}")
    
    # In a real implementation, this would:
    # 1. Store analysis results in database
    # 2. Schedule periodic re-analysis
    # 3. Monitor utilization patterns
    # 4. Generate alerts for optimization opportunities
    
    pass

def _create_mock_vm_inventory(vm_count: int, monthly_spend: float) -> List[Dict]:
    """Create mock VM inventory for recommendations"""
    
    vm_inventory = []
    avg_vm_cost = monthly_spend / vm_count
    
    for i in range(vm_count):
        # Vary VM characteristics based on cost
        if avg_vm_cost > 200:  # High-cost VMs
            cpu_cores = 8
            memory_mb = 32768
            workload = "production"
        elif avg_vm_cost > 100:  # Medium-cost VMs
            cpu_cores = 4
            memory_mb = 16384
            workload = "production"
        else:  # Low-cost VMs
            cpu_cores = 2
            memory_mb = 8192
            workload = "development"
        
        vm_inventory.append({
            "VM": f"vm-{i+1:03d}",
            "CPUs": cpu_cores,
            "Memory": memory_mb,
            "Powerstate": "poweredOn",
            "workload_type": workload
        })
    
    return vm_inventory

def _filter_recommendations_by_risk(savings_portfolio: Any, risk_tolerance: str, stability_score: float) -> List[Dict]:
    """Filter recommendations based on risk tolerance"""
    
    all_plans = savings_portfolio.compute_savings_plans + savings_portfolio.ec2_instance_savings_plans
    filtered_plans = []
    
    risk_thresholds = {
        "low": 40,
        "medium": 70,
        "high": 100
    }
    
    max_risk = risk_thresholds.get(risk_tolerance, 70)
    
    for plan in all_plans:
        if plan.commitment_risk_score <= max_risk:
            # Additional filtering based on stability
            if stability_score < 70 and plan.commitment_term == "3_year":
                continue  # Skip 3-year plans for unstable workloads
            
            filtered_plans.append({
                "plan_type": plan.plan_type,
                "instance_family": plan.instance_family,
                "commitment_term": plan.commitment_term,
                "monthly_commitment": plan.monthly_commitment,
                "estimated_monthly_savings": plan.estimated_monthly_savings,
                "risk_score": plan.commitment_risk_score,
                "confidence": plan.recommendation_confidence
            })
    
    return filtered_plans

def _generate_next_steps(recommendations: List[Dict], risk_tolerance: str) -> List[str]:
    """Generate next steps based on recommendations"""
    
    next_steps = []
    
    if recommendations:
        next_steps.append("Review workload stability over the past 3 months")
        next_steps.append("Start with the highest-confidence recommendation")
        
        if risk_tolerance == "low":
            next_steps.append("Begin with 1-year commitments and no-upfront payment")
        elif risk_tolerance == "high":
            next_steps.append("Consider 3-year commitments for maximum savings")
        
        next_steps.append("Implement monitoring to track utilization")
        next_steps.append("Schedule monthly review of Savings Plans performance")
    else:
        next_steps.append("Increase workload stability before implementing Savings Plans")
        next_steps.append("Consider Reserved Instances as an alternative")
    
    return next_steps

async def _analyze_scenario(scenario: Dict[str, Any], metrics: List[str]) -> Dict[str, Any]:
    """Analyze a single Savings Plans scenario"""
    
    # Mock scenario analysis (in real implementation, would use actual pricing data)
    analysis = {
        "commitment_term": scenario.get("commitment_term", "1_year"),
        "payment_option": scenario.get("payment_option", "no_upfront"),
        "plan_type": scenario.get("plan_type", "compute")
    }
    
    if "savings" in metrics:
        analysis["estimated_annual_savings"] = scenario.get("monthly_commitment", 1000) * 12 * 0.3
    
    if "risk" in metrics:
        risk_score = 30 if scenario.get("commitment_term") == "1_year" else 60
        if scenario.get("payment_option") == "all_upfront":
            risk_score += 20
        analysis["risk_score"] = risk_score
    
    if "flexibility" in metrics:
        flexibility = 90 if scenario.get("plan_type") == "compute" else 60
        analysis["flexibility_score"] = flexibility
    
    return analysis

def _generate_comparison_summary(results: List[Dict], metrics: List[str]) -> Dict[str, Any]:
    """Generate comparison summary across scenarios"""
    
    summary = {}
    
    if "savings" in metrics:
        savings_values = [r.get("estimated_annual_savings", 0) for r in results]
        summary["savings"] = {
            "highest": max(savings_values),
            "lowest": min(savings_values),
            "average": sum(savings_values) / len(savings_values)
        }
    
    if "risk" in metrics:
        risk_values = [r.get("risk_score", 0) for r in results]
        summary["risk"] = {
            "highest": max(risk_values),
            "lowest": min(risk_values),
            "average": sum(risk_values) / len(risk_values)
        }
    
    return summary

def _recommend_best_scenario(results: List[Dict]) -> Dict[str, Any]:
    """Recommend the best scenario based on analysis"""
    
    # Simple scoring: maximize savings, minimize risk
    best_scenario = None
    best_score = -1
    
    for result in results:
        savings = result.get("estimated_annual_savings", 0)
        risk = result.get("risk_score", 100)
        
        # Score = savings / 1000 - risk / 100 (normalize and weight)
        score = (savings / 1000) - (risk / 100)
        
        if score > best_score:
            best_score = score
            best_scenario = result
    
    return {
        "scenario": best_scenario,
        "score": best_score,
        "reasoning": "Optimizes for highest savings with acceptable risk level"
    }
