"""
AWS Pricing JSON Parser
Parses AWS bulk pricing JSON data into structured database records
"""

import json
import logging
from typing import Dict, List, Optional, Generator
from datetime import datetime, date
import re

logger = logging.getLogger(__name__)

class AWSPricingParser:
    """Parses AWS bulk pricing JSON data"""
    
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
    
    def __init__(self):
        """Initialize parser"""
        self.stats = {
            'products_processed': 0,
            'pricing_records_created': 0,
            'errors': 0
        }
        logger.info("AWS Pricing Parser initialized")
    
    def parse_ec2_pricing(self, pricing_data: Dict) -> Generator[Dict, None, None]:
        """Parse EC2 pricing data and yield pricing records"""
        
        if not pricing_data or 'products' not in pricing_data or 'terms' not in pricing_data:
            logger.error("Invalid EC2 pricing data structure")
            return
        
        products = pricing_data['products']
        terms = pricing_data['terms']
        
        logger.info(f"Parsing EC2 pricing data: {len(products)} products")
        
        for product_sku, product_data in products.items():
            try:
                self.stats['products_processed'] += 1
                
                # Extract product attributes
                attributes = product_data.get('attributes', {})
                
                # Skip non-EC2 instance products
                if attributes.get('servicecode') != 'AmazonEC2':
                    continue
                
                # Skip products without instance type
                instance_type = attributes.get('instanceType')
                if not instance_type:
                    continue
                
                # Extract basic attributes
                location = attributes.get('location', '')
                region = self._map_location_to_region(location)
                if not region:
                    continue
                
                operating_system = self._normalize_os(attributes.get('operatingSystem', 'Linux'))
                tenancy = attributes.get('tenancy', 'Shared')
                
                # Skip unsupported configurations
                if attributes.get('preInstalledSw', 'NA') != 'NA':
                    continue
                if attributes.get('capacitystatus', 'Used') != 'Used':
                    continue
                
                # Process pricing terms
                yield from self._process_ec2_terms(
                    product_sku, terms, instance_type, region, location,
                    operating_system, tenancy
                )
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error processing product {product_sku}: {e}")
                continue
        
        logger.info(f"EC2 parsing completed: {self.stats['pricing_records_created']} records created")
    
    def _process_ec2_terms(self, product_sku: str, terms: Dict, instance_type: str,
                          region: str, location: str, operating_system: str, tenancy: str) -> Generator[Dict, None, None]:
        """Process pricing terms for an EC2 product"""
        
        # Process On-Demand pricing
        if 'OnDemand' in terms and product_sku in terms['OnDemand']:
            for term_sku, term_data in terms['OnDemand'][product_sku].items():
                try:
                    price_per_hour = self._extract_hourly_price(term_data)
                    if price_per_hour is not None:
                        yield {
                            'instance_type': instance_type,
                            'region': region,
                            'location': location,
                            'operating_system': operating_system,
                            'tenancy': tenancy,
                            'pricing_model': 'OnDemand',
                            'term_length': None,
                            'payment_option': None,
                            'price_per_hour': price_per_hour,
                            'currency': 'USD',
                            'effective_date': date.today()
                        }
                        self.stats['pricing_records_created'] += 1
                except Exception as e:
                    logger.debug(f"Error processing OnDemand term {term_sku}: {e}")
        
        # Process Reserved Instance pricing
        if 'Reserved' in terms and product_sku in terms['Reserved']:
            for term_sku, term_data in terms['Reserved'][product_sku].items():
                try:
                    term_attributes = term_data.get('termAttributes', {})
                    lease_contract_length = term_attributes.get('LeaseContractLength', '')
                    purchase_option = term_attributes.get('PurchaseOption', '')
                    
                    # Map term length
                    term_length = self._map_term_length(lease_contract_length)
                    payment_option = self._map_payment_option(purchase_option)
                    
                    if term_length and payment_option:
                        price_per_hour = self._extract_hourly_price(term_data)
                        if price_per_hour is not None:
                            yield {
                                'instance_type': instance_type,
                                'region': region,
                                'location': location,
                                'operating_system': operating_system,
                                'tenancy': tenancy,
                                'pricing_model': 'Reserved',
                                'term_length': term_length,
                                'payment_option': payment_option,
                                'price_per_hour': price_per_hour,
                                'currency': 'USD',
                                'effective_date': date.today()
                            }
                            self.stats['pricing_records_created'] += 1
                except Exception as e:
                    logger.debug(f"Error processing Reserved term {term_sku}: {e}")
    
    def parse_ebs_pricing(self, pricing_data: Dict) -> Generator[Dict, None, None]:
        """Parse EBS pricing data and yield pricing records"""
        
        if not pricing_data or 'products' not in pricing_data or 'terms' not in pricing_data:
            logger.error("Invalid EBS pricing data structure")
            return
        
        products = pricing_data['products']
        terms = pricing_data['terms']
        
        logger.info(f"Parsing EBS pricing data: {len(products)} products")
        
        for product_sku, product_data in products.items():
            try:
                self.stats['products_processed'] += 1
                
                # Extract product attributes
                attributes = product_data.get('attributes', {})
                
                # Skip non-EBS products
                if attributes.get('servicecode') != 'AmazonEBS':
                    continue
                
                # Extract volume type
                volume_type = attributes.get('volumeType')
                if not volume_type:
                    continue
                
                # Extract location and map to region
                location = attributes.get('location', '')
                region = self._map_location_to_region(location)
                if not region:
                    continue
                
                # Process OnDemand pricing only for EBS
                if 'OnDemand' in terms and product_sku in terms['OnDemand']:
                    for term_sku, term_data in terms['OnDemand'][product_sku].items():
                        try:
                            price_per_gb_month = self._extract_monthly_price(term_data)
                            if price_per_gb_month is not None:
                                yield {
                                    'volume_type': volume_type,
                                    'region': region,
                                    'location': location,
                                    'price_per_gb_month': price_per_gb_month,
                                    'currency': 'USD',
                                    'effective_date': date.today()
                                }
                                self.stats['pricing_records_created'] += 1
                        except Exception as e:
                            logger.debug(f"Error processing EBS term {term_sku}: {e}")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error processing EBS product {product_sku}: {e}")
                continue
        
        logger.info(f"EBS parsing completed: {self.stats['pricing_records_created']} records created")
    
    def _extract_hourly_price(self, term_data: Dict) -> Optional[float]:
        """Extract hourly price from term data"""
        
        try:
            price_dimensions = term_data.get('priceDimensions', {})
            
            for dimension_key, dimension_data in price_dimensions.items():
                price_per_unit = dimension_data.get('pricePerUnit', {})
                usd_price = price_per_unit.get('USD')
                
                if usd_price and usd_price != '0.0000000000':
                    return float(usd_price)
            
            return None
            
        except (ValueError, TypeError) as e:
            logger.debug(f"Error extracting hourly price: {e}")
            return None
    
    def _extract_monthly_price(self, term_data: Dict) -> Optional[float]:
        """Extract monthly price from term data"""
        
        try:
            price_dimensions = term_data.get('priceDimensions', {})
            
            for dimension_key, dimension_data in price_dimensions.items():
                price_per_unit = dimension_data.get('pricePerUnit', {})
                usd_price = price_per_unit.get('USD')
                
                if usd_price and usd_price != '0.0000000000':
                    return float(usd_price)
            
            return None
            
        except (ValueError, TypeError) as e:
            logger.debug(f"Error extracting monthly price: {e}")
            return None
    
    def _map_location_to_region(self, location: str) -> Optional[str]:
        """Map AWS location name to region code"""
        
        # Direct mapping
        if location in self.REGION_MAPPING:
            return self.REGION_MAPPING[location]
        
        # Try partial matching for variations
        for aws_location, region in self.REGION_MAPPING.items():
            if location.lower() in aws_location.lower() or aws_location.lower() in location.lower():
                return region
        
        # Log unknown locations for debugging
        if location and location != 'Any':
            logger.debug(f"Unknown location: {location}")
        
        return None
    
    def _normalize_os(self, operating_system: str) -> str:
        """Normalize operating system names"""
        
        os_lower = operating_system.lower()
        
        if 'linux' in os_lower:
            return 'Linux'
        elif 'windows' in os_lower:
            return 'Windows'
        elif 'rhel' in os_lower or 'red hat' in os_lower:
            return 'RHEL'
        elif 'suse' in os_lower:
            return 'SUSE'
        else:
            return operating_system
    
    def _map_term_length(self, lease_contract_length: str) -> Optional[str]:
        """Map lease contract length to standard term"""
        
        if '1yr' in lease_contract_length or '1 yr' in lease_contract_length:
            return '1yr'
        elif '3yr' in lease_contract_length or '3 yr' in lease_contract_length:
            return '3yr'
        else:
            return None
    
    def _map_payment_option(self, purchase_option: str) -> Optional[str]:
        """Map purchase option to standard payment option"""
        
        option_lower = purchase_option.lower()
        
        if 'no upfront' in option_lower:
            return 'No Upfront'
        elif 'partial upfront' in option_lower:
            return 'Partial Upfront'
        elif 'all upfront' in option_lower:
            return 'All Upfront'
        else:
            return None
    
    def get_parsing_stats(self) -> Dict:
        """Get parsing statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset parsing statistics"""
        self.stats = {
            'products_processed': 0,
            'pricing_records_created': 0,
            'errors': 0
        }
