"""
Sample Data Generator for Bulk Pricing Development
Generates realistic AWS pricing data for development without downloads
Bypasses the download bottleneck that was blocking development
"""

import json
from datetime import datetime, date
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SampleDataGenerator:
    """Generates sample AWS pricing data for development"""
    
    # Common instance types with realistic pricing
    SAMPLE_INSTANCE_TYPES = {
        # General Purpose
        't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832,
        't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
        'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384, 'm5.4xlarge': 0.768,
        'm5.8xlarge': 1.536, 'm5.12xlarge': 2.304, 'm5.16xlarge': 3.072, 'm5.24xlarge': 4.608,
        
        # Compute Optimized
        'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34, 'c5.4xlarge': 0.68,
        'c5.9xlarge': 1.53, 'c5.12xlarge': 2.04, 'c5.18xlarge': 3.06, 'c5.24xlarge': 4.08,
        
        # Memory Optimized
        'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504, 'r5.4xlarge': 1.008,
        'r5.8xlarge': 2.016, 'r5.12xlarge': 3.024, 'r5.16xlarge': 4.032, 'r5.24xlarge': 6.048,
        
        # Storage Optimized
        'i3.large': 0.156, 'i3.xlarge': 0.312, 'i3.2xlarge': 0.624, 'i3.4xlarge': 1.248,
        'i3.8xlarge': 2.496, 'i3.16xlarge': 4.992
    }
    
    # AWS Regions with location mapping
    REGIONS = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'eu-west-1': 'Europe (Ireland)',
        'eu-west-2': 'Europe (London)',
        'eu-central-1': 'Europe (Frankfurt)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)'
    }
    
    # Regional pricing multipliers (us-east-1 as baseline)
    REGIONAL_MULTIPLIERS = {
        'us-east-1': 1.0,
        'us-east-2': 0.98,
        'us-west-1': 1.15,
        'us-west-2': 1.05,
        'eu-west-1': 1.12,
        'eu-west-2': 1.14,
        'eu-central-1': 1.16,
        'ap-southeast-1': 1.18,
        'ap-southeast-2': 1.20,
        'ap-northeast-1': 1.22
    }
    
    # Reserved Instance discounts (approximate)
    RESERVED_DISCOUNTS = {
        '1yr_no_upfront': 0.25,      # 25% discount
        '1yr_partial_upfront': 0.30,  # 30% discount
        '1yr_all_upfront': 0.35,     # 35% discount
        '3yr_no_upfront': 0.40,      # 40% discount
        '3yr_partial_upfront': 0.45,  # 45% discount
        '3yr_all_upfront': 0.50      # 50% discount
    }
    
    # EBS Volume pricing (per GB-month)
    EBS_PRICING = {
        'gp3': 0.08,
        'gp2': 0.10,
        'io1': 0.125,
        'io2': 0.125,
        'st1': 0.045,
        'sc1': 0.025
    }
    
    def __init__(self):
        """Initialize sample data generator"""
        self.current_date = date.today().isoformat()
        logger.info("Sample data generator initialized")
    
    def generate_ec2_pricing_data(self) -> List[Dict]:
        """Generate comprehensive EC2 pricing data"""
        pricing_records = []
        
        for instance_type, base_price in self.SAMPLE_INSTANCE_TYPES.items():
            for region, location in self.REGIONS.items():
                regional_multiplier = self.REGIONAL_MULTIPLIERS.get(region, 1.0)
                regional_price = base_price * regional_multiplier
                
                # On-Demand pricing
                pricing_records.append({
                    'instance_type': instance_type,
                    'region': region,
                    'location': location,
                    'operating_system': 'Linux',
                    'tenancy': 'Shared',
                    'pricing_model': 'OnDemand',
                    'term_length': None,
                    'payment_option': None,
                    'price_per_hour': round(regional_price, 6),
                    'currency': 'USD',
                    'effective_date': self.current_date
                })
                
                # Windows pricing (typically 2x Linux)
                pricing_records.append({
                    'instance_type': instance_type,
                    'region': region,
                    'location': location,
                    'operating_system': 'Windows',
                    'tenancy': 'Shared',
                    'pricing_model': 'OnDemand',
                    'term_length': None,
                    'payment_option': None,
                    'price_per_hour': round(regional_price * 2.0, 6),
                    'currency': 'USD',
                    'effective_date': self.current_date
                })
                
                # Reserved Instance pricing
                for term_payment, discount in self.RESERVED_DISCOUNTS.items():
                    term, payment = term_payment.split('_', 1)
                    reserved_price = regional_price * (1 - discount)
                    
                    pricing_records.append({
                        'instance_type': instance_type,
                        'region': region,
                        'location': location,
                        'operating_system': 'Linux',
                        'tenancy': 'Shared',
                        'pricing_model': 'Reserved',
                        'term_length': term,
                        'payment_option': payment.replace('_', ' ').title(),
                        'price_per_hour': round(reserved_price, 6),
                        'currency': 'USD',
                        'effective_date': self.current_date
                    })
        
        logger.info(f"Generated {len(pricing_records)} EC2 pricing records")
        return pricing_records
    
    def generate_ebs_pricing_data(self) -> List[Dict]:
        """Generate EBS storage pricing data"""
        pricing_records = []
        
        for volume_type, base_price in self.EBS_PRICING.items():
            for region, location in self.REGIONS.items():
                regional_multiplier = self.REGIONAL_MULTIPLIERS.get(region, 1.0)
                regional_price = base_price * regional_multiplier
                
                pricing_records.append({
                    'volume_type': volume_type,
                    'region': region,
                    'location': location,
                    'price_per_gb_month': round(regional_price, 6),
                    'currency': 'USD',
                    'effective_date': self.current_date
                })
        
        logger.info(f"Generated {len(pricing_records)} EBS pricing records")
        return pricing_records
    
    def generate_savings_plans_data(self) -> List[Dict]:
        """Generate Savings Plans pricing data"""
        pricing_records = []
        
        # Compute Savings Plans (cross-instance family)
        for instance_type, base_price in self.SAMPLE_INSTANCE_TYPES.items():
            for region in self.REGIONS.keys():
                regional_multiplier = self.REGIONAL_MULTIPLIERS.get(region, 1.0)
                regional_price = base_price * regional_multiplier
                
                # 1-year Compute Savings Plans (20% discount)
                pricing_records.append({
                    'instance_type': instance_type,
                    'region': region,
                    'operating_system': 'Linux',
                    'pricing_model': 'ComputeSavingsPlans',
                    'term_length': '1yr',
                    'payment_option': 'No Upfront',
                    'price_per_hour': round(regional_price * 0.8, 6),
                    'currency': 'USD',
                    'effective_date': self.current_date
                })
                
                # 3-year Compute Savings Plans (35% discount)
                pricing_records.append({
                    'instance_type': instance_type,
                    'region': region,
                    'operating_system': 'Linux',
                    'pricing_model': 'ComputeSavingsPlans',
                    'term_length': '3yr',
                    'payment_option': 'No Upfront',
                    'price_per_hour': round(regional_price * 0.65, 6),
                    'currency': 'USD',
                    'effective_date': self.current_date
                })
        
        logger.info(f"Generated {len(pricing_records)} Savings Plans records")
        return pricing_records
    
    def generate_complete_sample_dataset(self) -> Dict:
        """Generate complete sample dataset for development"""
        logger.info("Generating complete sample pricing dataset...")
        
        dataset = {
            'ec2_pricing': self.generate_ec2_pricing_data(),
            'ebs_pricing': self.generate_ebs_pricing_data(),
            'savings_plans': self.generate_savings_plans_data(),
            'metadata': {
                'generated_date': datetime.now().isoformat(),
                'total_records': 0,
                'coverage': {
                    'instance_types': len(self.SAMPLE_INSTANCE_TYPES),
                    'regions': len(self.REGIONS),
                    'pricing_models': ['OnDemand', 'Reserved', 'ComputeSavingsPlans']
                }
            }
        }
        
        # Calculate total records
        total_records = (
            len(dataset['ec2_pricing']) + 
            len(dataset['ebs_pricing']) + 
            len(dataset['savings_plans'])
        )
        dataset['metadata']['total_records'] = total_records
        
        logger.info(f"Sample dataset generated: {total_records} total records")
        return dataset
    
    def save_sample_data_to_file(self, filename: str = None) -> str:
        """Save sample data to JSON file"""
        if filename is None:
            filename = f"sample_pricing_data_{self.current_date}.json"
        
        dataset = self.generate_complete_sample_dataset()
        
        with open(filename, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"Sample data saved to {filename}")
        return filename

def main():
    """Generate and save sample data"""
    generator = SampleDataGenerator()
    filename = generator.save_sample_data_to_file()
    print(f"Sample pricing data generated: {filename}")

if __name__ == "__main__":
    main()
