"""
Migration Scope Analysis Service
Implements comprehensive migration readiness analysis including AI-powered blocker detection,
infrastructure insights, and workload classification
"""

import uuid
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import AI services
from .ai_blocker_analyzer import AIBlockerAnalyzer

# Official RVTools Column Mapping (consistent with cost_estimates_service.py)
RVTOOLS_COLUMNS = {
    'vm_name': 'VM',
    'cpu_cores': 'CPUs', 
    'memory_mib': 'Memory',
    'storage_provisioned_mib': 'Provisioned MiB',
    'storage_used_mib': 'In Use MiB',
    'os_type': 'OS according to the configuration file',
    'power_state': 'Powerstate',
    'datacenter': 'Datacenter',
    'cluster': 'Cluster',
    'host': 'Host'
}

# Import models
try:
    from models.core_models import (
        MigrationBlocker,
        MigrationBlockerSeverity,
        OutOfScopeItem,
        WorkloadClassification,
        InfrastructureInsights,
        MigrationScopeAnalysis
    )
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.core_models import (
        MigrationBlocker,
        MigrationBlockerSeverity,
        OutOfScopeItem,
        WorkloadClassification,
        InfrastructureInsights,
        MigrationScopeAnalysis
    )

class MigrationScopeService:
    """
    Service for analyzing migration scope and readiness with AI-powered blocker detection
    """
    
    def __init__(self):
        # Initialize AI blocker analyzer
        self.ai_blocker_analyzer = AIBlockerAnalyzer()
        
        # Configuration for blocker detection (fallback)
        self.legacy_os_patterns = [
            'windows server 2003',
            'windows server 2008',
            'windows xp',
            'windows vista',
            'centos 6',
            'rhel 6',
            'ubuntu 14.04',
            'ubuntu 16.04'
        ]
        
        self.vmware_management_patterns = [
            'vcenter', 'esxi', 'nsx', 'vsan', 'vrops', 'vrealize',
            'horizon', 'workspace', 'vmware', 'vsphere'
        ]
        
        self.database_indicators = [
            'sql', 'mysql', 'postgres', 'oracle', 'mongodb', 'redis',
            'database', 'db', 'mariadb', 'cassandra', 'elasticsearch'
        ]
    
    def _convert_mib_to_gb(self, mib_value: float) -> float:
        """Convert MiB to GB: 1 MiB = 1.048576 MB, 1 GB = 1024 MB"""
        if mib_value <= 0:
            return 0.0
        return (mib_value * 1.048576) / 1024
        
    def _safe_get_numeric_value(self, vm_data: Dict, column_name: str, default: float = 0.0) -> float:
        """Safely extract numeric value from VM data"""
        try:
            value = vm_data.get(column_name, default)
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def _extract_vm_data(self, vm: Dict[str, Any]) -> Dict[str, Any]:
        """Extract VM data using official RVTools column names with fallbacks"""
        # Extract storage with consumed storage preference and fallback
        consumed_storage_mib = self._safe_get_numeric_value(vm, RVTOOLS_COLUMNS['storage_used_mib'], 0)
        
        # Use consumed storage if available, otherwise fallback to provisioned
        if consumed_storage_mib > 0:
            storage_mib = consumed_storage_mib
        else:
            storage_mib = self._safe_get_numeric_value(vm, RVTOOLS_COLUMNS['storage_provisioned_mib'], 51200)
        
        return {
            'vm_name': vm.get(RVTOOLS_COLUMNS['vm_name'], vm.get('vm_name', 'Unknown')),
            'cpu_cores': int(self._safe_get_numeric_value(vm, RVTOOLS_COLUMNS['cpu_cores'], 2)),
            'memory_mib': self._safe_get_numeric_value(vm, RVTOOLS_COLUMNS['memory_mib'], 4096),
            'memory_gb': self._convert_mib_to_gb(self._safe_get_numeric_value(vm, RVTOOLS_COLUMNS['memory_mib'], 4096)),
            'storage_mib': storage_mib,
            'storage_gb': self._convert_mib_to_gb(storage_mib),
            'os_type': vm.get(RVTOOLS_COLUMNS['os_type'], vm.get('os_type', vm.get('OS', ''))),
            'power_state': vm.get(RVTOOLS_COLUMNS['power_state'], vm.get('power_state', 'unknown')),
            'cluster': vm.get(RVTOOLS_COLUMNS['cluster'], vm.get('cluster', '')),
            'host': vm.get(RVTOOLS_COLUMNS['host'], vm.get('host', '')),
            'datacenter': vm.get(RVTOOLS_COLUMNS['datacenter'], vm.get('datacenter', ''))
        }
    
    async def analyze_migration_scope(
        self, 
        session_id: str, 
        vm_inventory: List[Dict[str, Any]]
    ) -> MigrationScopeAnalysis:
        """
        Perform comprehensive migration scope analysis with AI-powered blocker detection
        
        Args:
            session_id: Analysis session identifier
            vm_inventory: List of VM data from RVTools
            
        Returns:
            Complete migration scope analysis
        """
        
        # Detect migration blockers using AI (with fallback to rule-based)
        migration_blockers = await self.detect_migration_blockers_ai(vm_inventory)
        
        # Identify out-of-scope items
        out_of_scope_items = await self.identify_out_of_scope_items(vm_inventory)
        
        # Classify workloads
        workload_classifications = await self.classify_workloads(vm_inventory)
        
        # Generate infrastructure insights
        infrastructure_insights = await self.generate_infrastructure_insights(vm_inventory)
        
        # Calculate complexity score
        complexity_score = self.calculate_migration_complexity(
            migration_blockers, len(vm_inventory), infrastructure_insights
        )
        
        # Estimate timeline
        estimated_timeline = self.estimate_migration_timeline(
            len(vm_inventory), complexity_score, migration_blockers
        )
        
        return MigrationScopeAnalysis(
            session_id=session_id,
            total_vms=len(vm_inventory),
            estimated_timeline_months=estimated_timeline,
            complexity_score=complexity_score,
            migration_blockers=migration_blockers,
            out_of_scope_items=out_of_scope_items,
            workload_classifications=workload_classifications,
            infrastructure_insights=infrastructure_insights
        )
    
    async def detect_migration_blockers_ai(self, vm_inventory: List[Dict]) -> List[MigrationBlocker]:
        """
        Detect migration blockers using AI analysis with fallback to rule-based detection
        
        Args:
            vm_inventory: List of VM data
            
        Returns:
            List of detected migration blockers
        """
        try:
            # Use AI blocker analyzer
            ai_result = await self.ai_blocker_analyzer.analyze_migration_blockers(vm_inventory)
            
            if ai_result and ai_result.get('blockers'):
                # Convert AI blocker format to MigrationBlocker objects
                migration_blockers = []
                
                for blocker_data in ai_result['blockers']:
                    # Map severity levels
                    severity_mapping = {
                        'critical': MigrationBlockerSeverity.CRITICAL,
                        'high': MigrationBlockerSeverity.HIGH,
                        'medium': MigrationBlockerSeverity.MEDIUM,
                        'low': MigrationBlockerSeverity.LOW
                    }
                    
                    severity = severity_mapping.get(
                        blocker_data.get('severity', 'medium').lower(),
                        MigrationBlockerSeverity.MEDIUM
                    )
                    
                    # Create MigrationBlocker object
                    blocker = MigrationBlocker(
                        id=blocker_data.get('id', f"ai_blocker_{uuid.uuid4().hex[:8]}"),
                        vm_name=blocker_data.get('vm_name', 'Unknown'),
                        severity=severity,
                        issue_type=blocker_data.get('issue_type', 'Unknown'),
                        description=blocker_data.get('description', ''),
                        remediation=blocker_data.get('remediation', ''),
                        confidence_score=blocker_data.get('confidence_score', 0.8)
                    )
                    
                    migration_blockers.append(blocker)
                
                print(f"✅ AI blocker detection successful: {len(migration_blockers)} blockers found")
                return migration_blockers
            
        except Exception as e:
            print(f"⚠️ AI blocker detection failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based detection
        return await self.detect_migration_blockers_fallback(vm_inventory)
    
    async def detect_migration_blockers_fallback(self, vm_inventory: List[Dict]) -> List[MigrationBlocker]:
        """
        Fallback rule-based blocker detection (original logic)
        
        Args:
            vm_inventory: List of VM data
            
        Returns:
            List of detected migration blockers
        """
        blockers = []
        
        for vm in vm_inventory:
            # Extract VM data using official RVTools columns
            vm_data = self._extract_vm_data(vm)
            vm_name = vm_data['vm_name']
            os_type = vm_data['os_type'].lower()
            storage_gb = vm_data['storage_gb']
            memory_gb = vm_data['memory_gb']
            cpu_cores = vm_data['cpu_cores']
            
            # Check for legacy OS versions
            for legacy_os in self.legacy_os_patterns:
                if legacy_os in os_type:
                    severity = MigrationBlockerSeverity.CRITICAL if '2003' in legacy_os or '2008' in legacy_os else MigrationBlockerSeverity.HIGH
                    
                    blockers.append(MigrationBlocker(
                        id=f"legacy_os_{vm_name}_{uuid.uuid4().hex[:8]}",
                        vm_name=vm_name,
                        severity=severity,
                        issue_type="Legacy Operating System",
                        description=f"Unsupported OS version detected: {os_type}",
                        remediation=self._get_os_remediation(os_type),
                        confidence_score=0.95
                    ))
                    break
            
            # Check for large storage requirements (potential migration challenge)
            if storage_gb > 1000:  # 1TB+
                severity = MigrationBlockerSeverity.HIGH if storage_gb > 5000 else MigrationBlockerSeverity.MEDIUM
                
                blockers.append(MigrationBlocker(
                    id=f"large_storage_{vm_name}_{uuid.uuid4().hex[:8]}",
                    vm_name=vm_name,
                    severity=severity,
                    issue_type="Large Storage Requirement",
                    description=f"Large storage requirement: {storage_gb:.1f}GB",
                    remediation="Consider AWS EFS, FSx, or data archival strategies for large datasets",
                    confidence_score=0.8
                ))
            
            # Check for high resource requirements
            if cpu_cores > 32 or memory_gb > 256:
                blockers.append(MigrationBlocker(
                    id=f"high_resources_{vm_name}_{uuid.uuid4().hex[:8]}",
                    vm_name=vm_name,
                    severity=MigrationBlockerSeverity.MEDIUM,
                    issue_type="High Resource Requirements",
                    description=f"High resource VM: {cpu_cores} vCPUs, {memory_gb:.1f}GB RAM",
                    remediation="Evaluate instance families like r5, c5, or m5 for high-performance workloads",
                    confidence_score=0.7
                ))
            
            # Check for potential legacy applications
            installed_software = vm.get('installed_software', '').lower()
            if any(legacy in installed_software for legacy in ['.net framework 2.0', '.net framework 3.5', 'java 6', 'java 7']):
                blockers.append(MigrationBlocker(
                    id=f"legacy_app_{vm_name}_{uuid.uuid4().hex[:8]}",
                    vm_name=vm_name,
                    severity=MigrationBlockerSeverity.HIGH,
                    issue_type="Legacy Application Framework",
                    description="Legacy application framework detected",
                    remediation="Upgrade to modern framework versions or containerize applications",
                    confidence_score=0.85
                ))
            
            # Check for specialized hardware dependencies
            if self._has_hardware_dependencies(vm):
                blockers.append(MigrationBlocker(
                    id=f"hardware_dep_{vm_name}_{uuid.uuid4().hex[:8]}",
                    vm_name=vm_name,
                    severity=MigrationBlockerSeverity.HIGH,
                    issue_type="Hardware Dependencies",
                    description="Specialized hardware dependencies detected",
                    remediation="Evaluate cloud-native alternatives or specialized EC2 instances",
                    confidence_score=0.6
                ))
        
        print(f"⚠️ Using fallback rule-based blocker detection: {len(blockers)} blockers found")
        return blockers
    
    async def identify_out_of_scope_items(self, vm_inventory: List[Dict]) -> List[OutOfScopeItem]:
        """
        Identify VMware management servers and infrastructure components
        
        Args:
            vm_inventory: List of VM data
            
        Returns:
            List of out-of-scope items
        """
        out_of_scope = []
        
        for vm in vm_inventory:
            # Extract VM data using official RVTools columns
            vm_data = self._extract_vm_data(vm)
            vm_name = vm_data['vm_name']
            vm_name_lower = vm_name.lower()
            
            # Check for VMware management components
            for indicator in self.vmware_management_patterns:
                if indicator in vm_name_lower:
                    out_of_scope.append(OutOfScopeItem(
                        vm_name=vm_name,
                        reason="VMware management infrastructure component",
                        category="vmware_management",
                        auto_detected=True
                    ))
                    break
            
            # Check for backup and monitoring infrastructure
            backup_indicators = ['backup', 'veeam', 'commvault', 'networker', 'avamar']
            if any(indicator in vm_name for indicator in backup_indicators):
                out_of_scope.append(OutOfScopeItem(
                    vm_name=vm.get('vm_name', vm.get('VM', 'Unknown')),
                    reason="Backup infrastructure - replace with AWS Backup",
                    category="infrastructure",
                    auto_detected=True
                ))
            
            # Check for network infrastructure
            network_indicators = ['firewall', 'loadbalancer', 'proxy', 'dns', 'dhcp']
            if any(indicator in vm_name for indicator in network_indicators):
                out_of_scope.append(OutOfScopeItem(
                    vm_name=vm.get('vm_name', vm.get('VM', 'Unknown')),
                    reason="Network infrastructure - replace with AWS native services",
                    category="infrastructure",
                    auto_detected=True
                ))
        
        return out_of_scope
    
    async def classify_workloads(self, vm_inventory: List[Dict]) -> List[WorkloadClassification]:
        """
        Classify workloads based on naming conventions and characteristics
        
        Args:
            vm_inventory: List of VM data
            
        Returns:
            List of workload classifications
        """
        classifications = {
            "production": [],
            "development": [],
            "testing": [],
            "staging": []
        }
        
        for vm in vm_inventory:
            # Extract VM data using official RVTools columns
            vm_data = self._extract_vm_data(vm)
            vm_name = vm_data['vm_name']
            vm_name_lower = vm_name.lower()
            cpu_cores = vm_data['cpu_cores']
            memory_gb = vm_data['memory_gb']
            # Classification based on naming patterns
            if any(prod in vm_name_lower for prod in ['prod', 'production', 'prd']):
                classifications["production"].append(vm_name)
            elif any(dev in vm_name_lower for dev in ['dev', 'development', 'dvl']):
                classifications["development"].append(vm_name)
            elif any(test in vm_name_lower for test in ['test', 'tst', 'qa', 'uat']):
                classifications["testing"].append(vm_name)
            elif any(stage in vm_name_lower for stage in ['stage', 'staging', 'stg']):
                classifications["staging"].append(vm_name)
            else:
                # Classification based on resource allocation
                if cpu_cores >= 8 or memory_gb >= 32:
                    classifications["production"].append(vm_name)
                elif cpu_cores >= 4 or memory_gb >= 16:
                    classifications["staging"].append(vm_name)
                else:
                    classifications["development"].append(vm.get('vm_name', vm.get('VM', 'Unknown')))
        
        total_vms = len(vm_inventory)
        result = []
        
        for classification, vm_names in classifications.items():
            if vm_names:  # Only include classifications with VMs
                result.append(WorkloadClassification(
                    classification=classification,
                    vm_count=len(vm_names),
                    percentage=round((len(vm_names) / total_vms) * 100, 1),
                    vm_names=vm_names
                ))
        
        return result
    
    async def generate_infrastructure_insights(self, vm_inventory: List[Dict]) -> InfrastructureInsights:
        """
        Generate comprehensive infrastructure insights
        
        Args:
            vm_inventory: List of VM data
            
        Returns:
            Infrastructure insights summary
        """
        total_vms = len(vm_inventory)
        total_storage_gb = 0
        total_vcpus = 0
        total_memory_gb = 0
        
        # OS breakdown
        os_breakdown = {"windows": 0, "linux": 0, "other": 0}
        
        for vm in vm_inventory:
            # Extract VM data using official RVTools columns
            vm_data = self._extract_vm_data(vm)
            
            # Accumulate totals
            total_storage_gb += vm_data['storage_gb']
            total_vcpus += vm_data['cpu_cores']
            total_memory_gb += vm_data['memory_gb']
            
            # OS classification
            os_type = vm_data['os_type'].lower()
            if 'windows' in os_type:
                os_breakdown["windows"] += 1
            elif any(linux_os in os_type for linux_os in ['linux', 'ubuntu', 'centos', 'rhel', 'suse']):
                os_breakdown["linux"] += 1
            else:
                os_breakdown["other"] += 1
        
        # Production vs Non-production ratio (simplified)
        prod_count = sum(1 for vm in vm_inventory 
                        if any(prod in self._extract_vm_data(vm)['vm_name'].lower() 
                              for prod in ['prod', 'production', 'prd']))
        
        return InfrastructureInsights(
            total_vms=total_vms,
            total_storage_tb=round(total_storage_gb / 1024, 1),
            os_breakdown=os_breakdown,
            prod_nonprod_ratio={
                "production": round((prod_count / total_vms) * 100, 1) if total_vms > 0 else 0,
                "non_production": round(((total_vms - prod_count) / total_vms) * 100, 1) if total_vms > 0 else 0
            },
            average_vm_specs={
                "cpu": round(total_vcpus / total_vms, 1) if total_vms > 0 else 0,
                "ram_gb": round(total_memory_gb / total_vms, 1) if total_vms > 0 else 0
            },
            total_resources={
                "total_vcpus": total_vcpus,
                "total_ram_tb": round(total_memory_gb / 1024, 1)
            }
        )
    
    def calculate_migration_complexity(
        self, 
        blockers: List[MigrationBlocker], 
        total_vms: int, 
        insights: InfrastructureInsights
    ) -> int:
        """
        Calculate migration complexity score (0-100)
        
        Args:
            blockers: List of migration blockers
            total_vms: Total number of VMs
            insights: Infrastructure insights
            
        Returns:
            Complexity score from 0-100
        """
        complexity_score = 0
        
        # Base complexity from VM count
        if total_vms > 500:
            complexity_score += 30
        elif total_vms > 100:
            complexity_score += 20
        elif total_vms > 50:
            complexity_score += 10
        
        # Complexity from blockers
        critical_blockers = len([b for b in blockers if b.severity == MigrationBlockerSeverity.CRITICAL])
        high_blockers = len([b for b in blockers if b.severity == MigrationBlockerSeverity.HIGH])
        medium_blockers = len([b for b in blockers if b.severity == MigrationBlockerSeverity.MEDIUM])
        
        complexity_score += critical_blockers * 15
        complexity_score += high_blockers * 10
        complexity_score += medium_blockers * 5
        
        # Complexity from OS diversity
        os_types = len([count for count in insights.os_breakdown.values() if count > 0])
        complexity_score += os_types * 5
        
        # Complexity from resource distribution
        if insights.total_resources["total_vcpus"] > 1000:
            complexity_score += 15
        elif insights.total_resources["total_vcpus"] > 500:
            complexity_score += 10
        
        # Cap at 100
        return min(complexity_score, 100)
    
    def estimate_migration_timeline(
        self, 
        total_vms: int, 
        complexity_score: int, 
        blockers: List[MigrationBlocker]
    ) -> int:
        """
        Estimate migration timeline in months
        
        Args:
            total_vms: Total number of VMs
            complexity_score: Migration complexity score
            blockers: List of migration blockers
            
        Returns:
            Estimated timeline in months
        """
        base_timeline = 3  # Base 3 months
        
        # Add time based on VM count
        if total_vms > 500:
            base_timeline += 12
        elif total_vms > 100:
            base_timeline += 6
        elif total_vms > 50:
            base_timeline += 3
        
        # Add time based on complexity
        if complexity_score > 80:
            base_timeline += 6
        elif complexity_score > 60:
            base_timeline += 3
        elif complexity_score > 40:
            base_timeline += 2
        
        # Add time for critical blockers
        critical_blockers = len([b for b in blockers if b.severity == MigrationBlockerSeverity.CRITICAL])
        base_timeline += critical_blockers * 2
        
        return min(base_timeline, 24)  # Cap at 24 months
    
    # Helper methods
    def _get_os_remediation(self, os_type: str) -> str:
        """Get OS-specific remediation advice"""
        if 'windows' in os_type:
            if '2003' in os_type or '2008' in os_type:
                return "Upgrade to Windows Server 2019/2022 before migration"
            else:
                return "Consider upgrading to latest Windows Server version"
        elif 'centos 6' in os_type or 'rhel 6' in os_type:
            return "Upgrade to CentOS 8/RHEL 8 or migrate to Amazon Linux 2"
        elif 'ubuntu' in os_type:
            return "Upgrade to Ubuntu 20.04 LTS or 22.04 LTS"
        else:
            return "Upgrade to a supported operating system version"
    
    def _has_hardware_dependencies(self, vm: Dict[str, Any]) -> bool:
        """Check if VM has specialized hardware dependencies"""
        # This is a simplified check - in production, this would be more sophisticated
        vm_name = vm.get('vm_name', vm.get('VM', '')).lower()
        
        hardware_indicators = [
            'gpu', 'cuda', 'graphics', 'cad', 'rendering',
            'fpga', 'accelerator', 'hpc', 'cluster'
        ]
        
        return any(indicator in vm_name for indicator in hardware_indicators)

# Global service instance
migration_scope_service = MigrationScopeService()
