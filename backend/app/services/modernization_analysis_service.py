"""
Modernization Analysis Service
AI-powered detection of modernization opportunities for VM workloads
Enhanced with intelligent analysis while maintaining existing API compatibility
"""

import logging
import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import re

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import AI services
from .ai_modernization_analyzer import AIModernizationAnalyzer

from ..models.core_models import (
    ModernizationType,
    ModernizationOpportunity,
    ModernizationCostImpact,
        ModernizationAnalysis
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplexityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class WorkloadPattern:
    """Detected workload pattern for modernization analysis"""
    pattern_type: str
    confidence: float
    indicators: List[str]
    modernization_candidates: List[ModernizationType]

class ModernizationAnalysisService:
    """
    Service for analyzing modernization opportunities with AI-powered analysis
    Detects containerization, serverless, and managed services opportunities
    """
    
    def __init__(self):
        # Initialize AI modernization analyzer
        self.ai_modernization_analyzer = AIModernizationAnalyzer()
        
        # Database patterns for managed database recommendations (fallback)
        self.database_patterns = {
            'mysql': {
                'service': 'Amazon RDS MySQL',
                'serverless_option': 'Amazon Aurora Serverless v2',
                'cost_multiplier': 0.7,  # 30% savings typical
                'complexity': ComplexityLevel.LOW
            },
            'postgresql': {
                'service': 'Amazon RDS PostgreSQL',
                'serverless_option': 'Amazon Aurora Serverless v2',
                'cost_multiplier': 0.7,
                'complexity': ComplexityLevel.LOW
            },
            'oracle': {
                'service': 'Amazon RDS Oracle',
                'serverless_option': None,
                'cost_multiplier': 0.8,  # Less savings due to licensing
                'complexity': ComplexityLevel.MEDIUM
            },
            'sql server': {
                'service': 'Amazon RDS SQL Server',
                'serverless_option': None,
                'cost_multiplier': 0.75,
                'complexity': ComplexityLevel.MEDIUM
            },
            'mongodb': {
                'service': 'Amazon DocumentDB',
                'serverless_option': None,
                'cost_multiplier': 0.6,  # Higher savings for NoSQL
                'complexity': ComplexityLevel.LOW
            }
        }
        
        # Application patterns for containerization
        self.containerization_patterns = {
            'web_application': {
                'indicators': ['web', 'app', 'api', 'frontend', 'backend'],
                'service': 'Amazon ECS/EKS',
                'cost_multiplier': 0.6,  # 40% savings typical
                'complexity': ComplexityLevel.MEDIUM
            },
            'microservices': {
                'indicators': ['service', 'micro', 'api'],
                'service': 'Amazon EKS',
                'cost_multiplier': 0.5,  # Higher savings for microservices
                'complexity': ComplexityLevel.HIGH
            },
            'batch_processing': {
                'indicators': ['batch', 'job', 'worker', 'process'],
                'service': 'AWS Batch',
                'cost_multiplier': 0.4,  # Significant savings for batch
                'complexity': ComplexityLevel.MEDIUM
            }
        }
        
        # Serverless patterns
        self.serverless_patterns = {
            'api_gateway': {
                'indicators': ['api', 'gateway', 'rest', 'endpoint'],
                'service': 'AWS Lambda + API Gateway',
                'cost_multiplier': 0.3,  # 70% savings for low-traffic APIs
                'complexity': ComplexityLevel.HIGH
            },
            'scheduled_tasks': {
                'indicators': ['cron', 'schedule', 'task', 'job'],
                'service': 'AWS Lambda + EventBridge',
                'cost_multiplier': 0.2,  # 80% savings for scheduled tasks
                'complexity': ComplexityLevel.MEDIUM
            },
            'event_processing': {
                'indicators': ['event', 'queue', 'message', 'stream'],
                'service': 'AWS Lambda + SQS/SNS',
                'cost_multiplier': 0.3,
                'complexity': ComplexityLevel.MEDIUM
            }
        }
        
        logger.info("AI-Enhanced Modernization Analysis Service initialized")
    
    async def analyze_modernization_opportunities(
        self, 
        session_id: str, 
        vm_inventory: List[Dict], 
        cost_estimates: List[Dict]
    ) -> ModernizationAnalysis:
        """
        Analyze modernization opportunities for VM inventory using AI with fallback
        """
        logger.info(f"Starting AI-enhanced modernization analysis for session {session_id} with {len(vm_inventory)} VMs")
        
        try:
            # Use AI modernization analyzer
            ai_result = await self.ai_modernization_analyzer.analyze_modernization_opportunities(
                vm_inventory, cost_estimates
            )
            
            if ai_result and ai_result.get('opportunities'):
                # Convert AI opportunities to ModernizationOpportunity objects
                opportunities = []
                
                for opp_data in ai_result['opportunities']:
                    # Map modernization types
                    type_mapping = {
                        'containerization': ModernizationType.CONTAINERIZATION,
                        'serverless': ModernizationType.SERVERLESS,
                        'managed_database': ModernizationType.MANAGED_DATABASE,
                        'managed_services': ModernizationType.MANAGED_SERVICES
                    }
                    
                    modernization_type = type_mapping.get(
                        opp_data.get('modernization_type', 'managed_services'),
                        ModernizationType.MANAGED_SERVICES
                    )
                    
                    # Create ModernizationOpportunity object
                    opportunity = ModernizationOpportunity(
                        id=f"ai_mod_{session_id}_{len(opportunities)+1}",
                        vm_name=opp_data.get('vm_name', 'Unknown'),
                        current_workload_type=opp_data.get('current_workload_type', 'Unknown'),
                        modernization_type=modernization_type,
                        target_aws_service=opp_data.get('target_aws_service', ''),
                        current_monthly_cost=opp_data.get('current_monthly_cost', 0.0),
                        modernized_monthly_cost=opp_data.get('modernized_monthly_cost', 0.0),
                        monthly_savings=opp_data.get('monthly_savings', 0.0),
                        annual_savings=opp_data.get('annual_savings', 0.0),
                        benefits=opp_data.get('operational_benefits', []),
                        implementation_complexity=opp_data.get('implementation_complexity', 'Medium')
                    )
                    
                    opportunities.append(opportunity)
                
                # Calculate cost impact
                cost_impact = self._calculate_modernization_cost_impact_from_ai(ai_result)
                
                # Group opportunities by type
                opportunities_by_type = self._group_opportunities_by_type(opportunities)
                
                # Create analysis result
                analysis = ModernizationAnalysis(
                    session_id=session_id,
                    cost_impact=cost_impact,
                    opportunities=opportunities,
                    opportunities_by_type=opportunities_by_type,
                    total_opportunities=len(opportunities)
                )
                
                logger.info(f"✅ AI modernization analysis completed: {len(opportunities)} opportunities found")
                return analysis
            
        except Exception as e:
            logger.error(f"⚠️ AI modernization analysis failed, falling back to rule-based: {e}")
        
        # Fallback to original rule-based analysis
        return await self._analyze_modernization_fallback(session_id, vm_inventory, cost_estimates)
    
    async def _analyze_modernization_fallback(
        self, 
        session_id: str, 
        vm_inventory: List[Dict], 
        cost_estimates: List[Dict]
    ) -> ModernizationAnalysis:
        """
        Fallback to original rule-based modernization analysis
        """
        logger.info(f"Using fallback modernization analysis for session {session_id}")
        
        try:
            opportunities = []
            
            # Analyze each VM for modernization opportunities (original logic)
            for i, vm_data in enumerate(vm_inventory):
                vm_cost = cost_estimates[i] if i < len(cost_estimates) else None
                vm_opportunities = self._analyze_vm_modernization_fallback(vm_data, vm_cost)
                opportunities.extend(vm_opportunities)
            
            # Calculate cost impact
            cost_impact = self._calculate_modernization_cost_impact(opportunities, cost_estimates)
            
            # Group opportunities by type
            opportunities_by_type = self._group_opportunities_by_type(opportunities)
            
            # Create analysis result
            analysis = ModernizationAnalysis(
                session_id=session_id,
                cost_impact=cost_impact,
                opportunities=opportunities,
                opportunities_by_type=opportunities_by_type,
                total_opportunities=len(opportunities)
            )
            
            logger.info(f"⚠️ Fallback modernization analysis completed: {len(opportunities)} opportunities found")
            return analysis
            
        except Exception as e:
            logger.error(f"Fallback modernization analysis failed for session {session_id}: {e}")
            raise RuntimeError(f"Modernization analysis failed: {e}")
    
    def _calculate_modernization_cost_impact_from_ai(self, ai_result: Dict) -> ModernizationCostImpact:
        """Calculate cost impact from AI analysis results"""
        
        analysis_summary = ai_result.get('analysis_summary', {})
        opportunities = ai_result.get('opportunities', [])
        
        current_total = sum(opp.get('current_monthly_cost', 0) for opp in opportunities)
        modernized_total = sum(opp.get('modernized_monthly_cost', 0) for opp in opportunities)
        
        return ModernizationCostImpact(
            current_aws_monthly_cost=current_total,
            modernized_aws_monthly_cost=modernized_total,
            total_monthly_savings=analysis_summary.get('total_monthly_savings', 0),
            total_annual_savings=analysis_summary.get('total_annual_savings', 0),
            savings_percentage=analysis_summary.get('average_savings_percentage', 0)
        )
    
    def _analyze_vm_modernization_fallback(self, vm_data: Dict, vm_cost: Optional[Dict]) -> List[ModernizationOpportunity]:
        """
        Analyze a single VM for modernization opportunities
        """
        opportunities = []
        vm_name = vm_data.get('VM', vm_data.get('vm_name', 'Unknown'))
        
        # Get current monthly cost
        current_monthly_cost = vm_cost.get('total_monthly_cost', 100.0) if vm_cost else 100.0
        
        # Detect workload patterns
        workload_patterns = self._detect_workload_patterns(vm_data)
        
        # Generate opportunities based on patterns
        for pattern in workload_patterns:
            for modernization_type in pattern.modernization_candidates:
                opportunity = self._create_modernization_opportunity(
                    vm_data, 
                    pattern, 
                    modernization_type, 
                    current_monthly_cost
                )
                if opportunity:
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _detect_workload_patterns(self, vm_data: Dict) -> List[WorkloadPattern]:
        """
        Detect workload patterns from VM data
        """
        patterns = []
        vm_name = vm_data.get('VM', vm_data.get('vm_name', '')).lower()
        os_type = vm_data.get('OS', vm_data.get('os_type', '')).lower()
        
        # Database pattern detection
        database_pattern = self._detect_database_pattern(vm_name, os_type)
        if database_pattern:
            patterns.append(database_pattern)
        
        # Application pattern detection
        app_patterns = self._detect_application_patterns(vm_name, vm_data)
        patterns.extend(app_patterns)
        
        # Serverless pattern detection
        serverless_patterns = self._detect_serverless_patterns(vm_name, vm_data)
        patterns.extend(serverless_patterns)
        
        return patterns
    
    def _detect_database_pattern(self, vm_name: str, os_type: str) -> Optional[WorkloadPattern]:
        """
        Detect database workload patterns
        """
        for db_type, config in self.database_patterns.items():
            if db_type in vm_name or db_type.replace(' ', '') in vm_name:
                return WorkloadPattern(
                    pattern_type=f"database_{db_type.replace(' ', '_')}",
                    confidence=0.9,
                    indicators=[f"{db_type} database detected in VM name"],
                    modernization_candidates=[ModernizationType.MANAGED_DATABASE]
                )
        
        # Generic database detection
        db_indicators = ['db', 'database', 'sql', 'mysql', 'postgres', 'oracle', 'mongo']
        if any(indicator in vm_name for indicator in db_indicators):
            return WorkloadPattern(
                pattern_type="database_generic",
                confidence=0.7,
                indicators=["Database indicators found in VM name"],
                modernization_candidates=[ModernizationType.MANAGED_DATABASE]
            )
        
        return None
    
    def _detect_application_patterns(self, vm_name: str, vm_data: Dict) -> List[WorkloadPattern]:
        """
        Detect application workload patterns for containerization
        """
        patterns = []
        
        for pattern_name, config in self.containerization_patterns.items():
            indicators_found = [ind for ind in config['indicators'] if ind in vm_name]
            
            if indicators_found:
                confidence = min(0.9, len(indicators_found) * 0.3)
                patterns.append(WorkloadPattern(
                    pattern_type=pattern_name,
                    confidence=confidence,
                    indicators=[f"Found indicators: {', '.join(indicators_found)}"],
                    modernization_candidates=[ModernizationType.CONTAINERIZATION]
                ))
        
        return patterns
    
    def _detect_serverless_patterns(self, vm_name: str, vm_data: Dict) -> List[WorkloadPattern]:
        """
        Detect serverless workload patterns
        """
        patterns = []
        
        # Check CPU and memory for serverless suitability
        cpu_cores = vm_data.get('CPUs', vm_data.get('cpu_cores', 4))
        memory_mb = vm_data.get('Memory', vm_data.get('memory_mb', 8192))
        memory_gb = memory_mb / 1024 if memory_mb > 100 else memory_mb
        
        # Small workloads are good serverless candidates
        if cpu_cores <= 2 and memory_gb <= 8:
            for pattern_name, config in self.serverless_patterns.items():
                indicators_found = [ind for ind in config['indicators'] if ind in vm_name]
                
                if indicators_found:
                    confidence = min(0.8, len(indicators_found) * 0.4)
                    patterns.append(WorkloadPattern(
                        pattern_type=pattern_name,
                        confidence=confidence,
                        indicators=[f"Small workload with indicators: {', '.join(indicators_found)}"],
                        modernization_candidates=[ModernizationType.SERVERLESS]
                    ))
        
        return patterns
    
    def _create_modernization_opportunity(
        self, 
        vm_data: Dict, 
        pattern: WorkloadPattern, 
        modernization_type: ModernizationType,
        current_monthly_cost: float
    ) -> Optional[ModernizationOpportunity]:
        """
        Create a modernization opportunity based on detected pattern
        """
        vm_name = vm_data.get('VM', vm_data.get('vm_name', 'Unknown'))
        
        # Determine target service and cost multiplier
        target_service, cost_multiplier, complexity, benefits = self._get_modernization_details(
            pattern, modernization_type
        )
        
        if not target_service:
            return None
        
        # Calculate modernized cost
        modernized_monthly_cost = current_monthly_cost * cost_multiplier
        monthly_savings = current_monthly_cost - modernized_monthly_cost
        annual_savings = monthly_savings * 12
        
        # Generate unique ID
        opportunity_id = f"{vm_name}_{modernization_type.value}_{pattern.pattern_type}"
        
        return ModernizationOpportunity(
            id=opportunity_id,
            vm_name=vm_name,
            current_workload_type=pattern.pattern_type,
            modernization_type=modernization_type,
            target_aws_service=target_service,
            current_monthly_cost=current_monthly_cost,
            modernized_monthly_cost=modernized_monthly_cost,
            monthly_savings=monthly_savings,
            annual_savings=annual_savings,
            benefits=benefits,
            implementation_complexity=complexity.value
        )
    
    def _get_modernization_details(
        self, 
        pattern: WorkloadPattern, 
        modernization_type: ModernizationType
    ) -> Tuple[str, float, ComplexityLevel, List[str]]:
        """
        Get modernization details based on pattern and type
        """
        if modernization_type == ModernizationType.MANAGED_DATABASE:
            # Find matching database pattern
            for db_type, config in self.database_patterns.items():
                if db_type.replace(' ', '_') in pattern.pattern_type:
                    benefits = [
                        "Automated backups and maintenance",
                        "High availability and disaster recovery",
                        "Automatic scaling capabilities",
                        "Reduced operational overhead",
                        "Enhanced security features"
                    ]
                    return config['service'], config['cost_multiplier'], config['complexity'], benefits
            
            # Generic database modernization
            benefits = [
                "Managed database service benefits",
                "Reduced operational overhead",
                "Improved reliability and availability"
            ]
            return "Amazon RDS", 0.7, ComplexityLevel.MEDIUM, benefits
        
        elif modernization_type == ModernizationType.CONTAINERIZATION:
            # Find matching containerization pattern
            for pattern_name, config in self.containerization_patterns.items():
                if pattern_name in pattern.pattern_type:
                    benefits = [
                        "Improved resource utilization",
                        "Faster deployment and scaling",
                        "Better development workflow",
                        "Microservices architecture enablement",
                        "Cost optimization through right-sizing"
                    ]
                    return config['service'], config['cost_multiplier'], config['complexity'], benefits
            
            # Generic containerization
            benefits = [
                "Container orchestration benefits",
                "Improved scalability and efficiency"
            ]
            return "Amazon ECS", 0.6, ComplexityLevel.MEDIUM, benefits
        
        elif modernization_type == ModernizationType.SERVERLESS:
            # Find matching serverless pattern
            for pattern_name, config in self.serverless_patterns.items():
                if pattern_name in pattern.pattern_type:
                    benefits = [
                        "Pay-per-use pricing model",
                        "Automatic scaling to zero",
                        "No server management required",
                        "Built-in high availability",
                        "Significant cost savings for variable workloads"
                    ]
                    return config['service'], config['cost_multiplier'], config['complexity'], benefits
            
            # Generic serverless
            benefits = [
                "Serverless architecture benefits",
                "Reduced operational costs"
            ]
            return "AWS Lambda", 0.3, ComplexityLevel.HIGH, benefits
        
        elif modernization_type == ModernizationType.MANAGED_SERVICES:
            benefits = [
                "Fully managed service benefits",
                "Reduced operational complexity",
                "Built-in scalability and reliability"
            ]
            return "AWS Managed Services", 0.8, ComplexityLevel.LOW, benefits
        
        return None, 1.0, ComplexityLevel.HIGH, []
    
    def _calculate_modernization_cost_impact(
        self, 
        opportunities: List[ModernizationOpportunity], 
        cost_estimates: List[Dict]
    ) -> ModernizationCostImpact:
        """
        Calculate overall cost impact of modernization opportunities
        """
        if not opportunities:
            return ModernizationCostImpact(
                current_aws_monthly_cost=0.0,
                modernized_aws_monthly_cost=0.0,
                total_monthly_savings=0.0,
                total_annual_savings=0.0,
                savings_percentage=0.0
            )
        
        # Calculate current AWS monthly cost
        current_aws_monthly_cost = sum(est.get('total_monthly_cost', 0) for est in cost_estimates)
        
        # Calculate total savings from opportunities
        total_monthly_savings = sum(opp.monthly_savings for opp in opportunities)
        total_annual_savings = total_monthly_savings * 12
        
        # Calculate modernized cost
        modernized_aws_monthly_cost = current_aws_monthly_cost - total_monthly_savings
        
        # Calculate savings percentage
        savings_percentage = (total_monthly_savings / current_aws_monthly_cost * 100) if current_aws_monthly_cost > 0 else 0
        
        return ModernizationCostImpact(
            current_aws_monthly_cost=current_aws_monthly_cost,
            modernized_aws_monthly_cost=modernized_aws_monthly_cost,
            total_monthly_savings=total_monthly_savings,
            total_annual_savings=total_annual_savings,
            savings_percentage=savings_percentage
        )
    
    def _group_opportunities_by_type(
        self, 
        opportunities: List[ModernizationOpportunity]
    ) -> Dict[ModernizationType, List[ModernizationOpportunity]]:
        """
        Group opportunities by modernization type
        """
        grouped = {}
        
        for opportunity in opportunities:
            mod_type = opportunity.modernization_type
            if mod_type not in grouped:
                grouped[mod_type] = []
            grouped[mod_type].append(opportunity)
        
        return grouped
    
    def get_modernization_summary(self, analysis: ModernizationAnalysis) -> Dict:
        """
        Get summary statistics for modernization analysis
        """
        summary = {
            "total_opportunities": analysis.total_opportunities,
            "total_monthly_savings": analysis.cost_impact.total_monthly_savings,
            "total_annual_savings": analysis.cost_impact.total_annual_savings,
            "savings_percentage": analysis.cost_impact.savings_percentage,
            "opportunities_by_type": {},
            "complexity_breakdown": {"low": 0, "medium": 0, "high": 0}
        }
        
        # Count opportunities by type
        for mod_type, opportunities in analysis.opportunities_by_type.items():
            summary["opportunities_by_type"][mod_type.value] = {
                "count": len(opportunities),
                "total_savings": sum(opp.monthly_savings for opp in opportunities),
                "average_savings": sum(opp.monthly_savings for opp in opportunities) / len(opportunities) if opportunities else 0
            }
        
        # Count by complexity
        for opportunity in analysis.opportunities:
            complexity = opportunity.implementation_complexity
            summary["complexity_breakdown"][complexity] += 1
        
        return summary

# Global modernization analysis service
modernization_service = ModernizationAnalysisService()
