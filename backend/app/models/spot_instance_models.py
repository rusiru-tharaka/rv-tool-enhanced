"""
Spot Instance Models
Phase 2.3: Spot Instance Pricing
Comprehensive data models for Spot Instance analysis and recommendations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum

class SpotInstanceState(str, Enum):
    """Spot Instance request states"""
    PENDING_EVALUATION = "pending-evaluation"
    PENDING_FULFILLMENT = "pending-fulfillment"
    ACTIVE = "active"
    CANCELLED_RUNNING = "cancelled-running"
    CANCELLED_TERMINATING = "cancelled-terminating"
    CLOSED = "closed"
    FAILED = "failed"

class SpotFleetState(str, Enum):
    """Spot Fleet request states"""
    SUBMITTED = "submitted"
    ACTIVE = "active"
    CANCELLED_RUNNING = "cancelled_running"
    CANCELLED_TERMINATING = "cancelled_terminating"
    CANCELLED = "cancelled"
    MODIFYING = "modifying"

class InterruptionRisk(str, Enum):
    """Spot Instance interruption risk levels"""
    VERY_LOW = "very_low"      # <5% interruption frequency
    LOW = "low"                # 5-10% interruption frequency
    MODERATE = "moderate"      # 10-15% interruption frequency
    HIGH = "high"              # 15-20% interruption frequency
    VERY_HIGH = "very_high"    # >20% interruption frequency

class SpotStrategy(str, Enum):
    """Spot Instance bidding strategies"""
    LOWEST_PRICE = "lowest_price"
    DIVERSIFIED = "diversified"
    CAPACITY_OPTIMIZED = "capacity_optimized"
    CAPACITY_OPTIMIZED_PRIORITIZED = "capacity_optimized_prioritized"

@dataclass
class SpotPriceHistory:
    """Historical spot price data point"""
    instance_type: str
    availability_zone: str
    timestamp: datetime
    spot_price: float
    product_description: str = "Linux/UNIX"
    
    # Calculated fields
    price_change: Optional[float] = None  # Change from previous price
    price_change_percentage: Optional[float] = None
    volatility_score: Optional[float] = None  # 0-100, higher = more volatile

@dataclass
class SpotPriceAnalysis:
    """Comprehensive spot price analysis for an instance type"""
    instance_type: str
    region: str
    availability_zones: List[str] = field(default_factory=list)
    
    # Current pricing
    current_spot_price: float = 0.0
    on_demand_price: float = 0.0
    current_savings_percentage: float = 0.0
    
    # Historical analysis
    price_history: List[SpotPriceHistory] = field(default_factory=list)
    average_price_7d: float = 0.0
    average_price_30d: float = 0.0
    min_price_30d: float = 0.0
    max_price_30d: float = 0.0
    
    # Volatility metrics
    price_volatility: float = 0.0  # Standard deviation of prices
    volatility_score: float = 0.0  # 0-100, normalized volatility
    stability_score: float = 0.0   # 0-100, inverse of volatility
    
    # Interruption analysis
    interruption_frequency: float = 0.0  # Interruptions per week
    interruption_risk: InterruptionRisk = InterruptionRisk.MODERATE
    average_runtime_hours: float = 0.0
    
    # Availability analysis
    availability_score: float = 0.0  # 0-100, capacity availability
    best_availability_zones: List[str] = field(default_factory=list)
    
    # Recommendations
    recommended_bid_price: float = 0.0
    recommended_strategy: SpotStrategy = SpotStrategy.CAPACITY_OPTIMIZED
    suitability_score: float = 0.0  # 0-100, overall suitability for spot

@dataclass
class SpotInstanceRecommendation:
    """Spot Instance recommendation with detailed analysis"""
    instance_type: str
    instance_family: str
    region: str
    availability_zones: List[str] = field(default_factory=list)
    
    # Pricing analysis
    current_spot_price: float = 0.0
    recommended_bid_price: float = 0.0
    on_demand_price: float = 0.0
    potential_savings: float = 0.0
    savings_percentage: float = 0.0
    
    # Risk assessment
    interruption_risk: InterruptionRisk = InterruptionRisk.MODERATE
    expected_runtime_hours: float = 0.0
    interruption_frequency: float = 0.0
    
    # Capacity and availability
    capacity_score: float = 0.0  # 0-100, likelihood of getting capacity
    availability_zones_ranked: List[Tuple[str, float]] = field(default_factory=list)  # (AZ, score)
    
    # Strategy recommendations
    recommended_strategy: SpotStrategy = SpotStrategy.CAPACITY_OPTIMIZED
    diversification_recommendation: bool = False
    mixed_instance_types: List[str] = field(default_factory=list)
    
    # Workload suitability
    workload_suitability: Dict[str, float] = field(default_factory=dict)  # workload_type -> suitability_score
    fault_tolerance_required: bool = True
    
    # Financial projections
    estimated_monthly_cost: float = 0.0
    estimated_monthly_savings: float = 0.0
    cost_with_interruptions: float = 0.0  # Including restart costs
    
    # Implementation guidance
    implementation_notes: List[str] = field(default_factory=list)
    monitoring_requirements: List[str] = field(default_factory=list)
    fallback_strategies: List[str] = field(default_factory=list)

@dataclass
class SpotFleetConfiguration:
    """Spot Fleet configuration recommendation"""
    fleet_name: str
    target_capacity: int
    allocation_strategy: SpotStrategy = SpotStrategy.CAPACITY_OPTIMIZED
    
    # Instance specifications
    instance_specifications: List[Dict[str, Any]] = field(default_factory=list)
    # Each spec: {"instance_type": str, "weight": int, "subnet_ids": List[str], "spot_price": float}
    
    # Fleet settings
    replace_unhealthy_instances: bool = True
    terminate_instances_on_delete: bool = True
    instance_interruption_behavior: str = "terminate"  # terminate, stop, hibernate
    
    # Pricing and capacity
    total_spot_price_limit: Optional[float] = None
    on_demand_allocation_strategy: str = "lowest-price"
    on_demand_percentage: int = 0  # Percentage of capacity to maintain as on-demand
    
    # Scaling configuration
    auto_scaling_enabled: bool = False
    min_capacity: int = 1
    max_capacity: Optional[int] = None
    
    # Cost projections
    estimated_hourly_cost: float = 0.0
    estimated_monthly_cost: float = 0.0
    potential_monthly_savings: float = 0.0
    
    # Risk management
    diversification_score: float = 0.0  # 0-100, higher = more diversified
    interruption_resilience: float = 0.0  # 0-100, higher = more resilient
    
    # Monitoring and alerts
    cloudwatch_monitoring: bool = True
    interruption_alerts: bool = True
    capacity_alerts: bool = True

@dataclass
class SpotInstanceUtilization:
    """Spot Instance utilization and performance metrics"""
    instance_id: str
    instance_type: str
    availability_zone: str
    launch_time: datetime
    
    # Current status
    state: SpotInstanceState = SpotInstanceState.ACTIVE
    spot_price_paid: float = 0.0
    current_spot_price: float = 0.0
    
    # Runtime metrics
    total_runtime_hours: float = 0.0
    interruptions_count: int = 0
    average_session_hours: float = 0.0
    longest_session_hours: float = 0.0
    
    # Cost metrics
    total_cost: float = 0.0
    cost_per_hour: float = 0.0
    savings_vs_on_demand: float = 0.0
    savings_percentage: float = 0.0
    
    # Performance indicators
    utilization_efficiency: float = 0.0  # 0-100, how well capacity is used
    interruption_impact: float = 0.0     # 0-100, impact of interruptions on workload
    
    # Interruption history
    interruption_events: List[Dict[str, Any]] = field(default_factory=list)
    # Each event: {"timestamp": datetime, "reason": str, "warning_time": int}

@dataclass
class SpotMarketAnalysis:
    """Comprehensive spot market analysis for a region"""
    region: str
    analysis_timestamp: datetime
    
    # Market overview
    total_instance_types_analyzed: int = 0
    average_savings_percentage: float = 0.0
    market_volatility_score: float = 0.0  # 0-100, overall market volatility
    
    # Instance family analysis
    family_analysis: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # family -> {"avg_savings": float, "volatility": float, "availability": float}
    
    # Availability zone analysis
    az_analysis: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # az -> {"capacity_score": float, "price_competitiveness": float}
    
    # Trending data
    price_trends: Dict[str, str] = field(default_factory=dict)  # instance_type -> trend ("rising", "falling", "stable")
    capacity_trends: Dict[str, str] = field(default_factory=dict)  # instance_type -> trend
    
    # Market recommendations
    best_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    # Each opportunity: {"instance_type": str, "savings": float, "risk": str, "recommendation": str}
    
    market_timing_advice: str = ""
    risk_factors: List[str] = field(default_factory=list)
    
    # Seasonal patterns
    seasonal_patterns: Dict[str, List[float]] = field(default_factory=dict)  # instance_type -> monthly_multipliers

@dataclass
class SpotOptimizationStrategy:
    """Comprehensive Spot Instance optimization strategy"""
    strategy_name: str
    description: str
    target_workload_types: List[str] = field(default_factory=list)
    
    # Strategic components
    spot_recommendations: List[SpotInstanceRecommendation] = field(default_factory=list)
    fleet_configurations: List[SpotFleetConfiguration] = field(default_factory=list)
    
    # Financial projections
    total_potential_savings: float = 0.0
    monthly_cost_reduction: float = 0.0
    annual_savings_projection: float = 0.0
    
    # Risk management
    overall_risk_level: InterruptionRisk = InterruptionRisk.MODERATE
    risk_mitigation_measures: List[str] = field(default_factory=list)
    fallback_strategies: List[str] = field(default_factory=list)
    
    # Implementation plan
    implementation_phases: List[Dict[str, Any]] = field(default_factory=list)
    # Each phase: {"name": str, "duration_weeks": int, "actions": List[str], "expected_savings": float}
    
    timeline_weeks: int = 8
    success_criteria: List[str] = field(default_factory=list)
    
    # Monitoring and optimization
    monitoring_requirements: List[str] = field(default_factory=list)
    optimization_triggers: List[str] = field(default_factory=list)
    review_frequency_weeks: int = 2
    
    # Integration with other pricing models
    hybrid_approach: bool = False
    on_demand_percentage: float = 0.0
    reserved_instance_percentage: float = 0.0
    spot_percentage: float = 100.0

@dataclass
class SpotInstanceAlert:
    """Spot Instance monitoring alert"""
    alert_id: str
    instance_id: str
    alert_type: str  # "price_spike", "interruption_warning", "capacity_shortage"
    severity: str    # "info", "warning", "critical"
    
    timestamp: datetime
    message: str
    current_spot_price: float
    threshold_price: float
    
    # Alert-specific data
    alert_data: Dict[str, Any] = field(default_factory=dict)
    
    # Response recommendations
    recommended_actions: List[str] = field(default_factory=list)
    auto_response_enabled: bool = False
    
    # Status tracking
    acknowledged: bool = False
    resolved: bool = False
    resolution_notes: Optional[str] = None
