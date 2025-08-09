"""
Cost Estimates Service - Hardcoded Parameters Version (Fixed)
Forces 3-Year RI for Production and On-Demand 50% for Non-Production
Fixed to handle InstanceRecommendation objects correctly
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import asyncio
import math

# Use our enhanced pricing service
from .bulk_pricing.local_pricing_service_enhanced import EnhancedLocalPricingService
from .aws_pricing_service import InstancePricing, StoragePricing
from .instance_recommendation_service import (
    recommendation_service, 
    VMSpecification, 
    InstanceRecommendation, 
    WorkloadType
)
from ..models.core_models import (
    TCOParameters, 
    VMCostEstimate, 
    CostSummary, 
    CostEstimatesAnalysis
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CostEstimatesServiceHardcodedFixed:
    """
    Enhanced Cost Estimates Service with hardcoded parameters (Fixed)
    Forces 3-Year RI for Production and On-Demand 50% for Non-Production
    """
    
    def __init__(self):
        # Use our enhanced pricing service with complete Singapore data
        self.pricing_service = EnhancedLocalPricingService()
        logger.info("CostEstimatesServiceHardcodedFixed initialized with enhanced pricing service")
    
    async def analyze_cost_estimates(
        self, 
        session_id: str, 
        vm_inventory: List[Dict], 
        tco_parameters: TCOParameters
    ) -> CostEstimatesAnalysis:
        """
        Perform cost analysis with HARDCODED parameters for consistent results
        """
        logger.info(f"🔧 HARDCODED FIXED: Starting cost analysis for session {session_id}")
        logger.info(f"📊 Processing {len(vm_inventory)} VMs with hardcoded pricing model")
        
        # 🔧 HARDCODE THE PARAMETERS HERE
        hardcoded_params = TCOParameters(
            target_region=tco_parameters.target_region,  # Keep user's region
            pricing_model="mixed",  # Mixed: Production RI, Non-Production On-Demand
            production_ri_years=3,  # 🔧 HARDCODED: 3-Year RI for Production
            non_production_ri_years=1,  # Not used in mixed mode
            production_utilization_percent=100,  # Full utilization for Production
            non_production_utilization_percent=50,  # 🔧 HARDCODED: 50% for Non-Production
            include_storage=True,
            include_network=True,
            include_observability=True
        )
        
        logger.info(f"🎯 HARDCODED PARAMETERS APPLIED:")
        logger.info(f"   - Pricing Model: {hardcoded_params.pricing_model}")
        logger.info(f"   - Production RI: {hardcoded_params.production_ri_years} years")
        logger.info(f"   - Non-Production Utilization: {hardcoded_params.non_production_utilization_percent}%")
        
        try:
            # Convert VM inventory to specifications
            vm_specs = await self._convert_inventory_to_specs_async(vm_inventory)
            logger.info(f"✅ Converted {len(vm_specs)} VMs to specifications")
            
            # Filter VMs (using hardcoded parameters)
            filtered_specs = self._filter_vms_by_parameters(vm_specs, hardcoded_params)
            logger.info(f"✅ Filtered to {len(filtered_specs)} VMs")
            
            # Generate instance recommendations
            logger.info("🔍 Generating instance recommendations...")
            recommendations = await self._generate_recommendations_batch(filtered_specs)
            logger.info(f"✅ Generated {len(recommendations)} recommendations")
            
            # Get pricing data using our enhanced service
            logger.info("💰 Fetching pricing data from enhanced service...")
            instance_types = list(set(rec.instance_type for rec in recommendations))
            
            try:
                pricing_data = await self.pricing_service.get_multiple_instance_pricing_cached(
                    instance_types, 
                    hardcoded_params.target_region
                )
                logger.info(f"✅ Retrieved pricing for {len(pricing_data)} instance types")
            except Exception as e:
                logger.error(f"❌ Pricing retrieval failed: {e}")
                raise ValueError(f"Failed to get pricing data: {e}")
            
            # Get storage pricing
            try:
                storage_pricing = await self.pricing_service.get_storage_pricing_cached(
                    "gp3", 
                    hardcoded_params.target_region
                )
                logger.info(f"✅ Retrieved storage pricing for {hardcoded_params.target_region}")
            except Exception as e:
                logger.warning(f"⚠️ Storage pricing failed, using fallback: {e}")
                storage_pricing = self._get_fallback_storage_pricing(hardcoded_params.target_region)
            
            # Calculate detailed estimates with hardcoded parameters
            logger.info("🧮 Calculating detailed cost estimates...")
            detailed_estimates = await self._calculate_detailed_estimates_parallel(
                filtered_specs, 
                recommendations, 
                pricing_data, 
                storage_pricing, 
                hardcoded_params  # Use hardcoded parameters
            )
            
            logger.info(f"✅ Generated {len(detailed_estimates)} detailed estimates")
            
            # Calculate summary
            cost_summary = self._calculate_cost_summary(detailed_estimates, hardcoded_params)
            
            # Create analysis result
            analysis = CostEstimatesAnalysis(
                session_id=session_id,
                detailed_estimates=detailed_estimates,
                cost_summary=cost_summary,
                tco_parameters=hardcoded_params,  # Return hardcoded parameters
                total_vms_analyzed=len(detailed_estimates),
                analysis_timestamp=datetime.utcnow()
            )
            
            logger.info(f"🎉 Cost analysis completed successfully")
            logger.info(f"📊 Total Monthly Cost: ${cost_summary.total_monthly_cost:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Cost analysis failed: {e}")
            raise ValueError(f"Cost analysis failed: {e}")
    
    async def _convert_inventory_to_specs_async(self, vm_inventory: List[Dict]) -> List[VMSpecification]:
        """Convert VM inventory to VMSpecification objects"""
        
        vm_specs = []
        
        for vm_data in vm_inventory:
            try:
                # Extract VM data with fallbacks
                vm_name = vm_data.get('vm_name', vm_data.get('VM', 'Unknown'))
                cpu_cores = int(vm_data.get('cpu_count', vm_data.get('CPUs', 1)))
                
                # Handle memory conversion (MB to GB)
                memory_mb = float(vm_data.get('memory_mb', vm_data.get('Memory', 1024)))
                memory_gb = memory_mb / 1024 if memory_mb >= 1024 else memory_mb
                
                # Handle storage
                storage_gb = float(vm_data.get('disk_gb', vm_data.get('storage_gb', 20)))
                
                # Determine workload type based on VM name
                workload_type = WorkloadType.PRODUCTION if 'prod' in vm_name.lower() else WorkloadType.DEVELOPMENT
                
                # Create VM specification
                vm_spec = VMSpecification(
                    vm_name=vm_name,
                    cpu_cores=cpu_cores,
                    memory_gb=memory_gb,
                    storage_gb=storage_gb,
                    workload_type=workload_type,
                    os_type='linux'  # Default to Linux
                )
                
                vm_specs.append(vm_spec)
                logger.debug(f"Converted VM: {vm_name} ({cpu_cores}C/{memory_gb:.1f}GB/{storage_gb:.1f}GB)")
                
            except Exception as e:
                logger.error(f"Failed to convert VM {vm_data}: {e}")
                continue
        
        return vm_specs
    
    def _filter_vms_by_parameters(self, vm_specs: List[VMSpecification], tco_parameters: TCOParameters) -> List[VMSpecification]:
        """Filter VMs based on parameters (currently returns all)"""
        return vm_specs
    
    async def _generate_recommendations_batch(self, vm_specs: List[VMSpecification]) -> List[InstanceRecommendation]:
        """Generate instance recommendations in batches"""
        
        recommendations = []
        batch_size = 50
        
        for i in range(0, len(vm_specs), batch_size):
            batch = vm_specs[i:i + batch_size]
            batch_recommendations = recommendation_service.recommend_multiple_instances(batch)
            recommendations.extend(batch_recommendations)
            
            if i + batch_size < len(vm_specs):
                await asyncio.sleep(0.1)
        
        return recommendations
    
    async def _calculate_detailed_estimates_parallel(
        self,
        vm_specs: List[VMSpecification],
        recommendations: List[InstanceRecommendation],
        pricing_data: Dict[str, InstancePricing],
        storage_pricing: StoragePricing,
        tco_parameters: TCOParameters
    ) -> List[VMCostEstimate]:
        """Calculate detailed cost estimates with hardcoded pricing logic"""
        
        # 🔧 FIXED: Create lookup by index since recommendations don't have vm_name
        estimates = []
        
        for i, vm_spec in enumerate(vm_specs):
            try:
                # Get corresponding recommendation by index
                if i < len(recommendations):
                    recommendation = recommendations[i]
                else:
                    logger.warning(f"No recommendation found for {vm_spec.vm_name}")
                    continue
                
                instance_pricing = pricing_data.get(recommendation.instance_type)
                if not instance_pricing:
                    logger.warning(f"No pricing found for {recommendation.instance_type}")
                    continue
                
                # 🔧 HARDCODED PRICING LOGIC
                pricing_plan, hourly_rate = self._determine_hardcoded_pricing(
                    vm_spec, instance_pricing, tco_parameters
                )
                
                # Calculate costs
                monthly_hours = 730  # Standard month
                
                # Apply utilization for non-production
                if vm_spec.workload_type != WorkloadType.PRODUCTION:
                    utilization = tco_parameters.non_production_utilization_percent / 100
                    effective_hours = monthly_hours * utilization
                else:
                    effective_hours = monthly_hours
                
                instance_cost = hourly_rate * effective_hours
                
                # Calculate storage cost
                storage_cost = vm_spec.storage_gb * storage_pricing.price_per_gb_month
                
                total_monthly_cost = instance_cost + storage_cost
                
                # Create estimate
                estimate = VMCostEstimate(
                    vm_name=vm_spec.vm_name,
                    cpu_cores=vm_spec.cpu_cores,
                    memory_gb=vm_spec.memory_gb,
                    storage_gb=vm_spec.storage_gb,
                    recommended_instance_type=recommendation.instance_type,
                    instance_cost=instance_cost,
                    storage_cost=storage_cost,
                    total_monthly_cost=total_monthly_cost,
                    pricing_plan=pricing_plan,
                    operating_system='Linux',
                    environment='Production' if vm_spec.workload_type == WorkloadType.PRODUCTION else 'Non-Production'
                )
                
                estimates.append(estimate)
                logger.debug(f"Calculated estimate for {vm_spec.vm_name}: ${total_monthly_cost:.2f}/month ({pricing_plan})")
                
            except Exception as e:
                logger.error(f"Failed to calculate estimate for {vm_spec.vm_name}: {e}")
                continue
        
        return estimates
    
    def _determine_hardcoded_pricing(
        self, 
        vm_spec: VMSpecification, 
        instance_pricing: InstancePricing, 
        tco_parameters: TCOParameters
    ) -> Tuple[str, float]:
        """
        🔧 HARDCODED PRICING LOGIC:
        - Production: 3-Year Reserved Instance (No Upfront)
        - Non-Production: On-Demand
        """
        
        if vm_spec.workload_type == WorkloadType.PRODUCTION:
            # 🔧 HARDCODED: Production always uses 3-Year RI No Upfront
            if hasattr(instance_pricing, 'reserved_3yr_no_upfront') and instance_pricing.reserved_3yr_no_upfront:
                logger.debug(f"Using 3yr RI for Production VM: {vm_spec.vm_name}")
                return "Reserved Instance (3 Year No Upfront)", instance_pricing.reserved_3yr_no_upfront
            elif hasattr(instance_pricing, 'reserved_1yr_no_upfront') and instance_pricing.reserved_1yr_no_upfront:
                logger.warning(f"3yr RI not available, using 1yr RI for {vm_spec.vm_name}")
                return "Reserved Instance (1 Year No Upfront)", instance_pricing.reserved_1yr_no_upfront
            else:
                logger.warning(f"No RI pricing available, using On-Demand for {vm_spec.vm_name}")
                return "On-Demand (RI Fallback)", instance_pricing.on_demand_price_per_hour
        else:
            # 🔧 HARDCODED: Non-Production always uses On-Demand
            logger.debug(f"Using On-Demand for Non-Production VM: {vm_spec.vm_name}")
            return "On-Demand", instance_pricing.on_demand_price_per_hour
    
    def _calculate_cost_summary(self, detailed_estimates: List[VMCostEstimate], tco_parameters: TCOParameters) -> CostSummary:
        """Calculate cost summary from detailed estimates"""
        
        if not detailed_estimates:
            return CostSummary(
                total_monthly_cost=0.0,
                total_annual_cost=0.0,
                total_instance_cost=0.0,
                total_storage_cost=0.0,
                average_monthly_cost_per_vm=0.0
            )
        
        total_monthly = sum(est.total_monthly_cost for est in detailed_estimates)
        total_instance = sum(est.instance_cost for est in detailed_estimates)
        total_storage = sum(est.storage_cost for est in detailed_estimates)
        
        return CostSummary(
            total_monthly_cost=total_monthly,
            total_annual_cost=total_monthly * 12,
            total_instance_cost=total_instance,
            total_storage_cost=total_storage,
            average_monthly_cost_per_vm=total_monthly / len(detailed_estimates)
        )
    
    def _get_fallback_storage_pricing(self, region: str) -> StoragePricing:
        """Get fallback storage pricing"""
        
        regional_rates = {
            'ap-southeast-1': 0.12,  # Singapore
            'us-east-1': 0.10,       # Virginia
            'us-west-2': 0.10,       # Oregon
            'eu-west-1': 0.11        # Ireland
        }
        
        rate = regional_rates.get(region, 0.10)
        
        return StoragePricing(
            volume_type='gp3',
            region=region,
            price_per_gb_month=rate,
            currency='USD'
        )

# Create singleton instance
cost_estimates_service_hardcoded_fixed = CostEstimatesServiceHardcodedFixed()
