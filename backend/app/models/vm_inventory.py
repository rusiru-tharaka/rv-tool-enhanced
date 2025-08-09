"""
VM Inventory model for storing RVTools data
Optimized for handling 2000+ VM records
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class VMInventory(BaseModel):
    """VM Inventory model based on RVTools export structure"""
    __tablename__ = 'vm_inventory'
    
    # Session relationship
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    
    # Basic VM Information
    vm_name = Column(String(255), nullable=False, index=True)
    dns_name = Column(String(255))
    powerstate = Column(String(50), index=True)
    template = Column(Boolean, default=False)
    config_status = Column(String(50))
    
    # Hardware Configuration
    cpus = Column(Integer, nullable=False, index=True)
    memory_mb = Column(BigInteger, nullable=False, index=True)
    nics = Column(Integer, default=1)
    disks = Column(Integer, default=1)
    
    # Storage Information
    provisioned_mb = Column(BigInteger, index=True)
    in_use_mb = Column(BigInteger)
    unshared_mb = Column(BigInteger)
    
    # Operating System
    guest_os = Column(String(255), index=True)
    vm_version = Column(String(50))
    tools_version = Column(String(100))
    tools_status = Column(String(50))
    
    # Infrastructure Location
    host = Column(String(255), index=True)
    cluster = Column(String(255), index=True)
    datacenter = Column(String(255), index=True)
    folder = Column(String(500))
    
    # Resource Pool and vApp
    resource_pool = Column(String(255))
    vapp = Column(String(255))
    
    # Network Configuration
    network_1 = Column(String(255))
    network_2 = Column(String(255))
    network_3 = Column(String(255))
    network_4 = Column(String(255))
    
    # Performance and Limits
    cpu_limit = Column(Integer)
    cpu_reservation = Column(Integer)
    memory_limit = Column(Integer)
    memory_reservation = Column(Integer)
    
    # Annotations and Notes
    annotation = Column(Text)
    notes = Column(Text)
    
    # Custom Attributes (for additional RVTools fields)
    custom_field_1 = Column(String(255))
    custom_field_2 = Column(String(255))
    custom_field_3 = Column(String(255))
    
    # Analysis flags
    migration_complexity = Column(String(50))  # low, medium, high
    modernization_candidate = Column(Boolean, default=False)
    
    # Relationships
    session = relationship("Session", back_populates="vm_inventory")
    migration_blockers = relationship("MigrationBlocker", back_populates="vm")
    cost_estimates = relationship("CostEstimate", back_populates="vm")
    modernization_opportunities = relationship("ModernizationOpportunity", back_populates="vm")
    
    # Indexes for performance with large datasets
    __table_args__ = (
        Index('idx_vm_session_name', 'session_id', 'vm_name'),
        Index('idx_vm_cluster_datacenter', 'cluster', 'datacenter'),
        Index('idx_vm_resources', 'cpus', 'memory_mb'),
        Index('idx_vm_storage', 'provisioned_mb', 'in_use_mb'),
        Index('idx_vm_os_power', 'guest_os', 'powerstate'),
        Index('idx_vm_host_cluster', 'host', 'cluster'),
        Index('idx_vm_migration_analysis', 'migration_complexity', 'modernization_candidate'),
    )
    
    def __repr__(self):
        return f"<VMInventory(vm_name='{self.vm_name}', cpus={self.cpus}, memory_mb={self.memory_mb})>"
    
    @property
    def memory_gb(self):
        """Convert memory from MB to GB"""
        return round(self.memory_mb / 1024, 2) if self.memory_mb else 0
    
    @property
    def provisioned_gb(self):
        """Convert provisioned storage from MB to GB"""
        return round(self.provisioned_mb / 1024, 2) if self.provisioned_mb else 0
    
    @property
    def in_use_gb(self):
        """Convert in-use storage from MB to GB"""
        return round(self.in_use_mb / 1024, 2) if self.in_use_mb else 0
    
    def to_dict(self):
        """Convert to dictionary with computed fields"""
        data = super().to_dict()
        data.update({
            'memory_gb': self.memory_gb,
            'provisioned_gb': self.provisioned_gb,
            'in_use_gb': self.in_use_gb
        })
        return data
    
    @classmethod
    def get_summary_stats(cls, session, session_id=None):
        """Get summary statistics for VM inventory"""
        query = session.query(cls)
        if session_id:
            query = query.filter(cls.session_id == session_id)
        
        vms = query.all()
        
        if not vms:
            return {
                'total_vms': 0,
                'total_cpus': 0,
                'total_memory_gb': 0,
                'total_storage_gb': 0,
                'os_breakdown': {},
                'cluster_breakdown': {},
                'powerstate_breakdown': {}
            }
        
        # Calculate totals
        total_cpus = sum(vm.cpus for vm in vms if vm.cpus)
        total_memory_gb = sum(vm.memory_gb for vm in vms)
        total_storage_gb = sum(vm.provisioned_gb for vm in vms)
        
        # OS breakdown
        os_breakdown = {}
        for vm in vms:
            os = vm.guest_os or 'Unknown'
            os_breakdown[os] = os_breakdown.get(os, 0) + 1
        
        # Cluster breakdown
        cluster_breakdown = {}
        for vm in vms:
            cluster = vm.cluster or 'Unknown'
            cluster_breakdown[cluster] = cluster_breakdown.get(cluster, 0) + 1
        
        # Power state breakdown
        powerstate_breakdown = {}
        for vm in vms:
            state = vm.powerstate or 'Unknown'
            powerstate_breakdown[state] = powerstate_breakdown.get(state, 0) + 1
        
        return {
            'total_vms': len(vms),
            'total_cpus': total_cpus,
            'total_memory_gb': round(total_memory_gb, 2),
            'total_storage_gb': round(total_storage_gb, 2),
            'os_breakdown': os_breakdown,
            'cluster_breakdown': cluster_breakdown,
            'powerstate_breakdown': powerstate_breakdown
        }
