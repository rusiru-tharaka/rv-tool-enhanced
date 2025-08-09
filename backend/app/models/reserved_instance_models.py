"""
Reserved Instance Models
Phase 2.2: Reserved Instance Optimization
Comprehensive data models for RI analysis and recommendations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

class RITerm(str, Enum):
    """Reserved Instance term options"""
    ONE_YEAR = "1_year"
    THREE_YEAR = "3_year"

class RIPaymentOption(str, Enum):
    """Reserved Instance payment options"""
    NO_UPFRONT = "no_upfront"
    PARTIAL_UPFRONT = "partial_upfront"
    ALL_UPFRONT = "all_upfront"

class RIOfferingClass(str, Enum):
    """Reserved Instance offering class"""
    STANDARD = "standard"
    CONVERTIBLE = "convertible"

class RIScope(str, Enum):
    """Reserved Instance scope"""
    AVAILABILITY_ZONE = "availability_zone"
    REGION = "region"

@dataclass
class RIUtilizationMetrics:
    """Reserved Instance utilization metrics"""
    utilization_percentage: float = 0.0
    hours_used: float = 0.0
    hours_reserved: float = 0.0
    net_savings: float = 0.0
    on_demand_cost_equivalent: float = 0.0
    ri_cost: float = 0.0
    
    # Time-based metrics
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Performance indicators
    underutilization_hours: float = 0.0
    overutilization_cost: float = 0.0
    efficiency_score: float = 0.0  # 0-100

@dataclass
class RIPricingDetails:
    """Detailed Reserved Instance pricing information"""
    instance_type: str
    region: str
    availability_zone: Optional[str] = None
    
    # Pricing structure
    term: RITerm = RITerm.ONE_YEAR
    payment_option: RIPaymentOption = RIPaymentOption.NO_UPFRONT
    offering_class: RIOfferingClass = RIOfferingClass.STANDARD
    scope: RIScope = RIScope.REGION
    
    # Cost breakdown
    upfront_cost: float = 0.0
    hourly_cost: float = 0.0
    effective_hourly_cost: float = 0.0  # Including amortized upfront
    
    # Comparison with on-demand
    on_demand_hourly: float = 0.0
    hourly_savings: float = 0.0
    savings_percentage: float = 0.0
    
    # Break-even analysis
    break_even_hours: int = 0
    break_even_months: float = 0.0
    
    # Additional metadata
    platform: str = "Linux/UNIX"
    tenancy: str = "default"
    product_description: str = ""

@dataclass
class RIRecommendation:
    """Reserved Instance purchase recommendation"""
    instance_type: str
    instance_family: str
    region: str
    availability_zone: Optional[str] = None
    
    # Recommendation details
    recommended_quantity: int = 1
    term: RITerm = RITerm.ONE_YEAR
    payment_option: RIPaymentOption = RIPaymentOption.NO_UPFRONT
    offering_class: RIOfferingClass = RIOfferingClass.STANDARD
    
    # Financial analysis
    total_upfront_cost: float = 0.0
    monthly_recurring_cost: float = 0.0
    annual_cost: float = 0.0
    
    # Savings analysis
    estimated_monthly_savings: float = 0.0
    estimated_annual_savings: float = 0.0
    savings_percentage: float = 0.0
    payback_period_months: float = 0.0
    
    # Risk assessment
    utilization_requirement: float = 0.0  # Minimum utilization needed to break even
    confidence_score: float = 0.0  # 0-1, based on historical usage patterns
    risk_level: str = "medium"  # low, medium, high
    
    # Supporting data
    historical_usage_hours: float = 0.0
    projected_usage_hours: float = 0.0
    workload_stability_score: float = 0.0
    
    # Optimization notes
    optimization_notes: List[str] = field(default_factory=list)
    alternative_options: List[Dict] = field(default_factory=list)

@dataclass
class RIPortfolio:
    """Complete Reserved Instance portfolio analysis"""
    session_id: str
    analysis_timestamp: datetime
    
    # Portfolio summary
    total_recommendations: int = 0
    total_upfront_investment: float = 0.0
    total_annual_savings: float = 0.0
    portfolio_savings_percentage: float = 0.0
    
    # Recommendations by category
    one_year_recommendations: List[RIRecommendation] = field(default_factory=list)
    three_year_recommendations: List[RIRecommendation] = field(default_factory=list)
    
    # Payment option analysis
    no_upfront_total: float = 0.0
    partial_upfront_total: float = 0.0
    all_upfront_total: float = 0.0
    
    # Risk analysis
    portfolio_risk_score: float = 0.0  # 0-100
    diversification_score: float = 0.0  # 0-100
    liquidity_impact: float = 0.0  # Cash flow impact
    
    # Performance projections
    projected_utilization: Dict[str, float] = field(default_factory=dict)
    break_even_timeline: Dict[str, float] = field(default_factory=dict)
    
    # Optimization insights
    optimization_opportunities: List[Dict] = field(default_factory=list)
    risk_mitigation_strategies: List[str] = field(default_factory=list)

@dataclass
class RIUtilizationReport:
    """Reserved Instance utilization analysis report"""
    ri_id: str
    instance_type: str
    region: str
    
    # Current RI details
    term: RITerm
    payment_option: RIPaymentOption
    start_date: datetime
    end_date: datetime
    
    # Utilization metrics
    current_utilization: RIUtilizationMetrics
    historical_utilization: List[RIUtilizationMetrics] = field(default_factory=list)
    
    # Performance analysis
    average_utilization: float = 0.0
    peak_utilization: float = 0.0
    minimum_utilization: float = 0.0
    utilization_trend: str = "stable"  # increasing, decreasing, stable, volatile
    
    # Financial impact
    actual_savings: float = 0.0
    potential_savings: float = 0.0
    savings_realization: float = 0.0  # Percentage of potential savings achieved
    
    # Optimization recommendations
    optimization_recommendations: List[str] = field(default_factory=list)
    modification_suggestions: List[Dict] = field(default_factory=list)

@dataclass
class RIModificationOption:
    """Reserved Instance modification options"""
    current_ri_id: str
    modification_type: str  # "exchange", "modify", "split", "merge"
    
    # Current configuration
    current_instance_type: str
    current_quantity: int
    
    # Target configuration
    target_instance_type: str
    target_quantity: int
    target_availability_zone: Optional[str] = None
    
    # Financial impact
    cost_difference: float = 0.0
    savings_impact: float = 0.0
    
    # Feasibility
    is_feasible: bool = True
    constraints: List[str] = field(default_factory=list)
    
    # Timeline
    processing_time_days: int = 1
    effective_date: Optional[datetime] = None

@dataclass
class RIOptimizationStrategy:
    """Comprehensive RI optimization strategy"""
    strategy_name: str
    description: str
    
    # Strategic components
    purchase_recommendations: List[RIRecommendation] = field(default_factory=list)
    modification_recommendations: List[RIModificationOption] = field(default_factory=list)
    
    # Financial projections
    total_investment_required: float = 0.0
    projected_annual_savings: float = 0.0
    roi_percentage: float = 0.0
    payback_period_months: float = 0.0
    
    # Implementation plan
    implementation_phases: List[Dict] = field(default_factory=list)
    timeline_months: int = 12
    
    # Risk assessment
    strategy_risk_level: str = "medium"
    risk_factors: List[str] = field(default_factory=list)
    mitigation_plans: List[str] = field(default_factory=list)
    
    # Success metrics
    success_criteria: List[str] = field(default_factory=list)
    monitoring_requirements: List[str] = field(default_factory=list)
