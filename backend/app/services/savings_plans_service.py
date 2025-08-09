"""
Savings Plans Service
Comprehensive AWS Savings Plans analysis and recommendation service
Provides intelligent Savings Plans recommendations based on workload patterns
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import math

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .aws_pricing_service import pricing_service, SavingsPlansPrice, InstancePricing
from .instance_recommendation_service import (
    recommendation_service, 
    VMSpecification, 
    InstanceRecommendation, 
    WorkloadType
)

# Optional import for historical pricing service
try:
    from .historical_pricing_service import historical_pricing_service
    HISTORICAL_PRICING_AVAILABLE = True
except ImportError:
    historical_pricing_service = None
    HISTORICAL_PRICING_AVAILABLE = False
    logger.warning("Historical pricing service not available - some features may be limited")

from ..models.core_models import TCOParameters

@dataclass
class SavingsPlansRecommendation:
    """Comprehensive Savings Plans recommendation"""
    plan_type: str  # "compute" or "ec2_instance"
    instance_family: Optional[str] = None
    region: str = ""
    commitment_term: str = "1_year"  # "1_year" or "3_year"
    payment_option: str = "no_upfront"  # "no_upfront", "partial_upfront", "all_upfront"
    
    # Financial Analysis
    hourly_commitment: float = 0.0
    monthly_commitment: float = 0.0
    annual_commitment: float = 0.0
    upfront_payment: float = 0.0
    
    # Savings Analysis
    estimated_monthly_savings: float = 0.0
    estimated_annual_savings: float = 0.0
    savings_percentage: float = 0.0
    break_even_months: int = 0
    
    # Coverage Analysis
    covered_instances: List[str] = field(default_factory=list)
    coverage_percentage: float = 0.0
    utilization_percentage: float = 0.0
    
    # Risk Analysis
    commitment_risk_score: float = 0.0  # 0-100, higher = more risky
    flexibility_score: float = 0.0  # 0-100, higher = more flexible
    recommendation_confidence: float = 0.0  # 0-1
    
    # Additional Details
    applicable_instance_types: List[str] = field(default_factory=list)
    workload_suitability: str = "high"  # "high", "medium", "low"
    notes: List[str] = field(default_factory=list)

@dataclass
class SavingsPlansPortfolio:
    """Complete Savings Plans portfolio recommendation"""
    total_monthly_commitment: float
    total_annual_commitment: float
    total_upfront_payment: float
    total_monthly_savings: float
    total_annual_savings: float
    overall_savings_percentage: float
    
    compute_savings_plans: List[SavingsPlansRecommendation]
    ec2_instance_savings_plans: List[SavingsPlansRecommendation]
    
    portfolio_risk_score: float
    diversification_score: float
    recommendation_summary: str

class SavingsPlansService:
    """
    Advanced Savings Plans analysis and recommendation service
    """
    
    def __init__(self):
        self.pricing_service = pricing_service
        self.historical_service = historical_pricing_service if HISTORICAL_PRICING_AVAILABLE else None
        
        # Savings Plans configuration
        self.commitment_terms = ["1_year", "3_year"]
        self.payment_options = ["no_upfront", "partial_upfront", "all_upfront"]
        self.instance_families = ["m5", "c5", "r5", "t3", "m6i", "c6i", "r6i"]
        
        logger.info("Savings Plans Service initialized")
    
    async def analyze_savings_opportunities(
        self,
        vm_inventory: List[Dict],
        tco_parameters: TCOParameters,
        current_monthly_spend: float
    ) -> SavingsPlansPortfolio:
        """
        Analyze comprehensive Savings Plans opportunities for VM inventory
        """
        logger.info(f"Analyzing Savings Plans opportunities for {len(vm_inventory)} VMs")
        
        try:
            # Analyze workload patterns
            workload_analysis = await self._analyze_workload_patterns(vm_inventory)
            
            # Get current pricing for comparison
            current_pricing = await self._get_current_pricing_baseline(vm_inventory, tco_parameters.target_region)
            
            # Generate Compute Savings Plans recommendations
            compute_recommendations = await self._generate_compute_savings_recommendations(
                workload_analysis, current_pricing, tco_parameters
            )
            
            # Generate EC2 Instance Savings Plans recommendations
            ec2_recommendations = await self._generate_ec2_instance_savings_recommendations(
                workload_analysis, current_pricing, tco_parameters
            )
            
            # Optimize portfolio mix
            optimized_portfolio = await self._optimize_savings_portfolio(
                compute_recommendations, ec2_recommendations, current_monthly_spend
            )
            
            logger.info(f"Generated Savings Plans portfolio with {len(optimized_portfolio.compute_savings_plans)} "
                       f"Compute and {len(optimized_portfolio.ec2_instance_savings_plans)} EC2 Instance plans")
            
            return optimized_portfolio
            
        except Exception as e:
            logger.error(f"Failed to analyze Savings Plans opportunities: {e}")
            raise RuntimeError(f"Savings Plans analysis failed: {e}")
    
    async def _analyze_workload_patterns(self, vm_inventory: List[Dict]) -> Dict:
        """Analyze workload patterns to determine Savings Plans suitability"""
        
        workload_analysis = {
            "total_vms": len(vm_inventory),
            "instance_families": {},
            "workload_types": {},
            "utilization_patterns": {},
            "stability_score": 0.0
        }
        
        # Analyze instance family distribution
        for vm in vm_inventory:
            # Determine likely instance family based on VM characteristics
            cpu_cores = int(vm.get('CPUs', 1))
            memory_gb = float(vm.get('Memory', 1024)) / 1024  # Convert from MB
            
            instance_family = self._determine_instance_family(cpu_cores, memory_gb)
            workload_analysis["instance_families"][instance_family] = \
                workload_analysis["instance_families"].get(instance_family, 0) + 1
            
            # Analyze workload type
            workload_type = self._determine_workload_type(vm)
            workload_analysis["workload_types"][workload_type] = \
                workload_analysis["workload_types"].get(workload_type, 0) + 1
        
        # Calculate stability score (higher = more suitable for Savings Plans)
        production_vms = workload_analysis["workload_types"].get("production", 0)
        workload_analysis["stability_score"] = (production_vms / len(vm_inventory)) * 100
        
        return workload_analysis
    
    def _determine_instance_family(self, cpu_cores: int, memory_gb: float) -> str:
        """Determine likely AWS instance family based on VM characteristics"""
        
        memory_per_cpu = memory_gb / cpu_cores if cpu_cores > 0 else 0
        
        # Memory-optimized workloads
        if memory_per_cpu > 6:
            return "r5"  # Memory optimized
        # Compute-optimized workloads
        elif memory_per_cpu < 2:
            return "c5"  # Compute optimized
        # Burstable workloads (small instances)
        elif cpu_cores <= 2 and memory_gb <= 8:
            return "t3"  # Burstable
        # General purpose (default)
        else:
            return "m5"  # General purpose
    
    def _determine_workload_type(self, vm: Dict) -> str:
        """Determine workload type based on VM characteristics"""
        
        vm_name = vm.get('VM', '').lower()
        power_state = vm.get('Powerstate', 'poweredOn')
        
        # Production indicators
        if any(keyword in vm_name for keyword in ['prod', 'production', 'prd']):
            return "production"
        # Development indicators
        elif any(keyword in vm_name for keyword in ['dev', 'development', 'test', 'staging']):
            return "development"
        # Powered off VMs
        elif power_state != 'poweredOn':
            return "inactive"
        # Default to production for conservative Savings Plans recommendations
        else:
            return "production"
    
    async def _get_current_pricing_baseline(self, vm_inventory: List[Dict], region: str) -> Dict:
        """Get current on-demand pricing baseline for comparison"""
        
        baseline = {
            "total_monthly_cost": 0.0,
            "instance_costs": {},
            "family_costs": {}
        }
        
        # Calculate current on-demand costs
        for vm in vm_inventory:
            cpu_cores = int(vm.get('CPUs', 1))
            memory_gb = float(vm.get('Memory', 1024)) / 1024
            
            # Estimate instance type
            instance_family = self._determine_instance_family(cpu_cores, memory_gb)
            estimated_instance_type = self._estimate_instance_type(cpu_cores, memory_gb, instance_family)
            
            try:
                pricing = await self.pricing_service.get_instance_pricing(estimated_instance_type, region)
                monthly_cost = pricing.on_demand_hourly * 24 * 30  # Approximate monthly cost
                
                baseline["total_monthly_cost"] += monthly_cost
                baseline["instance_costs"][estimated_instance_type] = \
                    baseline["instance_costs"].get(estimated_instance_type, 0) + monthly_cost
                baseline["family_costs"][instance_family] = \
                    baseline["family_costs"].get(instance_family, 0) + monthly_cost
                    
            except Exception as e:
                logger.warning(f"Could not get pricing for {estimated_instance_type}: {e}")
        
        return baseline
    
    def _estimate_instance_type(self, cpu_cores: int, memory_gb: float, instance_family: str) -> str:
        """Estimate specific instance type based on CPU and memory requirements"""
        
        # Instance type mappings based on CPU cores
        instance_mappings = {
            "t3": {1: "t3.micro", 2: "t3.small", 4: "t3.medium", 8: "t3.large"},
            "m5": {2: "m5.large", 4: "m5.xlarge", 8: "m5.2xlarge", 16: "m5.4xlarge"},
            "c5": {2: "c5.large", 4: "c5.xlarge", 8: "c5.2xlarge", 16: "c5.4xlarge"},
            "r5": {2: "r5.large", 4: "r5.xlarge", 8: "r5.2xlarge", 16: "r5.4xlarge"}
        }
        
        family_mapping = instance_mappings.get(instance_family, instance_mappings["m5"])
        
        # Find closest match based on CPU cores
        closest_cpu = min(family_mapping.keys(), key=lambda x: abs(x - cpu_cores))
        return family_mapping[closest_cpu]
    
    async def _generate_compute_savings_recommendations(
        self,
        workload_analysis: Dict,
        current_pricing: Dict,
        tco_parameters: TCOParameters
    ) -> List[SavingsPlansRecommendation]:
        """Generate Compute Savings Plans recommendations"""
        
        recommendations = []
        
        # Only recommend if workload is stable enough
        if workload_analysis["stability_score"] < 60:
            logger.info("Workload stability too low for Compute Savings Plans recommendations")
            return recommendations
        
        # Calculate optimal commitment levels
        monthly_baseline = current_pricing["total_monthly_cost"]
        
        # Conservative recommendation: 70% of current spend
        conservative_commitment = monthly_baseline * 0.7
        
        # Aggressive recommendation: 90% of current spend
        aggressive_commitment = monthly_baseline * 0.9
        
        for commitment_level, commitment_amount in [
            ("conservative", conservative_commitment),
            ("aggressive", aggressive_commitment)
        ]:
            for term in self.commitment_terms:
                for payment in self.payment_options:
                    try:
                        # Get Compute Savings Plans pricing
                        savings_plans = await self.pricing_service.get_savings_plans_pricing(
                            "compute", tco_parameters.target_region, term, payment
                        )
                        
                        if savings_plans:
                            savings_plan = savings_plans[0]  # Take first available
                            
                            # Calculate savings
                            hourly_commitment = commitment_amount / (30 * 24)  # Convert monthly to hourly
                            monthly_savings = commitment_amount * (savings_plan.savings_percentage / 100)
                            annual_savings = monthly_savings * 12
                            
                            # Calculate risk and flexibility scores
                            risk_score = self._calculate_commitment_risk(term, payment, commitment_level)
                            flexibility_score = self._calculate_flexibility_score("compute", None)
                            
                            recommendation = SavingsPlansRecommendation(
                                plan_type="compute",
                                region=tco_parameters.target_region,
                                commitment_term=term,
                                payment_option=payment,
                                hourly_commitment=hourly_commitment,
                                monthly_commitment=commitment_amount,
                                annual_commitment=commitment_amount * 12,
                                upfront_payment=savings_plan.upfront_cost,
                                estimated_monthly_savings=monthly_savings,
                                estimated_annual_savings=annual_savings,
                                savings_percentage=savings_plan.savings_percentage,
                                break_even_months=self._calculate_break_even_months(
                                    savings_plan.upfront_cost, monthly_savings
                                ),
                                coverage_percentage=70 if commitment_level == "conservative" else 90,
                                utilization_percentage=85,  # Estimated utilization
                                commitment_risk_score=risk_score,
                                flexibility_score=flexibility_score,
                                recommendation_confidence=0.8 if commitment_level == "conservative" else 0.6,
                                workload_suitability="high" if workload_analysis["stability_score"] > 80 else "medium",
                                notes=[
                                    f"Covers {commitment_level} portion of compute workload",
                                    f"Suitable for stable workloads with {workload_analysis['stability_score']:.1f}% stability"
                                ]
                            )
                            
                            recommendations.append(recommendation)
                            
                    except Exception as e:
                        logger.warning(f"Could not generate Compute Savings Plans recommendation: {e}")
        
        # Sort by savings amount (descending)
        recommendations.sort(key=lambda x: x.estimated_annual_savings, reverse=True)
        
        # Return top 3 recommendations
        return recommendations[:3]
    
    async def _generate_ec2_instance_savings_recommendations(
        self,
        workload_analysis: Dict,
        current_pricing: Dict,
        tco_parameters: TCOParameters
    ) -> List[SavingsPlansRecommendation]:
        """Generate EC2 Instance Savings Plans recommendations"""
        
        recommendations = []
        
        # Generate recommendations for each significant instance family
        for family, vm_count in workload_analysis["instance_families"].items():
            if vm_count < 2:  # Skip families with too few instances
                continue
            
            family_cost = current_pricing["family_costs"].get(family, 0)
            if family_cost < 100:  # Skip low-cost families
                continue
            
            for term in self.commitment_terms:
                for payment in self.payment_options:
                    try:
                        # Get EC2 Instance Savings Plans pricing
                        savings_plans = await self.pricing_service.get_savings_plans_pricing(
                            family, tco_parameters.target_region, term, payment
                        )
                        
                        if savings_plans:
                            savings_plan = savings_plans[0]
                            
                            # Calculate optimal commitment (80% of family spend)
                            monthly_commitment = family_cost * 0.8
                            hourly_commitment = monthly_commitment / (30 * 24)
                            
                            # Calculate savings
                            monthly_savings = monthly_commitment * (savings_plan.savings_percentage / 100)
                            annual_savings = monthly_savings * 12
                            
                            # Get applicable instance types for this family
                            applicable_types = self._get_family_instance_types(family)
                            
                            recommendation = SavingsPlansRecommendation(
                                plan_type="ec2_instance",
                                instance_family=family,
                                region=tco_parameters.target_region,
                                commitment_term=term,
                                payment_option=payment,
                                hourly_commitment=hourly_commitment,
                                monthly_commitment=monthly_commitment,
                                annual_commitment=monthly_commitment * 12,
                                upfront_payment=savings_plan.upfront_cost,
                                estimated_monthly_savings=monthly_savings,
                                estimated_annual_savings=annual_savings,
                                savings_percentage=savings_plan.savings_percentage,
                                break_even_months=self._calculate_break_even_months(
                                    savings_plan.upfront_cost, monthly_savings
                                ),
                                coverage_percentage=80,
                                utilization_percentage=90,
                                commitment_risk_score=self._calculate_commitment_risk(term, payment, "moderate"),
                                flexibility_score=self._calculate_flexibility_score("ec2_instance", family),
                                recommendation_confidence=0.75,
                                applicable_instance_types=applicable_types,
                                workload_suitability="high",
                                notes=[
                                    f"Optimized for {family} instance family",
                                    f"Covers {vm_count} VMs in this family"
                                ]
                            )
                            
                            recommendations.append(recommendation)
                            
                    except Exception as e:
                        logger.warning(f"Could not generate EC2 Instance Savings Plans for {family}: {e}")
        
        # Sort by savings amount (descending)
        recommendations.sort(key=lambda x: x.estimated_annual_savings, reverse=True)
        
        # Return top 5 recommendations
        return recommendations[:5]
    
    def _calculate_commitment_risk(self, term: str, payment: str, commitment_level: str) -> float:
        """Calculate commitment risk score (0-100, higher = more risky)"""
        
        risk_score = 0.0
        
        # Term risk
        if term == "3_year":
            risk_score += 40
        else:  # 1_year
            risk_score += 20
        
        # Payment risk
        if payment == "all_upfront":
            risk_score += 30
        elif payment == "partial_upfront":
            risk_score += 15
        # no_upfront adds 0
        
        # Commitment level risk
        if commitment_level == "aggressive":
            risk_score += 25
        elif commitment_level == "moderate":
            risk_score += 15
        # conservative adds 0
        
        return min(risk_score, 100.0)
    
    def _calculate_flexibility_score(self, plan_type: str, instance_family: Optional[str]) -> float:
        """Calculate flexibility score (0-100, higher = more flexible)"""
        
        if plan_type == "compute":
            return 90.0  # Compute Savings Plans are very flexible
        elif plan_type == "ec2_instance":
            # EC2 Instance Savings Plans are less flexible
            return 60.0
        
        return 50.0
    
    def _calculate_break_even_months(self, upfront_cost: float, monthly_savings: float) -> int:
        """Calculate break-even period in months"""
        
        if monthly_savings <= 0:
            return 999  # Never breaks even
        
        return math.ceil(upfront_cost / monthly_savings)
    
    def _get_family_instance_types(self, family: str) -> List[str]:
        """Get common instance types for a family"""
        
        family_types = {
            "t3": ["t3.micro", "t3.small", "t3.medium", "t3.large", "t3.xlarge"],
            "m5": ["m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge", "m5.8xlarge"],
            "c5": ["c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "c5.9xlarge"],
            "r5": ["r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge", "r5.8xlarge"]
        }
        
        return family_types.get(family, [])
    
    async def _optimize_savings_portfolio(
        self,
        compute_recommendations: List[SavingsPlansRecommendation],
        ec2_recommendations: List[SavingsPlansRecommendation],
        current_monthly_spend: float
    ) -> SavingsPlansPortfolio:
        """Optimize the overall Savings Plans portfolio"""
        
        # Select best recommendations based on savings and risk
        selected_compute = []
        selected_ec2 = []
        
        # Select top Compute Savings Plan (if any)
        if compute_recommendations:
            best_compute = max(compute_recommendations, 
                             key=lambda x: x.estimated_annual_savings - (x.commitment_risk_score * 100))
            selected_compute.append(best_compute)
        
        # Select top EC2 Instance Savings Plans (up to 3)
        if ec2_recommendations:
            # Sort by value (savings minus risk penalty)
            ec2_by_value = sorted(ec2_recommendations, 
                                key=lambda x: x.estimated_annual_savings - (x.commitment_risk_score * 50),
                                reverse=True)
            selected_ec2 = ec2_by_value[:3]
        
        # Calculate portfolio totals
        total_monthly_commitment = sum(r.monthly_commitment for r in selected_compute + selected_ec2)
        total_annual_commitment = sum(r.annual_commitment for r in selected_compute + selected_ec2)
        total_upfront_payment = sum(r.upfront_payment for r in selected_compute + selected_ec2)
        total_monthly_savings = sum(r.estimated_monthly_savings for r in selected_compute + selected_ec2)
        total_annual_savings = sum(r.estimated_annual_savings for r in selected_compute + selected_ec2)
        
        overall_savings_percentage = (total_monthly_savings / current_monthly_spend * 100) if current_monthly_spend > 0 else 0
        
        # Calculate portfolio risk and diversification scores
        portfolio_risk_score = self._calculate_portfolio_risk(selected_compute + selected_ec2)
        diversification_score = self._calculate_diversification_score(selected_compute + selected_ec2)
        
        # Generate recommendation summary
        recommendation_summary = self._generate_portfolio_summary(
            selected_compute, selected_ec2, total_annual_savings, overall_savings_percentage
        )
        
        return SavingsPlansPortfolio(
            total_monthly_commitment=total_monthly_commitment,
            total_annual_commitment=total_annual_commitment,
            total_upfront_payment=total_upfront_payment,
            total_monthly_savings=total_monthly_savings,
            total_annual_savings=total_annual_savings,
            overall_savings_percentage=overall_savings_percentage,
            compute_savings_plans=selected_compute,
            ec2_instance_savings_plans=selected_ec2,
            portfolio_risk_score=portfolio_risk_score,
            diversification_score=diversification_score,
            recommendation_summary=recommendation_summary
        )
    
    def _calculate_portfolio_risk(self, recommendations: List[SavingsPlansRecommendation]) -> float:
        """Calculate overall portfolio risk score"""
        
        if not recommendations:
            return 0.0
        
        # Weight risk by commitment amount
        total_commitment = sum(r.annual_commitment for r in recommendations)
        if total_commitment == 0:
            return 0.0
        
        weighted_risk = sum(
            r.commitment_risk_score * (r.annual_commitment / total_commitment)
            for r in recommendations
        )
        
        return weighted_risk
    
    def _calculate_diversification_score(self, recommendations: List[SavingsPlansRecommendation]) -> float:
        """Calculate portfolio diversification score (0-100, higher = more diversified)"""
        
        if not recommendations:
            return 0.0
        
        # Count different plan types and terms
        plan_types = set(r.plan_type for r in recommendations)
        terms = set(r.commitment_term for r in recommendations)
        families = set(r.instance_family for r in recommendations if r.instance_family)
        
        # Base score from variety
        diversification = len(plan_types) * 20 + len(terms) * 15 + len(families) * 10
        
        return min(diversification, 100.0)
    
    def _generate_portfolio_summary(
        self,
        compute_plans: List[SavingsPlansRecommendation],
        ec2_plans: List[SavingsPlansRecommendation],
        total_savings: float,
        savings_percentage: float
    ) -> str:
        """Generate human-readable portfolio summary"""
        
        summary_parts = []
        
        if compute_plans:
            summary_parts.append(f"{len(compute_plans)} Compute Savings Plan(s)")
        
        if ec2_plans:
            families = [p.instance_family for p in ec2_plans if p.instance_family]
            summary_parts.append(f"{len(ec2_plans)} EC2 Instance Savings Plan(s) covering {', '.join(families)} families")
        
        if not summary_parts:
            return "No Savings Plans recommendations generated"
        
        summary = f"Recommended portfolio: {' and '.join(summary_parts)}. "
        summary += f"Estimated annual savings: ${total_savings:,.2f} ({savings_percentage:.1f}% of current spend)."
        
        return summary

# Global Savings Plans service instance
savings_plans_service = SavingsPlansService()
