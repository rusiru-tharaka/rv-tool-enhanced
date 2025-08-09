"""
Spot Instance Service
Phase 2.3: Spot Instance Pricing
Comprehensive Spot Instance analysis, recommendations, and optimization service
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio
import math
import statistics
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
from ..models.spot_instance_models import (
    SpotInstanceState, SpotFleetState, InterruptionRisk, SpotStrategy,
    SpotPriceHistory, SpotPriceAnalysis, SpotInstanceRecommendation,
    SpotFleetConfiguration, SpotInstanceUtilization, SpotMarketAnalysis,
    SpotOptimizationStrategy, SpotInstanceAlert
)

class SpotInstanceService:
    """
    Comprehensive Spot Instance analysis and optimization service
    Provides intelligent Spot recommendations, price analysis, and fleet optimization
    """
    
    def __init__(self):
        self.pricing_service = pricing_service
        self.recommendation_service = recommendation_service
        
        # Spot configuration
        self.supported_strategies = [
            SpotStrategy.LOWEST_PRICE,
            SpotStrategy.DIVERSIFIED,
            SpotStrategy.CAPACITY_OPTIMIZED,
            SpotStrategy.CAPACITY_OPTIMIZED_PRIORITIZED
        ]
        
        # Risk thresholds
        self.interruption_risk_thresholds = {
            InterruptionRisk.VERY_LOW: 0.05,
            InterruptionRisk.LOW: 0.10,
            InterruptionRisk.MODERATE: 0.15,
            InterruptionRisk.HIGH: 0.20,
            InterruptionRisk.VERY_HIGH: 1.0
        }
        
        logger.info("Spot Instance Service initialized")
    
    async def analyze_spot_opportunities(
        self,
        session_id: str,
        vm_inventory: List[Dict],
        tco_parameters: TCOParameters,
        current_monthly_spend: float
    ) -> SpotOptimizationStrategy:
        """
        Analyze comprehensive Spot Instance opportunities for VM inventory
        """
        logger.info(f"Analyzing Spot opportunities for session {session_id} with {len(vm_inventory)} VMs")
        
        try:
            # Analyze workload patterns for Spot suitability
            workload_analysis = await self._analyze_workload_patterns_for_spot(vm_inventory)
            
            # Get current pricing baseline
            current_pricing = await self._get_current_pricing_baseline(vm_inventory, tco_parameters.target_region)
            
            # Analyze spot market conditions
            market_analysis = await self._analyze_spot_market(tco_parameters.target_region)
            
            # Generate Spot recommendations
            spot_recommendations = await self._generate_spot_recommendations(
                workload_analysis, current_pricing, market_analysis, tco_parameters
            )
            
            # Generate Spot Fleet configurations
            fleet_configurations = await self._generate_spot_fleet_configurations(
                spot_recommendations, workload_analysis, tco_parameters
            )
            
            # Create optimization strategy
            optimization_strategy = await self._create_optimization_strategy(
                spot_recommendations, fleet_configurations, current_monthly_spend, workload_analysis
            )
            
            logger.info(f"Generated Spot optimization strategy with {len(spot_recommendations)} "
                       f"recommendations and {len(fleet_configurations)} fleet configurations")
            
            return optimization_strategy
            
        except Exception as e:
            logger.error(f"Failed to analyze Spot opportunities: {e}")
            raise RuntimeError(f"Spot analysis failed: {e}")
    
    async def _analyze_workload_patterns_for_spot(self, vm_inventory: List[Dict]) -> Dict[str, Any]:
        """Analyze workload patterns to determine Spot suitability"""
        
        analysis = {
            "total_vms": len(vm_inventory),
            "fault_tolerant_workloads": 0,
            "batch_processing_workloads": 0,
            "development_workloads": 0,
            "spot_suitable_workloads": 0,
            "workload_distribution": {},
            "spot_suitability_score": 0.0
        }
        
        fault_tolerant = 0
        batch_processing = 0
        development = 0
        
        for vm in vm_inventory:
            workload_type = self._determine_workload_type(vm)
            vm_name = vm.get('VM', '').lower()
            
            # Count workload types
            analysis["workload_distribution"][workload_type] = \
                analysis["workload_distribution"].get(workload_type, 0) + 1
            
            # Determine Spot suitability
            is_spot_suitable = False
            
            # Development and testing workloads are generally Spot-suitable
            if workload_type in ["development", "testing"]:
                development += 1
                is_spot_suitable = True
            
            # Batch processing workloads (identified by naming patterns)
            elif any(keyword in vm_name for keyword in ['batch', 'job', 'worker', 'queue', 'process']):
                batch_processing += 1
                is_spot_suitable = True
            
            # Fault-tolerant applications (identified by patterns)
            elif any(keyword in vm_name for keyword in ['web', 'app', 'api', 'service', 'worker']):
                fault_tolerant += 1
                is_spot_suitable = True
            
            if is_spot_suitable:
                analysis["spot_suitable_workloads"] += 1
        
        analysis["fault_tolerant_workloads"] = fault_tolerant
        analysis["batch_processing_workloads"] = batch_processing
        analysis["development_workloads"] = development
        
        # Calculate Spot suitability score (0-100)
        if len(vm_inventory) > 0:
            suitability_ratio = analysis["spot_suitable_workloads"] / len(vm_inventory)
            analysis["spot_suitability_score"] = suitability_ratio * 100
        
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
            return "production"  # Default to production for conservative analysis
    
    async def _get_current_pricing_baseline(self, vm_inventory: List[Dict], region: str) -> Dict[str, Any]:
        """Get current on-demand pricing baseline for Spot comparison"""
        
        baseline = {
            "total_monthly_cost": 0.0,
            "instance_costs": {},
            "family_costs": {},
            "instance_usage": {}
        }
        
        for vm in vm_inventory:
            cpu_cores = int(vm.get('CPUs', 1))
            memory_gb = float(vm.get('Memory', 1024)) / 1024
            
            instance_family = self._determine_instance_family(cpu_cores, memory_gb)
            estimated_instance_type = self._estimate_instance_type(cpu_cores, memory_gb, instance_family)
            
            try:
                pricing = await self.pricing_service.get_instance_pricing(estimated_instance_type, region)
                monthly_cost = pricing.on_demand_hourly * 24 * 30
                
                baseline["total_monthly_cost"] += monthly_cost
                baseline["instance_costs"][estimated_instance_type] = \
                    baseline["instance_costs"].get(estimated_instance_type, 0) + monthly_cost
                baseline["family_costs"][instance_family] = \
                    baseline["family_costs"].get(instance_family, 0) + monthly_cost
                
                # Track instance usage for Spot recommendations
                if estimated_instance_type not in baseline["instance_usage"]:
                    baseline["instance_usage"][estimated_instance_type] = {
                        "count": 0,
                        "monthly_cost": 0.0,
                        "workload_types": [],
                        "spot_suitability": []
                    }
                
                baseline["instance_usage"][estimated_instance_type]["count"] += 1
                baseline["instance_usage"][estimated_instance_type]["monthly_cost"] += monthly_cost
                baseline["instance_usage"][estimated_instance_type]["workload_types"].append(
                    self._determine_workload_type(vm)
                )
                baseline["instance_usage"][estimated_instance_type]["spot_suitability"].append(
                    self._assess_vm_spot_suitability(vm)
                )
                
            except Exception as e:
                logger.warning(f"Could not get pricing for {estimated_instance_type}: {e}")
        
        return baseline
    
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
    
    def _assess_vm_spot_suitability(self, vm: Dict) -> float:
        """Assess individual VM's suitability for Spot instances (0-100)"""
        
        score = 0.0
        vm_name = vm.get('VM', '').lower()
        workload_type = self._determine_workload_type(vm)
        
        # Workload type scoring
        if workload_type == "development":
            score += 40
        elif workload_type == "testing":
            score += 35
        elif workload_type == "staging":
            score += 25
        else:  # production
            score += 10
        
        # Application type scoring (based on naming patterns)
        if any(keyword in vm_name for keyword in ['batch', 'job', 'worker', 'queue']):
            score += 30  # Batch processing
        elif any(keyword in vm_name for keyword in ['web', 'app', 'api']):
            score += 20  # Web applications (if fault-tolerant)
        elif any(keyword in vm_name for keyword in ['db', 'database', 'sql']):
            score -= 20  # Databases are less suitable
        
        # Size-based scoring (smaller instances are more suitable)
        cpu_cores = int(vm.get('CPUs', 1))
        if cpu_cores <= 2:
            score += 15
        elif cpu_cores <= 4:
            score += 10
        elif cpu_cores <= 8:
            score += 5
        
        return min(100.0, max(0.0, score))
    
    async def _analyze_spot_market(self, region: str) -> SpotMarketAnalysis:
        """Analyze current Spot market conditions"""
        
        # Mock market analysis (in real implementation, use AWS EC2 Spot Price History API)
        market_analysis = SpotMarketAnalysis(
            region=region,
            analysis_timestamp=datetime.utcnow(),
            total_instance_types_analyzed=50,
            average_savings_percentage=65.0,
            market_volatility_score=35.0
        )
        
        # Mock family analysis
        market_analysis.family_analysis = {
            "m5": {"avg_savings": 68.0, "volatility": 25.0, "availability": 85.0},
            "c5": {"avg_savings": 72.0, "volatility": 30.0, "availability": 80.0},
            "r5": {"avg_savings": 65.0, "volatility": 35.0, "availability": 75.0},
            "t3": {"avg_savings": 60.0, "volatility": 40.0, "availability": 90.0}
        }
        
        # Mock AZ analysis
        azs = [f"{region}a", f"{region}b", f"{region}c"]
        market_analysis.az_analysis = {
            az: {"capacity_score": 80.0 + (i * 5), "price_competitiveness": 75.0 + (i * 3)}
            for i, az in enumerate(azs)
        }
        
        # Mock best opportunities
        market_analysis.best_opportunities = [
            {
                "instance_type": "m5.large",
                "savings": 70.0,
                "risk": "low",
                "recommendation": "Excellent for fault-tolerant workloads"
            },
            {
                "instance_type": "c5.xlarge",
                "savings": 75.0,
                "risk": "moderate",
                "recommendation": "Good for compute-intensive batch jobs"
            }
        ]
        
        market_analysis.market_timing_advice = "Favorable conditions for Spot adoption"
        market_analysis.risk_factors = [
            "Moderate volatility in c5 family",
            "Capacity constraints possible during peak hours"
        ]
        
        return market_analysis
    
    async def _generate_spot_recommendations(
        self,
        workload_analysis: Dict[str, Any],
        current_pricing: Dict[str, Any],
        market_analysis: SpotMarketAnalysis,
        tco_parameters: TCOParameters
    ) -> List[SpotInstanceRecommendation]:
        """Generate Spot Instance recommendations"""
        
        recommendations = []
        
        # Only recommend Spot if workloads are suitable
        if workload_analysis["spot_suitability_score"] < 30:
            logger.info("Workload suitability too low for Spot recommendations")
            return recommendations
        
        # Generate recommendations for each suitable instance type
        for instance_type, usage_data in current_pricing["instance_usage"].items():
            if usage_data["count"] < 1:
                continue
            
            # Calculate average Spot suitability
            avg_suitability = sum(usage_data["spot_suitability"]) / len(usage_data["spot_suitability"])
            
            if avg_suitability < 40:  # Skip if not suitable enough
                continue
            
            try:
                recommendation = await self._create_spot_recommendation(
                    instance_type, usage_data, market_analysis, tco_parameters.target_region, avg_suitability
                )
                
                if recommendation and recommendation.savings_percentage > 30:  # Minimum 30% savings
                    recommendations.append(recommendation)
                    
            except Exception as e:
                logger.warning(f"Failed to create Spot recommendation for {instance_type}: {e}")
        
        # Sort by savings percentage (descending)
        recommendations.sort(key=lambda x: x.savings_percentage, reverse=True)
        
        return recommendations[:10]  # Return top 10 recommendations
    
    async def _create_spot_recommendation(
        self,
        instance_type: str,
        usage_data: Dict[str, Any],
        market_analysis: SpotMarketAnalysis,
        region: str,
        suitability_score: float
    ) -> Optional[SpotInstanceRecommendation]:
        """Create a specific Spot recommendation"""
        
        try:
            # Get current on-demand pricing
            current_pricing = await self.pricing_service.get_instance_pricing(instance_type, region)
            
            # Simulate spot pricing (in real implementation, use AWS Spot Price API)
            spot_analysis = self._simulate_spot_pricing(current_pricing, instance_type, market_analysis)
            
            # Calculate savings
            potential_savings = current_pricing.on_demand_hourly - spot_analysis["current_spot_price"]
            savings_percentage = (potential_savings / current_pricing.on_demand_hourly * 100) if current_pricing.on_demand_hourly > 0 else 0
            
            # Assess interruption risk
            interruption_risk = self._assess_interruption_risk(instance_type, spot_analysis["volatility"])
            
            # Calculate expected runtime
            expected_runtime = self._calculate_expected_runtime(interruption_risk, spot_analysis["interruption_frequency"])
            
            # Determine workload suitability
            workload_suitability = self._calculate_workload_suitability(usage_data["workload_types"], suitability_score)
            
            # Generate availability zones ranking
            az_ranking = self._rank_availability_zones(region, market_analysis)
            
            recommendation = SpotInstanceRecommendation(
                instance_type=instance_type,
                instance_family=instance_type.split('.')[0],
                region=region,
                availability_zones=[az for az, _ in az_ranking],
                current_spot_price=spot_analysis["current_spot_price"],
                recommended_bid_price=spot_analysis["recommended_bid_price"],
                on_demand_price=current_pricing.on_demand_hourly,
                potential_savings=potential_savings,
                savings_percentage=savings_percentage,
                interruption_risk=interruption_risk,
                expected_runtime_hours=expected_runtime,
                interruption_frequency=spot_analysis["interruption_frequency"],
                capacity_score=spot_analysis["capacity_score"],
                availability_zones_ranked=az_ranking,
                recommended_strategy=self._recommend_spot_strategy(instance_type, interruption_risk),
                workload_suitability=workload_suitability,
                fault_tolerance_required=True,
                estimated_monthly_cost=spot_analysis["current_spot_price"] * 24 * 30,
                estimated_monthly_savings=potential_savings * 24 * 30,
                implementation_notes=self._generate_implementation_notes(instance_type, interruption_risk, savings_percentage),
                monitoring_requirements=self._generate_monitoring_requirements(instance_type, interruption_risk),
                fallback_strategies=self._generate_fallback_strategies(instance_type, interruption_risk)
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Failed to create Spot recommendation: {e}")
            return None
    
    def _simulate_spot_pricing(self, current_pricing: InstancePricing, instance_type: str, market_analysis: SpotMarketAnalysis) -> Dict[str, Any]:
        """Simulate spot pricing analysis (in real implementation, use AWS APIs)"""
        
        # Base spot price (typically 60-80% savings from on-demand)
        base_savings = 0.70  # 70% average savings
        current_spot_price = current_pricing.on_demand_hourly * (1 - base_savings)
        
        # Add some volatility based on instance family
        family = instance_type.split('.')[0]
        family_data = market_analysis.family_analysis.get(family, {"volatility": 30.0, "availability": 80.0})
        
        volatility_factor = family_data["volatility"] / 100
        price_variation = current_spot_price * volatility_factor * 0.2  # Up to 20% variation
        
        # Recommended bid price (slightly above current to reduce interruption risk)
        recommended_bid_price = current_spot_price * 1.15  # 15% buffer
        
        return {
            "current_spot_price": current_spot_price,
            "recommended_bid_price": min(recommended_bid_price, current_pricing.on_demand_hourly * 0.9),
            "volatility": volatility_factor,
            "interruption_frequency": volatility_factor * 0.1,  # Higher volatility = more interruptions
            "capacity_score": family_data["availability"]
        }
    
    def _assess_interruption_risk(self, instance_type: str, volatility: float) -> InterruptionRisk:
        """Assess interruption risk based on pricing volatility and instance characteristics"""
        
        # Base risk from volatility
        if volatility < 0.2:
            return InterruptionRisk.VERY_LOW
        elif volatility < 0.3:
            return InterruptionRisk.LOW
        elif volatility < 0.4:
            return InterruptionRisk.MODERATE
        elif volatility < 0.5:
            return InterruptionRisk.HIGH
        else:
            return InterruptionRisk.VERY_HIGH
    
    def _calculate_expected_runtime(self, interruption_risk: InterruptionRisk, interruption_frequency: float) -> float:
        """Calculate expected runtime hours before interruption"""
        
        # Base runtime hours by risk level
        base_runtime = {
            InterruptionRisk.VERY_LOW: 168,    # ~1 week
            InterruptionRisk.LOW: 72,          # ~3 days
            InterruptionRisk.MODERATE: 24,     # ~1 day
            InterruptionRisk.HIGH: 12,         # ~12 hours
            InterruptionRisk.VERY_HIGH: 6      # ~6 hours
        }
        
        return base_runtime.get(interruption_risk, 24)
    
    def _calculate_workload_suitability(self, workload_types: List[str], base_suitability: float) -> Dict[str, float]:
        """Calculate suitability scores for different workload types"""
        
        suitability = {}
        
        for workload_type in set(workload_types):
            if workload_type == "development":
                suitability[workload_type] = min(100.0, base_suitability + 20)
            elif workload_type == "testing":
                suitability[workload_type] = min(100.0, base_suitability + 15)
            elif workload_type == "staging":
                suitability[workload_type] = min(100.0, base_suitability + 10)
            else:  # production
                suitability[workload_type] = max(0.0, base_suitability - 10)
        
        return suitability
    
    def _rank_availability_zones(self, region: str, market_analysis: SpotMarketAnalysis) -> List[Tuple[str, float]]:
        """Rank availability zones by capacity and pricing"""
        
        az_scores = []
        
        for az, data in market_analysis.az_analysis.items():
            # Combined score: capacity (70%) + price competitiveness (30%)
            combined_score = (data["capacity_score"] * 0.7) + (data["price_competitiveness"] * 0.3)
            az_scores.append((az, combined_score))
        
        # Sort by score (descending)
        az_scores.sort(key=lambda x: x[1], reverse=True)
        
        return az_scores
    
    def _recommend_spot_strategy(self, instance_type: str, interruption_risk: InterruptionRisk) -> SpotStrategy:
        """Recommend optimal Spot strategy based on instance and risk characteristics"""
        
        if interruption_risk in [InterruptionRisk.VERY_LOW, InterruptionRisk.LOW]:
            return SpotStrategy.LOWEST_PRICE
        elif interruption_risk == InterruptionRisk.MODERATE:
            return SpotStrategy.CAPACITY_OPTIMIZED
        else:
            return SpotStrategy.DIVERSIFIED
    
    def _generate_implementation_notes(self, instance_type: str, interruption_risk: InterruptionRisk, savings_percentage: float) -> List[str]:
        """Generate implementation notes for Spot recommendation"""
        
        notes = []
        
        # Savings-based notes
        if savings_percentage > 70:
            notes.append("Excellent savings opportunity - high priority for fault-tolerant workloads")
        elif savings_percentage > 50:
            notes.append("Good savings potential - suitable for batch processing and development")
        
        # Risk-based notes
        if interruption_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH]:
            notes.append("High interruption risk - implement robust fault tolerance and checkpointing")
        elif interruption_risk == InterruptionRisk.MODERATE:
            notes.append("Moderate interruption risk - ensure application can handle restarts gracefully")
        
        # Instance-specific notes
        if instance_type.startswith('t3'):
            notes.append("Burstable instances - monitor CPU credit usage patterns")
        elif instance_type.startswith('c5'):
            notes.append("Compute-optimized - ideal for CPU-intensive batch processing")
        elif instance_type.startswith('r5'):
            notes.append("Memory-optimized - suitable for in-memory processing workloads")
        
        return notes
    
    def _generate_monitoring_requirements(self, instance_type: str, interruption_risk: InterruptionRisk) -> List[str]:
        """Generate monitoring requirements for Spot instances"""
        
        requirements = [
            "Monitor spot price trends and set price alerts",
            "Track interruption frequency and patterns",
            "Monitor application restart success rates"
        ]
        
        if interruption_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH]:
            requirements.extend([
                "Implement real-time interruption warnings",
                "Monitor checkpoint/save state frequency",
                "Track work completion rates before interruption"
            ])
        
        return requirements
    
    def _generate_fallback_strategies(self, instance_type: str, interruption_risk: InterruptionRisk) -> List[str]:
        """Generate fallback strategies for Spot instances"""
        
        strategies = [
            "Maintain on-demand instances for critical workloads",
            "Implement automatic failover to on-demand when spot unavailable"
        ]
        
        if interruption_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH]:
            strategies.extend([
                "Use multiple instance types and availability zones",
                "Implement job queuing with automatic retry mechanisms",
                "Consider mixed instance types in Auto Scaling Groups"
            ])
        
        return strategies
    
    async def _generate_spot_fleet_configurations(
        self,
        spot_recommendations: List[SpotInstanceRecommendation],
        workload_analysis: Dict[str, Any],
        tco_parameters: TCOParameters
    ) -> List[SpotFleetConfiguration]:
        """Generate Spot Fleet configurations based on recommendations"""
        
        fleet_configurations = []
        
        if not spot_recommendations:
            return fleet_configurations
        
        # Group recommendations by workload type for fleet configuration
        workload_groups = self._group_recommendations_by_workload(spot_recommendations)
        
        for workload_type, recommendations in workload_groups.items():
            if len(recommendations) < 2:  # Need at least 2 instance types for diversification
                continue
            
            try:
                fleet_config = await self._create_spot_fleet_configuration(
                    workload_type, recommendations, tco_parameters
                )
                
                if fleet_config:
                    fleet_configurations.append(fleet_config)
                    
            except Exception as e:
                logger.warning(f"Failed to create Spot Fleet configuration for {workload_type}: {e}")
        
        return fleet_configurations
    
    def _group_recommendations_by_workload(self, recommendations: List[SpotInstanceRecommendation]) -> Dict[str, List[SpotInstanceRecommendation]]:
        """Group Spot recommendations by primary workload type"""
        
        groups = {}
        
        for rec in recommendations:
            # Find the workload type with highest suitability
            primary_workload = max(rec.workload_suitability.items(), key=lambda x: x[1])[0] if rec.workload_suitability else "general"
            
            if primary_workload not in groups:
                groups[primary_workload] = []
            
            groups[primary_workload].append(rec)
        
        return groups
    
    async def _create_spot_fleet_configuration(
        self,
        workload_type: str,
        recommendations: List[SpotInstanceRecommendation],
        tco_parameters: TCOParameters
    ) -> Optional[SpotFleetConfiguration]:
        """Create a Spot Fleet configuration for a specific workload type"""
        
        try:
            # Calculate target capacity based on workload type
            base_capacity = len(recommendations) * 2  # Base capacity
            
            if workload_type == "production":
                target_capacity = base_capacity
                on_demand_percentage = 20  # 20% on-demand for production
            elif workload_type == "development":
                target_capacity = max(1, base_capacity // 2)
                on_demand_percentage = 0  # No on-demand for development
            else:
                target_capacity = base_capacity
                on_demand_percentage = 10  # 10% on-demand for other workloads
            
            # Create instance specifications
            instance_specs = []
            total_estimated_cost = 0.0
            
            for i, rec in enumerate(recommendations[:5]):  # Limit to top 5 instance types
                # Calculate weight based on savings and capacity score
                weight = int((rec.savings_percentage + rec.capacity_score) / 20)  # Normalize to reasonable weight
                weight = max(1, min(weight, 10))  # Ensure weight is between 1-10
                
                # Select best availability zones
                subnet_ids = [f"subnet-{az.replace(tco_parameters.target_region, '')}" for az, _ in rec.availability_zones_ranked[:2]]
                
                spec = {
                    "instance_type": rec.instance_type,
                    "weight": weight,
                    "subnet_ids": subnet_ids,
                    "spot_price": rec.recommended_bid_price
                }
                
                instance_specs.append(spec)
                total_estimated_cost += rec.estimated_monthly_cost * weight
            
            # Determine allocation strategy
            avg_interruption_risk = sum(1 for rec in recommendations if rec.interruption_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH]) / len(recommendations)
            
            if avg_interruption_risk > 0.5:
                allocation_strategy = SpotStrategy.DIVERSIFIED
            else:
                allocation_strategy = SpotStrategy.CAPACITY_OPTIMIZED
            
            # Calculate diversification score
            instance_families = set(rec.instance_family for rec in recommendations)
            diversification_score = min(100.0, len(instance_families) * 25)  # Up to 4 families = 100%
            
            # Calculate interruption resilience
            avg_expected_runtime = sum(rec.expected_runtime_hours for rec in recommendations) / len(recommendations)
            interruption_resilience = min(100.0, avg_expected_runtime / 24 * 25)  # 24 hours = 25%, up to 100%
            
            fleet_config = SpotFleetConfiguration(
                fleet_name=f"spot-fleet-{workload_type}",
                target_capacity=target_capacity,
                allocation_strategy=allocation_strategy,
                instance_specifications=instance_specs,
                on_demand_percentage=on_demand_percentage,
                estimated_hourly_cost=total_estimated_cost / (24 * 30),  # Convert monthly to hourly
                estimated_monthly_cost=total_estimated_cost,
                potential_monthly_savings=sum(rec.estimated_monthly_savings for rec in recommendations),
                diversification_score=diversification_score,
                interruption_resilience=interruption_resilience
            )
            
            return fleet_config
            
        except Exception as e:
            logger.error(f"Failed to create Spot Fleet configuration: {e}")
            return None
    
    async def _create_optimization_strategy(
        self,
        spot_recommendations: List[SpotInstanceRecommendation],
        fleet_configurations: List[SpotFleetConfiguration],
        current_monthly_spend: float,
        workload_analysis: Dict[str, Any]
    ) -> SpotOptimizationStrategy:
        """Create comprehensive Spot optimization strategy"""
        
        # Calculate total potential savings
        total_potential_savings = sum(rec.estimated_monthly_savings for rec in spot_recommendations)
        annual_savings = total_potential_savings * 12
        
        # Determine overall risk level
        high_risk_count = sum(1 for rec in spot_recommendations if rec.interruption_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH])
        if high_risk_count > len(spot_recommendations) * 0.5:
            overall_risk = InterruptionRisk.HIGH
        elif high_risk_count > len(spot_recommendations) * 0.3:
            overall_risk = InterruptionRisk.MODERATE
        else:
            overall_risk = InterruptionRisk.LOW
        
        # Generate implementation phases
        implementation_phases = self._generate_implementation_phases(
            spot_recommendations, fleet_configurations, workload_analysis
        )
        
        # Generate risk mitigation measures
        risk_mitigation = self._generate_risk_mitigation_measures(overall_risk, workload_analysis)
        
        # Generate fallback strategies
        fallback_strategies = self._generate_strategy_fallback_strategies(overall_risk)
        
        # Calculate hybrid approach percentages
        spot_suitable_ratio = workload_analysis["spot_suitable_workloads"] / workload_analysis["total_vms"]
        
        strategy = SpotOptimizationStrategy(
            strategy_name="Comprehensive Spot Instance Optimization",
            description=f"Optimize {workload_analysis['spot_suitable_workloads']} suitable workloads for Spot instances",
            target_workload_types=list(workload_analysis["workload_distribution"].keys()),
            spot_recommendations=spot_recommendations,
            fleet_configurations=fleet_configurations,
            total_potential_savings=total_potential_savings,
            monthly_cost_reduction=total_potential_savings,
            annual_savings_projection=annual_savings,
            overall_risk_level=overall_risk,
            risk_mitigation_measures=risk_mitigation,
            fallback_strategies=fallback_strategies,
            implementation_phases=implementation_phases,
            timeline_weeks=8,
            success_criteria=self._generate_success_criteria(total_potential_savings, overall_risk),
            monitoring_requirements=self._generate_strategy_monitoring_requirements(),
            optimization_triggers=self._generate_optimization_triggers(),
            hybrid_approach=spot_suitable_ratio < 0.8,  # Use hybrid if less than 80% suitable
            spot_percentage=min(80.0, spot_suitable_ratio * 100),
            on_demand_percentage=max(20.0, (1 - spot_suitable_ratio) * 100)
        )
        
        return strategy
    
    def _generate_implementation_phases(
        self,
        spot_recommendations: List[SpotInstanceRecommendation],
        fleet_configurations: List[SpotFleetConfiguration],
        workload_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate phased implementation plan"""
        
        phases = []
        
        # Phase 1: Development and Testing Workloads
        dev_test_savings = sum(
            rec.estimated_monthly_savings for rec in spot_recommendations
            if any(wt in ["development", "testing"] for wt in rec.workload_suitability.keys())
        )
        
        phases.append({
            "name": "Phase 1: Development & Testing",
            "duration_weeks": 2,
            "actions": [
                "Implement Spot instances for development workloads",
                "Deploy testing environments on Spot",
                "Establish monitoring and alerting",
                "Validate fault tolerance mechanisms"
            ],
            "expected_savings": dev_test_savings,
            "risk_level": "low"
        })
        
        # Phase 2: Batch Processing and Non-Critical Production
        batch_savings = sum(
            rec.estimated_monthly_savings for rec in spot_recommendations
            if rec.interruption_risk in [InterruptionRisk.LOW, InterruptionRisk.MODERATE]
        ) - dev_test_savings
        
        phases.append({
            "name": "Phase 2: Batch Processing & Non-Critical Production",
            "duration_weeks": 3,
            "actions": [
                "Deploy Spot Fleet configurations for batch workloads",
                "Implement job queuing and retry mechanisms",
                "Optimize instance type diversification",
                "Monitor interruption patterns and adjust"
            ],
            "expected_savings": max(0, batch_savings),
            "risk_level": "moderate"
        })
        
        # Phase 3: Advanced Optimization
        remaining_savings = sum(rec.estimated_monthly_savings for rec in spot_recommendations) - dev_test_savings - max(0, batch_savings)
        
        phases.append({
            "name": "Phase 3: Advanced Optimization",
            "duration_weeks": 3,
            "actions": [
                "Implement advanced Spot Fleet strategies",
                "Optimize bid pricing based on historical data",
                "Deploy mixed instance type Auto Scaling Groups",
                "Implement predictive scaling based on spot price trends"
            ],
            "expected_savings": max(0, remaining_savings),
            "risk_level": "moderate"
        })
        
        return phases
    
    def _generate_risk_mitigation_measures(self, overall_risk: InterruptionRisk, workload_analysis: Dict[str, Any]) -> List[str]:
        """Generate risk mitigation measures based on overall risk level"""
        
        measures = [
            "Implement comprehensive application checkpointing",
            "Use multiple availability zones for diversification",
            "Maintain on-demand capacity for critical workloads"
        ]
        
        if overall_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH]:
            measures.extend([
                "Implement aggressive diversification across instance types",
                "Use Spot Fleet with capacity-optimized allocation",
                "Implement real-time workload migration capabilities",
                "Maintain higher on-demand percentage (30-40%)"
            ])
        
        if workload_analysis["spot_suitable_workloads"] < workload_analysis["total_vms"] * 0.5:
            measures.append("Focus on most suitable workloads first, expand gradually")
        
        return measures
    
    def _generate_strategy_fallback_strategies(self, overall_risk: InterruptionRisk) -> List[str]:
        """Generate fallback strategies for the optimization strategy"""
        
        strategies = [
            "Automatic failover to on-demand instances when Spot unavailable",
            "Job queuing system with automatic retry on interruption",
            "Reserved Instance backup for critical production workloads"
        ]
        
        if overall_risk in [InterruptionRisk.HIGH, InterruptionRisk.VERY_HIGH]:
            strategies.extend([
                "Multi-region deployment for critical batch processing",
                "Hybrid pricing model with maximum 50% Spot allocation",
                "Preemptible workload scheduling during low-demand periods"
            ])
        
        return strategies
    
    def _generate_success_criteria(self, total_savings: float, overall_risk: InterruptionRisk) -> List[str]:
        """Generate success criteria for the optimization strategy"""
        
        criteria = [
            f"Achieve minimum ${total_savings * 0.8:,.0f} monthly savings (80% of potential)",
            "Maintain application availability above 95%",
            "Keep interruption-related downtime below 5% of total runtime"
        ]
        
        if overall_risk == InterruptionRisk.LOW:
            criteria.append("Achieve 90%+ of projected savings within 8 weeks")
        else:
            criteria.append("Achieve 70%+ of projected savings within 12 weeks")
        
        return criteria
    
    def _generate_strategy_monitoring_requirements(self) -> List[str]:
        """Generate monitoring requirements for the optimization strategy"""
        
        return [
            "Real-time spot price monitoring and alerting",
            "Interruption frequency and pattern analysis",
            "Application restart success rate tracking",
            "Cost savings realization monitoring",
            "Capacity availability trend analysis",
            "Workload performance impact assessment"
        ]
    
    def _generate_optimization_triggers(self) -> List[str]:
        """Generate triggers for strategy optimization"""
        
        return [
            "Spot price increases above 80% of on-demand for 24+ hours",
            "Interruption frequency exceeds 20% for any instance type",
            "Savings realization drops below 60% of projected",
            "Application performance degrades by more than 10%",
            "New instance types become available with better pricing"
        ]

# Global Spot Instance service instance
spot_instance_service = SpotInstanceService()
