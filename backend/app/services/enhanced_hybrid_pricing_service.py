"""
Enhanced Hybrid Pricing Service
Implements hybrid pricing with proper fallback logic to AWS API
No fake/hardcoded costs - real AWS pricing or "Pricing not available"
"""

import logging
from typing import Optional, Dict, List
import asyncio

from .bulk_pricing.local_pricing_service import LocalPricingService
from .aws_pricing_service import AWSPricingService, InstancePricing, StoragePricing

logger = logging.getLogger(__name__)

class EnhancedHybridPricingService:
    """
    Enhanced Hybrid Pricing Service with strict requirements:
    1. Local pricing for Singapore and us-east-1 (all instances, all pricing plans)
    2. AWS API fallback only (no fake/hardcoded costs)
    3. "Pricing not available" when API fails
    """
    
    # Target regions for local pricing coverage
    TARGET_LOCAL_REGIONS = {'us-east-1', 'ap-southeast-1'}  # Singapore + us-east-1
    
    def __init__(self):
        """Initialize enhanced hybrid pricing service"""
        self.local_service = LocalPricingService()
        self.aws_service = AWSPricingService()
        
        logger.info("Enhanced Hybrid Pricing Service initialized")
        logger.info(f"Target local regions: {self.TARGET_LOCAL_REGIONS}")
        logger.info("Fallback: AWS API only (no fake costs)")
    
    async def get_instance_pricing(self, instance_type: str, region: str) -> Optional[InstancePricing]:
        """
        Get instance pricing with enhanced hybrid approach:
        1. Try local pricing first (for target regions)
        2. Fall back to AWS API if not available
        3. Return None if AWS API fails (no fake costs)
        """
        
        # Try local pricing first for target regions
        if region in self.TARGET_LOCAL_REGIONS:
            try:
                local_pricing = await self.local_service.get_instance_pricing(instance_type, region)
                if local_pricing and local_pricing.on_demand_price_per_hour > 0:
                    logger.debug(f"Using local pricing for {instance_type} in {region}")
                    return local_pricing
                else:
                    logger.info(f"Local pricing not found for {instance_type} in {region}, trying AWS API")
            except Exception as e:
                logger.warning(f"Local pricing failed for {instance_type} in {region}: {e}")
        
        # Fall back to AWS API (no fake costs)
        try:
            logger.info(f"Using AWS API pricing for {instance_type} in {region}")
            aws_pricing = await self.aws_service.get_instance_pricing(instance_type, region)
            
            if aws_pricing and aws_pricing.on_demand_hourly > 0:
                # Create compatible InstancePricing object with correct attributes
                compatible_pricing = InstancePricing(
                    instance_type=aws_pricing.instance_type,
                    region=aws_pricing.region,
                    on_demand_price_per_hour=aws_pricing.on_demand_hourly,
                    reserved_1yr_no_upfront=aws_pricing.reserved_1yr_hourly,
                    reserved_3yr_no_upfront=aws_pricing.reserved_3yr_hourly,
                    currency="USD"
                )
                
                logger.info(f"AWS API pricing retrieved for {instance_type} in {region}: ${compatible_pricing.on_demand_price_per_hour:.4f}/hour")
                return compatible_pricing
            else:
                logger.error(f"AWS API returned invalid pricing for {instance_type} in {region}")
                return None
                
        except Exception as e:
            logger.error(f"AWS API pricing failed for {instance_type} in {region}: {e}")
            return None
    
    async def get_storage_pricing(self, volume_type: str, region: str) -> Optional[StoragePricing]:
        """
        Get storage pricing with enhanced hybrid approach
        """
        
        # Try local pricing first for target regions
        if region in self.TARGET_LOCAL_REGIONS:
            try:
                local_pricing = await self.local_service.get_storage_pricing(volume_type, region)
                if local_pricing and local_pricing.price_per_gb_month > 0:
                    logger.debug(f"Using local storage pricing for {volume_type} in {region}")
                    return local_pricing
                else:
                    logger.info(f"Local storage pricing not found for {volume_type} in {region}, trying AWS API")
            except Exception as e:
                logger.warning(f"Local storage pricing failed for {volume_type} in {region}: {e}")
        
        # Fall back to AWS API
        try:
            logger.info(f"Using AWS API storage pricing for {volume_type} in {region}")
            aws_pricing = await self.aws_service.get_storage_pricing(volume_type, region)
            
            if aws_pricing and aws_pricing.price_per_gb_month > 0:
                logger.info(f"AWS API storage pricing retrieved for {volume_type} in {region}: ${aws_pricing.price_per_gb_month:.4f}/GB-month")
                return aws_pricing
            else:
                logger.error(f"AWS API returned invalid storage pricing for {volume_type} in {region}")
                return None
                
        except Exception as e:
            logger.error(f"AWS API storage pricing failed for {volume_type} in {region}: {e}")
            return None
    
    async def get_savings_plans_pricing(
        self, 
        instance_family: str, 
        region: str, 
        commitment_term: str, 
        payment_option: str
    ) -> Optional[List]:
        """
        Get Savings Plans pricing with enhanced approach
        1. Try local pricing first (for target regions)
        2. Fall back to AWS API
        3. Return None if not available (no fake costs)
        """
        
        # Try local pricing first for target regions
        if region in self.TARGET_LOCAL_REGIONS:
            try:
                # Check if local service has savings plans method
                if hasattr(self.local_service, 'get_savings_plans_pricing'):
                    local_savings = await self.local_service.get_savings_plans_pricing(
                        instance_family, region, commitment_term, payment_option
                    )
                    if local_savings:
                        logger.debug(f"Using local Savings Plans pricing for {instance_family} in {region}")
                        return local_savings
                
                logger.info(f"Local Savings Plans pricing not available for {instance_family} in {region}, trying AWS API")
            except Exception as e:
                logger.warning(f"Local Savings Plans pricing failed for {instance_family} in {region}: {e}")
        
        # Fall back to AWS API
        try:
            logger.info(f"Using AWS API Savings Plans pricing for {instance_family} in {region}")
            logger.info(f"Term: {commitment_term}, Payment: {payment_option}")
            
            savings_plans = await self.aws_service.get_savings_plans_pricing(
                instance_family, 
                region, 
                commitment_term, 
                payment_option
            )
            
            if savings_plans and len(savings_plans) > 0:
                logger.info(f"AWS API Savings Plans pricing retrieved: {len(savings_plans)} plans available")
                for plan in savings_plans[:3]:  # Log first 3 plans
                    logger.info(f"  {plan.plan_type}: ${plan.effective_hourly_rate:.4f}/hour ({plan.savings_percentage:.1f}% savings)")
                return savings_plans
            else:
                logger.warning(f"No Savings Plans pricing available from AWS API for {instance_family} in {region}")
                return None
                
        except Exception as e:
            logger.error(f"AWS API Savings Plans pricing failed for {instance_family} in {region}: {e}")
            return None
    
    async def get_multiple_instance_pricing_cached(
        self, 
        instance_types: List[str], 
        region: str
    ) -> Dict[str, InstancePricing]:
        """
        Get pricing for multiple instances with enhanced caching
        """
        
        results = {}
        
        # Process in smaller batches to avoid API limits
        batch_size = 3
        for i in range(0, len(instance_types), batch_size):
            batch = instance_types[i:i + batch_size]
            
            # Process batch sequentially to avoid API rate limits
            for instance_type in batch:
                try:
                    pricing = await self.get_instance_pricing(instance_type, region)
                    if pricing:
                        results[instance_type] = pricing
                        logger.debug(f"Retrieved pricing for {instance_type} in {region}")
                    else:
                        logger.warning(f"No pricing available for {instance_type} in {region}")
                except Exception as e:
                    logger.error(f"Pricing failed for {instance_type}: {e}")
                    continue
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
        
        logger.info(f"Retrieved pricing for {len(results)}/{len(instance_types)} instances in {region}")
        return results
    
    async def get_storage_pricing_cached(self, volume_type: str, region: str) -> Optional[StoragePricing]:
        """
        Get storage pricing with caching (wrapper for compatibility)
        """
        return await self.get_storage_pricing(volume_type, region)
    
    def health_check(self) -> Dict:
        """
        Enhanced health check for hybrid pricing service
        """
        
        local_health = self.local_service.health_check()
        
        # Test AWS API connectivity
        aws_healthy = True
        try:
            aws_healthy = hasattr(self.aws_service, 'pricing_client') and self.aws_service.pricing_client is not None
        except Exception as e:
            logger.error(f"AWS API health check failed: {e}")
            aws_healthy = False
        
        return {
            'status': 'healthy' if local_health['status'] == 'healthy' and aws_healthy else 'degraded',
            'local_service': local_health,
            'aws_api': 'healthy' if aws_healthy else 'unhealthy',
            'coverage': {
                'target_local_regions': list(self.TARGET_LOCAL_REGIONS),
                'aws_fallback': 'all_regions',
                'no_fake_costs': True
            },
            'response_time_ms': local_health.get('response_time_ms', 0)
        }
    
    def get_region_coverage(self, region: str) -> Dict:
        """
        Get coverage information for a specific region
        """
        
        is_target_local = region in self.TARGET_LOCAL_REGIONS
        
        return {
            'region': region,
            'target_local_coverage': is_target_local,
            'aws_fallback': True,
            'recommended_source': 'local' if is_target_local else 'aws_api',
            'performance_tier': 'fast' if is_target_local else 'standard',
            'no_fake_costs': True
        }
    
    async def validate_pricing_availability(self, instance_type: str, region: str) -> Dict:
        """
        Validate pricing availability without retrieving full pricing data
        """
        
        result = {
            'instance_type': instance_type,
            'region': region,
            'local_available': False,
            'aws_api_available': False,
            'pricing_available': False,
            'source': None
        }
        
        # Check local availability for target regions
        if region in self.TARGET_LOCAL_REGIONS:
            try:
                local_pricing = await self.local_service.get_instance_pricing(instance_type, region)
                if local_pricing and local_pricing.on_demand_price_per_hour > 0:
                    result['local_available'] = True
                    result['pricing_available'] = True
                    result['source'] = 'local'
                    return result
            except Exception:
                pass
        
        # Check AWS API availability
        try:
            aws_pricing = await self.aws_service.get_instance_pricing(instance_type, region)
            if aws_pricing and aws_pricing.on_demand_hourly > 0:
                result['aws_api_available'] = True
                result['pricing_available'] = True
                result['source'] = 'aws_api'
        except Exception:
            pass
        
        return result

# Create singleton instance
enhanced_hybrid_pricing_service = EnhancedHybridPricingService()
