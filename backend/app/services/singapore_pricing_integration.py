"""
Singapore Pricing Integration
Provides Singapore region pricing data for cost calculations
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SingaporePricingService:
    """Service for Singapore region pricing data"""
    
    def __init__(self):
        self.pricing_data = None
        self.load_pricing_data()
    
    def load_pricing_data(self):
        """Load Singapore pricing data"""
        try:
            pricing_file = '/home/ubuntu/rvtool/enhanced-ux/backend/data/singapore_pricing.json'
            with open(pricing_file, 'r') as f:
                self.pricing_data = json.load(f)
            logger.info("Singapore pricing data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Singapore pricing data: {e}")
            self.pricing_data = None
    
    def get_instance_pricing(self, instance_type: str, pricing_model: str) -> float:
        """Get instance pricing for Singapore region"""
        if not self.pricing_data:
            return 0.0
        
        try:
            instance_pricing = self.pricing_data.get('instance_pricing', {})
            if instance_type in instance_pricing:
                return instance_pricing[instance_type].get(pricing_model, 0.0)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting instance pricing: {e}")
            return 0.0
    
    def get_storage_pricing(self, storage_type: str = 'gp3') -> float:
        """Get storage pricing for Singapore region"""
        if not self.pricing_data:
            return 0.0
        
        try:
            storage_pricing = self.pricing_data.get('storage_pricing', {})
            return storage_pricing.get(storage_type, 0.0)
        except Exception as e:
            logger.error(f"Error getting storage pricing: {e}")
            return 0.0
    
    def calculate_monthly_cost(self, hourly_rate: float, utilization: float = 1.0) -> float:
        """Calculate monthly cost from hourly rate"""
        hours_per_month = 24 * 30.44  # Average month
        return hourly_rate * hours_per_month * utilization
    
    def get_standardized_cost(self, instance_type: str, environment: str, storage_gb: float = 0) -> Dict:
        """Get standardized cost calculation for Singapore region"""
        try:
            # Determine pricing model based on environment
            if environment == 'Production':
                pricing_model = 'reserved_3y_no_upfront'
                utilization = 1.0
            else:
                pricing_model = 'on_demand'
                utilization = 0.5  # 50% utilization for non-production
            
            # Get instance pricing
            hourly_rate = self.get_instance_pricing(instance_type, pricing_model)
            instance_monthly_cost = self.calculate_monthly_cost(hourly_rate, utilization)
            
            # Get storage pricing
            storage_rate = self.get_storage_pricing('gp3')  # Default to gp3
            storage_monthly_cost = storage_gb * storage_rate
            
            # Calculate total
            total_monthly_cost = instance_monthly_cost + storage_monthly_cost
            
            return {
                'instance_type': instance_type,
                'environment': environment,
                'pricing_model': pricing_model,
                'utilization': utilization,
                'hourly_rate': hourly_rate,
                'instance_monthly_cost': instance_monthly_cost,
                'storage_gb': storage_gb,
                'storage_rate': storage_rate,
                'storage_monthly_cost': storage_monthly_cost,
                'total_monthly_cost': total_monthly_cost,
                'region': 'ap-southeast-1'
            }
            
        except Exception as e:
            logger.error(f"Error calculating standardized cost: {e}")
            return {
                'instance_type': instance_type,
                'environment': environment,
                'error': str(e),
                'total_monthly_cost': 0.0
            }

# Global instance
singapore_pricing_service = SingaporePricingService()
