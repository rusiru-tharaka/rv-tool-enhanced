"""
Reserved Instance API Router
Phase 2.2: Reserved Instance Optimization
RESTful API endpoints for AWS Reserved Instance analysis and recommendations
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from ..services.cost_estimates_service import cost_estimates_service
from ..services.reserved_instance_service import reserved_instance_service
from ..models.core_models import TCOParameters, VMCostEstimate
from ..models.reserved_instance_models import RITerm, RIPaymentOption, RIOfferingClass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/reserved-instances", tags=["Reserved Instances"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RIAnalysisRequest(BaseModel):
    """Request model for Reserved Instance analysis"""
    session_id: str = Field(..., description="Analysis session ID")
    tco_parameters: TCOParameters = Field(..., description="TCO calculation parameters")
    detailed_estimates: Optional[List[Dict[str, Any]]] = Field(None, description="Existing cost estimates")
    analysis_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Analysis configuration options")

class RIRecommendationRequest(BaseModel):
    """Request model for RI recommendations"""
    session_id: str = Field(..., description="Analysis session ID")
    current_monthly_spend: float = Field(..., gt=0, description="Current monthly AWS spend")
    workload_stability_score: Optional[float] = Field(80.0, ge=0, le=100, description="Workload stability score")
    preferred_term: Optional[RITerm] = Field(RITerm.ONE_YEAR, description="Preferred RI term")
    preferred_payment: Optional[RIPaymentOption] = Field(RIPaymentOption.NO_UPFRONT, description="Preferred payment option")
    budget_limit: Optional[float] = Field(None, description="Budget limit for upfront investment")

class RIComparisonRequest(BaseModel):
    """Request model for RI comparison analysis"""
    session_id: str = Field(..., description="Analysis session ID")
    comparison_scenarios: List[Dict[str, Any]] = Field(..., description="RI scenarios to compare")
    comparison_metrics: Optional[List[str]] = Field(
        default_factory=lambda: ["savings", "investment", "risk", "payback"], 
        description="Metrics to compare"
    )

class RIUtilizationRequest(BaseModel):
    """Request model for RI utilization analysis"""
    session_id: str = Field(..., description="Analysis session ID")
    ri_ids: Optional[List[str]] = Field(None, description="Specific RI IDs to analyze")
    time_period_days: Optional[int] = Field(30, ge=1, le=365, description="Analysis time period in days")

class RIOptimizationRequest(BaseModel):
    """Request model for RI optimization"""
    session_id: str = Field(..., description="Analysis session ID")
    current_ri_portfolio: Optional[Dict[str, Any]] = Field(None, description="Current RI portfolio")
    optimization_goals: Optional[List[str]] = Field(
        default_factory=lambda: ["maximize_savings", "minimize_risk"], 
        description="Optimization goals"
    )

class RIResponse(BaseModel):
    """Response model for Reserved Instance analysis"""
    success: bool
    session_id: str
    analysis_timestamp: datetime
    current_monthly_spend: float
    total_potential_annual_savings: float
    potential_savings_percentage: float
    ri_portfolio: Dict[str, Any]
    implementation_roadmap: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    comparison_analysis: Optional[Dict[str, Any]] = None

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=RIResponse)
async def analyze_reserved_instance_opportunities(
    request: RIAnalysisRequest,
    background_tasks: BackgroundTasks
) -> RIResponse:
    """
    Analyze Reserved Instance opportunities for existing cost estimates
    
    This endpoint provides comprehensive RI analysis including:
    - 1-year and 3-year RI recommendations
    - Payment option optimization
    - Portfolio risk assessment
    - Implementation roadmap
    - Comparison with Savings Plans
    """
    logger.info(f"Starting Reserved Instance analysis for session {request.session_id}")
    
    try:
        # Validate session and get existing cost estimates
        if not request.detailed_estimates:
            raise HTTPException(
                status_code=400,
                detail="Detailed cost estimates required for Reserved Instance analysis"
            )
        
        # Convert request estimates to VMCostEstimate objects
        detailed_estimates = []
        for est_data in request.detailed_estimates:
            try:
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
        
        # Perform Reserved Instance analysis
        analysis_result = await cost_estimates_service.analyze_reserved_instance_opportunities(
            request.session_id,
            detailed_estimates,
            request.tco_parameters
        )
        
        # Schedule background optimization analysis
        background_tasks.add_task(
            _perform_background_ri_optimization,
            request.session_id,
            analysis_result
        )
        
        return RIResponse(
            success=True,
            session_id=request.session_id,
            analysis_timestamp=analysis_result["analysis_timestamp"],
            current_monthly_spend=analysis_result["current_monthly_spend"],
            total_potential_annual_savings=analysis_result["total_potential_annual_savings"],
            potential_savings_percentage=analysis_result["potential_savings_percentage"],
            ri_portfolio=analysis_result["ri_portfolio"].__dict__,
            implementation_roadmap=analysis_result["implementation_roadmap"],
            risk_assessment=analysis_result["ri_analysis"]["risk_assessment"],
            comparison_analysis=analysis_result["comparison_analysis"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reserved Instance analysis failed for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reserved Instance analysis failed: {str(e)}"
        )

@router.post("/recommendations")
async def get_reserved_instance_recommendations(
    request: RIRecommendationRequest
) -> JSONResponse:
    """
    Get tailored Reserved Instance recommendations based on specific criteria
    
    Provides customized RI recommendations based on:
    - Current spend patterns
    - Workload stability
    - Preferred terms and payment options
    - Budget constraints
    """
    logger.info(f"Generating Reserved Instance recommendations for session {request.session_id}")
    
    try:
        # Create mock VM inventory based on spend
        estimated_vm_count = max(1, int(request.current_monthly_spend / 100))
        mock_vm_inventory = _create_mock_vm_inventory_for_ri(estimated_vm_count, request.current_monthly_spend)
        
        # Create basic TCO parameters
        tco_parameters = TCOParameters(
            target_region="us-east-1",
            pricing_model="mixed"
        )
        
        # Analyze RI opportunities
        ri_portfolio = await reserved_instance_service.analyze_ri_opportunities(
            request.session_id, mock_vm_inventory, tco_parameters, request.current_monthly_spend
        )
        
        # Filter recommendations based on preferences
        filtered_recommendations = _filter_ri_recommendations(
            ri_portfolio, request.preferred_term, request.preferred_payment, 
            request.budget_limit, request.workload_stability_score
        )
        
        return JSONResponse(content={
            "success": True,
            "session_id": request.session_id,
            "recommendations": filtered_recommendations,
            "portfolio_summary": {
                "total_annual_savings": ri_portfolio.total_annual_savings,
                "total_upfront_investment": ri_portfolio.total_upfront_investment,
                "portfolio_risk_score": ri_portfolio.portfolio_risk_score,
                "diversification_score": ri_portfolio.diversification_score
            },
            "implementation_guidance": _generate_ri_implementation_guidance(
                filtered_recommendations, request.workload_stability_score
            )
        })
        
    except Exception as e:
        logger.error(f"Failed to generate RI recommendations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RI recommendations generation failed: {str(e)}"
        )

@router.post("/compare")
async def compare_reserved_instance_scenarios(
    request: RIComparisonRequest
) -> JSONResponse:
    """
    Compare different Reserved Instance scenarios
    
    Provides side-by-side comparison of:
    - Different RI terms (1-year vs 3-year)
    - Payment options (No Upfront, Partial, All Upfront)
    - Risk/return profiles
    - Break-even analysis
    """
    logger.info(f"Comparing RI scenarios for session {request.session_id}")
    
    try:
        comparison_results = []
        
        for i, scenario in enumerate(request.comparison_scenarios):
            scenario_name = scenario.get("name", f"Scenario {i+1}")
            
            # Analyze each scenario
            scenario_analysis = await _analyze_ri_scenario(scenario, request.comparison_metrics)
            scenario_analysis["scenario_name"] = scenario_name
            
            comparison_results.append(scenario_analysis)
        
        # Generate comparison summary
        comparison_summary = _generate_ri_comparison_summary(comparison_results, request.comparison_metrics)
        
        # Recommend best scenario
        best_scenario = _recommend_best_ri_scenario(comparison_results)
        
        return JSONResponse(content={
            "success": True,
            "session_id": request.session_id,
            "comparison_results": comparison_results,
            "comparison_summary": comparison_summary,
            "recommended_scenario": best_scenario,
            "analysis_timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"RI scenario comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RI scenario comparison failed: {str(e)}"
        )

@router.get("/utilization/{session_id}")
async def get_reserved_instance_utilization(
    session_id: str,
    days: Optional[int] = 30
) -> JSONResponse:
    """
    Get Reserved Instance utilization metrics over time
    
    Returns:
    - Historical utilization data
    - Performance trends
    - Optimization recommendations
    - Underutilization alerts
    """
    logger.info(f"Retrieving RI utilization for session {session_id}")
    
    try:
        # Mock utilization data (in real implementation, fetch from AWS Cost Explorer API)
        utilization_data = {
            "session_id": session_id,
            "period_days": days,
            "overall_utilization": 87.3,
            "utilization_trend": "stable",
            "ri_utilization_details": [
                {
                    "ri_id": "ri-1234567890abcdef0",
                    "instance_type": "m5.large",
                    "term": "1_year",
                    "utilization_percentage": 92.1,
                    "net_savings": 245.50,
                    "status": "optimal"
                },
                {
                    "ri_id": "ri-0987654321fedcba0",
                    "instance_type": "c5.xlarge",
                    "term": "3_year",
                    "utilization_percentage": 78.4,
                    "net_savings": 189.30,
                    "status": "underutilized"
                }
            ],
            "optimization_opportunities": [
                {
                    "type": "modification",
                    "description": "Consider modifying underutilized c5.xlarge to c5.large",
                    "potential_savings": 50.0,
                    "effort": "low"
                },
                {
                    "type": "additional_purchase",
                    "description": "High on-demand usage detected for r5.2xlarge instances",
                    "potential_savings": 180.0,
                    "effort": "medium"
                }
            ],
            "alerts": [
                {
                    "severity": "warning",
                    "message": "RI utilization below 80% for c5.xlarge",
                    "recommendation": "Consider modification or exchange"
                }
            ]
        }
        
        return JSONResponse(content={
            "success": True,
            "utilization_data": utilization_data,
            "analysis_timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve RI utilization data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RI utilization data retrieval failed: {str(e)}"
        )

@router.post("/optimize")
async def optimize_reserved_instance_portfolio(
    request: RIOptimizationRequest
) -> JSONResponse:
    """
    Optimize existing Reserved Instance portfolio
    
    Provides:
    - Portfolio optimization recommendations
    - Modification suggestions
    - Exchange opportunities
    - Performance improvements
    """
    logger.info(f"Optimizing RI portfolio for session {request.session_id}")
    
    try:
        # Analyze current portfolio (mock implementation)
        optimization_analysis = {
            "session_id": request.session_id,
            "current_portfolio_value": 125000.0,
            "optimization_opportunities": [
                {
                    "type": "exchange",
                    "current_ri": "m5.large (3-year)",
                    "recommended_ri": "m5.xlarge (3-year)",
                    "reason": "Better match for current usage patterns",
                    "potential_savings": 200.0,
                    "implementation_effort": "low"
                },
                {
                    "type": "modification",
                    "current_ri": "c5.2xlarge (1-year)",
                    "recommended_change": "Split into 2x c5.xlarge",
                    "reason": "Improve utilization flexibility",
                    "potential_savings": 150.0,
                    "implementation_effort": "medium"
                }
            ],
            "new_purchase_recommendations": [
                {
                    "instance_type": "r5.large",
                    "quantity": 2,
                    "term": "1_year",
                    "payment_option": "partial_upfront",
                    "annual_savings": 480.0,
                    "upfront_cost": 720.0
                }
            ],
            "portfolio_health_score": 78.5,
            "optimization_priority": [
                "Address underutilized RIs first",
                "Implement high-savings modifications",
                "Consider new purchases for high on-demand usage"
            ]
        }
        
        return JSONResponse(content={
            "success": True,
            "optimization_analysis": optimization_analysis,
            "analysis_timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"RI portfolio optimization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RI portfolio optimization failed: {str(e)}"
        )

@router.get("/market-analysis/{region}")
async def get_reserved_instance_market_analysis(
    region: str,
    instance_families: Optional[List[str]] = None
) -> JSONResponse:
    """
    Get Reserved Instance market analysis for a specific region
    
    Returns:
    - Current RI pricing trends
    - Availability analysis
    - Savings opportunities by instance family
    - Market recommendations
    """
    logger.info(f"Retrieving RI market analysis for region {region}")
    
    try:
        # Mock market analysis (in real implementation, use AWS pricing APIs)
        market_analysis = {
            "region": region,
            "analysis_date": datetime.utcnow().isoformat(),
            "pricing_trends": {
                "1_year_savings_range": "20-35%",
                "3_year_savings_range": "35-55%",
                "trend": "stable",
                "last_updated": "2025-07-26"
            },
            "instance_family_analysis": [
                {
                    "family": "m5",
                    "availability": "high",
                    "average_savings_1yr": 28.5,
                    "average_savings_3yr": 42.1,
                    "recommendation": "Strong buy - high availability and good savings"
                },
                {
                    "family": "c5",
                    "availability": "medium",
                    "average_savings_1yr": 31.2,
                    "average_savings_3yr": 48.7,
                    "recommendation": "Consider - good savings but limited availability"
                },
                {
                    "family": "r5",
                    "availability": "high",
                    "average_savings_1yr": 26.8,
                    "average_savings_3yr": 41.5,
                    "recommendation": "Buy for memory-intensive workloads"
                }
            ],
            "market_insights": [
                "RI availability is currently high across most instance families",
                "3-year terms showing consistent 40%+ savings across all families",
                "Partial upfront payment options provide good balance of savings and flexibility"
            ],
            "timing_recommendation": "Favorable market conditions for RI purchases"
        }
        
        return JSONResponse(content={
            "success": True,
            "market_analysis": market_analysis
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve RI market analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RI market analysis failed: {str(e)}"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _perform_background_ri_optimization(session_id: str, analysis_result: Dict[str, Any]):
    """Perform background RI optimization analysis"""
    logger.info(f"Performing background RI optimization for session {session_id}")
    
    # In a real implementation, this would:
    # 1. Store analysis results in database
    # 2. Schedule periodic re-analysis
    # 3. Monitor RI utilization patterns
    # 4. Generate alerts for optimization opportunities
    
    pass

def _create_mock_vm_inventory_for_ri(vm_count: int, monthly_spend: float) -> List[Dict]:
    """Create mock VM inventory optimized for RI analysis"""
    
    vm_inventory = []
    avg_vm_cost = monthly_spend / vm_count
    
    for i in range(vm_count):
        # Create more stable workloads for RI analysis
        if i < vm_count * 0.7:  # 70% production workloads
            workload = "production"
            cpu_cores = 4 if avg_vm_cost > 150 else 2
            memory_mb = 16384 if avg_vm_cost > 150 else 8192
        else:
            workload = "development"
            cpu_cores = 2
            memory_mb = 8192
        
        vm_inventory.append({
            "VM": f"vm-{workload}-{i+1:03d}",
            "CPUs": cpu_cores,
            "Memory": memory_mb,
            "Powerstate": "poweredOn",
            "workload_type": workload
        })
    
    return vm_inventory

def _filter_ri_recommendations(
    ri_portfolio: Any, 
    preferred_term: RITerm, 
    preferred_payment: RIPaymentOption,
    budget_limit: Optional[float],
    stability_score: float
) -> List[Dict]:
    """Filter RI recommendations based on preferences"""
    
    all_recommendations = ri_portfolio.one_year_recommendations + ri_portfolio.three_year_recommendations
    filtered_recommendations = []
    
    for rec in all_recommendations:
        # Filter by term preference
        if preferred_term and rec.term != preferred_term:
            continue
        
        # Filter by payment preference
        if preferred_payment and rec.payment_option != preferred_payment:
            continue
        
        # Filter by budget
        if budget_limit and rec.total_upfront_cost > budget_limit:
            continue
        
        # Filter by stability requirements
        if stability_score < 70 and rec.term == RITerm.THREE_YEAR:
            continue
        
        filtered_recommendations.append({
            "instance_type": rec.instance_type,
            "term": rec.term.value,
            "payment_option": rec.payment_option.value,
            "quantity": rec.recommended_quantity,
            "upfront_cost": rec.total_upfront_cost,
            "annual_savings": rec.estimated_annual_savings,
            "savings_percentage": rec.savings_percentage,
            "risk_level": rec.risk_level,
            "confidence_score": rec.confidence_score
        })
    
    return filtered_recommendations

def _generate_ri_implementation_guidance(
    recommendations: List[Dict], 
    stability_score: float
) -> List[str]:
    """Generate implementation guidance for RI recommendations"""
    
    guidance = []
    
    if recommendations:
        guidance.append("Start with highest-confidence recommendations first")
        
        if stability_score < 70:
            guidance.append("Begin with 1-year terms due to lower workload stability")
        else:
            guidance.append("Consider 3-year terms for maximum savings on stable workloads")
        
        guidance.append("Implement in phases to validate utilization patterns")
        guidance.append("Monitor utilization closely in first 90 days")
        
        high_upfront_count = sum(1 for r in recommendations if r.get("upfront_cost", 0) > 5000)
        if high_upfront_count > 0:
            guidance.append("Consider partial-upfront options to manage cash flow")
    else:
        guidance.append("No suitable RI recommendations found")
        guidance.append("Focus on workload stabilization before considering RIs")
    
    return guidance

async def _analyze_ri_scenario(scenario: Dict[str, Any], metrics: List[str]) -> Dict[str, Any]:
    """Analyze a single RI scenario"""
    
    analysis = {
        "term": scenario.get("term", "1_year"),
        "payment_option": scenario.get("payment_option", "no_upfront"),
        "instance_type": scenario.get("instance_type", "m5.large")
    }
    
    if "savings" in metrics:
        base_savings = 25 if scenario.get("term") == "1_year" else 45
        payment_bonus = {"no_upfront": 0, "partial_upfront": 3, "all_upfront": 7}.get(
            scenario.get("payment_option", "no_upfront"), 0
        )
        analysis["savings_percentage"] = base_savings + payment_bonus
    
    if "investment" in metrics:
        monthly_cost = scenario.get("monthly_cost", 100)
        upfront_multiplier = {"no_upfront": 0, "partial_upfront": 6, "all_upfront": 12}.get(
            scenario.get("payment_option", "no_upfront"), 0
        )
        analysis["upfront_investment"] = monthly_cost * upfront_multiplier
    
    if "risk" in metrics:
        term_risk = 20 if scenario.get("term") == "1_year" else 40
        payment_risk = {"no_upfront": 0, "partial_upfront": 10, "all_upfront": 20}.get(
            scenario.get("payment_option", "no_upfront"), 0
        )
        analysis["risk_score"] = term_risk + payment_risk
    
    if "payback" in metrics:
        savings_pct = analysis.get("savings_percentage", 25)
        upfront = analysis.get("upfront_investment", 0)
        monthly_cost = scenario.get("monthly_cost", 100)
        monthly_savings = monthly_cost * (savings_pct / 100)
        analysis["payback_months"] = (upfront / monthly_savings) if monthly_savings > 0 else 0
    
    return analysis

def _generate_ri_comparison_summary(results: List[Dict], metrics: List[str]) -> Dict[str, Any]:
    """Generate comparison summary across RI scenarios"""
    
    summary = {}
    
    if "savings" in metrics:
        savings_values = [r.get("savings_percentage", 0) for r in results]
        summary["savings"] = {
            "highest": max(savings_values),
            "lowest": min(savings_values),
            "average": sum(savings_values) / len(savings_values)
        }
    
    if "investment" in metrics:
        investment_values = [r.get("upfront_investment", 0) for r in results]
        summary["investment"] = {
            "highest": max(investment_values),
            "lowest": min(investment_values),
            "average": sum(investment_values) / len(investment_values)
        }
    
    if "risk" in metrics:
        risk_values = [r.get("risk_score", 0) for r in results]
        summary["risk"] = {
            "highest": max(risk_values),
            "lowest": min(risk_values),
            "average": sum(risk_values) / len(risk_values)
        }
    
    return summary

def _recommend_best_ri_scenario(results: List[Dict]) -> Dict[str, Any]:
    """Recommend the best RI scenario based on analysis"""
    
    best_scenario = None
    best_score = -1
    
    for result in results:
        savings = result.get("savings_percentage", 0)
        risk = result.get("risk_score", 100)
        investment = result.get("upfront_investment", 0)
        
        # Score = savings - risk penalty - investment penalty
        score = savings - (risk / 2) - (investment / 1000)
        
        if score > best_score:
            best_score = score
            best_scenario = result
    
    return {
        "scenario": best_scenario,
        "score": best_score,
        "reasoning": "Optimizes for highest savings with acceptable risk and investment levels"
    }
