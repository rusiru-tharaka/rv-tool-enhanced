"""
Real AI Integration with Claude 3.7 Sonnet via Amazon Bedrock
Enhanced UX Migration Analysis Platform - AI-Powered Analysis
"""

import json
import boto3
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BedrockAIEngine:
    """AI-powered analysis engine using Claude 3.7 Sonnet via Amazon Bedrock"""
    
    def __init__(self, profile_name: str = "smartslot", region: str = "us-east-1"):
        """Initialize Bedrock client with smartslot profile"""
        try:
            # Initialize Bedrock client with smartslot profile
            session = boto3.Session(profile_name=profile_name)
            self.bedrock_client = session.client('bedrock-runtime', region_name=region)
            # Use Claude 3.7 Sonnet inference profile
            self.model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            self.ai_enabled = True
            logger.info(f"✅ Bedrock AI Engine initialized with Claude 3.7 Sonnet via inference profile")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bedrock client: {e}")
            self.ai_enabled = False
            self.bedrock_client = None
    
    async def invoke_claude(self, prompt: str, max_tokens: int = 4000) -> Optional[str]:
        """Invoke Claude 3.7 Sonnet via Bedrock"""
        if not self.ai_enabled:
            logger.warning("AI not enabled, skipping Claude invocation")
            return None
        
        try:
            # Prepare the request body for Claude 3.7 Sonnet
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.1,  # Low temperature for consistent analysis
                "top_p": 0.9
            }
            
            # Invoke the model
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            else:
                logger.error("Unexpected response format from Claude")
                return None
                
        except Exception as e:
            logger.error(f"Error invoking Claude 3.7 Sonnet: {e}")
            return None
    
    async def analyze_migration_complexity(self, vm_inventory: List[Dict]) -> Dict[str, Any]:
        """AI-powered migration complexity analysis using Claude 3.7 Sonnet"""
        
        # Prepare sample data for analysis (first 10 VMs to avoid token limits)
        sample_vms = vm_inventory[:10]
        total_vms = len(vm_inventory)
        
        # Calculate basic statistics
        total_vcpus = sum(vm.get('CPUs', 2) for vm in vm_inventory)
        total_ram_gb = sum(vm.get('Memory', 4096) for vm in vm_inventory) / 1024
        total_storage_gb = sum(vm.get('Provisioned MB', 51200) for vm in vm_inventory) / 1024
        
        prompt = f"""
You are a senior VMware to AWS migration architect with 15+ years of experience. Analyze this VMware environment for migration complexity and provide detailed insights.

ENVIRONMENT OVERVIEW:
- Total VMs: {total_vms}
- Total vCPUs: {total_vcpus}
- Total RAM: {total_ram_gb:.1f} GB
- Total Storage: {total_storage_gb:.1f} GB

SAMPLE VM INVENTORY (first 10 VMs):
{json.dumps(sample_vms, indent=2)}

Please provide a comprehensive analysis in the following JSON format:

{{
    "complexity_score": <integer 0-100>,
    "estimated_timeline_months": <integer>,
    "key_challenges": [
        "<challenge 1>",
        "<challenge 2>",
        "<challenge 3>"
    ],
    "migration_blockers": [
        {{
            "vm_name": "<vm_name>",
            "severity": "<critical|high|medium|low>",
            "issue_type": "<issue_category>",
            "description": "<detailed_description>",
            "remediation": "<recommended_solution>",
            "confidence_score": <float 0.0-1.0>
        }}
    ],
    "workload_classification": {{
        "production": {{
            "count": <integer>,
            "percentage": <float>,
            "indicators": ["<indicator1>", "<indicator2>"]
        }},
        "development": {{
            "count": <integer>,
            "percentage": <float>,
            "indicators": ["<indicator1>", "<indicator2>"]
        }},
        "testing": {{
            "count": <integer>,
            "percentage": <float>,
            "indicators": ["<indicator1>", "<indicator2>"]
        }}
    }},
    "recommended_approach": "<migration_strategy>",
    "risk_assessment": {{
        "overall_risk": "<low|medium|high|critical>",
        "technical_risks": ["<risk1>", "<risk2>"],
        "business_risks": ["<risk1>", "<risk2>"]
    }},
    "ai_insights": {{
        "analysis_confidence": <float 0.0-1.0>,
        "key_observations": ["<observation1>", "<observation2>"],
        "recommendations": ["<recommendation1>", "<recommendation2>"]
    }}
}}

Focus on:
1. VM naming patterns to identify production vs non-production workloads
2. Resource allocation patterns that indicate workload types
3. Potential migration blockers based on VM characteristics
4. Realistic timeline estimation based on environment size and complexity
5. Risk factors that could impact migration success

Provide only the JSON response, no additional text.
"""
        
        # Get AI analysis
        ai_response = await self.invoke_claude(prompt, max_tokens=4000)
        
        if ai_response:
            try:
                # Parse AI response
                ai_analysis = json.loads(ai_response)
                
                # Add metadata
                ai_analysis['ai_metadata'] = {
                    'model_used': 'Claude 3.7 Sonnet',
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'total_vms_analyzed': total_vms,
                    'sample_size': len(sample_vms),
                    'ai_enabled': True
                }
                
                return ai_analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                return self._fallback_analysis(vm_inventory)
        else:
            logger.warning("AI analysis failed, using fallback")
            return self._fallback_analysis(vm_inventory)
    
    async def analyze_modernization_opportunities(self, vm_inventory: List[Dict]) -> List[Dict[str, Any]]:
        """AI-powered modernization opportunity analysis"""
        
        # Analyze first 20 VMs for modernization opportunities
        sample_vms = vm_inventory[:20]
        
        prompt = f"""
You are an AWS modernization expert specializing in identifying containerization, serverless, and managed services opportunities. Analyze these VMs for modernization potential.

VM INVENTORY TO ANALYZE:
{json.dumps(sample_vms, indent=2)}

For each VM that has modernization potential, provide analysis in this JSON format:

{{
    "opportunities": [
        {{
            "vm_name": "<vm_name>",
            "current_workload_type": "<workload_category>",
            "modernization_type": "<managed_database|serverless|containerization|managed_services>",
            "target_aws_service": "<specific_aws_service>",
            "confidence_score": <float 0.0-1.0>,
            "implementation_complexity": "<low|medium|high>",
            "estimated_cost_savings_percentage": <integer 0-100>,
            "benefits": [
                "<benefit1>",
                "<benefit2>",
                "<benefit3>"
            ],
            "implementation_steps": [
                "<step1>",
                "<step2>",
                "<step3>"
            ],
            "considerations": [
                "<consideration1>",
                "<consideration2>"
            ]
        }}
    ],
    "summary": {{
        "total_opportunities": <integer>,
        "high_confidence_opportunities": <integer>,
        "potential_cost_savings": "<percentage_range>",
        "recommended_priority_order": [
            "<vm_name1>",
            "<vm_name2>"
        ]
    }}
}}

Focus on identifying:
1. Database workloads → Amazon RDS/Aurora
2. Web applications → AWS App Runner/ECS
3. API services → AWS Lambda
4. Cache systems → Amazon ElastiCache
5. File servers → Amazon EFS/FSx
6. Batch processing → AWS Batch

Look for naming patterns, resource characteristics, and workload indicators. Provide only the JSON response.
"""
        
        ai_response = await self.invoke_claude(prompt, max_tokens=3000)
        
        if ai_response:
            try:
                ai_analysis = json.loads(ai_response)
                opportunities = ai_analysis.get('opportunities', [])
                
                # Add AI metadata to each opportunity
                for opp in opportunities:
                    opp['ai_generated'] = True
                    opp['analysis_timestamp'] = datetime.utcnow().isoformat()
                
                return opportunities
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse modernization AI response: {e}")
                return self._fallback_modernization_analysis(sample_vms)
        else:
            return self._fallback_modernization_analysis(sample_vms)
    
    async def generate_migration_recommendations(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive migration recommendations based on analysis"""
        
        prompt = f"""
Based on this migration analysis, provide detailed recommendations for a successful VMware to AWS migration:

ANALYSIS RESULTS:
{json.dumps(analysis_results, indent=2)}

Provide recommendations in this JSON format:

{{
    "executive_summary": "<2-3 sentence summary>",
    "migration_strategy": {{
        "recommended_approach": "<lift-and-shift|replatform|refactor|hybrid>",
        "phasing_strategy": [
            {{
                "phase": 1,
                "description": "<phase_description>",
                "vm_count": <integer>,
                "duration_weeks": <integer>,
                "focus": "<phase_focus>"
            }}
        ]
    }},
    "cost_optimization": {{
        "immediate_opportunities": ["<opportunity1>", "<opportunity2>"],
        "long_term_savings": ["<saving1>", "<saving2>"],
        "estimated_savings_percentage": <integer>
    }},
    "risk_mitigation": {{
        "critical_actions": ["<action1>", "<action2>"],
        "contingency_plans": ["<plan1>", "<plan2>"]
    }},
    "success_factors": [
        "<factor1>",
        "<factor2>",
        "<factor3>"
    ],
    "next_steps": [
        {{
            "step": "<step_description>",
            "timeline": "<timeframe>",
            "owner": "<responsible_team>"
        }}
    ]
}}

Provide only the JSON response.
"""
        
        ai_response = await self.invoke_claude(prompt, max_tokens=2500)
        
        if ai_response:
            try:
                recommendations = json.loads(ai_response)
                recommendations['ai_generated'] = True
                recommendations['generated_at'] = datetime.utcnow().isoformat()
                return recommendations
            except json.JSONDecodeError:
                return self._fallback_recommendations()
        else:
            return self._fallback_recommendations()
    
    def _fallback_analysis(self, vm_inventory: List[Dict]) -> Dict[str, Any]:
        """Fallback analysis when AI is not available"""
        total_vms = len(vm_inventory)
        
        return {
            "complexity_score": min(100, 30 + (total_vms // 20)),
            "estimated_timeline_months": max(6, min(36, total_vms // 50)),
            "key_challenges": ["Large-scale migration complexity", "Resource planning required"],
            "migration_blockers": [],
            "workload_classification": {
                "production": {"count": total_vms // 2, "percentage": 50.0},
                "development": {"count": total_vms // 4, "percentage": 25.0},
                "testing": {"count": total_vms // 4, "percentage": 25.0}
            },
            "recommended_approach": "Phased migration approach",
            "risk_assessment": {
                "overall_risk": "medium",
                "technical_risks": ["Scale complexity"],
                "business_risks": ["Timeline management"]
            },
            "ai_metadata": {
                "ai_enabled": False,
                "fallback_analysis": True,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        }
    
    def _fallback_modernization_analysis(self, vm_inventory: List[Dict]) -> List[Dict[str, Any]]:
        """Fallback modernization analysis"""
        return [
            {
                "vm_name": "sample-modernization",
                "modernization_type": "managed_database",
                "target_aws_service": "Amazon RDS",
                "confidence_score": 0.5,
                "ai_generated": False,
                "fallback_analysis": True
            }
        ]
    
    def _fallback_recommendations(self) -> Dict[str, Any]:
        """Fallback recommendations"""
        return {
            "executive_summary": "Standard migration approach recommended",
            "migration_strategy": {
                "recommended_approach": "lift-and-shift",
                "phasing_strategy": []
            },
            "ai_generated": False,
            "fallback_analysis": True
        }

# Global AI engine instance
bedrock_ai_engine = BedrockAIEngine(profile_name="smartslot")

# Async wrapper functions for use in FastAPI
async def get_ai_migration_analysis(vm_inventory: List[Dict]) -> Dict[str, Any]:
    """Get AI-powered migration analysis"""
    return await bedrock_ai_engine.analyze_migration_complexity(vm_inventory)

async def get_ai_modernization_opportunities(vm_inventory: List[Dict]) -> List[Dict[str, Any]]:
    """Get AI-powered modernization opportunities"""
    return await bedrock_ai_engine.analyze_modernization_opportunities(vm_inventory)

async def get_ai_migration_recommendations(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """Get AI-powered migration recommendations"""
    return await bedrock_ai_engine.generate_migration_recommendations(analysis_results)
