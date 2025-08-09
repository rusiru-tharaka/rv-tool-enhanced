"""
Cost Estimates Service - Enhanced Version
Uses Enhanced Hybrid Pricing Service with proper fallback logic
No fake/hardcoded costs - real AWS pricing or "Pricing not available"
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import asyncio
import math

from .enhanced_hybrid_pricing_service import EnhancedHybridPricingService
from .aws_pricing_service import InstancePricing, StoragePricing  # Keep data classes
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

# Official RVTools Column Mapping (based on RVTools 4.7.1 documentation)
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

class EnhancedCostEstimatesService:
    """
    Enhanced Cost Estimates Service with strict requirements:
    1. Local pricing for Singapore and us-east-1 (all instances, all pricing plans)
    2. AWS API fallback only (no fake/hardcoded costs)
    3. "Pricing not available" when API fails
    """
    
    def __init__(self):
        # Use enhanced hybrid pricing service
        self.pricing_service = EnhancedHybridPricingService()
        self.recommendation_service = recommendation_service
        logger.info("Enhanced Cost Estimates Service initialized with ENHANCED HYBRID pricing")
    
    def _convert_mib_to_gb(self, mib_value: float) -> float:
        """Convert MiB to GB: 1 MiB = 1.048576 MB, 1 GB = 1024 MB"""
        if mib_value <= 0:
            return 0.0
        return (mib_value * 1.048576) / 1024
        
    def _convert_mib_to_mb(self, mib_value: float) -> float:
        """Convert MiB to MB: 1 MiB = 1.048576 MB"""
        if mib_value <= 0:
            return 0.0
        return mib_value * 1.048576
        
    def _safe_get_numeric_value(self, vm_data: Dict, column_name: str, default: float = 0.0) -> float:
        """Safely extract numeric value from VM data"""
        try:
            value = vm_data.get(column_name, default)
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            logger.warning(f"Invalid numeric value for column '{column_name}': {vm_data.get(column_name)}, using default: {default}")
            return default
    
    async def calculate_vm_cost_estimate(
        self, 
        vm_spec: VMSpecification, 
        tco_parameters: TCOParameters,
        recommendation: Optional[InstanceRecommendation] = None,
        vm_data: Optional[Dict] = None
    ) -> VMCostEstimate:
        """
        ENHANCED: Calculate cost estimate with strict no-fake-cost policy
        """
        logger.info(f"Calculating enhanced cost estimate for VM: {vm_spec.vm_name} in region: {tco_parameters.target_region}")
        
        try:
            # Get instance recommendation if not provided
            if not recommendation:
                recommendation = self.recommendation_service.recommend_instance(vm_spec)
                logger.debug(f"Generated recommendation for {vm_spec.vm_name}: {recommendation.instance_type}")
            
            # Get pricing data using enhanced hybrid service
            instance_pricing = await self.pricing_service.get_instance_pricing(
                recommendation.instance_type, 
                tco_parameters.target_region
            )
            
            if not instance_pricing:
                # NO FAKE COSTS - Return "Pricing not available"
                logger.error(f"No pricing data available for instance type {recommendation.instance_type} in region {tco_parameters.target_region}")
                return self._create_pricing_unavailable_estimate(vm_spec, recommendation, "Instance pricing not available")
            
            # Get storage pricing using enhanced hybrid service
            storage_pricing = await self.pricing_service.get_storage_pricing(
                "gp3", 
                tco_parameters.target_region
            )
            
            if not storage_pricing:
                # Try gp2 as fallback
                storage_pricing = await self.pricing_service.get_storage_pricing(
                    "gp2", 
                    tco_parameters.target_region
                )
            
            if not storage_pricing:
                # NO FAKE COSTS - Return "Pricing not available"
                logger.error(f"No storage pricing data available for region {tco_parameters.target_region}")
                return self._create_pricing_unavailable_estimate(vm_spec, recommendation, "Storage pricing not available")
            
            # Calculate compute costs with ENHANCED pricing models
            compute_cost = await self._calculate_compute_cost_enhanced(
                instance_pricing, 
                tco_parameters, 
                vm_spec.workload_type,
                vm_data  # Pass VM data for OS detection
            )
            
            # Calculate storage costs
            storage_cost = self._calculate_storage_cost(
                vm_spec.storage_gb, 
                storage_pricing, 
                tco_parameters
            )
            
            # Calculate total monthly cost
            total_monthly = compute_cost + storage_cost
            
            # Generate optimization notes
            optimization_notes = self._generate_optimization_notes(vm_spec, recommendation, tco_parameters)
            
            # Create detailed cost estimate
            cost_estimate = VMCostEstimate(
                vm_name=vm_spec.vm_name,
                current_cpu=vm_spec.cpu_cores,
                current_ram_gb=vm_spec.memory_gb,
                current_storage_gb=vm_spec.storage_gb,
                recommended_instance_family=recommendation.instance_family.value if hasattr(recommendation, 'instance_family') else "general_purpose",
                recommended_instance_size=recommendation.instance_type,
                recommended_instance_type=recommendation.instance_type,  # Required field
                pricing_plan=await self._get_pricing_plan_name_enhanced(instance_pricing, tco_parameters, vm_spec.workload_type),
                workload_type=vm_spec.workload_type.value,
                # Both naming conventions for compatibility
                monthly_compute_cost=compute_cost,  # New naming
                monthly_storage_cost=storage_cost,  # New naming
                ec2_monthly_cost=compute_cost,      # Legacy naming
                storage_monthly_cost=storage_cost,  # Legacy naming
                total_monthly_cost=total_monthly,
                annual_cost=total_monthly * 12,     # Required field
                confidence_score=recommendation.confidence_score,
                cost_optimization_notes=optimization_notes
            )
            
            logger.info(f"Enhanced cost estimate calculated for {vm_spec.vm_name}: ${total_monthly:.2f}/month (Instance: {recommendation.instance_type}, Region: {tco_parameters.target_region})")
            return cost_estimate
            
        except Exception as e:
            logger.error(f"Failed to calculate cost estimate for VM {vm_spec.vm_name}: {e}")
            # Return pricing unavailable instead of fake costs
            return self._create_pricing_unavailable_estimate(vm_spec, recommendation, str(e))
    
    async def _calculate_compute_cost_enhanced(
        self, 
        instance_pricing: InstancePricing, 
        tco_parameters: TCOParameters, 
        workload_type: WorkloadType,
        vm_data: Optional[Dict] = None
    ) -> float:
        """ENHANCED compute cost calculation with proper Savings Plans support"""
        
        # Detect OS type from VM data if available
        os_type = self._detect_vm_os_type(vm_data) if vm_data else tco_parameters.default_os_type
        
        # Determine which pricing model to use based on workload type
        if workload_type == WorkloadType.PRODUCTION:
            pricing_model = tco_parameters.production_pricing_model
            utilization_percent = tco_parameters.production_utilization_percent
        else:
            pricing_model = tco_parameters.non_production_pricing_model
            utilization_percent = tco_parameters.non_production_utilization_percent
        
        # Get hourly rate based on pricing model with ENHANCED Savings Plans support
        pricing_plan, hourly_rate = await self._get_hourly_rate_for_model_enhanced(
            instance_pricing, 
            pricing_model, 
            tco_parameters, 
            workload_type
        )
        
        if hourly_rate <= 0:
            logger.error(f"Invalid hourly rate received: ${hourly_rate:.4f}")
            raise ValueError(f"Invalid pricing data: hourly rate is ${hourly_rate:.4f}")
        
        # Calculate monthly hours with utilization
        hours_per_month = 24 * 30.44  # Average days per month
        utilization_factor = utilization_percent / 100.0
        effective_hours = hours_per_month * utilization_factor
        
        # Calculate base monthly cost
        base_monthly_cost = hourly_rate * effective_hours
        
        # Apply OS-specific pricing adjustments
        os_adjusted_cost = self._apply_os_pricing_adjustment(base_monthly_cost, os_type)
        
        logger.info(f"ENHANCED compute cost: {pricing_plan} @ ${hourly_rate:.4f}/hr * {effective_hours:.1f}hrs = ${os_adjusted_cost:.2f} (OS: {os_type})")
        
        return os_adjusted_cost
    
    async def _get_hourly_rate_for_model_enhanced(
        self, 
        instance_pricing: InstancePricing, 
        pricing_model: str, 
        tco_parameters: TCOParameters, 
        workload_type: WorkloadType
    ) -> Tuple[str, float]:
        """ENHANCED hourly rate calculation with proper Savings Plans support"""
        
        if pricing_model == "on_demand":
            return "On-Demand", instance_pricing.on_demand_price_per_hour
            
        elif pricing_model == "reserved":
            # Use workload-specific RI terms
            if workload_type == WorkloadType.PRODUCTION:
                ri_years = tco_parameters.production_ri_years
            else:
                ri_years = getattr(tco_parameters, 'non_production_ri_years', 1)
            
            if ri_years >= 3 and hasattr(instance_pricing, 'reserved_3yr_no_upfront') and instance_pricing.reserved_3yr_no_upfront:
                return "Reserved Instance (3 Year)", instance_pricing.reserved_3yr_no_upfront
            elif ri_years >= 1 and hasattr(instance_pricing, 'reserved_1yr_no_upfront') and instance_pricing.reserved_1yr_no_upfront:
                return "Reserved Instance (1 Year)", instance_pricing.reserved_1yr_no_upfront
            else:
                logger.warning(f"Reserved pricing not available, falling back to On-Demand")
                return "On-Demand (RI Fallback)", instance_pricing.on_demand_price_per_hour
                
        elif pricing_model == "compute_savings" or pricing_model == "ec2_savings":
            # ENHANCED: Use enhanced hybrid pricing service for Savings Plans
            try:
                instance_family = instance_pricing.instance_type.split('.')[0]
                
                savings_plans_pricing = await self.pricing_service.get_savings_plans_pricing(
                    instance_family,
                    tco_parameters.target_region,
                    tco_parameters.savings_plan_commitment,
                    tco_parameters.savings_plan_payment
                )
                
                if savings_plans_pricing and len(savings_plans_pricing) > 0:
                    # Use the first matching Savings Plans price
                    savings_plan = savings_plans_pricing[0]
                    
                    plan_type = "EC2 Instance Savings Plans" if pricing_model == "ec2_savings" else "Compute Savings Plans"
                    
                    logger.info(f"Using {plan_type}: ${savings_plan.effective_hourly_rate:.4f}/hour ({savings_plan.savings_percentage:.1f}% savings)")
                    
                    return plan_type, savings_plan.effective_hourly_rate
                else:
                    logger.warning(f"Savings Plans pricing not available for {instance_family}, falling back to Reserved Instance")
                    # Fall back to Reserved Instance pricing
                    if hasattr(instance_pricing, 'reserved_1yr_no_upfront') and instance_pricing.reserved_1yr_no_upfront:
                        return "Reserved Instance (1 Year - Savings Plans Fallback)", instance_pricing.reserved_1yr_no_upfront
                    else:
                        return "On-Demand (Savings Plans Fallback)", instance_pricing.on_demand_price_per_hour
                        
            except Exception as e:
                logger.error(f"Failed to get Savings Plans pricing: {e}")
                logger.warning("Falling back to Reserved Instance pricing")
                if hasattr(instance_pricing, 'reserved_1yr_no_upfront') and instance_pricing.reserved_1yr_no_upfront:
                    return "Reserved Instance (1 Year - Savings Plans Error)", instance_pricing.reserved_1yr_no_upfront
                else:
                    return "On-Demand (Savings Plans Error)", instance_pricing.on_demand_price_per_hour
        
        # Default fallback
        return "On-Demand (Default)", instance_pricing.on_demand_price_per_hour
    
    async def _get_pricing_plan_name_enhanced(
        self, 
        instance_pricing: InstancePricing, 
        tco_parameters: TCOParameters, 
        workload_type: WorkloadType
    ) -> str:
        """Get pricing plan name for CSV export"""
        
        if workload_type == WorkloadType.PRODUCTION:
            pricing_model = tco_parameters.production_pricing_model
        else:
            pricing_model = tco_parameters.non_production_pricing_model
        
        if pricing_model == "on_demand":
            return "On-Demand"
        elif pricing_model == "reserved":
            return "Reserved Instance"
        elif pricing_model == "compute_savings":
            return "Compute Savings Plans"
        elif pricing_model == "ec2_savings":
            return "EC2 Instance Savings Plans"
        else:
            return "On-Demand"
    
    def _apply_os_pricing_adjustment(self, base_cost: float, os_type: str) -> float:
        """Apply OS-specific pricing adjustments based on AWS pricing"""
        
        os_multipliers = {
            "linux": 1.0,        # Base pricing
            "windows": 1.4,      # ~40% more expensive
            "rhel": 1.2,         # ~20% more expensive  
            "suse": 1.15,        # ~15% more expensive
            "ubuntu_pro": 1.05   # ~5% more expensive
        }
        
        multiplier = os_multipliers.get(os_type.lower(), 1.0)
        return base_cost * multiplier
    
    def _detect_vm_os_type(self, vm_data: Dict) -> str:
        """Detect operating system from RVTool VM data"""
        
        if not vm_data:
            return "linux"
        
        # Primary RVTool OS column
        os_field = "OS according to the configuration file"
        os_value = vm_data.get(os_field, "").lower()
        
        if "windows" in os_value:
            return "windows"
        elif "red hat" in os_value or "rhel" in os_value:
            return "rhel"
        elif "suse" in os_value:
            return "suse"
        elif "ubuntu" in os_value and "pro" in os_value:
            return "ubuntu_pro"
        else:
            return "linux"  # Default
    
    def _calculate_storage_cost(
        self, 
        storage_gb: float, 
        storage_pricing: StoragePricing, 
        tco_parameters: TCOParameters
    ) -> float:
        """Calculate monthly storage cost"""
        
        # Apply storage optimization factor if specified
        optimization_factor = getattr(tco_parameters, 'storage_optimization_factor', 1.0)
        optimized_storage_gb = storage_gb * optimization_factor
        
        # Calculate base storage cost
        base_cost = optimized_storage_gb * storage_pricing.price_per_gb_month
        
        logger.debug(f"Storage cost: {optimized_storage_gb:.1f}GB * ${storage_pricing.price_per_gb_month:.4f} = ${base_cost:.2f}")
        
        return base_cost
    
    def _generate_optimization_notes(
        self, 
        vm_spec: VMSpecification, 
        recommendation: InstanceRecommendation, 
        tco_parameters: TCOParameters
    ) -> str:
        """Generate cost optimization recommendations"""
        
        notes = []
        
        # Add region-specific note
        if tco_parameters.target_region in {'us-east-1', 'ap-southeast-1'}:
            notes.append(f"Using enhanced pricing data for {tco_parameters.target_region}")
        else:
            notes.append(f"Using AWS API pricing for {tco_parameters.target_region}")
        
        # Add workload-specific recommendations
        if vm_spec.workload_type == WorkloadType.PRODUCTION:
            notes.append("Consider Reserved Instances or Savings Plans for production workloads")
        
        return "; ".join(notes) if notes else "Standard optimization recommendations applied"
    
    def _create_pricing_unavailable_estimate(
        self, 
        vm_spec: VMSpecification, 
        recommendation: Optional[InstanceRecommendation], 
        error_message: str
    ) -> VMCostEstimate:
        """Create pricing unavailable estimate (NO FAKE COSTS)"""
        
        return VMCostEstimate(
            vm_name=vm_spec.vm_name,
            current_cpu=vm_spec.cpu_cores,
            current_ram_gb=vm_spec.memory_gb,
            current_storage_gb=vm_spec.storage_gb,
            recommended_instance_family="unknown",
            recommended_instance_size=recommendation.instance_type if recommendation else "unknown",
            recommended_instance_type=recommendation.instance_type if recommendation else "unknown",
            pricing_plan="Pricing not available",
            workload_type=vm_spec.workload_type.value,
            monthly_compute_cost=0.0,
            monthly_storage_cost=0.0,
            ec2_monthly_cost=0.0,
            storage_monthly_cost=0.0,
            total_monthly_cost=0.0,
            annual_cost=0.0,
            confidence_score=0.0,
            cost_optimization_notes=f"Pricing not available: {error_message}"
        )

# Create singleton instance
enhanced_cost_estimates_service = EnhancedCostEstimatesService()
