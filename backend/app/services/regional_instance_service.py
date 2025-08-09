"""
Regional Instance Validation Service
Handles region-specific instance type availability and alternatives
"""

import logging
import asyncio
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta

from services.aws_pricing_service import AWSPricingService

logger = logging.getLogger(__name__)

class RegionalInstanceService:
    """Service for managing region-specific instance type availability and alternatives"""
    
    def __init__(self, pricing_service: AWSPricingService):
        self.pricing_service = pricing_service
        self.availability_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=24)  # Cache for 24 hours
        
        # Pre-defined instance type alternatives mapping
        self.instance_alternatives = {
            # General Purpose alternatives
            'm5.large': ['m5d.large', 'm5dn.large', 'm6i.large', 'm6a.large', 'm5n.large', 'm5a.large'],
            'm5.xlarge': ['m5d.xlarge', 'm5dn.xlarge', 'm6i.xlarge', 'm6a.xlarge', 'm5n.xlarge', 'm5a.xlarge'],
            'm5.2xlarge': ['m5d.2xlarge', 'm5dn.2xlarge', 'm6i.2xlarge', 'm6a.2xlarge', 'm5n.2xlarge', 'm5a.2xlarge'],
            'm5.4xlarge': ['m5d.4xlarge', 'm5dn.4xlarge', 'm6i.4xlarge', 'm6a.4xlarge', 'm5n.4xlarge', 'm5a.4xlarge'],
            'm5.8xlarge': ['m5d.8xlarge', 'm5dn.8xlarge', 'm6i.8xlarge', 'm6a.8xlarge', 'm5n.8xlarge', 'm5a.8xlarge'],
            
            # Compute Optimized alternatives
            'c5.large': ['c5d.large', 'c5n.large', 'c6i.large', 'c6a.large', 'c5a.large'],
            'c5.xlarge': ['c5d.xlarge', 'c5n.xlarge', 'c6i.xlarge', 'c6a.xlarge', 'c5a.xlarge'],
            'c5.2xlarge': ['c5d.2xlarge', 'c5n.2xlarge', 'c6i.2xlarge', 'c6a.2xlarge', 'c5a.2xlarge'],
            'c5.4xlarge': ['c5d.4xlarge', 'c5n.4xlarge', 'c6i.4xlarge', 'c6a.4xlarge', 'c5a.4xlarge'],
            
            # Memory Optimized alternatives
            'r5.large': ['r5d.large', 'r5dn.large', 'r6i.large', 'r6a.large', 'r5n.large', 'r5a.large'],
            'r5.xlarge': ['r5d.xlarge', 'r5dn.xlarge', 'r6i.xlarge', 'r6a.xlarge', 'r5n.xlarge', 'r5a.xlarge'],
            'r5.2xlarge': ['r5d.2xlarge', 'r5dn.2xlarge', 'r6i.2xlarge', 'r6a.2xlarge', 'r5n.2xlarge', 'r5a.2xlarge'],
            'r5.4xlarge': ['r5d.4xlarge', 'r5dn.4xlarge', 'r6i.4xlarge', 'r6a.4xlarge', 'r5n.4xlarge', 'r5a.4xlarge'],
            
            # Burstable alternatives
            't3.micro': ['t3a.micro', 't4g.micro', 't2.micro'],
            't3.small': ['t3a.small', 't4g.small', 't2.small'],
            't3.medium': ['t3a.medium', 't4g.medium', 't2.medium'],
            't3.large': ['t3a.large', 't4g.large', 't2.large'],
            't3.xlarge': ['t3a.xlarge', 't4g.xlarge', 't2.xlarge'],
            't3.2xlarge': ['t3a.2xlarge', 't4g.2xlarge', 't2.2xlarge'],
        }
        
        # Region-specific known working alternatives (based on investigation)
        self.region_specific_alternatives = {
            'ap-southeast-1': {  # Singapore
                'm5.large': None,  # No working alternatives found
                'm5.xlarge': 'm5d.xlarge',
                'm5.2xlarge': 'm6a.2xlarge',
                'm5.4xlarge': 'm5a.4xlarge',
                't3.small': None,  # No working alternatives found
            }
        }
    
    async def get_available_instances(self, region: str) -> Set[str]:
        """Get available instance types for a region with caching"""
        
        cache_key = f"available_{region}"
        
        # Check cache first
        if self._is_cached(cache_key):
            logger.info(f"Using cached instance availability for {region}")
            return self.availability_cache[cache_key]
        
        try:
            logger.info(f"Fetching available instance types for {region}")
            instance_types = await self.pricing_service.get_available_instance_types(region)
            available_set = set(instance_types)
            
            # Cache the result
            self._cache_availability(cache_key, available_set)
            
            logger.info(f"Found {len(available_set)} available instance types in {region}")
            return available_set
            
        except Exception as e:
            logger.error(f"Failed to get available instance types for {region}: {e}")
            # Return empty set if we can't get availability
            return set()
    
    async def validate_instance_availability(self, instance_type: str, region: str) -> bool:
        """Validate if an instance type is available in the target region"""
        
        available_instances = await self.get_available_instances(region)
        is_available = instance_type in available_instances
        
        logger.debug(f"Instance {instance_type} availability in {region}: {is_available}")
        return is_available
    
    async def get_best_alternative(self, instance_type: str, region: str) -> Tuple[Optional[str], Optional[float], str]:
        """
        Get the best available alternative for an instance type in a region
        
        Returns:
            - alternative_instance_type: str or None
            - price_difference: float or None (positive means more expensive)
            - reason: str explaining the choice
        """
        
        # First check if the original instance is available
        if await self.validate_instance_availability(instance_type, region):
            return instance_type, 0.0, "Original instance type available"
        
        logger.info(f"Finding alternative for {instance_type} in {region}")
        
        # Check region-specific alternatives first
        if region in self.region_specific_alternatives:
            region_alt = self.region_specific_alternatives[region].get(instance_type)
            if region_alt:
                if await self.validate_instance_availability(region_alt, region):
                    try:
                        # Get pricing comparison
                        original_price = await self._get_fallback_price(instance_type, region)
                        alt_price = await self._get_instance_price(region_alt, region)
                        price_diff = alt_price - original_price if original_price else 0.0
                        
                        return region_alt, price_diff, f"Region-specific alternative (${price_diff:+.4f}/hr difference)"
                    except Exception as e:
                        logger.warning(f"Could not get pricing comparison: {e}")
                        return region_alt, None, "Region-specific alternative (pricing comparison unavailable)"
        
        # Check general alternatives
        alternatives = self.instance_alternatives.get(instance_type, [])
        available_instances = await self.get_available_instances(region)
        
        best_alternative = None
        best_price = float('inf')
        best_price_diff = None
        
        for alt_instance in alternatives:
            if alt_instance in available_instances:
                try:
                    # Try to get pricing for this alternative
                    alt_price = await self._get_instance_price(alt_instance, region)
                    if alt_price and alt_price < best_price:
                        best_alternative = alt_instance
                        best_price = alt_price
                        
                        # Calculate price difference
                        original_price = await self._get_fallback_price(instance_type, region)
                        best_price_diff = alt_price - original_price if original_price else 0.0
                        
                except Exception as e:
                    logger.warning(f"Could not get pricing for alternative {alt_instance}: {e}")
                    # Still consider it as an alternative even without pricing
                    if not best_alternative:
                        best_alternative = alt_instance
                        best_price_diff = None
        
        if best_alternative:
            reason = f"Best available alternative"
            if best_price_diff is not None:
                reason += f" (${best_price_diff:+.4f}/hr difference)"
            return best_alternative, best_price_diff, reason
        
        # No alternatives found
        logger.warning(f"No alternatives found for {instance_type} in {region}")
        return None, None, f"No alternatives available in {region}"
    
    async def get_regional_recommendation(self, instance_type: str, region: str) -> Dict:
        """
        Get comprehensive regional recommendation including alternatives and pricing
        
        Returns detailed information about instance availability and alternatives
        """
        
        result = {
            'original_instance': instance_type,
            'region': region,
            'original_available': False,
            'recommended_instance': None,
            'price_difference': None,
            'reason': '',
            'alternatives_checked': 0,
            'alternatives_available': []
        }
        
        # Check original availability
        result['original_available'] = await self.validate_instance_availability(instance_type, region)
        
        if result['original_available']:
            result['recommended_instance'] = instance_type
            result['price_difference'] = 0.0
            result['reason'] = "Original instance type available"
            return result
        
        # Find best alternative
        alternative, price_diff, reason = await self.get_best_alternative(instance_type, region)
        
        result['recommended_instance'] = alternative
        result['price_difference'] = price_diff
        result['reason'] = reason
        
        # Get list of all available alternatives for transparency
        alternatives = self.instance_alternatives.get(instance_type, [])
        available_instances = await self.get_available_instances(region)
        
        result['alternatives_checked'] = len(alternatives)
        result['alternatives_available'] = [alt for alt in alternatives if alt in available_instances]
        
        return result
    
    async def _get_instance_price(self, instance_type: str, region: str) -> Optional[float]:
        """Get on-demand hourly price for an instance type"""
        try:
            pricing = await self.pricing_service.get_instance_pricing(instance_type, region)
            return pricing.on_demand_hourly
        except Exception as e:
            logger.warning(f"Could not get pricing for {instance_type} in {region}: {e}")
            return None
    
    async def _get_fallback_price(self, instance_type: str, region: str) -> Optional[float]:
        """Get fallback price estimate for unavailable instance type"""
        # For unavailable instances, we can estimate based on similar instances
        # This is a simplified approach - in production, you might want more sophisticated estimation
        
        family = instance_type.split('.')[0]
        size = instance_type.split('.')[1]
        
        # Try to find a similar instance in the same family
        available_instances = await self.get_available_instances(region)
        similar_instances = [inst for inst in available_instances if inst.startswith(f"{family}.")]
        
        if similar_instances:
            # Use the first available instance in the same family as a price reference
            try:
                reference_pricing = await self._get_instance_price(similar_instances[0], region)
                # Apply a rough scaling factor based on size (this is very approximate)
                size_multipliers = {
                    'micro': 0.5, 'small': 1.0, 'medium': 2.0, 'large': 4.0,
                    'xlarge': 8.0, '2xlarge': 16.0, '4xlarge': 32.0, '8xlarge': 64.0
                }
                multiplier = size_multipliers.get(size, 4.0)  # Default to large
                return reference_pricing * multiplier if reference_pricing else None
            except Exception:
                pass
        
        return None
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self.availability_cache:
            return False
        
        if cache_key not in self.cache_expiry:
            return False
        
        return datetime.utcnow() < self.cache_expiry[cache_key]
    
    def _cache_availability(self, cache_key: str, availability_set: Set[str]):
        """Cache availability data"""
        self.availability_cache[cache_key] = availability_set
        self.cache_expiry[cache_key] = datetime.utcnow() + self.cache_duration
        logger.info(f"Cached availability data for {cache_key}")
    
    def clear_cache(self):
        """Clear all cached data"""
        self.availability_cache.clear()
        self.cache_expiry.clear()
        logger.info("Regional instance availability cache cleared")

# Global instance for use across the application
regional_instance_service = None

def get_regional_instance_service(pricing_service: AWSPricingService = None) -> RegionalInstanceService:
    """Get or create the global regional instance service"""
    global regional_instance_service
    
    if regional_instance_service is None:
        if pricing_service is None:
            from services.aws_pricing_service import AWSPricingService
            pricing_service = AWSPricingService(profile_name="smartslot")
        
        regional_instance_service = RegionalInstanceService(pricing_service)
        logger.info("Regional Instance Service initialized")
    
    return regional_instance_service
