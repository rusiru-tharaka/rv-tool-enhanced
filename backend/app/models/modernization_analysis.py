"""
Modernization Analysis models for storing modernization opportunities and recommendations
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel

class ModernizationType(str, Enum):
    """Types of modernization opportunities"""
    CONTAINERIZATION = "containerization"
    SERVERLESS = "serverless"
    MANAGED_DATABASE = "managed_database"
    MANAGED_SERVICE = "managed_service"
    CLOUD_NATIVE = "cloud_native"
    MICROSERVICES = "microservices"

class ImplementationComplexity(str, Enum):
    """Implementation complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ModernizationAnalysis(BaseModel):
    """Main modernization analysis results for a session"""
    __tablename__ = 'modernization_analysis'
    
    # Session relationship
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False, unique=True)
    
    # Summary statistics
    total_opportunities = Column(Integer, default=0)
    total_vms_analyzed = Column(Integer, default=0)
    modernizable_vms = Column(Integer, default=0)
    modernization_percentage = Column(Float, default=0.0)  # Percentage of VMs that can be modernized
    
    # Cost impact summary
    total_current_monthly_cost = Column(Float, default=0)
    total_modernized_monthly_cost = Column(Float, default=0)
    total_monthly_savings = Column(Float, default=0)
    total_annual_savings = Column(Float, default=0)
    average_savings_percentage = Column(Float, default=0.0)
    
    # Modernization categories breakdown
    modernization_categories = Column(JSON)  # Count by modernization type
    complexity_breakdown = Column(JSON)  # Count by implementation complexity
    
    # Implementation timeline
    estimated_implementation_months = Column(Integer)
    quick_wins_count = Column(Integer, default=0)  # Low complexity opportunities
    
    # Business impact assessment
    business_value_score = Column(Float)  # 0.0-10.0 scale
    innovation_potential = Column(String(50))  # low, medium, high
    operational_efficiency_gain = Column(Float)  # Percentage improvement
    
    # Risk assessment
    modernization_risk_level = Column(String(50))  # low, medium, high
    risk_factors = Column(JSON)  # List of identified risks
    mitigation_strategies = Column(JSON)  # Risk mitigation recommendations
    
    # Analysis metadata
    analysis_methodology = Column(String(100))
    confidence_level = Column(Float, default=0.8)  # 0.0-1.0
    analysis_parameters = Column(JSON)
    
    # Relationships
    session = relationship("Session", back_populates="modernization_analysis")
    modernization_opportunities = relationship("ModernizationOpportunity", back_populates="analysis", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ModernizationAnalysis(session_id='{self.session_id}', opportunities={self.total_opportunities})>"
    
    def get_savings_summary(self):
        """Get savings summary"""
        return {
            'current_monthly_cost': self.total_current_monthly_cost,
            'modernized_monthly_cost': self.total_modernized_monthly_cost,
            'monthly_savings': self.total_monthly_savings,
            'annual_savings': self.total_annual_savings,
            'savings_percentage': self.average_savings_percentage
        }
    
    def get_implementation_roadmap(self):
        """Get implementation roadmap by complexity"""
        return {
            'quick_wins': self.quick_wins_count,
            'total_timeline_months': self.estimated_implementation_months,
            'complexity_breakdown': self.complexity_breakdown or {},
            'business_value_score': self.business_value_score
        }

class ModernizationOpportunity(BaseModel):
    """Individual modernization opportunities for VMs"""
    __tablename__ = 'modernization_opportunities'
    
    # Relationships
    analysis_id = Column(UUID(as_uuid=True), ForeignKey('modernization_analysis.id'), nullable=False)
    vm_id = Column(UUID(as_uuid=True), ForeignKey('vm_inventory.id'), nullable=False)
    
    # Opportunity details
    modernization_type = Column(SQLEnum(ModernizationType), nullable=False)
    opportunity_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Current vs Target state
    current_workload_type = Column(String(100))
    target_aws_service = Column(String(100), nullable=False)
    target_architecture = Column(Text)
    
    # Cost analysis
    current_monthly_cost = Column(Float, nullable=False)
    modernized_monthly_cost = Column(Float, nullable=False)
    monthly_savings = Column(Float, nullable=False)
    annual_savings = Column(Float, nullable=False)
    savings_percentage = Column(Float)
    
    # Implementation details
    implementation_complexity = Column(SQLEnum(ImplementationComplexity), nullable=False)
    estimated_effort_hours = Column(Integer)
    estimated_timeline_weeks = Column(Integer)
    implementation_cost = Column(Float)  # One-time implementation cost
    
    # Benefits and value
    benefits = Column(JSON)  # List of benefits
    business_value_score = Column(Float)  # 0.0-10.0 scale
    technical_benefits = Column(JSON)  # List of technical benefits
    operational_benefits = Column(JSON)  # List of operational benefits
    
    # Risk assessment
    implementation_risks = Column(JSON)  # List of implementation risks
    risk_mitigation = Column(JSON)  # Risk mitigation strategies
    confidence_score = Column(Float, default=0.8)  # 0.0-1.0
    
    # Prerequisites and dependencies
    prerequisites = Column(JSON)  # List of prerequisites
    dependencies = Column(JSON)  # List of dependencies
    blockers = Column(JSON)  # List of potential blockers
    
    # Success criteria
    success_metrics = Column(JSON)  # List of success metrics
    kpis = Column(JSON)  # Key performance indicators
    
    # Priority and recommendation
    priority_score = Column(Float)  # 0.0-10.0 scale
    recommendation_strength = Column(String(50))  # strongly_recommended, recommended, consider, not_recommended
    
    # Additional metadata
    analysis_notes = Column(Text)
    tags = Column(JSON)  # List of tags for categorization
    
    # Relationships
    analysis = relationship("ModernizationAnalysis", back_populates="modernization_opportunities")
    vm = relationship("VMInventory", back_populates="modernization_opportunities")
    
    def __repr__(self):
        return f"<ModernizationOpportunity(type='{self.modernization_type}', savings=${self.monthly_savings:.2f}/month)>"
    
    def get_roi_analysis(self):
        """Calculate ROI analysis"""
        if self.implementation_cost and self.implementation_cost > 0:
            payback_months = self.implementation_cost / max(self.monthly_savings, 0.01)
            annual_roi = (self.annual_savings / self.implementation_cost) * 100 if self.implementation_cost > 0 else 0
        else:
            payback_months = 0
            annual_roi = float('inf') if self.annual_savings > 0 else 0
        
        return {
            'implementation_cost': self.implementation_cost or 0,
            'monthly_savings': self.monthly_savings,
            'annual_savings': self.annual_savings,
            'payback_months': round(payback_months, 1),
            'annual_roi_percentage': round(annual_roi, 1)
        }
    
    def get_implementation_plan(self):
        """Get implementation plan details"""
        return {
            'complexity': self.implementation_complexity.value,
            'estimated_hours': self.estimated_effort_hours,
            'estimated_weeks': self.estimated_timeline_weeks,
            'prerequisites': self.prerequisites or [],
            'dependencies': self.dependencies or [],
            'blockers': self.blockers or [],
            'risks': self.implementation_risks or [],
            'mitigation': self.risk_mitigation or []
        }
    
    def to_dict(self):
        """Convert to dictionary with VM information and analysis"""
        data = super().to_dict()
        if self.vm:
            data['vm_name'] = self.vm.vm_name
            data['vm_cluster'] = self.vm.cluster
            data['vm_cpus'] = self.vm.cpus
            data['vm_memory_gb'] = self.vm.memory_gb
        
        data['roi_analysis'] = self.get_roi_analysis()
        data['implementation_plan'] = self.get_implementation_plan()
        return data
