"""
AI-Powered Migration Blocker Analyzer
Replaces rule-based blocker detection with intelligent AI analysis
"""

import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .ai_service_wrapper import AIServiceWrapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIBlockerAnalyzer:
    """AI-powered migration blocker analysis using Claude 3.7 Sonnet"""
    
    def __init__(self, profile_name: str = "smartslot", region: str = "us-east-1"):
        """Initialize AI blocker analyzer"""
        self.ai_service = AIServiceWrapper(profile_name=profile_name, region=region)
        logger.info("✅ AI Blocker Analyzer initialized")
    
    def _summarize_vm_inventory(self, vm_inventory: List[Dict]) -> str:
        """Create comprehensive summary of VM inventory for AI analysis"""
        
        if not vm_inventory:
            return "No VM inventory provided"
        
        total_vms = len(vm_inventory)
        
        # Analyze OS distribution
        os_counts = {}
        power_state_counts = {}
        cpu_total = 0
        memory_total = 0
        storage_total = 0
        
        for vm in vm_inventory:
            # OS analysis
            os = vm.get('OS', 'Unknown').lower()
            # Normalize OS names
            if 'windows' in os:
                if '2003' in os or '2008' in os:
                    os_key = 'Windows Legacy (2003/2008)'
                elif '2012' in os:
                    os_key = 'Windows 2012'
                elif '2016' in os:
                    os_key = 'Windows 2016'
                elif '2019' in os:
                    os_key = 'Windows 2019'
                elif '2022' in os:
                    os_key = 'Windows 2022'
                else:
                    os_key = 'Windows Other'
            elif 'linux' in os or 'ubuntu' in os or 'centos' in os or 'rhel' in os:
                os_key = 'Linux'
            else:
                os_key = 'Other/Unknown'
            
            os_counts[os_key] = os_counts.get(os_key, 0) + 1
            
            # Power state analysis
            power_state = vm.get('Powerstate', 'Unknown')
            power_state_counts[power_state] = power_state_counts.get(power_state, 0) + 1
            
            # Resource totals
            cpu_total += vm.get('CPUs', 0)
            memory_total += vm.get('Memory', 0)
            storage_total += vm.get('Provisioned MB', 0)
        
        # Convert memory and storage to GB
        memory_gb = memory_total / 1024 if memory_total > 0 else 0
        storage_gb = storage_total / 1024 if storage_total > 0 else 0
        
        # Sample VM names for context
        sample_vm_names = [vm.get('VM', 'Unknown')[:50] for vm in vm_inventory[:10]]
        
        summary = f"""
ENVIRONMENT OVERVIEW:
- Total Virtual Machines: {total_vms}
- Total vCPUs: {cpu_total}
- Total Memory: {memory_gb:.1f} GB
- Total Storage: {storage_gb:.1f} GB

OPERATING SYSTEM DISTRIBUTION:
{json.dumps(os_counts, indent=2)}

POWER STATE DISTRIBUTION:
{json.dumps(power_state_counts, indent=2)}

SAMPLE VM NAMES (first 10):
{json.dumps(sample_vm_names, indent=2)}

DETAILED VM SAMPLE (first 5 VMs):
{json.dumps(vm_inventory[:5], indent=2)}
"""
        
        return summary
    
    def _create_blocker_analysis_prompt(self, vm_inventory: List[Dict]) -> str:
        """Create comprehensive prompt for AI blocker analysis"""
        
        vm_summary = self._summarize_vm_inventory(vm_inventory)
        
        system_role = """You are a senior VMware to AWS migration architect with 15+ years of experience. 
You specialize in identifying migration blockers and providing detailed remediation strategies."""
        
        context = f"""You are analyzing a VMware environment for migration to AWS. 
The environment contains {len(vm_inventory)} virtual machines with various configurations and workloads.

{vm_summary}"""
        
        task = """Analyze this VMware environment and identify specific migration blockers. Focus on:

1. LEGACY OPERATING SYSTEMS:
   - Windows 2003, 2008 (end of support)
   - Very old Linux distributions
   - Unsupported OS versions

2. APPLICATION DEPENDENCIES:
   - Applications that require specific hardware
   - Legacy applications with licensing issues
   - Applications with complex network dependencies

3. NETWORK CONFIGURATION ISSUES:
   - Complex network topologies
   - Hardcoded IP addresses
   - Network dependencies that are difficult to replicate

4. STORAGE REQUIREMENTS:
   - Very high IOPS requirements
   - Specific storage configurations
   - Large storage volumes that may be costly

5. COMPLIANCE AND SECURITY:
   - Regulatory compliance requirements
   - Security configurations that need special handling
   - Data sovereignty requirements

6. RESOURCE CONSTRAINTS:
   - VMs with unusual resource configurations
   - Very large VMs that may need right-sizing
   - VMs with specific CPU requirements

For each blocker identified, provide:
- Specific VM name affected
- Clear description of the issue
- Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- Detailed remediation steps (3-5 specific actions)
- Estimated effort (hours/days/weeks)
- Business impact if not resolved
- Confidence level (0.0-1.0)"""
        
        output_format = """{
    "analysis_summary": {
        "total_vms_analyzed": number,
        "total_blockers_found": number,
        "critical_blockers": number,
        "high_priority_blockers": number,
        "medium_priority_blockers": number,
        "low_priority_blockers": number,
        "most_common_issues": ["issue_type1", "issue_type2"],
        "overall_migration_risk": "LOW|MEDIUM|HIGH|CRITICAL",
        "estimated_remediation_effort": "X weeks"
    },
    "blockers": [
        {
            "vm_name": "specific-vm-name",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "issue_type": "legacy_os|application_dependency|network_config|storage_requirement|compliance|resource_constraint",
            "description": "Clear, specific description of the migration blocker",
            "remediation": "High-level remediation approach",
            "detailed_remediation_steps": [
                "Step 1: Specific action to take",
                "Step 2: Next specific action",
                "Step 3: Validation step"
            ],
            "estimated_effort": "2-3 days",
            "business_impact": "Description of impact if not resolved",
            "confidence_score": 0.85,
            "prerequisites": ["prerequisite1", "prerequisite2"],
            "alternative_approaches": [
                {
                    "approach": "Alternative solution description",
                    "complexity": "LOW|MEDIUM|HIGH",
                    "effort": "1-2 days"
                }
            ]
        }
    ]
}"""
        
        examples = """EXAMPLE BLOCKER:
{
    "vm_name": "legacy-app-server-01",
    "severity": "HIGH",
    "issue_type": "legacy_os",
    "description": "Running Windows Server 2008 R2 which is end-of-life and not supported on AWS",
    "remediation": "Upgrade to Windows Server 2019 or 2022 before migration",
    "detailed_remediation_steps": [
        "Step 1: Backup current VM and test application compatibility with Windows Server 2019",
        "Step 2: Create new Windows Server 2019 VM and migrate application",
        "Step 3: Test all application functionality and performance",
        "Step 4: Update documentation and procedures",
        "Step 5: Schedule cutover during maintenance window"
    ],
    "estimated_effort": "1-2 weeks",
    "business_impact": "Application will not be supported on AWS without OS upgrade, potential security vulnerabilities",
    "confidence_score": 0.95,
    "prerequisites": ["Application compatibility testing", "Backup verification"],
    "alternative_approaches": [
        {
            "approach": "Containerize the application to run on modern OS",
            "complexity": "HIGH",
            "effort": "3-4 weeks"
        }
    ]
}"""
        
        return self.ai_service.create_structured_prompt(
            system_role=system_role,
            context=context,
            task=task,
            output_format=output_format,
            examples=examples
        )
    
    def _create_fallback_blockers(self, vm_inventory: List[Dict]) -> List[Dict]:
        """Create basic blockers using rule-based logic as fallback"""
        
        blockers = []
        blocker_id = 1
        
        for vm in vm_inventory:
            vm_name = vm.get('VM', 'Unknown')
            os = vm.get('OS', '').lower()
            
            # Legacy OS detection
            if any(legacy in os for legacy in ['2003', '2008', 'xp', 'vista']):
                blockers.append({
                    'id': f"fallback-blocker-{blocker_id}",
                    'vm_name': vm_name,
                    'severity': 'high',
                    'issue_type': 'legacy_os',
                    'description': f'Legacy operating system detected: {vm.get("OS", "Unknown")}',
                    'remediation': 'Upgrade to supported OS version before migration',
                    'confidence_score': 0.7,
                    'detailed_remediation_steps': [
                        'Assess application compatibility with newer OS',
                        'Plan OS upgrade or application modernization',
                        'Test in development environment',
                        'Execute upgrade during maintenance window'
                    ],
                    'estimated_effort': '1-2 weeks',
                    'business_impact': 'Legacy OS not supported on AWS'
                })
                blocker_id += 1
            
            # High resource VMs
            cpu_count = vm.get('CPUs', 0)
            memory_mb = vm.get('Memory', 0)
            
            if cpu_count > 32 or memory_mb > 262144:  # >32 CPUs or >256GB RAM
                blockers.append({
                    'id': f"fallback-blocker-{blocker_id}",
                    'vm_name': vm_name,
                    'severity': 'medium',
                    'issue_type': 'resource_constraint',
                    'description': f'High resource VM: {cpu_count} CPUs, {memory_mb/1024:.1f}GB RAM',
                    'remediation': 'Evaluate right-sizing and AWS instance type compatibility',
                    'confidence_score': 0.6,
                    'detailed_remediation_steps': [
                        'Analyze actual resource utilization',
                        'Identify appropriate AWS instance types',
                        'Plan right-sizing strategy',
                        'Test performance with new sizing'
                    ],
                    'estimated_effort': '3-5 days',
                    'business_impact': 'May require expensive instance types or performance issues'
                })
                blocker_id += 1
        
        return blockers
    
    async def analyze_migration_blockers(self, vm_inventory: List[Dict]) -> Dict[str, Any]:
        """
        Analyze VM inventory for migration blockers using AI
        
        Args:
            vm_inventory: List of VM configuration dictionaries
            
        Returns:
            Dictionary containing blocker analysis results
        """
        
        if not vm_inventory:
            return {
                'analysis_summary': {
                    'total_vms_analyzed': 0,
                    'total_blockers_found': 0,
                    'overall_migration_risk': 'LOW'
                },
                'blockers': [],
                'metadata': {
                    'ai_used': False,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': 0.0
                }
            }
        
        logger.info(f"🔍 Starting AI blocker analysis for {len(vm_inventory)} VMs")
        
        # Create AI prompt
        prompt = self._create_blocker_analysis_prompt(vm_inventory)
        
        # Analyze with AI and fallback
        result = await self.ai_service.analyze_with_fallback(
            primary_prompt=prompt,
            fallback_function=self._create_fallback_blockers,
            fallback_args=(vm_inventory,),
            max_tokens=6000
        )
        
        # Process results
        if result['ai_used'] and result['data']:
            # AI analysis successful
            analysis_data = result['data']
            blockers = analysis_data.get('blockers', [])
            
            # Add IDs to blockers if not present
            for i, blocker in enumerate(blockers):
                if 'id' not in blocker:
                    blocker['id'] = f"ai-blocker-{i+1}"
            
            logger.info(f"✅ AI analysis complete: {len(blockers)} blockers found")
            
            return {
                'analysis_summary': analysis_data.get('analysis_summary', {}),
                'blockers': blockers,
                'metadata': {
                    'ai_used': True,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': result['confidence'],
                    'total_vms_analyzed': len(vm_inventory)
                }
            }
        
        elif result['fallback_used'] and result['data']:
            # Fallback analysis used
            blockers = result['data']
            
            logger.info(f"⚠️ Fallback analysis used: {len(blockers)} blockers found")
            
            return {
                'analysis_summary': {
                    'total_vms_analyzed': len(vm_inventory),
                    'total_blockers_found': len(blockers),
                    'critical_blockers': len([b for b in blockers if b.get('severity') == 'critical']),
                    'high_priority_blockers': len([b for b in blockers if b.get('severity') == 'high']),
                    'medium_priority_blockers': len([b for b in blockers if b.get('severity') == 'medium']),
                    'low_priority_blockers': len([b for b in blockers if b.get('severity') == 'low']),
                    'overall_migration_risk': 'MEDIUM'
                },
                'blockers': blockers,
                'metadata': {
                    'ai_used': False,
                    'fallback_used': True,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': result['confidence'],
                    'total_vms_analyzed': len(vm_inventory)
                }
            }
        
        else:
            # Both AI and fallback failed
            logger.error("❌ Both AI and fallback analysis failed")
            
            return {
                'analysis_summary': {
                    'total_vms_analyzed': len(vm_inventory),
                    'total_blockers_found': 0,
                    'overall_migration_risk': 'UNKNOWN'
                },
                'blockers': [],
                'metadata': {
                    'ai_used': False,
                    'fallback_used': False,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': 0.0,
                    'error': result.get('error', 'Unknown error'),
                    'total_vms_analyzed': len(vm_inventory)
                }
            }
    
    def get_blocker_statistics(self, blockers: List[Dict]) -> Dict[str, Any]:
        """Generate statistics from blocker analysis results"""
        
        if not blockers:
            return {
                'total_blockers': 0,
                'by_severity': {},
                'by_type': {},
                'average_confidence': 0.0
            }
        
        severity_counts = {}
        type_counts = {}
        confidence_scores = []
        
        for blocker in blockers:
            # Count by severity
            severity = blocker.get('severity', 'unknown').lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by type
            issue_type = blocker.get('issue_type', 'unknown')
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
            
            # Collect confidence scores
            confidence = blocker.get('confidence_score', 0.0)
            if isinstance(confidence, (int, float)):
                confidence_scores.append(confidence)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            'total_blockers': len(blockers),
            'by_severity': severity_counts,
            'by_type': type_counts,
            'average_confidence': round(avg_confidence, 2)
        }
