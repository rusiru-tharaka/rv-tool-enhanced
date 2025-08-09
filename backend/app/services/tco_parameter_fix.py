"""
TCO Parameter Fix for Singapore Region
Ensures correct 3-year Reserved Instance parameters and Singapore pricing
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TCOParameterFix:
    """Fix TCO parameters for Singapore region analysis"""
    
    def __init__(self):
        self.singapore_pricing = {
            # Correct Singapore pricing rates (ap-southeast-1)
            'instance_pricing': {
                'm5.xlarge': {
                    'on_demand': 0.232,
                    'reserved_1y_no_upfront': 0.160,
                    'reserved_3y_no_upfront': 0.140  # This should be used for production
                },
                'm5.2xlarge': {
                    'on_demand': 0.464,
                    'reserved_1y_no_upfront': 0.320,
                    'reserved_3y_no_upfront': 0.280  # This should be used for production
                },
                'm5.4xlarge': {
                    'on_demand': 0.928,
                    'reserved_1y_no_upfront': 0.640,
                    'reserved_3y_no_upfront': 0.560
                },
                't3.small': {
                    'on_demand': 0.0256,
                    'reserved_1y_no_upfront': 0.0176,
                    'reserved_3y_no_upfront': 0.0154
                }
            },
            'storage_pricing': {
                'gp3': 0.092  # per GB per month
            }
        }
    
    def fix_tco_parameters(self, tco_params: Dict) -> Dict:
        """Fix TCO parameters to ensure correct settings"""
        fixed_params = tco_params.copy()
        
        # Ensure Singapore region
        if tco_params.get('target_region') == 'ap-southeast-1':
            # Fix Reserved Instance parameters for production
            fixed_params.update({
                'production_model': 'reserved_instance',
                'reserved_instance_term': '3_year',  # Force 3-year term
                'reserved_instance_payment': 'no_upfront',  # Force no upfront
                'non_production_model': 'on_demand',
                'non_production_utilization': 0.5  # 50% utilization
            })
            
            logger.info("✅ Fixed TCO parameters for Singapore region (3-year RI, No Upfront)")
        
        return fixed_params
    
    def get_correct_pricing_key(self, environment: str, tco_params: Dict) -> str:
        """Get the correct pricing key based on environment and TCO parameters"""
        if environment == 'Production':
            # Force 3-year Reserved Instance for production
            return 'reserved_3y_no_upfront'
        else:
            # On-demand for non-production
            return 'on_demand'
    
    def calculate_correct_cost(self, instance_type: str, environment: str, storage_gb: float, tco_params: Dict) -> Dict:
        """Calculate correct cost using Singapore pricing"""
        try:
            # Get pricing key
            pricing_key = self.get_correct_pricing_key(environment, tco_params)
            
            # Get hourly rate
            if instance_type in self.singapore_pricing['instance_pricing']:
                hourly_rate = self.singapore_pricing['instance_pricing'][instance_type][pricing_key]
            else:
                logger.warning(f"No pricing for {instance_type}")
                return {}
            
            # Calculate utilization
            utilization = 1.0 if environment == 'Production' else 0.5
            
            # Calculate costs
            hours_per_month = 24 * 30.44
            instance_monthly_cost = hourly_rate * hours_per_month * utilization
            storage_monthly_cost = storage_gb * self.singapore_pricing['storage_pricing']['gp3']
            total_monthly_cost = instance_monthly_cost + storage_monthly_cost
            
            # Determine pricing plan display
            if pricing_key == 'reserved_3y_no_upfront':
                pricing_plan = 'Reserved Instance (3 Year)'
            else:
                pricing_plan = 'On-Demand'
            
            return {
                'instance_monthly_cost': round(instance_monthly_cost, 2),
                'storage_monthly_cost': round(storage_monthly_cost, 2),
                'total_monthly_cost': round(total_monthly_cost, 2),
                'pricing_plan': pricing_plan,
                'hourly_rate': hourly_rate,
                'utilization': utilization,
                'pricing_key': pricing_key
            }
            
        except Exception as e:
            logger.error(f"Error calculating correct cost: {e}")
            return {}

# Global instance
tco_parameter_fix = TCOParameterFix()
