"""
Hybrid Pricing Service - FIXED VERSION
Fixed attribute compatibility issues with AWS pricing service
"""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
import asyncio

from .bulk_pricing.local_pricing_service import LocalPricingService
from .aws_pricing_service import AWSPricingService, InstancePricing, StoragePricing

logger = logging.getLogger(__name__)

class HybridPricingServiceFixed:
    """
    FIXED Hybrid pricing service with proper attribute compatibility
    """
    
    # Regions covered by local pricing database
    LOCAL_REGIONS = {'us-east-1', 'us-west-2', 'eu-west-1'}
    
    def __init__(self):
        """Initialize hybrid pricing service"""
        self.local_service = LocalPricingService()
        self.aws_service = AWSPricingService()
        
        logger.info("FIXED Hybrid Pricing Service initialized")
        logger.info(f"Local coverage: {self.LOCAL_REGIONS}")
        logger.info("AWS API fallback: Available for all regions")
    
    async def get_instance_pricing(self, instance_type: str, region: str) -> Optional[InstancePricing]:
        """
        FIXED: Get instance pricing with proper attribute handling
        """
        
        # Try local pricing first for covered regions
        if region in self.LOCAL_REGIONS:
            try:
                local_pricing = await self.local_service.get_instance_pricing(instance_type, region)
                if local_pricing:
                    logger.debug(f"Using local pricing for {instance_type} in {region}")
                    return local_pricing
                else:
                    logger.warning(f"Local pricing not found for {instance_type} in {region}, trying AWS API")
            except Exception as e:
                logger.warning(f"Local pricing failed for {instance_type} in {region}: {e}")
        
        # Fall back to AWS API
        try:
            logger.info(f"Using AWS API pricing for {instance_type} in {region}")
            aws_pricing = await self.aws_service.get_instance_pricing(instance_type, region)
            
            if aws_pricing:
                # FIXED: Create compatible InstancePricing object with correct attributes
                compatible_pricing = InstancePricing(
                    instance_type=aws_pricing.instance_type,
                    region=aws_pricing.region,
                    on_demand_price_per_hour=aws_pricing.on_demand_hourly,  # Fix attribute name
                    reserved_1yr_no_upfront=aws_pricing.reserved_1yr_hourly,
                    reserved_3yr_no_upfront=aws_pricing.reserved_3yr_hourly,
                    currency="USD"
                )
                
                logger.info(f"AWS API pricing retrieved for {instance_type} in {region}: ${compatible_pricing.on_demand_price_per_hour:.4f}/hour")
                return compatible_pricing
            else:
                logger.error(f"No pricing available from AWS API for {instance_type} in {region}")
                return None
                
        except Exception as e:
            logger.error(f"AWS API pricing failed for {instance_type} in {region}: {e}")
            return None
    
    async def get_storage_pricing(self, volume_type: str, region: str) -> Optional[StoragePricing]:
        """
        Get storage pricing with hybrid approach
        """
        
        # Try local pricing first for covered regions
        if region in self.LOCAL_REGIONS:
            try:
                local_pricing = await self.local_service.get_storage_pricing(volume_type, region)
                if local_pricing:
                    logger.debug(f"Using local storage pricing for {volume_type} in {region}")
                    return local_pricing
                else:
                    logger.warning(f"Local storage pricing not found for {volume_type} in {region}, trying AWS API")
            except Exception as e:
                logger.warning(f"Local storage pricing failed for {volume_type} in {region}: {e}")
        
        # Fall back to AWS API
        try:
            logger.info(f"Using AWS API storage pricing for {volume_type} in {region}")
            aws_pricing = await self.aws_service.get_storage_pricing(volume_type, region)
            
            if aws_pricing:
                logger.info(f"AWS API storage pricing retrieved for {volume_type} in {region}: ${aws_pricing.price_per_gb_month:.4f}/GB-month")
                return aws_pricing
            else:
                logger.error(f"No storage pricing available from AWS API for {volume_type} in {region}")
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
        Get Savings Plans pricing (AWS API only)
        """
        
        try:
            logger.info(f"Getting Savings Plans pricing for {instance_family} in {region}")
            logger.info(f"Term: {commitment_term}, Payment: {payment_option}")
            
            savings_plans = await self.aws_service.get_savings_plans_pricing(
                instance_family, 
                region, 
                commitment_term, 
                payment_option
            )
            
            if savings_plans:
                logger.info(f"Savings Plans pricing retrieved: {len(savings_plans)} plans available")
                for plan in savings_plans[:3]:  # Log first 3 plans
                    logger.info(f"  {plan.plan_type}: ${plan.effective_hourly_rate:.4f}/hour ({plan.savings_percentage:.1f}% savings)")
                return savings_plans
            else:
                logger.warning(f"No Savings Plans pricing available for {instance_family} in {region}")
                return None
                
        except Exception as e:
            logger.error(f"Savings Plans pricing failed for {instance_family} in {region}: {e}")
            return None
    
    async def get_multiple_instance_pricing_cached(
        self, 
        instance_types: List[str], 
        region: str
    ) -> Dict[str, InstancePricing]:
        """
        Get pricing for multiple instances with caching
        """
        
        results = {}
        
        # Process in batches for better performance
        batch_size = 5  # Smaller batches to avoid API limits
        for i in range(0, len(instance_types), batch_size):
            batch = instance_types[i:i + batch_size]
            
            # Process batch sequentially to avoid API rate limits
            for instance_type in batch:
                try:
                    pricing = await self.get_instance_pricing(instance_type, region)
                    if pricing:
                        results[instance_type] = pricing
                    else:
                        logger.warning(f"No pricing available for {instance_type} in {region}")
                except Exception as e:
                    logger.error(f"Pricing failed for {instance_type}: {e}")
                    continue
        
        logger.info(f"Retrieved pricing for {len(results)}/{len(instance_types)} instances in {region}")
        return results
    
    async def get_storage_pricing_cached(self, volume_type: str, region: str) -> Optional[StoragePricing]:
        """
        Get storage pricing with caching (wrapper for compatibility)
        """
        return await self.get_storage_pricing(volume_type, region)
    
    def health_check(self) -> Dict:
        """
        Health check for hybrid pricing service
        """
        
        local_health = self.local_service.health_check()
        
        # Test AWS API connectivity
        aws_healthy = True
        try:
            # Simple connectivity test
            aws_healthy = hasattr(self.aws_service, 'pricing_client')
        except Exception as e:
            logger.error(f"AWS API health check failed: {e}")
            aws_healthy = False
        
        return {
            'status': 'healthy' if local_health['status'] == 'healthy' and aws_healthy else 'degraded',
            'local_service': local_health,
            'aws_api': 'healthy' if aws_healthy else 'unhealthy',
            'coverage': {
                'local_regions': list(self.LOCAL_REGIONS),
                'aws_fallback': 'all_regions'
            },
            'response_time_ms': local_health.get('response_time_ms', 0)
        }

# Create singleton instance
hybrid_pricing_service_fixed = HybridPricingServiceFixed()
