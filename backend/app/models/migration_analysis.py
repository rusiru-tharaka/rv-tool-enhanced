"""
Migration Analysis models for storing migration assessment results
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel

class BlockerSeverity(str, Enum):
    """Migration blocker severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MigrationComplexity(str, Enum):
    """Migration complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MigrationAnalysis(BaseModel):
    """Main migration analysis results for a session"""
    __tablename__ = 'migration_analysis'
    
    # Session relationship
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False, unique=True)
    
    # Overall assessment
    overall_complexity = Column(SQLEnum(MigrationComplexity), nullable=False)
    complexity_score = Column(Integer, nullable=False)  # 0-100 scale
    estimated_timeline_months = Column(Integer)
    confidence_level = Column(Float)  # 0.0-1.0
    
    # Workload classification summary
    workload_classifications = Column(JSON)  # List of classification results
    
    # Migration strategy recommendations
    recommended_strategy = Column(String(100))  # lift-and-shift, re-platform, refactor, etc.
    migration_waves = Column(JSON)  # Recommended migration waves
    
    # Risk assessment
    risk_level = Column(String(50))  # low, medium, high, critical
    risk_factors = Column(JSON)  # List of identified risk factors
    
    # Dependencies
    dependency_complexity = Column(String(50))
    external_dependencies = Column(JSON)  # List of external dependencies
    
    # Summary statistics
    total_blockers = Column(Integer, default=0)
    critical_blockers = Column(Integer, default=0)
    high_blockers = Column(Integer, default=0)
    medium_blockers = Column(Integer, default=0)
    low_blockers = Column(Integer, default=0)
    
    # Analysis metadata
    analysis_version = Column(String(50))
    analysis_parameters = Column(JSON)
    
    # Relationships
    session = relationship("Session", back_populates="migration_analysis")
    migration_blockers = relationship("MigrationBlocker", back_populates="analysis", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MigrationAnalysis(session_id='{self.session_id}', complexity='{self.overall_complexity}')>"
    
    def get_blocker_summary(self):
        """Get summary of migration blockers by severity"""
        return {
            'total': self.total_blockers,
            'critical': self.critical_blockers,
            'high': self.high_blockers,
            'medium': self.medium_blockers,
            'low': self.low_blockers
        }

class MigrationBlocker(BaseModel):
    """Individual migration blockers identified for VMs"""
    __tablename__ = 'migration_blockers'
    
    # Relationships
    analysis_id = Column(UUID(as_uuid=True), ForeignKey('migration_analysis.id'), nullable=False)
    vm_id = Column(UUID(as_uuid=True), ForeignKey('vm_inventory.id'), nullable=False)
    
    # Blocker details
    blocker_type = Column(String(100), nullable=False)  # hardware, software, network, etc.
    severity = Column(SQLEnum(BlockerSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Impact assessment
    impact_description = Column(Text)
    business_impact = Column(String(50))  # low, medium, high, critical
    technical_impact = Column(String(50))  # low, medium, high, critical
    
    # Remediation
    remediation_strategy = Column(Text)
    remediation_effort = Column(String(50))  # hours, days, weeks, months
    remediation_cost_estimate = Column(Float)  # USD
    
    # Resolution tracking
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_by = Column(String(255))
    
    # Additional metadata
    detected_by = Column(String(100))  # automated, manual, ai
    confidence_score = Column(Float)  # 0.0-1.0
    tags = Column(JSON)  # List of tags for categorization
    
    # Relationships
    analysis = relationship("MigrationAnalysis", back_populates="migration_blockers")
    vm = relationship("VMInventory", back_populates="migration_blockers")
    
    def __repr__(self):
        return f"<MigrationBlocker(type='{self.blocker_type}', severity='{self.severity}')>"
    
    def to_dict(self):
        """Convert to dictionary with VM information"""
        data = super().to_dict()
        if self.vm:
            data['vm_name'] = self.vm.vm_name
            data['vm_cluster'] = self.vm.cluster
        return data
