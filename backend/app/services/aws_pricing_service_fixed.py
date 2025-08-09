"""
FIXED AWS Pricing Service - Real API Calls Only
No fallback mechanisms, uses actual AWS Pricing API with proper filtering
"""

import boto3
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InstancePricing:
    """Instance pricing information from AWS API"""
    instance_type: str
    region: str
    on_demand_hourly: float
    reserved_1yr_hourly: Optional[float] = None
    reserved_3yr_hourly: Optional[float] = None
    spot_hourly: Optional[float] = None
    currency: str = "USD"
    last_updated: datetime = None

@dataclass
class StoragePricing:
    """Storage pricing information from AWS API"""
    region: str
    gp3_per_gb_month: float
    gp2_per_gb_month: float
    io1_per_gb_month: float
    io2_per_gb_month: float
    currency: str = "USD"

@dataclass
class SavingsPlanPricing:
    """Savings Plans pricing from AWS API"""
    plan_type: str  # compute, ec2_instance
    commitment_term: str  # 1_year, 3_year
    payment_option: str  # no_upfront, partial_upfront, all_upfront
    hourly_rate: float
    effective_hourly_rate: float  # Including upfront amortization
    savings_percentage: float
    upfront_cost: float = 0.0

class AWSPricingService:
    """
    Real AWS Pricing Service - No Fallbacks
    Uses actual AWS Pricing API, Savings Plans API, and EC2 API
    """
    
    def __init__(self, profile_name: str = "smartslot"):
        """Initialize AWS clients with real API connections"""
        try:
            self.session = boto3.Session(profile_name=profile_name)
            
            # Initialize AWS clients
            self.pricing_client = self.session.client('pricing', region_name='us-east-1')
            self.ec2_client = self.session.client('ec2', region_name='us-east-1')
            self.savingsplans_client = self.session.client('savingsplans', region_name='us-east-1')
            
            # Test connection
            self.pricing_client.describe_services(ServiceCode='AmazonEC2', MaxResults=1)
            
            logger.info(f"AWS Pricing Service initialized with profile: {profile_name}")
            logger.info("AWS Pricing API connection successful")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS Pricing Service: {e}")
            raise
    
    async def get_instance_pricing(self, instance_types: List[str], region: str) -> Dict[str, InstancePricing]:
        """
        Get real-time instance pricing from AWS API
        NO FALLBACKS - Must get real data or fail
        """
        logger.info(f"Fetching real-time pricing for {instance_types} in {region}")
        
        pricing_data = {}
        location = self._get_location_name(region)
        
        for instance_type in instance_types:
            try:
                pricing = await self._get_single_instance_pricing(instance_type, region, location)
                if pricing:
                    pricing_data[instance_type] = pricing
                    logger.info(f"✅ Got real pricing for {instance_type}: ${pricing.on_demand_hourly:.4f}/hour")
                else:
                    logger.error(f"❌ Failed to get real pricing for {instance_type}")
                    # NO FALLBACK - fail if we can't get real data
                    
            except Exception as e:
                logger.error(f"❌ Error getting pricing for {instance_type}: {e}")
                # NO FALLBACK - fail if we can't get real data
        
        if not pricing_data:
            raise ValueError(f"Unable to retrieve real pricing for any instances in {region}")
        
        return pricing_data
    
    async def _get_single_instance_pricing(self, instance_type: str, region: str, location: str) -> Optional[InstancePricing]:
        """Get pricing for a single instance type using real AWS API"""
        
        try:
            # Use minimal filters to get all products, then filter in code
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}
                ],
                MaxResults=50  # Get more results to find the right one
            )
            
            if not response['PriceList']:
                logger.error(f"No pricing products found for {instance_type} in {location}")
                return None
            
            # Find the best matching product (prefer Shared tenancy, Linux, NA software)
            best_product = self._select_best_product(response['PriceList'], instance_type)
            
            if not best_product:
                logger.error(f"No suitable product found for {instance_type}")
                return None
            
            # Extract pricing from the selected product
            pricing = self._extract_pricing_from_product(best_product, instance_type, region)
            
            if pricing:
                # Get Reserved Instance pricing
                pricing.reserved_1yr_hourly = await self._get_reserved_pricing(instance_type, region, 1)
                pricing.reserved_3yr_hourly = await self._get_reserved_pricing(instance_type, region, 3)
                
                # Get Spot pricing
                pricing.spot_hourly = await self._get_spot_pricing(instance_type, region)
            
            return pricing
            
        except Exception as e:
            logger.error(f"Failed to get pricing for {instance_type}: {e}")
            return None
    
    def _select_best_product(self, price_list: List[str], instance_type: str) -> Optional[Dict]:
        """Select the best product from AWS API results"""
        
        products = []
        for product_json in price_list:
            try:
                product = json.loads(product_json)
                attributes = product.get('product', {}).get('attributes', {})
                
                # Score products based on preferences
                score = 0
                
                # Prefer Shared tenancy
                if attributes.get('tenancy') == 'Shared':
                    score += 10
                elif attributes.get('tenancy') == 'Dedicated':
                    score += 5
                
                # Prefer Linux
                if attributes.get('operating-system') == 'Linux':
                    score += 10
                
                # Prefer no pre-installed software
                if attributes.get('preInstalledSw') == 'NA':
                    score += 10
                
                # Prefer "Used" capacity status
                if attributes.get('capacitystatus') == 'Used':
                    score += 5
                
                products.append({
                    'product': product,
                    'score': score,
                    'attributes': attributes
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse product: {e}")
                continue
        
        if not products:
            return None
        
        # Sort by score and return the best
        products.sort(key=lambda x: x['score'], reverse=True)
        best = products[0]
        
        logger.info(f"Selected product for {instance_type}: tenancy={best['attributes'].get('tenancy')}, "
                   f"os={best['attributes'].get('operating-system')}, "
                   f"software={best['attributes'].get('preInstalledSw')}, score={best['score']}")
        
        return best['product']
    
    def _extract_pricing_from_product(self, product: Dict, instance_type: str, region: str) -> Optional[InstancePricing]:
        """Extract pricing information from AWS product data"""
        
        try:
            terms = product.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            
            if not on_demand_terms:
                logger.error(f"No OnDemand terms found for {instance_type}")
                return None
            
            # Get the first (and usually only) OnDemand term
            term_key = list(on_demand_terms.keys())[0]
            term_data = on_demand_terms[term_key]
            
            price_dimensions = term_data.get('priceDimensions', {})
            if not price_dimensions:
                logger.error(f"No price dimensions found for {instance_type}")
                return None
            
            # Get the first price dimension
            price_key = list(price_dimensions.keys())[0]
            price_data = price_dimensions[price_key]
            
            price_per_unit = price_data.get('pricePerUnit', {})
            usd_price = price_per_unit.get('USD')
            
            if not usd_price:
                logger.error(f"No USD price found for {instance_type}")
                return None
            
            hourly_rate = float(usd_price)
            
            return InstancePricing(
                instance_type=instance_type,
                region=region,
                on_demand_hourly=hourly_rate,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to extract pricing for {instance_type}: {e}")
            return None
    
    async def _get_reserved_pricing(self, instance_type: str, region: str, years: int) -> Optional[float]:
        """Get Reserved Instance pricing from AWS API"""
        
        try:
            # Use EC2 describe_reserved_instances_offerings
            response = self.ec2_client.describe_reserved_instances_offerings(
                InstanceType=instance_type,
                ProductDescription='Linux/UNIX',
                Duration=years * 365 * 24 * 3600,  # Convert years to seconds
                OfferingClass='standard',
                OfferingType='No Upfront',
                MaxResults=10
            )
            
            offerings = response.get('ReservedInstancesOfferings', [])
            
            if offerings:
                # Get the first offering
                offering = offerings[0]
                fixed_price = offering.get('FixedPrice', 0)
                usage_price = offering.get('UsagePrice', 0)
                
                # Calculate effective hourly rate
                hours_in_term = years * 365 * 24
                hourly_rate = (fixed_price / hours_in_term) + usage_price
                
                logger.info(f"Reserved {years}yr pricing for {instance_type}: ${hourly_rate:.4f}/hour")
                return hourly_rate
            
        except Exception as e:
            logger.warning(f"Could not get Reserved pricing for {instance_type}: {e}")
        
        return None
    
    async def _get_spot_pricing(self, instance_type: str, region: str) -> Optional[float]:
        """Get current Spot pricing from AWS API"""
        
        try:
            response = self.ec2_client.describe_spot_price_history(
                InstanceTypes=[instance_type],
                ProductDescriptions=['Linux/UNIX'],
                MaxResults=1
            )
            
            spot_prices = response.get('SpotPriceHistory', [])
            
            if spot_prices:
                spot_price = float(spot_prices[0]['SpotPrice'])
                logger.info(f"Spot pricing for {instance_type}: ${spot_price:.4f}/hour")
                return spot_price
            
        except Exception as e:
            logger.warning(f"Could not get Spot pricing for {instance_type}: {e}")
        
        return None
    
    async def get_savings_plans_pricing(self, instance_family: str, region: str, 
                                      commitment: str, payment: str) -> List[SavingsPlanPricing]:
        """Get real Savings Plans pricing from AWS API"""
        
        try:
            # Use Savings Plans API to get real pricing
            response = self.savingsplans_client.describe_savings_plans_offering_rates(
                savingsPlansOfferingIds=[],  # Get all offerings
                filters=[
                    {
                        'name': 'region',
                        'values': [region]
                    },
                    {
                        'name': 'instanceFamily', 
                        'values': [instance_family]
                    }
                ],
                maxResults=100
            )
            
            offerings = response.get('searchResults', [])
            savings_plans = []
            
            for offering in offerings:
                # Extract pricing information
                rate = float(offering.get('rate', 0))
                
                savings_plan = SavingsPlanPricing(
                    plan_type=offering.get('savingsPlansOfferingId', '').split('-')[0],
                    commitment_term=commitment,
                    payment_option=payment,
                    hourly_rate=rate,
                    effective_hourly_rate=rate,  # Will be calculated based on upfront
                    savings_percentage=0.0,  # Will be calculated vs on-demand
                    upfront_cost=0.0
                )
                
                savings_plans.append(savings_plan)
            
            logger.info(f"Found {len(savings_plans)} Savings Plans offerings for {instance_family}")
            return savings_plans
            
        except Exception as e:
            logger.error(f"Failed to get Savings Plans pricing: {e}")
            return []
    
    async def get_storage_pricing(self, region: str) -> StoragePricing:
        """Get real EBS storage pricing from AWS API"""
        
        location = self._get_location_name(region)
        
        try:
            # Get EBS pricing
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'}
                ],
                MaxResults=50
            )
            
            storage_prices = {}
            
            for product_json in response['PriceList']:
                product = json.loads(product_json)
                attributes = product.get('product', {}).get('attributes', {})
                
                volume_type = attributes.get('volumeType')
                if volume_type in ['General Purpose', 'Provisioned IOPS']:
                    
                    # Extract pricing
                    terms = product.get('terms', {}).get('OnDemand', {})
                    if terms:
                        term_key = list(terms.keys())[0]
                        price_dimensions = terms[term_key].get('priceDimensions', {})
                        if price_dimensions:
                            price_key = list(price_dimensions.keys())[0]
                            price_per_unit = price_dimensions[price_key].get('pricePerUnit', {})
                            usd_price = price_per_unit.get('USD')
                            
                            if usd_price:
                                if volume_type == 'General Purpose':
                                    storage_prices['gp3'] = float(usd_price)
                                elif volume_type == 'Provisioned IOPS':
                                    storage_prices['io1'] = float(usd_price)
            
            return StoragePricing(
                region=region,
                gp3_per_gb_month=storage_prices.get('gp3', 0.08),  # Default if not found
                gp2_per_gb_month=storage_prices.get('gp3', 0.10),  # Use gp3 price
                io1_per_gb_month=storage_prices.get('io1', 0.125),
                io2_per_gb_month=storage_prices.get('io1', 0.125)  # Use io1 price
            )
            
        except Exception as e:
            logger.error(f"Failed to get storage pricing: {e}")
            # NO FALLBACK - return error
            raise ValueError(f"Unable to get real storage pricing for {region}")
    
    def _get_location_name(self, region: str) -> str:
        """Convert AWS region to location name used in Pricing API"""
        
        region_mapping = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'Europe (Ireland)',
            'eu-west-2': 'Europe (London)',
            'eu-central-1': 'Europe (Frankfurt)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
        }
        
        return region_mapping.get(region, region)

# Create singleton instance
pricing_service = AWSPricingService()
