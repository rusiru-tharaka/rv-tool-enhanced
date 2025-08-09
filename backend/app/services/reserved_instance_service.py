"""
Reserved Instance Service
Phase 2.2: Reserved Instance Optimization
Comprehensive RI analysis, recommendations, and optimization service
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
import math
from dataclasses import asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .aws_pricing_service import pricing_service, InstancePricing
from .instance_recommendation_service import (
    recommendation_service, 
    VMSpecification, 
    InstanceRecommendation, 
    WorkloadType
)
from ..models.core_models import TCOParameters
from ..models.reserved_instance_models import (
    RITerm, RIPaymentOption, RIOfferingClass, RIScope,
    RIPricingDetails, RIRecommendation, RIPortfolio,
    RIUtilizationMetrics, RIUtilizationReport,
    RIModificationOption, RIOptimizationStrategy
)

class ReservedInstanceService:
    """
    Comprehensive Reserved Instance analysis and optimization service
    Provides intelligent RI recommendations, utilization analysis, and portfolio optimization
    """
    
    def __init__(self):
        self.pricing_service = pricing_service
        self.recommendation_service = recommendation_service
        
        # RI configuration
        self.supported_terms = [RITerm.ONE_YEAR, RITerm.THREE_YEAR]
        self.supported_payment_options = [
            RIPaymentOption.NO_UPFRONT, 
            RIPaymentOption.PARTIAL_UPFRONT, 
            RIPaymentOption.ALL_UPFRONT
        ]
        self.supported_offering_classes = [RIOfferingClass.STANDARD, RIOfferingClass.CONVERTIBLE]
        
        logger.info("Reserved Instance Service initialized")
    
    async def analyze_ri_opportunities(
        self,
        session_id: str,
        vm_inventory: List[Dict],
        tco_parameters: TCOParameters,
        current_monthly_spend: float
    ) -> RIPortfolio:
        """
        Analyze comprehensive Reserved Instance opportunities for VM inventory
        """
        logger.info(f"Analyzing RI opportunities for session {session_id} with {len(vm_inventory)} VMs")
        
        try:
            # Analyze workload patterns for RI suitability
            workload_analysis = await self._analyze_workload_patterns_for_ri(vm_inventory)
            
            # Get current pricing baseline
            current_pricing = await self._get_current_pricing_baseline(vm_inventory, tco_parameters.target_region)
            
            # Generate RI recommendations for different terms and payment options
            one_year_recommendations = await self._generate_ri_recommendations(
                workload_analysis, current_pricing, tco_parameters, RITerm.ONE_YEAR
            )
            
            three_year_recommendations = await self._generate_ri_recommendations(
                workload_analysis, current_pricing, tco_parameters, RITerm.THREE_YEAR
            )
            
            # Optimize RI portfolio mix
            optimized_portfolio = await self._optimize_ri_portfolio(
                one_year_recommendations, three_year_recommendations, current_monthly_spend, tco_parameters
            )
            
            logger.info(f"Generated RI portfolio with {len(optimized_portfolio.one_year_recommendations)} "
                       f"1-year and {len(optimized_portfolio.three_year_recommendations)} 3-year recommendations")
            
            return optimized_portfolio
            
        except Exception as e:
            logger.error(f"Failed to analyze RI opportunities: {e}")
            raise RuntimeError(f"RI analysis failed: {e}")
    
    async def _analyze_workload_patterns_for_ri(self, vm_inventory: List[Dict]) -> Dict[str, Any]:
        """Analyze workload patterns to determine RI suitability"""
        
        analysis = {
            "total_vms": len(vm_inventory),
            "workload_stability": {},
            "instance_families": {},
            "ri_suitability_score": 0.0,
            "stable_workloads": 0,
            "production_workloads": 0
        }
        
        stable_workloads = 0
        production_workloads = 0
        
        for vm in vm_inventory:
            # Determine workload type and stability
            workload_type = self._determine_workload_type(vm)
            power_state = vm.get('Powerstate', 'poweredOn')
            
            # Count stable workloads (production + powered on)
            if workload_type == "production" and power_state == 'poweredOn':
                stable_workloads += 1
                production_workloads += 1
            elif power_state == 'poweredOn':
                stable_workloads += 1
            
            # Track workload distribution
            analysis["workload_stability"][workload_type] = \
                analysis["workload_stability"].get(workload_type, 0) + 1
            
            # Track instance family distribution
            cpu_cores = int(vm.get('CPUs', 1))
            memory_gb = float(vm.get('Memory', 1024)) / 1024
            instance_family = self._determine_instance_family(cpu_cores, memory_gb)
            analysis["instance_families"][instance_family] = \
                analysis["instance_families"].get(instance_family, 0) + 1
        
        analysis["stable_workloads"] = stable_workloads
        analysis["production_workloads"] = production_workloads
        
        # Calculate RI suitability score (0-100)
        stability_ratio = stable_workloads / len(vm_inventory) if vm_inventory else 0
        production_ratio = production_workloads / len(vm_inventory) if vm_inventory else 0
        
        # Higher score for more stable and production workloads
        analysis["ri_suitability_score"] = (stability_ratio * 60) + (production_ratio * 40)
        
        return analysis
    
    def _determine_workload_type(self, vm: Dict) -> str:
        """Determine workload type from VM characteristics"""
        vm_name = vm.get('VM', '').lower()
        
        if any(keyword in vm_name for keyword in ['prod', 'production', 'prd']):
            return "production"
        elif any(keyword in vm_name for keyword in ['dev', 'development', 'devel']):
            return "development"
        elif any(keyword in vm_name for keyword in ['test', 'testing', 'tst', 'qa']):
            return "testing"
        elif any(keyword in vm_name for keyword in ['stage', 'staging', 'stg']):
            return "staging"
        else:
            return "production"  # Default to production for conservative RI recommendations
    
    def _determine_instance_family(self, cpu_cores: int, memory_gb: float) -> str:
        """Determine likely AWS instance family based on VM characteristics"""
        memory_per_cpu = memory_gb / cpu_cores if cpu_cores > 0 else 0
        
        if memory_per_cpu > 6:
            return "r5"  # Memory optimized
        elif memory_per_cpu < 2:
            return "c5"  # Compute optimized
        elif cpu_cores <= 2 and memory_gb <= 8:
            return "t3"  # Burstable
        else:
            return "m5"  # General purpose
    
    async def _get_current_pricing_baseline(self, vm_inventory: List[Dict], region: str) -> Dict[str, Any]:
        """Get current on-demand pricing baseline for RI comparison"""
        
        baseline = {
            "total_monthly_cost": 0.0,
            "instance_costs": {},
            "family_costs": {},
            "instance_usage": {}  # Track usage patterns for RI sizing
        }
        
        for vm in vm_inventory:
            cpu_cores = int(vm.get('CPUs', 1))
            memory_gb = float(vm.get('Memory', 1024)) / 1024
            
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
                
                # Track instance usage for RI recommendations
                if estimated_instance_type not in baseline["instance_usage"]:
                    baseline["instance_usage"][estimated_instance_type] = {
                        "count": 0,
                        "monthly_cost": 0.0,
                        "workload_types": []
                    }
                
                baseline["instance_usage"][estimated_instance_type]["count"] += 1
                baseline["instance_usage"][estimated_instance_type]["monthly_cost"] += monthly_cost
                baseline["instance_usage"][estimated_instance_type]["workload_types"].append(
                    self._determine_workload_type(vm)
                )
                
            except Exception as e:
                logger.warning(f"Could not get pricing for {estimated_instance_type}: {e}")
        
        return baseline
    
    def _estimate_instance_type(self, cpu_cores: int, memory_gb: float, instance_family: str) -> str:
        """Estimate specific instance type based on CPU and memory requirements"""
        
        instance_mappings = {
            "t3": {1: "t3.micro", 2: "t3.small", 4: "t3.medium", 8: "t3.large"},
            "m5": {2: "m5.large", 4: "m5.xlarge", 8: "m5.2xlarge", 16: "m5.4xlarge"},
            "c5": {2: "c5.large", 4: "c5.xlarge", 8: "c5.2xlarge", 16: "c5.4xlarge"},
            "r5": {2: "r5.large", 4: "r5.xlarge", 8: "r5.2xlarge", 16: "r5.4xlarge"}
        }
        
        family_mapping = instance_mappings.get(instance_family, instance_mappings["m5"])
        closest_cpu = min(family_mapping.keys(), key=lambda x: abs(x - cpu_cores))
        return family_mapping[closest_cpu]
    
    async def _generate_ri_recommendations(
        self,
        workload_analysis: Dict[str, Any],
        current_pricing: Dict[str, Any],
        tco_parameters: TCOParameters,
        term: RITerm
    ) -> List[RIRecommendation]:
        """Generate RI recommendations for a specific term"""
        
        recommendations = []
        
        # Only recommend RIs if workload is stable enough
        min_stability_score = 60 if term == RITerm.ONE_YEAR else 75
        if workload_analysis["ri_suitability_score"] < min_stability_score:
            logger.info(f"Workload stability too low for {term.value} RI recommendations")
            return recommendations
        
        # Generate recommendations for each instance type with sufficient usage
        for instance_type, usage_data in current_pricing["instance_usage"].items():
            if usage_data["count"] < 1:  # Skip if less than 1 instance
                continue
            
            # Determine if workload is suitable for RI
            production_count = sum(1 for wt in usage_data["workload_types"] if wt == "production")
            stability_ratio = production_count / usage_data["count"]
            
            # Skip if not stable enough for the term
            required_stability = 0.5 if term == RITerm.ONE_YEAR else 0.8
            if stability_ratio < required_stability:
                continue
            
            # Generate recommendations for different payment options
            for payment_option in self.supported_payment_options:
                try:
                    ri_recommendation = await self._create_ri_recommendation(
                        instance_type, usage_data, term, payment_option, 
                        tco_parameters.target_region, stability_ratio
                    )
                    
                    if ri_recommendation and ri_recommendation.estimated_annual_savings > 100:
                        recommendations.append(ri_recommendation)
                        
                except Exception as e:
                    logger.warning(f"Failed to create RI recommendation for {instance_type}: {e}")
        
        # Sort by annual savings (descending)
        recommendations.sort(key=lambda x: x.estimated_annual_savings, reverse=True)
        
        return recommendations
    
    async def _create_ri_recommendation(
        self,
        instance_type: str,
        usage_data: Dict[str, Any],
        term: RITerm,
        payment_option: RIPaymentOption,
        region: str,
        stability_ratio: float
    ) -> Optional[RIRecommendation]:
        """Create a specific RI recommendation"""
        
        try:
            # Get current on-demand pricing
            current_pricing = await self.pricing_service.get_instance_pricing(instance_type, region)
            
            # Get RI pricing (simulate for now - in real implementation, use AWS RI pricing API)
            ri_pricing = self._simulate_ri_pricing(current_pricing, term, payment_option)
            
            # Calculate recommended quantity (conservative approach)
            recommended_quantity = max(1, int(usage_data["count"] * 0.8))  # 80% of current usage
            
            # Calculate costs
            total_upfront_cost = ri_pricing["upfront_cost"] * recommended_quantity
            monthly_recurring_cost = ri_pricing["hourly_cost"] * 24 * 30 * recommended_quantity
            annual_cost = total_upfront_cost + (monthly_recurring_cost * 12)
            
            # Calculate savings
            annual_on_demand_cost = current_pricing.on_demand_hourly * 24 * 365 * recommended_quantity
            estimated_annual_savings = annual_on_demand_cost - annual_cost
            savings_percentage = (estimated_annual_savings / annual_on_demand_cost * 100) if annual_on_demand_cost > 0 else 0
            
            # Calculate payback period
            monthly_savings = estimated_annual_savings / 12
            payback_period_months = (total_upfront_cost / monthly_savings) if monthly_savings > 0 else 999
            
            # Determine risk level
            risk_level = self._assess_ri_risk(term, payment_option, stability_ratio)
            
            # Calculate utilization requirement for break-even
            utilization_requirement = self._calculate_break_even_utilization(
                current_pricing.on_demand_hourly, ri_pricing["effective_hourly_cost"]
            )
            
            recommendation = RIRecommendation(
                instance_type=instance_type,
                instance_family=instance_type.split('.')[0],
                region=region,
                recommended_quantity=recommended_quantity,
                term=term,
                payment_option=payment_option,
                offering_class=RIOfferingClass.STANDARD,
                total_upfront_cost=total_upfront_cost,
                monthly_recurring_cost=monthly_recurring_cost,
                annual_cost=annual_cost,
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=estimated_annual_savings,
                savings_percentage=savings_percentage,
                payback_period_months=payback_period_months,
                utilization_requirement=utilization_requirement,
                confidence_score=stability_ratio,
                risk_level=risk_level,
                historical_usage_hours=usage_data["count"] * 24 * 30,  # Approximate
                projected_usage_hours=usage_data["count"] * 24 * 30 * 0.9,  # Slightly conservative
                workload_stability_score=stability_ratio * 100,
                optimization_notes=self._generate_ri_optimization_notes(
                    instance_type, term, payment_option, savings_percentage
                )
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to create RI recommendation: {e}")
            return None
    
    def _simulate_ri_pricing(
        self, 
        current_pricing: InstancePricing, 
        term: RITerm, 
        payment_option: RIPaymentOption
    ) -> Dict[str, float]:
        """Simulate RI pricing (in real implementation, use AWS RI pricing API)"""
        
        # Base savings percentages (approximate AWS RI savings)
        base_savings = {
            RITerm.ONE_YEAR: 0.25,  # 25% savings for 1-year
            RITerm.THREE_YEAR: 0.45  # 45% savings for 3-year
        }
        
        # Payment option adjustments
        payment_adjustments = {
            RIPaymentOption.NO_UPFRONT: 1.0,
            RIPaymentOption.PARTIAL_UPFRONT: 1.05,  # 5% additional savings
            RIPaymentOption.ALL_UPFRONT: 1.10  # 10% additional savings
        }
        
        savings_multiplier = base_savings[term] * payment_adjustments[payment_option]
        effective_hourly_cost = current_pricing.on_demand_hourly * (1 - savings_multiplier)
        
        # Calculate upfront and hourly components based on payment option
        total_term_hours = 8760 if term == RITerm.ONE_YEAR else 26280  # Hours in 1 or 3 years
        total_ri_cost = effective_hourly_cost * total_term_hours
        
        if payment_option == RIPaymentOption.ALL_UPFRONT:
            upfront_cost = total_ri_cost
            hourly_cost = 0.0
        elif payment_option == RIPaymentOption.PARTIAL_UPFRONT:
            upfront_cost = total_ri_cost * 0.5
            hourly_cost = (total_ri_cost * 0.5) / total_term_hours
        else:  # NO_UPFRONT
            upfront_cost = 0.0
            hourly_cost = effective_hourly_cost
        
        return {
            "upfront_cost": upfront_cost,
            "hourly_cost": hourly_cost,
            "effective_hourly_cost": effective_hourly_cost,
            "total_term_cost": total_ri_cost
        }
    
    def _assess_ri_risk(self, term: RITerm, payment_option: RIPaymentOption, stability_ratio: float) -> str:
        """Assess risk level for RI recommendation"""
        
        risk_score = 0
        
        # Term risk
        if term == RITerm.THREE_YEAR:
            risk_score += 30
        else:
            risk_score += 10
        
        # Payment risk
        if payment_option == RIPaymentOption.ALL_UPFRONT:
            risk_score += 25
        elif payment_option == RIPaymentOption.PARTIAL_UPFRONT:
            risk_score += 10
        
        # Stability risk
        if stability_ratio < 0.6:
            risk_score += 30
        elif stability_ratio < 0.8:
            risk_score += 15
        
        if risk_score <= 25:
            return "low"
        elif risk_score <= 50:
            return "medium"
        else:
            return "high"
    
    def _calculate_break_even_utilization(self, on_demand_hourly: float, ri_effective_hourly: float) -> float:
        """Calculate minimum utilization required to break even"""
        if on_demand_hourly <= 0:
            return 100.0
        
        break_even_utilization = (ri_effective_hourly / on_demand_hourly) * 100
        return min(100.0, max(0.0, break_even_utilization))
    
    def _generate_ri_optimization_notes(
        self, 
        instance_type: str, 
        term: RITerm, 
        payment_option: RIPaymentOption, 
        savings_percentage: float
    ) -> List[str]:
        """Generate optimization notes for RI recommendation"""
        
        notes = []
        
        # Savings-based notes
        if savings_percentage > 40:
            notes.append("Excellent savings opportunity - high priority for implementation")
        elif savings_percentage > 25:
            notes.append("Good savings potential - recommended for stable workloads")
        else:
            notes.append("Moderate savings - consider for long-term stable workloads only")
        
        # Term-based notes
        if term == RITerm.THREE_YEAR:
            notes.append("3-year term provides maximum savings but requires long-term commitment")
        else:
            notes.append("1-year term offers flexibility with good savings")
        
        # Payment option notes
        if payment_option == RIPaymentOption.ALL_UPFRONT:
            notes.append("All upfront payment maximizes savings but requires significant cash outlay")
        elif payment_option == RIPaymentOption.NO_UPFRONT:
            notes.append("No upfront payment provides cash flow flexibility")
        
        # Instance-specific notes
        if instance_type.startswith('t3'):
            notes.append("Burstable instances - monitor CPU utilization patterns")
        elif instance_type.startswith('r5'):
            notes.append("Memory-optimized instances - ideal for database workloads")
        elif instance_type.startswith('c5'):
            notes.append("Compute-optimized instances - suitable for CPU-intensive applications")
        
        return notes
    
    async def _optimize_ri_portfolio(
        self,
        one_year_recommendations: List[RIRecommendation],
        three_year_recommendations: List[RIRecommendation],
        current_monthly_spend: float,
        tco_parameters: TCOParameters
    ) -> RIPortfolio:
        """Optimize the overall RI portfolio"""
        
        # Select best recommendations based on savings, risk, and budget constraints
        selected_one_year = self._select_optimal_recommendations(
            one_year_recommendations, current_monthly_spend * 0.3  # 30% of spend for 1-year RIs
        )
        
        selected_three_year = self._select_optimal_recommendations(
            three_year_recommendations, current_monthly_spend * 0.5  # 50% of spend for 3-year RIs
        )
        
        # Calculate portfolio totals
        total_upfront_investment = sum(r.total_upfront_cost for r in selected_one_year + selected_three_year)
        total_annual_savings = sum(r.estimated_annual_savings for r in selected_one_year + selected_three_year)
        portfolio_savings_percentage = (total_annual_savings / (current_monthly_spend * 12) * 100) if current_monthly_spend > 0 else 0
        
        # Calculate payment option totals
        no_upfront_total = sum(r.total_upfront_cost for r in selected_one_year + selected_three_year 
                              if r.payment_option == RIPaymentOption.NO_UPFRONT)
        partial_upfront_total = sum(r.total_upfront_cost for r in selected_one_year + selected_three_year 
                                   if r.payment_option == RIPaymentOption.PARTIAL_UPFRONT)
        all_upfront_total = sum(r.total_upfront_cost for r in selected_one_year + selected_three_year 
                               if r.payment_option == RIPaymentOption.ALL_UPFRONT)
        
        # Calculate risk scores
        portfolio_risk_score = self._calculate_portfolio_risk_score(selected_one_year + selected_three_year)
        diversification_score = self._calculate_diversification_score(selected_one_year + selected_three_year)
        
        # Generate optimization opportunities
        optimization_opportunities = self._identify_optimization_opportunities(
            selected_one_year + selected_three_year, current_monthly_spend
        )
        
        portfolio = RIPortfolio(
            session_id=tco_parameters.session_id if hasattr(tco_parameters, 'session_id') else "default",
            analysis_timestamp=datetime.utcnow(),
            total_recommendations=len(selected_one_year) + len(selected_three_year),
            total_upfront_investment=total_upfront_investment,
            total_annual_savings=total_annual_savings,
            portfolio_savings_percentage=portfolio_savings_percentage,
            one_year_recommendations=selected_one_year,
            three_year_recommendations=selected_three_year,
            no_upfront_total=no_upfront_total,
            partial_upfront_total=partial_upfront_total,
            all_upfront_total=all_upfront_total,
            portfolio_risk_score=portfolio_risk_score,
            diversification_score=diversification_score,
            liquidity_impact=total_upfront_investment,
            optimization_opportunities=optimization_opportunities,
            risk_mitigation_strategies=self._generate_risk_mitigation_strategies(portfolio_risk_score)
        )
        
        return portfolio
    
    def _select_optimal_recommendations(
        self, 
        recommendations: List[RIRecommendation], 
        budget_limit: float
    ) -> List[RIRecommendation]:
        """Select optimal RI recommendations within budget constraints"""
        
        if not recommendations:
            return []
        
        # Sort by savings-to-investment ratio
        recommendations.sort(
            key=lambda x: x.estimated_annual_savings / max(x.total_upfront_cost, 1), 
            reverse=True
        )
        
        selected = []
        total_investment = 0.0
        
        for rec in recommendations:
            if total_investment + rec.total_upfront_cost <= budget_limit:
                selected.append(rec)
                total_investment += rec.total_upfront_cost
            
            # Limit to top 5 recommendations per term
            if len(selected) >= 5:
                break
        
        return selected
    
    def _calculate_portfolio_risk_score(self, recommendations: List[RIRecommendation]) -> float:
        """Calculate overall portfolio risk score"""
        
        if not recommendations:
            return 0.0
        
        # Weight risk by investment amount
        total_investment = sum(r.total_upfront_cost for r in recommendations)
        if total_investment == 0:
            return 0.0
        
        risk_mapping = {"low": 20, "medium": 50, "high": 80}
        
        weighted_risk = sum(
            risk_mapping.get(r.risk_level, 50) * (r.total_upfront_cost / total_investment)
            for r in recommendations
        )
        
        return weighted_risk
    
    def _calculate_diversification_score(self, recommendations: List[RIRecommendation]) -> float:
        """Calculate portfolio diversification score"""
        
        if not recommendations:
            return 0.0
        
        # Count different dimensions
        instance_families = set(r.instance_family for r in recommendations)
        terms = set(r.term for r in recommendations)
        payment_options = set(r.payment_option for r in recommendations)
        
        # Base score from variety
        diversification = len(instance_families) * 25 + len(terms) * 25 + len(payment_options) * 15
        
        # Bonus for balanced distribution
        if len(recommendations) > 1:
            one_year_count = sum(1 for r in recommendations if r.term == RITerm.ONE_YEAR)
            three_year_count = len(recommendations) - one_year_count
            
            if one_year_count > 0 and three_year_count > 0:
                diversification += 35  # Bonus for term diversification
        
        return min(diversification, 100.0)
    
    def _identify_optimization_opportunities(
        self, 
        recommendations: List[RIRecommendation], 
        current_monthly_spend: float
    ) -> List[Dict[str, Any]]:
        """Identify additional optimization opportunities"""
        
        opportunities = []
        
        # Check for underutilized potential
        total_potential_savings = sum(r.estimated_annual_savings for r in recommendations)
        if total_potential_savings < current_monthly_spend * 12 * 0.2:  # Less than 20% savings
            opportunities.append({
                "type": "increase_ri_coverage",
                "description": "Consider additional RI purchases to increase savings",
                "potential_impact": "Medium",
                "effort": "Low"
            })
        
        # Check for payment option optimization
        all_upfront_count = sum(1 for r in recommendations if r.payment_option == RIPaymentOption.ALL_UPFRONT)
        if all_upfront_count == 0:
            opportunities.append({
                "type": "payment_optimization",
                "description": "Consider all-upfront payment for maximum savings on stable workloads",
                "potential_impact": "Low",
                "effort": "Low"
            })
        
        # Check for term optimization
        three_year_count = sum(1 for r in recommendations if r.term == RITerm.THREE_YEAR)
        if three_year_count < len(recommendations) * 0.3:  # Less than 30% are 3-year
            opportunities.append({
                "type": "term_optimization",
                "description": "Evaluate 3-year terms for highly stable production workloads",
                "potential_impact": "High",
                "effort": "Medium"
            })
        
        return opportunities
    
    def _generate_risk_mitigation_strategies(self, portfolio_risk_score: float) -> List[str]:
        """Generate risk mitigation strategies based on portfolio risk"""
        
        strategies = []
        
        if portfolio_risk_score > 70:
            strategies.extend([
                "Start with shorter-term (1-year) RIs to reduce commitment risk",
                "Implement gradual RI adoption with quarterly reviews",
                "Consider convertible RIs for additional flexibility"
            ])
        
        if portfolio_risk_score > 50:
            strategies.extend([
                "Monitor utilization closely in first 3 months",
                "Set up automated alerts for underutilization",
                "Plan for RI modifications if usage patterns change"
            ])
        
        strategies.extend([
            "Diversify across multiple instance families and regions",
            "Maintain 20-30% on-demand capacity for flexibility",
            "Regular quarterly reviews of RI performance and optimization"
        ])
        
        return strategies

# Global Reserved Instance service instance
reserved_instance_service = ReservedInstanceService()
