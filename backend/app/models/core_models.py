"""
Enhanced UX Core Data Models
Implementation of all Pydantic models for 4-phase migration analysis
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# ============================================================================
# PHASE MANAGEMENT MODELS
# ============================================================================

class AnalysisPhase(str, Enum):
    MIGRATION_SCOPE = "migration_scope"
    COST_ESTIMATES = "cost_estimates"
    MODERNIZATION = "modernization"
    REPORT_GENERATION = "report_generation"

class AnalysisSession(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    current_phase: AnalysisPhase
    vm_inventory: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    completed_phases: List[AnalysisPhase] = []
    
    # Store analysis results for cross-phase integration
    migration_scope_analysis: Optional[Dict[str, Any]] = None
    
class PhaseProgress(BaseModel):
    phase: AnalysisPhase
    completed: bool
    completion_percentage: float = Field(ge=0, le=100)
    data: Optional[Dict[str, Any]] = None

# ============================================================================
# MIGRATION SCOPE MODELS
# ============================================================================

class MigrationBlockerSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MigrationBlocker(BaseModel):
    id: str
    vm_name: str
    severity: MigrationBlockerSeverity
    issue_type: str
    description: str
    remediation: str
    confidence_score: float = Field(ge=0, le=1)
    
class OutOfScopeItem(BaseModel):
    vm_name: str
    reason: str
    category: str  # "vmware_management", "infrastructure", "other"
    auto_detected: bool = True

class WorkloadClassification(BaseModel):
    classification: str  # "production", "development", "testing", "staging"
    vm_count: int
    percentage: float
    vm_names: List[str]

class InfrastructureInsights(BaseModel):
    total_vms: int
    total_storage_tb: float
    os_breakdown: Dict[str, int]  # {"windows": 180, "linux": 65}
    prod_nonprod_ratio: Dict[str, float]  # {"production": 59, "non_production": 41}
    average_vm_specs: Dict[str, float]  # {"cpu": 4, "ram_gb": 12}
    total_resources: Dict[str, float]  # {"total_vcpus": 980, "total_ram_tb": 2.9}

class MigrationScopeAnalysis(BaseModel):
    session_id: str
    total_vms: int
    estimated_timeline_months: int
    complexity_score: int = Field(ge=0, le=100)
    migration_blockers: List[MigrationBlocker]
    out_of_scope_items: List[OutOfScopeItem]
    workload_classifications: List[WorkloadClassification]
    infrastructure_insights: InfrastructureInsights

# ============================================================================
# COST ESTIMATES MODELS
# ============================================================================

class TCOParameters(BaseModel):
    """Enhanced TCO Parameters with Savings Plans and workload-specific pricing"""
    
    # Regional Configuration
    target_region: str = Field(
        default="us-east-1",
        description="Target AWS region for deployment"
    )
    
    # Legacy pricing model (maintained for backward compatibility)
    pricing_model: str = Field(
        default="mixed", 
        pattern="^(on_demand|reserved|mixed)$",
        description="Legacy pricing model (deprecated - use workload-specific models)"
    )
    
    # NEW: Workload-Specific Pricing Models
    production_pricing_model: str = Field(
        default="reserved",
        pattern="^(on_demand|reserved|compute_savings|ec2_savings)$",
        description="Pricing model for production workloads"
    )
    non_production_pricing_model: str = Field(
        default="on_demand",
        pattern="^(on_demand|reserved|compute_savings|ec2_savings)$",
        description="Pricing model for non-production workloads"
    )
    
    # NEW: Savings Plans Configuration
    savings_plan_commitment: str = Field(
        default="1_year",
        pattern="^(1_year|3_year)$",
        description="Savings Plans commitment term"
    )
    savings_plan_payment: str = Field(
        default="no_upfront",
        pattern="^(no_upfront|partial_upfront|all_upfront)$",
        description="Savings Plans payment option"
    )
    
    # NEW: Utilization-Based Pricing
    production_utilization_percent: int = Field(
        default=100,
        ge=25,
        le=100,
        description="Production workload utilization percentage (25-100%)"
    )
    non_production_utilization_percent: int = Field(
        default=50,
        ge=25,
        le=100,
        description="Non-production workload utilization percentage (25-100%)"
    )
    
    # NEW: Operating System Configuration
    default_os_type: str = Field(
        default="linux",
        pattern="^(linux|windows|rhel|suse|ubuntu_pro)$",
        description="Default operating system type for pricing"
    )
    
    # Enhanced Reserved Instance Configuration
    production_ri_years: int = Field(
        default=3,
        ge=1,
        le=3,
        description="Reserved Instance term for production workloads"
    )
    non_production_ri_years: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Reserved Instance term for non-production workloads"
    )
    
    # Legacy field (maintained for backward compatibility)
    production_ri_years_legacy: int = Field(
        default=3,
        ge=1,
        le=3,
        alias="production_ri_years",
        description="Legacy field - use production_ri_years instead"
    )
    
    # Existing Network and Observability Settings
    include_network: bool = Field(
        default=True,
        description="Include network costs in TCO calculation"
    )
    include_observability: bool = Field(
        default=True,
        description="Include observability costs in TCO calculation"
    )
    network_cost_percentage: float = Field(
        default=10.0,
        ge=0.0,
        le=50.0,
        description="Network cost as percentage of infrastructure cost"
    )
    observability_cost_percentage: float = Field(
        default=5.0,
        ge=0.0,
        le=25.0,
        description="Observability cost as percentage of infrastructure cost"
    )
    
    # NEW: Advanced Configuration
    enable_spot_instances: bool = Field(
        default=False,
        description="Enable Spot instance recommendations for suitable workloads"
    )
    spot_interruption_tolerance: str = Field(
        default="low",
        pattern="^(low|medium|high)$",
        description="Tolerance for Spot instance interruptions"
    )
    
    class Config:
        allow_population_by_field_name = True  # Support legacy field names
        schema_extra = {
            "example": {
                "target_region": "us-east-1",
                "production_pricing_model": "compute_savings",
                "non_production_pricing_model": "on_demand",
                "savings_plan_commitment": "3_year",
                "production_utilization_percent": 100,
                "non_production_utilization_percent": 50,
                "default_os_type": "linux",
                "include_network": True,
                "include_observability": True
            }
        }

class VMCostEstimate(BaseModel):
    vm_name: str
    current_cpu: int
    current_ram_gb: float
    current_storage_gb: float
    recommended_instance_family: str
    recommended_instance_size: str
    recommended_instance_type: str  # Added for compatibility
    pricing_plan: str  # "on_demand", "reserved", "compute_savings", "ec2_savings", "spot"
    workload_type: str  # "production", "development", "testing", "staging"
    
    # Cost attributes (multiple naming conventions for compatibility)
    monthly_compute_cost: float  # New naming convention
    monthly_storage_cost: float  # New naming convention
    ec2_monthly_cost: float  # Legacy naming convention
    storage_monthly_cost: float  # Legacy naming convention
    total_monthly_cost: float
    annual_cost: float  # Added for annual calculations
    
    # Additional attributes
    confidence_score: float = 1.0  # Recommendation confidence
    cost_optimization_notes: str = ""  # Optimization suggestions

class CostSummary(BaseModel):
    infrastructure_monthly_cost: float
    network_monthly_cost: float
    observability_monthly_cost: float
    total_monthly_cost: float
    total_annual_cost: float

class CostEstimatesAnalysis(BaseModel):
    session_id: str
    tco_parameters: TCOParameters
    cost_summary: CostSummary
    detailed_estimates: List[VMCostEstimate]
    total_vms_analyzed: int

# ============================================================================
# MODERNIZATION MODELS
# ============================================================================

class ModernizationType(str, Enum):
    MANAGED_DATABASE = "managed_database"
    SERVERLESS = "serverless"
    CONTAINERIZATION = "containerization"
    MANAGED_SERVICES = "managed_services"

class ModernizationOpportunity(BaseModel):
    id: str
    vm_name: str
    current_workload_type: str
    modernization_type: ModernizationType
    target_aws_service: str
    current_monthly_cost: float
    modernized_monthly_cost: float
    monthly_savings: float
    annual_savings: float
    benefits: List[str]
    implementation_complexity: str  # "low", "medium", "high"

class ModernizationCostImpact(BaseModel):
    current_aws_monthly_cost: float
    modernized_aws_monthly_cost: float
    total_monthly_savings: float
    total_annual_savings: float
    savings_percentage: float

class ModernizationAnalysis(BaseModel):
    session_id: str
    cost_impact: ModernizationCostImpact
    opportunities: List[ModernizationOpportunity]
    opportunities_by_type: Dict[ModernizationType, List[ModernizationOpportunity]]
    total_opportunities: int

# ============================================================================
# API RESPONSE MODELS
# ============================================================================

class PaginatedResponse(BaseModel):
    items: List[Any]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class SessionStatusResponse(BaseModel):
    session_id: str
    current_phase: AnalysisPhase
    completed_phases: List[AnalysisPhase]
    total_vms: int
    created_at: datetime
    updated_at: datetime

class PhaseAdvanceResponse(BaseModel):
    session_id: str
    current_phase: AnalysisPhase
    completed_phases: List[AnalysisPhase]
    success: bool
    message: str

# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationError(BaseModel):
    field: str
    message: str
    value: Any
