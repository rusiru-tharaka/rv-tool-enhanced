"""
Enhanced Local Pricing Service
Adds missing methods and API fallback functionality for Enhanced TCO
"""

import logging
import time
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

from .local_pricing_service import LocalPricingService, InstancePricing, StoragePricing
from .database import PricingDatabase

logger = logging.getLogger(__name__)

class EnhancedLocalPricingService(LocalPricingService):
    """Enhanced local pricing service with missing methods and API fallback"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.api_fallback_enabled = True
        self.api_fallback_count = 0
        logger.info("Enhanced Local Pricing Service initialized with API fallback")
    
    async def get_multiple_instance_pricing_cached(
        self, 
        instance_types: List[str], 
        region: str
    ) -> Dict[str, InstancePricing]:
        """
        Get pricing for multiple instance types with caching and API fallback
        This is the missing method that Enhanced TCO needs
        """
        logger.info(f"Getting pricing for {len(instance_types)} instances in {region}")
        
        pricing_data = {}
        missing_instances = []
        
        # Phase 1: Try to get from local database first
        for instance_type in instance_types:
            cache_key = f"ec2_{instance_type}_{region}"
            
            try:
                # Check cache first
                if cache_key in self.cache:
                    cached_data, timestamp = self.cache[cache_key]
                    if time.time() - timestamp < self.cache_ttl:
                        pricing_data[instance_type] = cached_data
                        logger.debug(f"✅ Cache hit for {instance_type}")
                        continue
                
                # Try local database
                pricing = await self.get_instance_pricing(instance_type, region)
                pricing_data[instance_type] = pricing
                
                # Cache the result
                self.cache[cache_key] = (pricing, time.time())
                
                logger.debug(f"✅ Local pricing found for {instance_type}")
                
            except ValueError as e:
                logger.warning(f"❌ Local pricing missing for {instance_type}: {e}")
                missing_instances.append(instance_type)
            except Exception as e:
                logger.error(f"❌ Error getting local pricing for {instance_type}: {e}")
                missing_instances.append(instance_type)
        
        # Phase 2: Fallback to AWS API for missing instances
        if missing_instances and self.api_fallback_enabled:
            logger.info(f"🔄 Falling back to AWS API for {len(missing_instances)} missing instances")
            
            try:
                api_pricing = await self._fetch_from_aws_api(missing_instances, region)
                pricing_data.update(api_pricing)
                self.api_fallback_count += len(api_pricing)
                
                logger.info(f"✅ AWS API fallback successful for {len(api_pricing)} instances")
                
            except Exception as e:
                logger.error(f"❌ AWS API fallback failed: {e}")
                
                # Phase 3: Create minimal fallback pricing for critical instances
                for instance_type in missing_instances:
                    try:
                        fallback_pricing = self._create_fallback_pricing(instance_type, region)
                        pricing_data[instance_type] = fallback_pricing
                        logger.warning(f"⚠️ Using fallback pricing for {instance_type}")
                    except Exception as fallback_error:
                        logger.error(f"❌ Failed to create fallback pricing for {instance_type}: {fallback_error}")
        
        elif missing_instances:
            logger.warning(f"⚠️ API fallback disabled, {len(missing_instances)} instances will be missing")
        
        logger.info(f"✅ Pricing retrieval completed: {len(pricing_data)}/{len(instance_types)} instances")
        
        return pricing_data
    
    async def get_storage_pricing_cached(
        self, 
        volume_type: str, 
        region: str
    ) -> StoragePricing:
        """
        Get storage pricing with caching and API fallback
        Enhanced version of the existing method
        """
        cache_key = f"storage_{volume_type}_{region}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"✅ Storage pricing cache hit for {volume_type} in {region}")
                return cached_data
        
        try:
            # Try local database
            pricing = await self.get_storage_pricing(volume_type, region)
            
            # Cache the result
            self.cache[cache_key] = (pricing, time.time())
            
            logger.debug(f"✅ Local storage pricing found for {volume_type} in {region}")
            return pricing
            
        except ValueError as e:
            logger.warning(f"❌ Local storage pricing missing for {volume_type} in {region}: {e}")
            
            if self.api_fallback_enabled:
                try:
                    # Fallback to AWS API
                    api_pricing = await self._fetch_storage_from_aws_api(volume_type, region)
                    
                    # Cache the result
                    self.cache[cache_key] = (api_pricing, time.time())
                    
                    logger.info(f"✅ AWS API storage pricing retrieved for {volume_type} in {region}")
                    return api_pricing
                    
                except Exception as api_error:
                    logger.error(f"❌ AWS API storage pricing failed: {api_error}")
            
            # Final fallback to default pricing
            default_pricing = self._get_default_storage_pricing(volume_type, region)
            logger.warning(f"⚠️ Using default storage pricing for {volume_type} in {region}")
            return default_pricing
    
    async def _fetch_from_aws_api(
        self, 
        instance_types: List[str], 
        region: str
    ) -> Dict[str, InstancePricing]:
        """Fetch missing pricing from AWS API and optionally cache to database"""
        
        try:
            # Import AWS service (lazy import to avoid circular dependencies)
            from services.aws_pricing_service import AWSPricingService
            aws_service = AWSPricingService()
            
        except ImportError as e:
            logger.error(f"❌ Cannot import AWSPricingService: {e}")
            return {}
        
        api_pricing = {}
        
        for instance_type in instance_types:
            try:
                logger.info(f"🔄 Fetching {instance_type} from AWS API...")
                
                # Get from AWS API with timeout
                pricing = await asyncio.wait_for(
                    aws_service.get_instance_pricing(instance_type, region),
                    timeout=30.0  # 30 second timeout
                )
                
                api_pricing[instance_type] = pricing
                
                # Store in local database for future use
                await self._store_pricing_in_database(pricing, region)
                
                logger.info(f"✅ AWS API pricing retrieved and stored for {instance_type}")
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Timeout fetching {instance_type} from AWS API")
            except Exception as e:
                logger.error(f"❌ Failed to get AWS API pricing for {instance_type}: {e}")
                
                # Create fallback pricing for this instance
                try:
                    fallback_pricing = self._create_fallback_pricing(instance_type, region)
                    api_pricing[instance_type] = fallback_pricing
                    logger.warning(f"⚠️ Using fallback pricing for {instance_type}")
                except Exception as fallback_error:
                    logger.error(f"❌ Failed to create fallback pricing: {fallback_error}")
        
        return api_pricing
    
    async def _fetch_storage_from_aws_api(
        self, 
        volume_type: str, 
        region: str
    ) -> StoragePricing:
        """Fetch storage pricing from AWS API"""
        
        try:
            from services.aws_pricing_service import AWSPricingService
            aws_service = AWSPricingService()
            
            pricing = await asyncio.wait_for(
                aws_service.get_storage_pricing(volume_type, region),
                timeout=15.0
            )
            
            # Store in database
            self.db.store_storage_pricing(
                volume_type=volume_type,
                region=region,
                price_per_gb_month=pricing.price_per_gb_month
            )
            
            return pricing
            
        except Exception as e:
            logger.error(f"Failed to fetch storage pricing from AWS API: {e}")
            raise
    
    async def _store_pricing_in_database(self, pricing: InstancePricing, region: str):
        """Store API-retrieved pricing in local database for future use"""
        
        try:
            # Store on-demand pricing
            if pricing.on_demand_price_per_hour:
                self.db.store_ec2_pricing(
                    instance_type=pricing.instance_type,
                    region=region,
                    pricing_model='OnDemand',
                    price_per_hour=pricing.on_demand_price_per_hour
                )
            
            # Store reserved instance pricing if available
            ri_options = [
                ('1yr', 'No Upfront', pricing.reserved_1yr_no_upfront),
                ('1yr', 'Partial Upfront', pricing.reserved_1yr_partial_upfront),
                ('1yr', 'All Upfront', pricing.reserved_1yr_all_upfront),
                ('3yr', 'No Upfront', pricing.reserved_3yr_no_upfront),
                ('3yr', 'Partial Upfront', pricing.reserved_3yr_partial_upfront),
                ('3yr', 'All Upfront', pricing.reserved_3yr_all_upfront),
            ]
            
            stored_count = 0
            for term, payment, price in ri_options:
                if price is not None and price > 0:
                    self.db.store_ec2_pricing(
                        instance_type=pricing.instance_type,
                        region=region,
                        pricing_model='Reserved',
                        term_length=term,
                        payment_option=payment,
                        price_per_hour=price
                    )
                    stored_count += 1
            
            logger.info(f"💾 Stored {stored_count + 1} pricing records for {pricing.instance_type}")
            
        except Exception as e:
            logger.warning(f"Failed to store pricing in database: {e}")
    
    def _create_fallback_pricing(self, instance_type: str, region: str) -> InstancePricing:
        """Create minimal fallback pricing when all else fails"""
        
        # Basic pricing estimates based on instance family and size
        fallback_rates = {
            # T3 family (burstable)
            't3.micro': 0.0128, 't3.small': 0.0256, 't3.medium': 0.0512,
            't3.large': 0.1024, 't3.xlarge': 0.2048, 't3.2xlarge': 0.4096,
            
            # M5 family (general purpose)
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
            'm5.4xlarge': 0.768, 'm5.8xlarge': 1.536, 'm5.12xlarge': 2.304,
            
            # R5 family (memory optimized)
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
            'r5.4xlarge': 1.008, 'r5.8xlarge': 2.016,
            
            # C5 family (compute optimized)
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
            'c5.4xlarge': 0.68, 'c5.9xlarge': 1.53
        }
        
        # Get base rate or estimate
        base_rate = fallback_rates.get(instance_type, 0.1)  # Default to $0.10/hour
        
        # Apply regional multiplier
        regional_multipliers = {
            'ap-southeast-1': 1.1,  # Singapore ~10% higher
            'eu-west-1': 1.05,      # Ireland ~5% higher
            'us-west-2': 1.02,      # Oregon ~2% higher
            'us-east-1': 1.0        # Virginia baseline
        }
        
        multiplier = regional_multipliers.get(region, 1.0)
        on_demand_rate = base_rate * multiplier
        
        # Estimate Reserved Instance rates (typically 30-40% discount)
        ri_1yr_rate = on_demand_rate * 0.7   # 30% discount
        ri_3yr_rate = on_demand_rate * 0.6   # 40% discount
        
        return InstancePricing(
            instance_type=instance_type,
            region=region,
            on_demand_price_per_hour=on_demand_rate,
            reserved_1yr_no_upfront=ri_1yr_rate,
            reserved_3yr_no_upfront=ri_3yr_rate,
            currency="USD",
            last_updated=datetime.utcnow()
        )
    
    def _get_default_storage_pricing(self, volume_type: str, region: str) -> StoragePricing:
        """Get default storage pricing when all else fails"""
        
        # Default storage rates by region (per GB/month)
        default_rates = {
            'ap-southeast-1': 0.12,  # Singapore
            'us-east-1': 0.10,       # Virginia
            'us-west-2': 0.10,       # Oregon
            'eu-west-1': 0.11        # Ireland
        }
        
        base_rate = default_rates.get(region, 0.10)
        
        # Volume type multipliers
        volume_multipliers = {
            'gp3': 1.0,    # General Purpose SSD (baseline)
            'gp2': 1.0,    # General Purpose SSD (legacy)
            'io1': 6.5,    # Provisioned IOPS SSD
            'io2': 6.5,    # Provisioned IOPS SSD
            'st1': 0.45,   # Throughput Optimized HDD
            'sc1': 0.25    # Cold HDD
        }
        
        multiplier = volume_multipliers.get(volume_type, 1.0)
        final_rate = base_rate * multiplier
        
        return StoragePricing(
            volume_type=volume_type,
            region=region,
            price_per_gb_month=final_rate,
            currency="USD"
        )
    
    def get_fallback_stats(self) -> Dict:
        """Get statistics about API fallback usage"""
        
        return {
            'api_fallback_enabled': self.api_fallback_enabled,
            'api_fallback_count': self.api_fallback_count,
            'cache_size': len(self.cache),
            'cache_ttl': self.cache_ttl
        }
    
    def enable_api_fallback(self, enabled: bool = True):
        """Enable or disable API fallback"""
        self.api_fallback_enabled = enabled
        logger.info(f"API fallback {'enabled' if enabled else 'disabled'}")
    
    def clear_cache(self):
        """Clear the pricing cache"""
        cache_size = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared pricing cache ({cache_size} entries)")

# Factory function to create the enhanced service
def create_enhanced_pricing_service(db_path: str = None) -> EnhancedLocalPricingService:
    """Factory function to create enhanced pricing service"""
    return EnhancedLocalPricingService(db_path)
