"""
Singapore Pricing Override
Patches existing pricing service to return correct Singapore prices
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SingaporePricingOverride:
    """Override pricing for Singapore region"""
    
    def __init__(self):
        self.singapore_pricing = self._load_singapore_pricing()
        self.original_get_multiple_instance_pricing_cached = None
        self.original_get_storage_pricing_cached = None
        
    def _load_singapore_pricing(self):
        """Load Singapore pricing data"""
        try:
            pricing_file = '/home/ubuntu/rvtool/enhanced-ux/backend/data/singapore_pricing.json'
            with open(pricing_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading Singapore pricing: {e}")
            return None
    
    def patch_pricing_service(self, pricing_service):
        """Patch the pricing service to use Singapore data"""
        if not self.singapore_pricing:
            return
        
        # Store original methods
        self.original_get_multiple_instance_pricing_cached = pricing_service.get_multiple_instance_pricing_cached
        self.original_get_storage_pricing_cached = pricing_service.get_storage_pricing_cached
        
        # Create patched methods
        async def patched_get_multiple_instance_pricing_cached(instance_types, region):
            if region == 'ap-southeast-1':
                # Return Singapore pricing
                result = {}
                for instance_type in instance_types:
                    if instance_type in self.singapore_pricing['instance_pricing']:
                        result[instance_type] = self.singapore_pricing['instance_pricing'][instance_type]
                    else:
                        result[instance_type] = {}
                return result
            else:
                # Use original method for other regions
                return await self.original_get_multiple_instance_pricing_cached(instance_types, region)
        
        async def patched_get_storage_pricing_cached(storage_type, region):
            if region == 'ap-southeast-1':
                # Return Singapore storage pricing
                return self.singapore_pricing.get('storage_pricing', {}).get(storage_type, 0.092)
            else:
                # Use original method for other regions
                return await self.original_get_storage_pricing_cached(storage_type, region)
        
        # Apply patches
        pricing_service.get_multiple_instance_pricing_cached = patched_get_multiple_instance_pricing_cached
        pricing_service.get_storage_pricing_cached = patched_get_storage_pricing_cached
        
        logger.info("✅ Singapore pricing override applied")

# Global instance
singapore_override = SingaporePricingOverride()
