"""
AWS Pricing JSON Parser - FIXED VERSION
Parses AWS bulk pricing JSON data into structured database records
Correctly extracts EBS pricing from EC2 data based on AWS official structure
"""

import json
import logging
from typing import Dict, List, Optional, Generator
from datetime import datetime, date
import re

logger = logging.getLogger(__name__)

class AWSPricingParser:
    """Parses AWS bulk pricing JSON data with correct EBS handling"""
    
    # Region name mapping (AWS location names to region codes)
    REGION_MAPPING = {
        'US East (N. Virginia)': 'us-east-1',
        'US East (Ohio)': 'us-east-2', 
        'US West (Oregon)': 'us-west-2',
        'US West (N. California)': 'us-west-1',
        'Europe (Ireland)': 'eu-west-1',
        'Europe (London)': 'eu-west-2',
        'Europe (Paris)': 'eu-west-3',
        'Europe (Frankfurt)': 'eu-central-1',
        'Europe (Stockholm)': 'eu-north-1',
        'Europe (Milan)': 'eu-south-1',
        'Asia Pacific (Singapore)': 'ap-southeast-1',
        'Asia Pacific (Sydney)': 'ap-southeast-2',
        'Asia Pacific (Jakarta)': 'ap-southeast-3',
        'Asia Pacific (Tokyo)': 'ap-northeast-1',
        'Asia Pacific (Seoul)': 'ap-northeast-2',
        'Asia Pacific (Osaka)': 'ap-northeast-3',
        'Asia Pacific (Mumbai)': 'ap-south-1',
        'Asia Pacific (Hong Kong)': 'ap-east-1',
        'Canada (Central)': 'ca-central-1',
        'South America (São Paulo)': 'sa-east-1',
        'Africa (Cape Town)': 'af-south-1',
        'Middle East (Bahrain)': 'me-south-1',
        'Middle East (UAE)': 'me-central-1',
        'AWS GovCloud (US-East)': 'us-gov-east-1',
        'AWS GovCloud (US-West)': 'us-gov-west-1'
    }
    
    # EBS Volume types mapping
    EBS_VOLUME_TYPES = {
        'gp2': 'General Purpose SSD (gp2)',
        'gp3': 'General Purpose SSD (gp3)', 
        'io1': 'Provisioned IOPS SSD (io1)',
        'io2': 'Provisioned IOPS SSD (io2)',
        'st1': 'Throughput Optimized HDD (st1)',
        'sc1': 'Cold HDD (sc1)',
        'standard': 'Magnetic'
    }
    
    def __init__(self):
        """Initialize parser"""
        self.stats = {
            'products_processed': 0,
            'ec2_instances_found': 0,
            'ebs_volumes_found': 0,
            'pricing_records_created': 0,
            'errors': 0
        }
        logger.info("AWS Pricing Parser initialized (with EBS extraction from EC2 data)")
    
    def get_region_code(self, location: str) -> Optional[str]:
        """Convert AWS location name to region code"""
        return self.REGION_MAPPING.get(location)
    
    def is_ebs_product(self, product: Dict) -> bool:
        """Check if a product is an EBS volume"""
        attributes = product.get('attributes', {})
        
        # Check for EBS-specific attributes
        product_family = attributes.get('productFamily', '')
        usage_type = attributes.get('usagetype', '')
        
        # EBS products have productFamily = "Storage" and specific usage patterns
        if product_family == 'Storage':
            # Check for EBS volume usage patterns
            ebs_patterns = [
                'VolumeUsage',  # Standard EBS volume usage
                'EBS:VolumeUsage',  # Explicit EBS volume usage
                'VolumeP-IOPS',  # Provisioned IOPS
                'VolumeIOPS'  # IOPS charges
            ]
            
            for pattern in ebs_patterns:
                if pattern in usage_type:
                    return True
        
        return False
    
    def is_ec2_instance_product(self, product: Dict) -> bool:
        """Check if a product is an EC2 instance"""
        attributes = product.get('attributes', {})
        
        product_family = attributes.get('productFamily', '')
        instance_type = attributes.get('instanceType', '')
        
        # EC2 instances have productFamily = "Compute Instance" and instanceType
        return (product_family == 'Compute Instance' and 
                instance_type and 
                instance_type != 'NA')
    
    def extract_ebs_volume_type(self, product: Dict) -> Optional[str]:
        """Extract EBS volume type from product attributes"""
        attributes = product.get('attributes', {})
        
        # Try different attribute names that might contain volume type
        volume_type_fields = ['volumeType', 'storageMedia', 'volumeApiName']
        
        for field in volume_type_fields:
            if field in attributes:
                value = attributes[field].lower()
                
                # Map common volume type names
                if 'gp3' in value:
                    return 'gp3'
                elif 'gp2' in value or 'general purpose' in value:
                    return 'gp2'
                elif 'io2' in value:
                    return 'io2'
                elif 'io1' in value or 'provisioned iops' in value:
                    return 'io1'
                elif 'st1' in value or 'throughput optimized' in value:
                    return 'st1'
                elif 'sc1' in value or 'cold' in value:
                    return 'sc1'
                elif 'standard' in value or 'magnetic' in value:
                    return 'standard'
        
        # Try to extract from usage type
        usage_type = attributes.get('usagetype', '').lower()
        if 'gp3' in usage_type:
            return 'gp3'
        elif 'gp2' in usage_type:
            return 'gp2'
        elif 'io1' in usage_type:
            return 'io1'
        elif 'io2' in usage_type:
            return 'io2'
        elif 'st1' in usage_type:
            return 'st1'
        elif 'sc1' in usage_type:
            return 'sc1'
        
        return None
    
    def parse_ec2_pricing(self, ec2_data: Dict) -> Generator[Dict, None, None]:
        """Parse EC2 pricing data and extract both EC2 instances and EBS volumes"""
        
        logger.info("Parsing EC2 pricing data (including EBS volumes)...")
        
        products = ec2_data.get('products', {})
        terms = ec2_data.get('terms', {})
        
        logger.info(f"Found {len(products)} products to process")
        
        for product_id, product in products.items():
            try:
                self.stats['products_processed'] += 1
                
                # Process EC2 instances
                if self.is_ec2_instance_product(product):
                    yield from self._parse_ec2_instance(product_id, product, terms)
                    self.stats['ec2_instances_found'] += 1
                
                # Process EBS volumes (extracted from EC2 data)
                elif self.is_ebs_product(product):
                    yield from self._parse_ebs_volume(product_id, product, terms)
                    self.stats['ebs_volumes_found'] += 1
                
                # Progress reporting
                if self.stats['products_processed'] % 1000 == 0:
                    logger.info(f"Processed {self.stats['products_processed']} products...")
                    
            except Exception as e:
                logger.error(f"Error processing product {product_id}: {e}")
                self.stats['errors'] += 1
                continue
        
        logger.info(f"EC2 parsing complete:")
        logger.info(f"  Products processed: {self.stats['products_processed']}")
        logger.info(f"  EC2 instances found: {self.stats['ec2_instances_found']}")
        logger.info(f"  EBS volumes found: {self.stats['ebs_volumes_found']}")
        logger.info(f"  Pricing records created: {self.stats['pricing_records_created']}")
        logger.info(f"  Errors: {self.stats['errors']}")
    
    def _parse_ec2_instance(self, product_id: str, product: Dict, terms: Dict) -> Generator[Dict, None, None]:
        """Parse EC2 instance pricing"""
        
        attributes = product.get('attributes', {})
        
        # Extract basic attributes
        instance_type = attributes.get('instanceType', '')
        location = attributes.get('location', '')
        region = self.get_region_code(location)
        
        if not region:
            return  # Skip if we can't map the region
        
        operating_system = attributes.get('operatingSystem', 'Linux')
        tenancy = attributes.get('tenancy', 'Shared')
        
        # Process On-Demand pricing
        on_demand_terms = terms.get('OnDemand', {}).get(product_id, {})
        for term_id, term_data in on_demand_terms.items():
            for dimension_id, dimension in term_data.get('priceDimensions', {}).items():
                price_per_unit = dimension.get('pricePerUnit', {})
                price_usd = price_per_unit.get('USD', '0')
                
                try:
                    price_float = float(price_usd)
                    if price_float > 0:  # Only include non-zero prices
                        yield {
                            'instance_type': instance_type,
                            'region': region,
                            'location': location,
                            'operating_system': operating_system,
                            'tenancy': tenancy,
                            'pricing_model': 'OnDemand',
                            'term_length': None,
                            'payment_option': None,
                            'price_per_hour': price_float,
                            'currency': 'USD',
                            'effective_date': date.today().isoformat()
                        }
                        self.stats['pricing_records_created'] += 1
                except ValueError:
                    continue
        
        # Process Reserved Instance pricing
        reserved_terms = terms.get('Reserved', {}).get(product_id, {})
        for term_id, term_data in reserved_terms.items():
            term_attributes = term_data.get('termAttributes', {})
            lease_length = term_attributes.get('LeaseContractLength', '')
            purchase_option = term_attributes.get('PurchaseOption', '')
            
            for dimension_id, dimension in term_data.get('priceDimensions', {}).items():
                price_per_unit = dimension.get('pricePerUnit', {})
                price_usd = price_per_unit.get('USD', '0')
                
                try:
                    price_float = float(price_usd)
                    if price_float > 0:
                        yield {
                            'instance_type': instance_type,
                            'region': region,
                            'location': location,
                            'operating_system': operating_system,
                            'tenancy': tenancy,
                            'pricing_model': 'Reserved',
                            'term_length': lease_length,
                            'payment_option': purchase_option,
                            'price_per_hour': price_float,
                            'currency': 'USD',
                            'effective_date': date.today().isoformat()
                        }
                        self.stats['pricing_records_created'] += 1
                except ValueError:
                    continue
    
    def _parse_ebs_volume(self, product_id: str, product: Dict, terms: Dict) -> Generator[Dict, None, None]:
        """Parse EBS volume pricing from EC2 data"""
        
        attributes = product.get('attributes', {})
        
        # Extract basic attributes
        location = attributes.get('location', '')
        region = self.get_region_code(location)
        
        if not region:
            return  # Skip if we can't map the region
        
        volume_type = self.extract_ebs_volume_type(product)
        if not volume_type:
            return  # Skip if we can't determine volume type
        
        # Process On-Demand pricing (EBS is typically only on-demand)
        on_demand_terms = terms.get('OnDemand', {}).get(product_id, {})
        for term_id, term_data in on_demand_terms.items():
            for dimension_id, dimension in term_data.get('priceDimensions', {}).items():
                price_per_unit = dimension.get('pricePerUnit', {})
                price_usd = price_per_unit.get('USD', '0')
                unit = dimension.get('unit', '')
                
                # EBS pricing is typically per GB-month
                if 'GB' in unit or 'gb' in unit.lower():
                    try:
                        price_float = float(price_usd)
                        if price_float > 0:
                            yield {
                                'volume_type': volume_type,
                                'region': region,
                                'location': location,
                                'price_per_gb_month': price_float,
                                'currency': 'USD',
                                'effective_date': date.today().isoformat()
                            }
                            self.stats['pricing_records_created'] += 1
                    except ValueError:
                        continue
    
    def parse_ebs_pricing(self, ebs_data: Dict) -> Generator[Dict, None, None]:
        """Parse EBS pricing data (fallback method if separate EBS data exists)"""
        
        logger.info("Note: EBS pricing should be extracted from EC2 data")
        logger.info("This method is a fallback for separate EBS data files")
        
        # This method is kept for compatibility but EBS data should come from EC2
        products = ebs_data.get('products', {})
        terms = ebs_data.get('terms', {})
        
        for product_id, product in products.items():
            try:
                if self.is_ebs_product(product):
                    yield from self._parse_ebs_volume(product_id, product, terms)
            except Exception as e:
                logger.error(f"Error processing EBS product {product_id}: {e}")
                continue
    
    def get_parsing_stats(self) -> Dict:
        """Get parsing statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset parsing statistics"""
        self.stats = {
            'products_processed': 0,
            'ec2_instances_found': 0,
            'ebs_volumes_found': 0,
            'pricing_records_created': 0,
            'errors': 0
        }
