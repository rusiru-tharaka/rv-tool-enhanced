"""
AI-Powered Modernization Analyzer
Enhances workload analysis with intelligent AI recommendations (no architecture generation)
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

class AIModernizationAnalyzer:
    """AI-powered modernization analysis using Claude 3.7 Sonnet"""
    
    def __init__(self, profile_name: str = "smartslot", region: str = "us-east-1"):
        """Initialize AI modernization analyzer"""
        self.ai_service = AIServiceWrapper(profile_name=profile_name, region=region)
        logger.info("✅ AI Modernization Analyzer initialized")
    
    def _summarize_vm_inventory_for_modernization(self, vm_inventory: List[Dict]) -> str:
        """Create comprehensive summary of VM inventory for modernization analysis"""
        
        if not vm_inventory:
            return "No VM inventory provided"
        
        total_vms = len(vm_inventory)
        
        # Analyze workload patterns from VM names
        workload_patterns = {}
        resource_summary = {
            'total_cpu': 0,
            'total_memory_gb': 0,
            'total_storage_gb': 0,
            'small_vms': 0,
            'medium_vms': 0,
            'large_vms': 0
        }
        
        for vm in vm_inventory:
            vm_name = vm.get('VM', 'Unknown').lower()
            
            # Categorize by naming patterns
            if any(pattern in vm_name for pattern in ['web', 'app', 'api', 'frontend']):
                workload_patterns['web_applications'] = workload_patterns.get('web_applications', 0) + 1
            elif any(pattern in vm_name for pattern in ['db', 'database', 'sql', 'mysql', 'postgres', 'oracle']):
                workload_patterns['databases'] = workload_patterns.get('databases', 0) + 1
            elif any(pattern in vm_name for pattern in ['batch', 'job', 'worker', 'process']):
                workload_patterns['batch_processing'] = workload_patterns.get('batch_processing', 0) + 1
            elif any(pattern in vm_name for pattern in ['service', 'micro', 'api']):
                workload_patterns['microservices'] = workload_patterns.get('microservices', 0) + 1
            else:
                workload_patterns['general_purpose'] = workload_patterns.get('general_purpose', 0) + 1
            
            # Resource analysis
            cpu = vm.get('CPUs', 0)
            memory_mb = vm.get('Memory', 0)
            storage_mb = vm.get('Provisioned MB', 0)
            
            resource_summary['total_cpu'] += cpu
            resource_summary['total_memory_gb'] += memory_mb / 1024 if memory_mb > 0 else 0
            resource_summary['total_storage_gb'] += storage_mb / 1024 if storage_mb > 0 else 0
            
            # VM size categorization
            if cpu <= 2 and memory_mb <= 4096:
                resource_summary['small_vms'] += 1
            elif cpu <= 8 and memory_mb <= 32768:
                resource_summary['medium_vms'] += 1
            else:
                resource_summary['large_vms'] += 1
        
        # Sample VM names for context
        sample_vm_names = [vm.get('VM', 'Unknown')[:50] for vm in vm_inventory[:10]]
        
        summary = f"""
MODERNIZATION ANALYSIS CONTEXT:
- Total Virtual Machines: {total_vms}
- Total vCPUs: {resource_summary['total_cpu']}
- Total Memory: {resource_summary['total_memory_gb']:.1f} GB
- Total Storage: {resource_summary['total_storage_gb']:.1f} GB

WORKLOAD DISTRIBUTION:
{json.dumps(workload_patterns, indent=2)}

VM SIZE DISTRIBUTION:
- Small VMs (≤2 CPU, ≤4GB): {resource_summary['small_vms']}
- Medium VMs (≤8 CPU, ≤32GB): {resource_summary['medium_vms']}
- Large VMs (>8 CPU, >32GB): {resource_summary['large_vms']}

SAMPLE VM NAMES (first 10):
{json.dumps(sample_vm_names, indent=2)}

DETAILED VM SAMPLE (first 5 VMs):
{json.dumps(vm_inventory[:5], indent=2)}
"""
        
        return summary
    
    def _create_modernization_analysis_prompt(self, vm_inventory: List[Dict], cost_estimates: List[Dict] = None) -> str:
        """Create comprehensive prompt for AI modernization analysis"""
        
        vm_summary = self._summarize_vm_inventory_for_modernization(vm_inventory)
        
        # Calculate total current costs if available
        total_monthly_cost = 0
        if cost_estimates:
            total_monthly_cost = sum(estimate.get('projected_monthly_cost', 0) for estimate in cost_estimates)
        
        system_role = """You are a senior AWS solutions architect with 15+ years of experience in cloud modernization. 
