"""
Cost Analysis models for storing AWS cost estimates and TCO calculations
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import BaseModel

class CostAnalysis(BaseModel):
    """Main cost analysis results for a session"""
    __tablename__ = 'cost_analysis'
    
    # Session relationship
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False, unique=True)
    
    # TCO Parameters used for calculation
    target_region = Column(String(50), nullable=False, default='us-east-1')
    pricing_model = Column(String(50), nullable=False, default='on_demand')  # on_demand, reserved, spot
    instance_family = Column(String(50), default='general_purpose')  # general_purpose, compute_optimized, memory_optimized
    reserved_instance_term = Column(String(20))  # 1year, 3year
    reserved_instance_payment = Column(String(20))  # no_upfront, partial_upfront, all_upfront
    
    # Cost Summary
    total_monthly_cost = Column(Float, nullable=False)
    total_annual_cost = Column(Float, nullable=False)
    
    # Cost breakdown
    infrastructure_monthly_cost = Column(Float, default=0)
    network_monthly_cost = Column(Float, default=0)
    storage_monthly_cost = Column(Float, default=0)
    observability_monthly_cost = Column(Float, default=0)
    backup_monthly_cost = Column(Float, default=0)
    
    # Comparison with current environment
    current_environment_monthly_cost = Column(Float)  # If provided
    monthly_savings = Column(Float)  # Positive = savings, Negative = additional cost
    annual_savings = Column(Float)
    savings_percentage = Column(Float)
    
    # Analysis metadata
    calculation_date = Column(DateTime, default=datetime.utcnow)
    pricing_data_version = Column(String(50))
    exchange_rate_used = Column(Float, default=1.0)  # For non-USD currencies
    currency = Column(String(10), default='USD')
    
    # Optimization recommendations
    optimization_opportunities = Column(JSON)  # List of cost optimization suggestions
    potential_monthly_savings = Column(Float, default=0)
    
    # Analysis parameters and assumptions
    analysis_assumptions = Column(JSON)  # Document assumptions made
    utilization_assumptions = Column(JSON)  # CPU/Memory utilization assumptions
    
    # Relationships
    session = relationship("Session", back_populates="cost_analysis")
    cost_estimates = relationship("CostEstimate", back_populates="analysis", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CostAnalysis(session_id='{self.session_id}', monthly_cost=${self.total_monthly_cost:.2f})>"
    
    def get_cost_breakdown(self):
        """Get detailed cost breakdown"""
        return {
            'infrastructure': self.infrastructure_monthly_cost,
            'network': self.network_monthly_cost,
            'storage': self.storage_monthly_cost,
            'observability': self.observability_monthly_cost,
            'backup': self.backup_monthly_cost,
            'total': self.total_monthly_cost
        }
    
    def get_savings_analysis(self):
        """Get savings analysis if current costs are provided"""
        if self.current_environment_monthly_cost:
            return {
                'current_monthly': self.current_environment_monthly_cost,
                'aws_monthly': self.total_monthly_cost,
                'monthly_savings': self.monthly_savings,
                'annual_savings': self.annual_savings,
                'savings_percentage': self.savings_percentage
            }
        return None

class CostEstimate(BaseModel):
    """Individual VM cost estimates"""
    __tablename__ = 'cost_estimates'
    
    # Relationships
    analysis_id = Column(UUID(as_uuid=True), ForeignKey('cost_analysis.id'), nullable=False)
    vm_id = Column(UUID(as_uuid=True), ForeignKey('vm_inventory.id'), nullable=False)
    
    # Instance recommendation
    recommended_instance_type = Column(String(50), nullable=False)
    recommended_instance_size = Column(String(50), nullable=False)
    instance_family = Column(String(50))
    
    # Pricing details
    pricing_plan = Column(String(50), nullable=False)  # on_demand, reserved_1yr, reserved_3yr, spot
    hourly_rate = Column(Float, nullable=False)
    monthly_compute_cost = Column(Float, nullable=False)
    
    # Storage costs
    ebs_volume_type = Column(String(20), default='gp3')
    ebs_volume_size_gb = Column(Integer)
    monthly_storage_cost = Column(Float, default=0)
    
    # Network costs
    monthly_network_cost = Column(Float, default=0)
    data_transfer_gb_estimate = Column(Float, default=0)
    
    # Additional services
    monthly_backup_cost = Column(Float, default=0)
    monthly_monitoring_cost = Column(Float, default=0)
    
    # Total costs
    total_monthly_cost = Column(Float, nullable=False)
    total_annual_cost = Column(Float, nullable=False)
    
    # Optimization flags
    rightsizing_opportunity = Column(Boolean, default=False)
    rightsizing_potential_savings = Column(Float, default=0)
    reserved_instance_savings = Column(Float, default=0)
    
    # Confidence and metadata
    confidence_score = Column(Float, default=0.8)  # 0.0-1.0
    calculation_notes = Column(JSON)  # Store calculation details
    
    # Performance matching
    cpu_match_score = Column(Float)  # How well CPU requirements match
    memory_match_score = Column(Float)  # How well memory requirements match
    storage_match_score = Column(Float)  # How well storage requirements match
    
    # Relationships
    analysis = relationship("CostAnalysis", back_populates="cost_estimates")
    vm = relationship("VMInventory", back_populates="cost_estimates")
    
    def __repr__(self):
        return f"<CostEstimate(vm_id='{self.vm_id}', instance='{self.recommended_instance_type}', cost=${self.total_monthly_cost:.2f})>"
    
    def get_cost_breakdown(self):
        """Get detailed cost breakdown for this VM"""
        return {
            'compute': self.monthly_compute_cost,
            'storage': self.monthly_storage_cost,
            'network': self.monthly_network_cost,
            'backup': self.monthly_backup_cost,
            'monitoring': self.monthly_monitoring_cost,
            'total': self.total_monthly_cost
        }
    
    def get_optimization_opportunities(self):
        """Get optimization opportunities for this VM"""
        opportunities = []
        
        if self.rightsizing_opportunity and self.rightsizing_potential_savings > 0:
            opportunities.append({
                'type': 'rightsizing',
                'description': 'Instance can be rightsized for better cost efficiency',
                'potential_monthly_savings': self.rightsizing_potential_savings
            })
        
        if self.reserved_instance_savings > 0:
            opportunities.append({
                'type': 'reserved_instances',
                'description': 'Reserved Instance pricing can reduce costs',
                'potential_monthly_savings': self.reserved_instance_savings
            })
        
        return opportunities
    
    def to_dict(self):
        """Convert to dictionary with VM information"""
        data = super().to_dict()
        if self.vm:
            data['vm_name'] = self.vm.vm_name
            data['vm_cpus'] = self.vm.cpus
            data['vm_memory_gb'] = self.vm.memory_gb
            data['vm_cluster'] = self.vm.cluster
        
        data['cost_breakdown'] = self.get_cost_breakdown()
        data['optimization_opportunities'] = self.get_optimization_opportunities()
        return data
