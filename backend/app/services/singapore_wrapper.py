"""
Singapore Pricing Wrapper for UI Integration
Simple wrapper to integrate Singapore pricing into existing cost calculations
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SingaporePricingWrapper:
    """Simple wrapper for Singapore pricing integration"""
    
    def __init__(self):
        self.pricing_data = self._load_pricing_data()
    
    def _load_pricing_data(self):
        """Load Singapore pricing data"""
        try:
            pricing_file = '/home/ubuntu/rvtool/enhanced-ux/backend/data/singapore_pricing.json'
            with open(pricing_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading Singapore pricing: {e}")
            return None
    
    def get_corrected_pricing(self, instance_type: str, region: str, pricing_model: str) -> Optional[float]:
        """Get corrected pricing for Singapore region"""
        if region != 'ap-southeast-1' or not self.pricing_data:
            return None
        
        try:
            instance_pricing = self.pricing_data.get('instance_pricing', {})
            if instance_type in instance_pricing:
                return instance_pricing[instance_type].get(pricing_model, None)
            return None
        except Exception as e:
            logger.error(f"Error getting corrected pricing: {e}")
            return None
    
    def get_corrected_costs(self, instance_type: str, environment: str, storage_gb: float = 0) -> Dict:
        """Get corrected costs for Singapore region"""
        try:
            # Determine pricing model based on environment
            if environment == 'Production':
                pricing_model = 'reserved_3y_no_upfront'
                utilization = 1.0
            else:
                pricing_model = 'on_demand'
                utilization = 0.5
            
            # Get instance pricing
            hourly_rate = self.get_corrected_pricing(instance_type, 'ap-southeast-1', pricing_model)
            if hourly_rate is None:
                return {}
            
            # Calculate costs
            hours_per_month = 24 * 30.44
            instance_monthly_cost = hourly_rate * hours_per_month * utilization
            
            # Storage cost
            storage_rate = self.pricing_data.get('storage_pricing', {}).get('gp3', 0.092)
            storage_monthly_cost = storage_gb * storage_rate
            
            total_monthly_cost = instance_monthly_cost + storage_monthly_cost
            
            return {
                'instance_monthly_cost': instance_monthly_cost,
                'storage_monthly_cost': storage_monthly_cost,
                'total_monthly_cost': total_monthly_cost,
                'hourly_rate': hourly_rate,
                'utilization': utilization,
                'pricing_model': pricing_model
            }
            
        except Exception as e:
            logger.error(f"Error calculating corrected costs: {e}")
            return {}

# Global instance
singapore_wrapper = SingaporePricingWrapper()