You specialize in identifying practical modernization opportunities that provide clear business value and ROI."""
        
        context = f"""You are analyzing a VMware environment for AWS modernization opportunities. 
The environment contains {len(vm_inventory)} virtual machines with various workloads.
Current estimated monthly AWS cost: ${total_monthly_cost:,.2f}

{vm_summary}"""
        
        task = """Analyze this environment for practical modernization opportunities. Focus on:

1. CONTAINERIZATION OPPORTUNITIES:
   - Web applications suitable for ECS/EKS
   - Microservices candidates
   - Batch processing workloads
   - Consider resource utilization and scaling patterns

2. SERVERLESS OPPORTUNITIES:
   - Low-traffic APIs suitable for Lambda
   - Scheduled tasks and cron jobs
   - Event-driven processing
   - Intermittent workloads with variable usage

3. MANAGED DATABASE OPPORTUNITIES:
   - Database workloads suitable for RDS
   - NoSQL candidates for DynamoDB/DocumentDB
   - Data warehousing for Redshift
   - Caching layers for ElastiCache

4. STORAGE OPTIMIZATION:
   - File shares for EFS/FSx
   - Object storage for S3
   - Backup and archival strategies
   - Content delivery for CloudFront

5. COMPUTE OPTIMIZATION:
   - Right-sizing opportunities
   - Spot instance candidates
   - Reserved instance recommendations
   - Auto-scaling potential

