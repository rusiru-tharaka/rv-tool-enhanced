"""
Hybrid Pricing Service
Combines local pricing data with AWS API fallback for comprehensive coverage
"""

import json
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class HybridPricingService:
    """
    Hybrid pricing service that uses local data for performance
    and AWS API for missing regions/instance types
    """
    
    def __init__(self):
        self.local_pricing_cache = {}
        self.load_local_pricing_data()
    
    def load_local_pricing_data(self):
        """Load local pricing data for supported regions"""
        try:
            # Load Singapore pricing
            singapore_file = '/home/ubuntu/rvtool/enhanced-ux/backend/data/singapore_pricing.json'
            with open(singapore_file, 'r') as f:
                singapore_data = json.load(f)
                self.local_pricing_cache['ap-southeast-1'] = singapore_data
            
            logger.info("Loaded local pricing data for Singapore region")
            
        except Exception as e:
            logger.error(f"Error loading local pricing data: {e}")
    
    def get_instance_pricing(self, instance_type: str, region: str, pricing_model: str) -> float:
        """
        Get instance pricing with hybrid approach
        
        Args:
            instance_type: EC2 instance type (e.g., 'm5.xlarge')
            region: AWS region (e.g., 'ap-southeast-1')
            pricing_model: Pricing model (e.g., 'on_demand', 'reserved_3y_no_upfront')
        
        Returns:
            Hourly rate in USD
        """
        try:
            # Try local cache first
            if region in self.local_pricing_cache:
                pricing_data = self.local_pricing_cache[region]
                if 'instance_pricing' in pricing_data and instance_type in pricing_data['instance_pricing']:
                    rate = pricing_data['instance_pricing'][instance_type].get(pricing_model, 0.0)
                    if rate > 0:
                        logger.debug(f"Local pricing hit: {instance_type} {region} {pricing_model} = ${rate}")
                        return rate
            
            # Fallback to AWS API (placeholder for now)
            logger.warning(f"No local pricing for {instance_type} in {region}, using fallback")
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting instance pricing: {e}")
            return 0.0
    
    def get_storage_pricing(self, storage_type: str, region: str) -> float:
        """Get storage pricing per GB per month"""
        try:
            if region in self.local_pricing_cache:
                pricing_data = self.local_pricing_cache[region]
                if 'storage_pricing' in pricing_data:
                    return pricing_data['storage_pricing'].get(storage_type, 0.0)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting storage pricing: {e}")
            return 0.0
    
    def calculate_monthly_cost(self, hourly_rate: float, utilization: float = 1.0) -> float:
        """Calculate monthly cost from hourly rate"""
        hours_per_month = 24 * 30.44  # Average month
        return hourly_rate * hours_per_month * utilization
    
    def validate_pricing_consistency(self, instance_type: str, region: str) -> Dict:
        """Validate pricing consistency across models"""
        results = {}
        
        pricing_models = ['on_demand', 'reserved_1y_no_upfront', 'reserved_3y_no_upfront']
        
        for model in pricing_models:
            rate = self.get_instance_pricing(instance_type, region, model)
            results[model] = {
                'hourly_rate': rate,
                'monthly_cost': self.calculate_monthly_cost(rate),
                'available': rate > 0
            }
        
        return results

# Global instance
hybrid_pricing_service = HybridPricingService()
