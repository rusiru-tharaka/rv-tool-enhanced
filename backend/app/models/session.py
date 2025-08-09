"""
Session model for managing analysis sessions
"""
from sqlalchemy import Column, String, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel

class AnalysisPhase(str, Enum):
    """Analysis phase enumeration"""
    MIGRATION_SCOPE = "migration_scope"
    COST_ESTIMATES = "cost_estimates"
    MODERNIZATION_OPPORTUNITIES = "modernization_opportunities"
    IMPLEMENTATION_ROADMAP = "implementation_roadmap"

class Session(BaseModel):
    """Session model for tracking analysis progress"""
    __tablename__ = 'sessions'
    
    # Session identification
    user_id = Column(String(255))  # Optional user identification
    session_name = Column(String(255))
    
    # Current analysis state
    current_phase = Column(SQLEnum(AnalysisPhase), default=AnalysisPhase.MIGRATION_SCOPE, nullable=False)
    completed_phases = Column(JSON, default=list)  # List of completed phases
    
    # VM inventory summary
    total_vms = Column(Integer, default=0)
    total_cpus = Column(Integer, default=0)
    total_memory_gb = Column(Integer, default=0)
    total_storage_gb = Column(Integer, default=0)
    
    # File information
    original_filename = Column(String(500))
    file_size_bytes = Column(Integer)
    file_upload_path = Column(String(1000))  # S3 path or local path
    
    # Analysis metadata
    analysis_metadata = Column(JSON, default=dict)  # Store additional analysis data
    
    # Relationships
    vm_inventory = relationship("VMInventory", back_populates="session", cascade="all, delete-orphan")
    migration_analysis = relationship("MigrationAnalysis", back_populates="session", uselist=False)
    cost_analysis = relationship("CostAnalysis", back_populates="session", uselist=False)
    modernization_analysis = relationship("ModernizationAnalysis", back_populates="session", uselist=False)
    
    def __repr__(self):
        return f"<Session(id='{self.id}', phase='{self.current_phase}', vms={self.total_vms})>"
    
    def can_advance_to_phase(self, target_phase: AnalysisPhase) -> bool:
        """Check if session can advance to target phase"""
        phase_order = [
            AnalysisPhase.MIGRATION_SCOPE,
            AnalysisPhase.COST_ESTIMATES,
            AnalysisPhase.MODERNIZATION_OPPORTUNITIES,
            AnalysisPhase.IMPLEMENTATION_ROADMAP
        ]
        
        try:
            current_index = phase_order.index(self.current_phase)
            target_index = phase_order.index(target_phase)
            
            # Can advance to next phase or stay in current phase
            return target_index <= current_index + 1
        except ValueError:
            return False
    
    def advance_phase(self) -> bool:
        """Advance to next phase if possible"""
        phase_order = [
            AnalysisPhase.MIGRATION_SCOPE,
            AnalysisPhase.COST_ESTIMATES,
            AnalysisPhase.MODERNIZATION_OPPORTUNITIES,
            AnalysisPhase.IMPLEMENTATION_ROADMAP
        ]
        
        try:
            current_index = phase_order.index(self.current_phase)
            if current_index < len(phase_order) - 1:
                # Add current phase to completed phases
                if not self.completed_phases:
                    self.completed_phases = []
                
                if self.current_phase.value not in self.completed_phases:
                    self.completed_phases.append(self.current_phase.value)
                
                # Advance to next phase
                self.current_phase = phase_order[current_index + 1]
                return True
        except ValueError:
            pass
        
        return False
    
    def get_progress_percentage(self) -> float:
        """Get overall progress percentage"""
        phase_order = [
            AnalysisPhase.MIGRATION_SCOPE,
            AnalysisPhase.COST_ESTIMATES,
            AnalysisPhase.MODERNIZATION_OPPORTUNITIES,
            AnalysisPhase.IMPLEMENTATION_ROADMAP
        ]
        
        try:
            current_index = phase_order.index(self.current_phase)
            completed_count = len(self.completed_phases or [])
            
            # Progress is based on completed phases plus partial credit for current phase
            total_phases = len(phase_order)
            progress = (completed_count + 0.5) / total_phases * 100
            
            return min(100.0, max(0.0, progress))
        except ValueError:
            return 0.0
    
    def to_dict(self):
        """Convert to dictionary with additional computed fields"""
        data = super().to_dict()
        data.update({
            'progress_percentage': self.get_progress_percentage(),
            'can_advance': self.current_phase != AnalysisPhase.IMPLEMENTATION_ROADMAP
        })
        return data