For each opportunity, provide:
- Clear business justification
- Estimated monthly cost savings
- Implementation complexity (Low/Medium/High)
- Risk assessment and mitigation
- Prerequisites and dependencies
- Estimated implementation timeline"""
        
        output_format = """{
    "analysis_summary": {
        "total_opportunities": number,
        "total_monthly_savings": number,
        "total_annual_savings": number,
        "by_category": {
            "containerization": number,
            "serverless": number,
            "managed_database": number,
            "storage_optimization": number,
            "compute_optimization": number
        },
        "average_savings_percentage": number,
        "implementation_complexity_distribution": {
            "low": number,
            "medium": number,
            "high": number
        }
    },
    "opportunities": [
        {
            "vm_name": "specific-vm-name",
            "current_workload_type": "Web Server",
            "modernization_type": "containerization",
            "target_aws_service": "Amazon ECS Fargate",
            "current_monthly_cost": 150.00,
            "modernized_monthly_cost": 95.00,
            "monthly_savings": 55.00,
            "annual_savings": 660.00,
            "savings_percentage": 36.7,
            "implementation_complexity": "Medium",
            "business_justification": "Detailed explanation of business benefits including scalability, maintenance reduction, and operational efficiency",
            "risk_assessment": "Low risk - standard web application with well-defined containerization patterns",
            "prerequisites": ["Application containerization", "CI/CD pipeline setup", "Load balancer configuration"],
            "estimated_implementation_time": "2-3 weeks",
            "operational_benefits": ["Auto-scaling", "Improved deployment speed", "Better resource utilization"],
            "technical_considerations": ["Database connectivity", "Session management", "Logging and monitoring"],
            "success_criteria": ["Performance maintained", "Cost savings achieved", "Deployment automation working"]
        }
    ]
}"""
        
        examples = """EXAMPLE OPPORTUNITY:
{
    "vm_name": "web-app-server-01",
    "current_workload_type": "Web Application Server",
    "modernization_type": "containerization",
    "target_aws_service": "Amazon ECS Fargate",
    "current_monthly_cost": 180.00,
    "modernized_monthly_cost": 108.00,
    "monthly_savings": 72.00,
    "annual_savings": 864.00,
    "savings_percentage": 40.0,
    "implementation_complexity": "Medium",
    "business_justification": "Containerizing this web application will provide auto-scaling capabilities, reduce operational overhead, and improve deployment speed. The application shows variable traffic patterns that would benefit from elastic scaling.",
    "risk_assessment": "Low risk - stateless web application with standard architecture patterns",
    "prerequisites": ["Containerize application", "Set up ECS cluster", "Configure load balancer", "Implement CI/CD pipeline"],
    "estimated_implementation_time": "3-4 weeks",
    "operational_benefits": ["Auto-scaling based on demand", "Zero-downtime deployments", "Improved resource utilization", "Simplified maintenance"],
    "technical_considerations": ["Database connection pooling", "Session state management", "Log aggregation", "Health checks"],
    "success_criteria": ["Response time < 200ms", "99.9% availability", "40% cost reduction achieved", "Automated deployments working"]
}"""
        
        return self.ai_service.create_structured_prompt(
            system_role=system_role,
            context=context,
            task=task,
            output_format=output_format,
            examples=examples
        )
    
    def _create_fallback_opportunities(self, vm_inventory: List[Dict], cost_estimates: List[Dict] = None) -> List[Dict]:
        """Create basic modernization opportunities using rule-based logic as fallback"""
        
        opportunities = []
        
        for i, vm in enumerate(vm_inventory):
            vm_name = vm.get('VM', 'Unknown')
            vm_name_lower = vm_name.lower()
            
            # Get cost estimate if available
            current_cost = 100.0  # Default cost
            if cost_estimates and i < len(cost_estimates):
                current_cost = cost_estimates[i].get('projected_monthly_cost', 100.0)
            
            # Web application containerization
            if any(pattern in vm_name_lower for pattern in ['web', 'app', 'frontend']):
                modernized_cost = current_cost * 0.6  # 40% savings
                opportunities.append({
                    'vm_name': vm_name,
                    'current_workload_type': 'Web Application',
                    'modernization_type': 'containerization',
                    'target_aws_service': 'Amazon ECS Fargate',
                    'current_monthly_cost': current_cost,
                    'modernized_monthly_cost': modernized_cost,
                    'monthly_savings': current_cost - modernized_cost,
                    'annual_savings': (current_cost - modernized_cost) * 12,
                    'savings_percentage': 40.0,
                    'implementation_complexity': 'Medium',
                    'business_justification': 'Containerization provides auto-scaling and operational efficiency',
                    'risk_assessment': 'Low risk for standard web applications',
                    'prerequisites': ['Application containerization', 'CI/CD setup'],
                    'estimated_implementation_time': '2-3 weeks'
                })
            
            # Database managed service
            elif any(pattern in vm_name_lower for pattern in ['db', 'database', 'sql', 'mysql', 'postgres']):
                modernized_cost = current_cost * 0.7  # 30% savings
                opportunities.append({
                    'vm_name': vm_name,
                    'current_workload_type': 'Database Server',
                    'modernization_type': 'managed_database',
                    'target_aws_service': 'Amazon RDS',
                    'current_monthly_cost': current_cost,
                    'modernized_monthly_cost': modernized_cost,
                    'monthly_savings': current_cost - modernized_cost,
                    'annual_savings': (current_cost - modernized_cost) * 12,
                    'savings_percentage': 30.0,
                    'implementation_complexity': 'Low',
                    'business_justification': 'Managed database reduces operational overhead and provides automated backups',
                    'risk_assessment': 'Low risk with proper migration planning',
                    'prerequisites': ['Database migration testing', 'Connection string updates'],
                    'estimated_implementation_time': '1-2 weeks'
                })
            
            # Batch processing serverless
            elif any(pattern in vm_name_lower for pattern in ['batch', 'job', 'worker']):
                modernized_cost = current_cost * 0.3  # 70% savings for batch
                opportunities.append({
                    'vm_name': vm_name,
                    'current_workload_type': 'Batch Processing',
                    'modernization_type': 'serverless',
                    'target_aws_service': 'AWS Lambda + EventBridge',
                    'current_monthly_cost': current_cost,
                    'modernized_monthly_cost': modernized_cost,
                    'monthly_savings': current_cost - modernized_cost,
                    'annual_savings': (current_cost - modernized_cost) * 12,
                    'savings_percentage': 70.0,
                    'implementation_complexity': 'Medium',
                    'business_justification': 'Serverless batch processing eliminates idle time costs',
                    'risk_assessment': 'Medium risk - requires application refactoring',
                    'prerequisites': ['Code refactoring', 'Event-driven architecture'],
                    'estimated_implementation_time': '3-4 weeks'
                })
        
        return opportunities
    
    async def analyze_modernization_opportunities(self, vm_inventory: List[Dict], cost_estimates: List[Dict] = None) -> Dict[str, Any]:
        """
        Analyze VM inventory for modernization opportunities using AI
        
        Args:
            vm_inventory: List of VM configuration dictionaries
            cost_estimates: Optional list of cost estimate dictionaries
            
        Returns:
            Dictionary containing modernization analysis results
        """
        
        if not vm_inventory:
            return {
                'analysis_summary': {
                    'total_opportunities': 0,
                    'total_monthly_savings': 0,
                    'total_annual_savings': 0
                },
                'opportunities': [],
                'metadata': {
                    'ai_used': False,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': 0.0
                }
            }
        
        logger.info(f"🔍 Starting AI modernization analysis for {len(vm_inventory)} VMs")
        
        # Create AI prompt
        prompt = self._create_modernization_analysis_prompt(vm_inventory, cost_estimates)
        
        # Analyze with AI and fallback
        result = await self.ai_service.analyze_with_fallback(
            primary_prompt=prompt,
            fallback_function=self._create_fallback_opportunities,
            fallback_args=(vm_inventory, cost_estimates),
            max_tokens=8000
        )
        
        # Process results
        if result['ai_used'] and result['data']:
            # AI analysis successful
            analysis_data = result['data']
            opportunities = analysis_data.get('opportunities', [])
            
            logger.info(f"✅ AI modernization analysis complete: {len(opportunities)} opportunities found")
            
            return {
                'analysis_summary': analysis_data.get('analysis_summary', {}),
                'opportunities': opportunities,
                'metadata': {
                    'ai_used': True,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': result['confidence'],
                    'total_vms_analyzed': len(vm_inventory)
                }
            }
        
        elif result['fallback_used'] and result['data']:
            # Fallback analysis used
            opportunities = result['data']
            
            # Calculate summary for fallback
            total_monthly_savings = sum(opp.get('monthly_savings', 0) for opp in opportunities)
            total_annual_savings = sum(opp.get('annual_savings', 0) for opp in opportunities)
            
            logger.info(f"⚠️ Fallback modernization analysis used: {len(opportunities)} opportunities found")
            
            return {
                'analysis_summary': {
                    'total_opportunities': len(opportunities),
                    'total_monthly_savings': total_monthly_savings,
                    'total_annual_savings': total_annual_savings,
                    'average_savings_percentage': 40.0  # Estimated average
                },
                'opportunities': opportunities,
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
            logger.error("❌ Both AI and fallback modernization analysis failed")
            
            return {
                'analysis_summary': {
                    'total_opportunities': 0,
                    'total_monthly_savings': 0,
                    'total_annual_savings': 0
                },
                'opportunities': [],
                'metadata': {
                    'ai_used': False,
                    'fallback_used': False,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'confidence': 0.0,
                    'error': result.get('error', 'Unknown error'),
                    'total_vms_analyzed': len(vm_inventory)
                }
            }
    
    def get_modernization_statistics(self, opportunities: List[Dict]) -> Dict[str, Any]:
        """Generate statistics from modernization analysis results"""
        
        if not opportunities:
            return {
                'total_opportunities': 0,
                'by_type': {},
                'by_complexity': {},
                'total_savings': 0.0,
                'average_savings_percentage': 0.0
            }
        
        type_counts = {}
        complexity_counts = {}
        total_monthly_savings = 0.0
        savings_percentages = []
        
        for opportunity in opportunities:
            # Count by type
            mod_type = opportunity.get('modernization_type', 'unknown')
            type_counts[mod_type] = type_counts.get(mod_type, 0) + 1
            
            # Count by complexity
            complexity = opportunity.get('implementation_complexity', 'unknown').lower()
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            
            # Sum savings
            monthly_savings = opportunity.get('monthly_savings', 0)
            if isinstance(monthly_savings, (int, float)):
                total_monthly_savings += monthly_savings
            
            # Collect savings percentages
            savings_pct = opportunity.get('savings_percentage', 0)
            if isinstance(savings_pct, (int, float)):
                savings_percentages.append(savings_pct)
        
        avg_savings_pct = sum(savings_percentages) / len(savings_percentages) if savings_percentages else 0.0
        
        return {
            'total_opportunities': len(opportunities),
            'by_type': type_counts,
            'by_complexity': complexity_counts,
            'total_monthly_savings': round(total_monthly_savings, 2),
            'total_annual_savings': round(total_monthly_savings * 12, 2),
            'average_savings_percentage': round(avg_savings_pct, 1)
        }
