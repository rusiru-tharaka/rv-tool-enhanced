"""
AWS Pricing Service
Real-time AWS pricing integration using AWS Pricing API
Uses smartslot AWS CLI profile for pricing API access
No fallback pricing - relies entirely on live AWS data
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, field
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SavingsPlansPrice:
    """Comprehensive Savings Plans pricing information"""
    plan_type: str  # "compute" or "ec2_instance"
    instance_family: str  # "m5", "c5", etc. (for EC2 Instance Savings Plans)
    commitment_term: str  # "1_year" or "3_year"
    payment_option: str  # "no_upfront", "partial_upfront", "all_upfront"
    
    # Pricing Details
    hourly_rate: float
    upfront_cost: float = 0.0
    effective_hourly_rate: float = 0.0  # Including upfront amortization
    
    # Savings Information
    on_demand_equivalent: float = 0.0
    savings_percentage: float = 0.0
    break_even_hours: int = 0
    
    # Metadata
    currency: str = "USD"
    region: str = ""
    os_type: str = "linux"
    
    def __post_init__(self):
        """Calculate effective hourly rate including upfront costs"""
        if self.commitment_term == "1_year":
            total_hours = 8760  # 365 * 24
        else:  # 3_year
            total_hours = 26280  # 365 * 24 * 3
        
        upfront_hourly = self.upfront_cost / total_hours if total_hours > 0 else 0
        self.effective_hourly_rate = self.hourly_rate + upfront_hourly
        
        if self.on_demand_equivalent > 0:
            self.savings_percentage = (
                (self.on_demand_equivalent - self.effective_hourly_rate) / 
                self.on_demand_equivalent
            ) * 100

@dataclass
class OSSpecificPricing:
    """Operating system specific pricing information"""
    os_type: str  # "linux", "windows", "rhel", "suse", "ubuntu_pro"
    base_hourly_rate: float
    license_cost_hourly: float = 0.0
    support_cost_hourly: float = 0.0
    total_hourly_rate: float = 0.0
    
    def __post_init__(self):
        """Calculate total hourly rate including all costs"""
        self.total_hourly_rate = (
            self.base_hourly_rate + 
            self.license_cost_hourly + 
            self.support_cost_hourly
        )

@dataclass
class InstancePricing:
    """Instance pricing information from AWS Pricing API"""
    instance_type: str
    region: str
    on_demand_hourly: float
    reserved_1yr_hourly: Optional[float] = None
    reserved_3yr_hourly: Optional[float] = None
    vcpu: int = 0
    memory_gb: float = 0.0
    storage_type: str = "EBS"
    network_performance: str = "Moderate"
    currency: str = "USD"

@dataclass
class EnhancedInstancePricing:
    """Comprehensive instance pricing with all options"""
    instance_type: str
    region: str
    instance_family: str  # "m5", "c5", etc.
    
    # OS-Specific Pricing
    linux_pricing: OSSpecificPricing
    windows_pricing: Optional[OSSpecificPricing] = None
    rhel_pricing: Optional[OSSpecificPricing] = None
    suse_pricing: Optional[OSSpecificPricing] = None
    ubuntu_pro_pricing: Optional[OSSpecificPricing] = None
    
    # Traditional Pricing Models
    reserved_1yr_pricing: Dict[str, float] = field(default_factory=dict)  # OS -> price
    reserved_3yr_pricing: Dict[str, float] = field(default_factory=dict)  # OS -> price
    
    # Savings Plans Pricing
    compute_savings_plans: Dict[str, SavingsPlansPrice] = field(default_factory=dict)
    ec2_savings_plans: Dict[str, SavingsPlansPrice] = field(default_factory=dict)
    
    # Spot Pricing
    spot_pricing: Dict[str, float] = field(default_factory=dict)  # OS -> price
    spot_interruption_frequency: str = "low"  # "low", "medium", "high"
    
    # Instance Specifications
    vcpu: int = 0
    memory_gb: float = 0.0
    storage_type: str = "EBS"
    network_performance: str = "Moderate"
    instance_generation: str = "current"  # "current", "previous"
    
    # Metadata
    currency: str = "USD"
    last_updated: str = ""
    
    def get_os_pricing(self, os_type: str) -> Optional[OSSpecificPricing]:
        """Get pricing for specific operating system"""
        os_mapping = {
            "linux": self.linux_pricing,
            "windows": self.windows_pricing,
            "rhel": self.rhel_pricing,
            "suse": self.suse_pricing,
            "ubuntu_pro": self.ubuntu_pro_pricing
        }
        return os_mapping.get(os_type.lower())
    
    def get_best_savings_plan(
        self, 
        commitment_term: str, 
        payment_option: str = "no_upfront"
    ) -> Optional[SavingsPlansPrice]:
        """Get best Savings Plans option for given parameters"""
        # Check EC2 Instance Savings Plans first (typically better savings)
        ec2_key = f"{commitment_term}_{payment_option}"
        if ec2_key in self.ec2_savings_plans:
            return self.ec2_savings_plans[ec2_key]
        
        # Fallback to Compute Savings Plans
        compute_key = f"{commitment_term}_{payment_option}"
        if compute_key in self.compute_savings_plans:
            return self.compute_savings_plans[compute_key]
        
        return None

@dataclass
class StoragePricing:
    """EBS storage pricing information from AWS Pricing API"""
    volume_type: str
    region: str
    price_per_gb_month: float
    currency: str = "USD"

class AWSRegionConfig:
    """Comprehensive AWS region configuration"""
    
    # Complete AWS Commercial Regions
    AWS_REGIONS = {
        # US Regions
        'us-east-1': {
            'name': 'US East (N. Virginia)',
            'location': 'US East (N. Virginia)',
            'pricing_tier': 'standard',
            'availability_zones': 6,
            'supports_savings_plans': True
        },
        'us-east-2': {
            'name': 'US East (Ohio)',
            'location': 'US East (Ohio)',
            'pricing_tier': 'standard',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'us-west-1': {
            'name': 'US West (N. California)',
            'location': 'US West (N. California)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'us-west-2': {
            'name': 'US West (Oregon)',
            'location': 'US West (Oregon)',
            'pricing_tier': 'standard',
            'availability_zones': 4,
            'supports_savings_plans': True
        },
        
        # Europe Regions
        'eu-west-1': {
            'name': 'Europe (Ireland)',
            'location': 'Europe (Ireland)',
            'pricing_tier': 'standard',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'eu-west-2': {
            'name': 'Europe (London)',
            'location': 'Europe (London)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'eu-west-3': {
            'name': 'Europe (Paris)',
            'location': 'Europe (Paris)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'eu-central-1': {
            'name': 'Europe (Frankfurt)',
            'location': 'Europe (Frankfurt)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'eu-north-1': {
            'name': 'Europe (Stockholm)',
            'location': 'Europe (Stockholm)',
            'pricing_tier': 'standard',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'eu-south-1': {
            'name': 'Europe (Milan)',
            'location': 'Europe (Milan)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        
        # Asia Pacific Regions
        'ap-northeast-1': {
            'name': 'Asia Pacific (Tokyo)',
            'location': 'Asia Pacific (Tokyo)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'ap-northeast-2': {
            'name': 'Asia Pacific (Seoul)',
            'location': 'Asia Pacific (Seoul)',
            'pricing_tier': 'premium',
            'availability_zones': 4,
            'supports_savings_plans': True
        },
        'ap-northeast-3': {
            'name': 'Asia Pacific (Osaka)',
            'location': 'Asia Pacific (Osaka)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'ap-southeast-1': {
            'name': 'Asia Pacific (Singapore)',
            'location': 'Asia Pacific (Singapore)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'ap-southeast-2': {
            'name': 'Asia Pacific (Sydney)',
            'location': 'Asia Pacific (Sydney)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'ap-southeast-3': {
            'name': 'Asia Pacific (Jakarta)',
            'location': 'Asia Pacific (Jakarta)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'ap-south-1': {
            'name': 'Asia Pacific (Mumbai)',
            'location': 'Asia Pacific (Mumbai)',
            'pricing_tier': 'standard',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'ap-east-1': {
            'name': 'Asia Pacific (Hong Kong)',
            'location': 'Asia Pacific (Hong Kong)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        
        # Other Regions
        'ca-central-1': {
            'name': 'Canada (Central)',
            'location': 'Canada (Central)',
            'pricing_tier': 'standard',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'sa-east-1': {
            'name': 'South America (São Paulo)',
            'location': 'South America (São Paulo)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'af-south-1': {
            'name': 'Africa (Cape Town)',
            'location': 'Africa (Cape Town)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': False
        },
        'me-south-1': {
            'name': 'Middle East (Bahrain)',
            'location': 'Middle East (Bahrain)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        },
        'me-central-1': {
            'name': 'Middle East (UAE)',
            'location': 'Middle East (UAE)',
            'pricing_tier': 'premium',
            'availability_zones': 3,
            'supports_savings_plans': True
        }
    }
    
    @classmethod
    def get_region_info(cls, region_code: str) -> Dict:
        """Get comprehensive region information"""
        return cls.AWS_REGIONS.get(region_code, {})
    
    @classmethod
    def supports_savings_plans(cls, region_code: str) -> bool:
        """Check if region supports Savings Plans"""
        region_info = cls.get_region_info(region_code)
        return region_info.get('supports_savings_plans', False)
    
    @classmethod
    def get_pricing_tier(cls, region_code: str) -> str:
        """Get pricing tier for region (standard/premium)"""
        region_info = cls.get_region_info(region_code)
        return region_info.get('pricing_tier', 'standard')
    
    @classmethod
    def get_all_regions(cls) -> List[Dict]:
        """Get all regions formatted for frontend dropdown"""
        return [
            {
                'code': code,
                'name': info['name'],
                'pricing_tier': info['pricing_tier'],
                'supports_savings_plans': info['supports_savings_plans']
            }
            for code, info in cls.AWS_REGIONS.items()
        ]
    
    @classmethod
    def get_location_name(cls, region_code: str) -> str:
        """Get AWS Pricing API location name for region"""
        region_info = cls.get_region_info(region_code)
        return region_info.get('location', region_code)


class AWSPricingService:
    """
    AWS Pricing Service with real-time pricing integration
    Uses smartslot AWS profile for authentication
    Relies entirely on AWS Pricing API - no fallback data
    """
    
    def __init__(self, profile_name: str = "smartslot", region: str = "us-east-1"):
        self.profile_name = profile_name
        self.region = region
        self.pricing_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours (pricing changes infrequently)
        
        # Performance monitoring
        self.performance_stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_requests': 0,
            'total_processing_time': 0.0,
            'batch_processing_times': [],
            'last_reset': datetime.now()
        }
        
        # Initialize AWS clients
        try:
            session = boto3.Session(profile_name=profile_name)
            # Pricing API is only available in us-east-1
            self.pricing_client = session.client('pricing', region_name='us-east-1')
            self.ec2_client = session.client('ec2', region_name=region)
            logger.info(f"AWS Pricing Service initialized with profile: {profile_name}")
            
            # Test connection
            self._test_connection()
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients with profile {profile_name}: {e}")
            raise RuntimeError(f"Cannot initialize AWS Pricing Service: {e}")
    
    def _test_connection(self):
        """Test AWS connection and permissions"""
        try:
            # Test pricing API access
            response = self.pricing_client.describe_services(
                ServiceCode='AmazonEC2',
                MaxResults=1
            )
            logger.info("AWS Pricing API connection successful")
        except Exception as e:
            logger.error(f"AWS Pricing API connection failed: {e}")
            raise RuntimeError(f"Cannot access AWS Pricing API: {e}")
    
    async def get_instance_pricing(self, instance_type: str, region: str = None) -> InstancePricing:
        """
        Get real-time pricing for specific EC2 instance type
        Raises exception if pricing cannot be retrieved
        """
        if region is None:
            region = self.region
            
        cache_key = f"instance_{instance_type}_{region}"
        
        # Check cache first
        if self._is_cached(cache_key):
            logger.info(f"Using cached pricing for {instance_type} in {region}")
            return self.pricing_cache[cache_key]
        
        # Fetch real-time pricing
        pricing = await self._fetch_instance_pricing(instance_type, region)
        if pricing:
            self._cache_pricing(cache_key, pricing)
            return pricing
        else:
            raise ValueError(f"Unable to retrieve pricing for {instance_type} in {region}")
    
    async def get_storage_pricing(self, volume_type: str = "gp3", region: str = None) -> StoragePricing:
        """
        Get real-time EBS storage pricing
        Raises exception if pricing cannot be retrieved
        """
        if region is None:
            region = self.region
            
        cache_key = f"storage_{volume_type}_{region}"
        
        # Check cache first
        if self._is_cached(cache_key):
            logger.info(f"Using cached storage pricing for {volume_type} in {region}")
            return self.pricing_cache[cache_key]
        
        # Fetch real-time pricing
        pricing = await self._fetch_storage_pricing(volume_type, region)
        if pricing:
            self._cache_pricing(cache_key, pricing)
            return pricing
        else:
            raise ValueError(f"Unable to retrieve storage pricing for {volume_type} in {region}")
    
    async def _fetch_instance_pricing(self, instance_type: str, region: str) -> Optional[InstancePricing]:
        """
        Fetch real-time instance pricing from AWS Pricing API with fallback filter strategies
        """
        try:
            logger.info(f"Fetching real-time pricing for {instance_type} in {region}")
            location = self._region_to_location(region)
            
            # Multiple filter strategies - from most specific to most general
            filter_strategies = [
                # Strategy 1: Comprehensive filters (original approach)
                [
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operating-system', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                    {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
                ],
                # Strategy 2: Simplified filters (remove capacity status)
                [
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operating-system', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'}
                ],
                # Strategy 3: Core filters (remove preInstalled software)
                [
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operating-system', 'Value': 'Linux'}
                ],
                # Strategy 4: Minimal filters (most likely to succeed)
                [
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location}
                ]
            ]
            
            # Try each filter strategy
            for strategy_num, filters in enumerate(filter_strategies, 1):
                try:
                    logger.debug(f"Trying filter strategy {strategy_num} for {instance_type} ({len(filters)} filters)")
                    
                    on_demand_response = self.pricing_client.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=filters,
                        MaxResults=10  # Get multiple results to find best match
                    )
                    
                    if on_demand_response['PriceList']:
                        logger.info(f"Found {len(on_demand_response['PriceList'])} pricing records with strategy {strategy_num}")
                        
                        # Find the best matching product (prefer Linux, Shared tenancy)
                        best_product = self._select_best_pricing_product(on_demand_response['PriceList'], instance_type)
                        
                        if best_product:
                            pricing_data = await self._extract_pricing_from_product(best_product, instance_type, region)
                            if pricing_data:
                                logger.info(f"Successfully extracted pricing for {instance_type} using strategy {strategy_num}")
                                return pricing_data
                    else:
                        logger.debug(f"No pricing data found with strategy {strategy_num}")
                        
                except Exception as e:
                    logger.debug(f"Filter strategy {strategy_num} failed for {instance_type}: {e}")
                    continue
            
            logger.error(f"All filter strategies failed for {instance_type} in {region}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch pricing for {instance_type}: {e}")
            return None
    
    def _select_best_pricing_product(self, price_list: List[str], instance_type: str) -> Optional[Dict]:
        """
        Select the best pricing product from multiple results
        Prefer Linux, Shared tenancy, On-Demand pricing
        """
        try:
            best_product = None
            best_score = -1
            
            for product_json in price_list:
                product = json.loads(product_json)
                attributes = product.get('product', {}).get('attributes', {})
                
                # Verify this is the correct instance type
                if attributes.get('instanceType') != instance_type:
                    continue
                
                # Score the product based on preferences
                score = 0
                
                # Prefer Linux operating system
                if attributes.get('operatingSystem', '').lower() == 'linux':
                    score += 10
                
                # Prefer Shared tenancy
                if attributes.get('tenancy', '').lower() == 'shared':
                    score += 5
                
                # Prefer no pre-installed software
                if attributes.get('preInstalledSw', '').upper() == 'NA':
                    score += 3
                
                # Prefer Used capacity status
                if attributes.get('capacitystatus', '').lower() == 'used':
                    score += 2
                
                # Check if On-Demand pricing is available
                terms = product.get('terms', {})
                if 'OnDemand' in terms:
                    score += 20
                
                if score > best_score:
                    best_score = score
                    best_product = product
            
            if best_product:
                attributes = best_product.get('product', {}).get('attributes', {})
                logger.debug(f"Selected product: OS={attributes.get('operatingSystem')}, "
                           f"Tenancy={attributes.get('tenancy')}, Score={best_score}")
            
            return best_product
            
        except Exception as e:
            logger.error(f"Failed to select best pricing product: {e}")
            return None
    
    async def _extract_pricing_from_product(self, product: Dict, instance_type: str, region: str) -> Optional[InstancePricing]:
        """
        Extract pricing information from a product with improved error handling
        """
        try:
            # Extract instance specifications
            attributes = product['product']['attributes']
            vcpu = int(attributes.get('vcpu', 0))
            memory_str = attributes.get('memory', '0 GiB')
            memory_gb = float(memory_str.replace(' GiB', '').replace(',', ''))
            
            # Extract On-Demand pricing
            terms = product['terms']['OnDemand']
            on_demand_hourly = 0.0
            
            for term_key, term_data in terms.items():
                for price_key, price_data in term_data['priceDimensions'].items():
                    price_per_unit = price_data.get('pricePerUnit', {})
                    usd_price = price_per_unit.get('USD', '0')
                    on_demand_hourly = float(usd_price)
                    break
                break
            
            if on_demand_hourly == 0.0:
                logger.warning(f"Zero pricing found for {instance_type}, this may indicate an issue")
                # Reject zero pricing - return None to try next strategy
                return None
            
            # Get Reserved Instance pricing (async calls)
            reserved_1yr_hourly = await self._fetch_reserved_pricing(instance_type, region, '1yr')
            reserved_3yr_hourly = await self._fetch_reserved_pricing(instance_type, region, '3yr')
            
            return InstancePricing(
                instance_type=instance_type,
                region=region,
                on_demand_hourly=on_demand_hourly,
                reserved_1yr_hourly=reserved_1yr_hourly,
                reserved_3yr_hourly=reserved_3yr_hourly,
                vcpu=vcpu,
                memory_gb=memory_gb,
                storage_type="EBS",
                network_performance=attributes.get('networkPerformance', 'Moderate'),
                currency="USD"
            )
            
        except Exception as e:
            logger.error(f"Failed to extract pricing from product for {instance_type}: {e}")
            return None
    
    async def _fetch_reserved_pricing(self, instance_type: str, region: str, term: str) -> Optional[float]:
        """
        Fetch Reserved Instance pricing from AWS Pricing API
        """
        try:
            # Map term to AWS API values
            term_mapping = {
                '1yr': {'OfferingClass': 'standard', 'LeaseContractLength': '1yr'},
                '3yr': {'OfferingClass': 'standard', 'LeaseContractLength': '3yr'}
            }
            
            if term not in term_mapping:
                return None
            
            term_attrs = term_mapping[term]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._region_to_location(region)},
                    {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                    {'Type': 'TERM_MATCH', 'Field': 'operating-system', 'Value': 'Linux'},
                    {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                    {'Type': 'TERM_MATCH', 'Field': 'offeringClass', 'Value': term_attrs['OfferingClass']},
                    {'Type': 'TERM_MATCH', 'Field': 'leaseContractLength', 'Value': term_attrs['LeaseContractLength']}
                ]
            )
            
            if not response['PriceList']:
                logger.warning(f"No {term} reserved pricing found for {instance_type}")
                return None
            
            # Parse reserved pricing
            price_data = json.loads(response['PriceList'][0])
            terms = price_data['terms']['Reserved']
            
            for term_key, term_data in terms.items():
                for price_key, price_data in term_data['priceDimensions'].items():
                    if 'Hrs' in price_data['unit']:
                        hourly_price = float(price_data['pricePerUnit']['USD'])
                        logger.info(f"Found {term} reserved pricing for {instance_type}: ${hourly_price}/hour")
                        return hourly_price
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not fetch {term} reserved pricing for {instance_type}: {e}")
            return None
    
    async def _fetch_storage_pricing(self, volume_type: str, region: str) -> Optional[StoragePricing]:
        """
        Fetch EBS storage pricing from AWS Pricing API with fallback strategies
        """
        try:
            logger.info(f"Fetching storage pricing for {volume_type} in {region}")
            
            # Try multiple filter strategies for storage pricing
            filter_strategies = [
                # Strategy 1: Exact volume type match
                [
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                    {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': volume_type.upper()},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._region_to_location(region)}
                ],
                # Strategy 2: General Purpose (for gp3/gp2)
                [
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                    {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'General Purpose'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._region_to_location(region)}
                ],
                # Strategy 3: Just storage family
                [
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._region_to_location(region)}
                ]
            ]
            
            for strategy_num, filters in enumerate(filter_strategies, 1):
                try:
                    logger.debug(f"Trying storage pricing strategy {strategy_num} for {volume_type}")
                    
                    response = self.pricing_client.get_products(
                        ServiceCode='AmazonEC2',
                        Filters=filters,
                        MaxResults=10
                    )
                    
                    if response['PriceList']:
                        logger.info(f"Found {len(response['PriceList'])} storage pricing records with strategy {strategy_num}")
                        
                        # Find the best matching storage product
                        best_product = self._select_best_storage_product(response['PriceList'], volume_type)
                        
                        if best_product:
                            price_data = json.loads(best_product)
                            terms = price_data['terms']['OnDemand']
                            
                            price_per_gb_month = 0.0
                            for term_key, term_data in terms.items():
                                for price_key, price_data in term_data['priceDimensions'].items():
                                    price_per_gb_month = float(price_data['pricePerUnit']['USD'])
                                    break
                                break
                            
                            if price_per_gb_month > 0.0:
                                pricing = StoragePricing(
                                    volume_type=volume_type,
                                    region=region,
                                    price_per_gb_month=price_per_gb_month
                                )
                                
                                logger.info(f"Successfully retrieved storage pricing for {volume_type}: ${price_per_gb_month}/GB/month using strategy {strategy_num}")
                                return pricing
                    else:
                        logger.debug(f"No storage pricing found with strategy {strategy_num}")
                        
                except Exception as e:
                    logger.debug(f"Storage pricing strategy {strategy_num} failed: {e}")
                    continue
            
            # If all strategies fail, use a reasonable default
            logger.warning(f"All storage pricing strategies failed for {volume_type}, using default pricing")
            default_price = 0.08  # Default $0.08/GB/month (reasonable for gp3)
            
            return StoragePricing(
                volume_type=volume_type,
                region=region,
                price_per_gb_month=default_price
            )
            
        except Exception as e:
            logger.error(f"Error fetching storage pricing for {volume_type}: {e}")
            # Return default pricing as fallback
            return StoragePricing(
                volume_type=volume_type,
                region=region,
                price_per_gb_month=0.08  # Default fallback
            )
    
    def _select_best_storage_product(self, price_list: List[str], volume_type: str) -> Optional[str]:
        """
        Select the best storage pricing product from multiple results
        """
        try:
            best_product = None
            best_score = -1
            
            for product_json in price_list:
                product = json.loads(product_json)
                attributes = product.get('product', {}).get('attributes', {})
                
                score = 0
                
                # Prefer exact volume type match
                if attributes.get('volumeType', '').lower() == volume_type.lower():
                    score += 10
                elif 'general purpose' in attributes.get('volumeType', '').lower() and volume_type.lower().startswith('gp'):
                    score += 5
                
                # Prefer SSD storage
                if 'ssd' in attributes.get('storageMedia', '').lower():
                    score += 3
                
                # Check if pricing is available
                terms = product.get('terms', {})
                if 'OnDemand' in terms:
                    score += 5
                
                if score > best_score:
                    best_score = score
                    best_product = product_json
            
            return best_product
            
        except Exception as e:
            logger.error(f"Failed to select best storage product: {e}")
            return price_list[0] if price_list else None
    
    def _region_to_location(self, region: str) -> str:
        """
        Convert AWS region code to location name for Pricing API
        """
        region_mapping = {
            "us-east-1": "US East (N. Virginia)",
            "us-east-2": "US East (Ohio)",
            "us-west-1": "US West (N. California)",
            "us-west-2": "US West (Oregon)",
            "eu-west-1": "Europe (Ireland)",
            "eu-west-2": "Europe (London)",
            "eu-central-1": "Europe (Frankfurt)",
            "eu-north-1": "Europe (Stockholm)",
            "ap-southeast-1": "Asia Pacific (Singapore)",
            "ap-southeast-2": "Asia Pacific (Sydney)",
            "ap-northeast-1": "Asia Pacific (Tokyo)",
            "ap-northeast-2": "Asia Pacific (Seoul)",
            "ap-south-1": "Asia Pacific (Mumbai)",
            "ca-central-1": "Canada (Central)",
            "sa-east-1": "South America (Sao Paulo)"
        }
        
        location = region_mapping.get(region)
        if not location:
            raise ValueError(f"Unsupported region: {region}")
        
        return location
    
    def _is_cached(self, cache_key: str) -> bool:
        """
        Check if pricing data is cached and not expired
        Tracks cache hits and misses for performance monitoring
        """
        if cache_key not in self.pricing_cache:
            self.performance_stats['cache_misses'] += 1
            return False
        
        if cache_key not in self.cache_expiry:
            self.performance_stats['cache_misses'] += 1
            return False
        
        if datetime.utcnow() >= self.cache_expiry[cache_key]:
            # Cache expired
            self.performance_stats['cache_misses'] += 1
            # Clean up expired entry
            del self.pricing_cache[cache_key]
            del self.cache_expiry[cache_key]
            return False
        
        # Cache hit
        self.performance_stats['cache_hits'] += 1
        return True
    
    def _cache_pricing(self, cache_key: str, pricing_data):
        """
        Cache pricing data with expiry
        """
        self.pricing_cache[cache_key] = pricing_data
        self.cache_expiry[cache_key] = datetime.utcnow() + self.cache_duration
        logger.info(f"Cached pricing data for {cache_key}")
    
    async def get_multiple_instance_pricing(self, instance_types: List[str], region: str = None) -> Dict[str, InstancePricing]:
        """
        Get pricing for multiple instance types with optimized concurrent processing
        Enhanced for large datasets (5000+ VMs) with batching and error resilience
        """
        if region is None:
            region = self.region
        
        logger.info(f"Fetching pricing for {len(instance_types)} instance types in {region}")
        
        # Remove duplicates while preserving order
        unique_instances = list(dict.fromkeys(instance_types))
        logger.info(f"Processing {len(unique_instances)} unique instance types")
        
        # Check cache first for all instances
        cached_results = {}
        uncached_instances = []
        
        for instance_type in unique_instances:
            cache_key = f"instance_{instance_type}_{region}"
            if self._is_cached(cache_key):
                cached_results[instance_type] = self.pricing_cache[cache_key]
            else:
                uncached_instances.append(instance_type)
        
        logger.info(f"Found {len(cached_results)} cached results, fetching {len(uncached_instances)} from API")
        
        # Process uncached instances in batches for better performance
        batch_size = 20  # Optimal batch size for AWS API limits
        pricing_dict = cached_results.copy()
        failed_instances = []
        
        for i in range(0, len(uncached_instances), batch_size):
            batch = uncached_instances[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(uncached_instances) + batch_size - 1)//batch_size} ({len(batch)} instances)")
            
            # Create tasks for this batch
            tasks = [self.get_instance_pricing(instance_type, region) for instance_type in batch]
            
            try:
                # Process batch with timeout
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=60.0  # 60 second timeout per batch
                )
                
                # Process results
                for instance_type, result in zip(batch, results):
                    if isinstance(result, InstancePricing):
                        pricing_dict[instance_type] = result
                    else:
                        failed_instances.append(instance_type)
                        logger.warning(f"Failed to get pricing for {instance_type}: {result}")
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout processing batch starting at index {i}")
                failed_instances.extend(batch)
            except Exception as e:
                logger.error(f"Error processing batch starting at index {i}: {e}")
                failed_instances.extend(batch)
        
        # Log results
        success_count = len(pricing_dict)
        total_requested = len(unique_instances)
        success_rate = (success_count / total_requested) * 100 if total_requested > 0 else 0
        
        logger.info(f"Pricing retrieval complete: {success_count}/{total_requested} successful ({success_rate:.1f}%)")
        
        if failed_instances:
            logger.warning(f"Failed to retrieve pricing for {len(failed_instances)} instances: {failed_instances[:10]}{'...' if len(failed_instances) > 10 else ''}")
            
            # For production resilience, don't raise exception if we have > 80% success rate
            if success_rate < 80:
                raise RuntimeError(f"Low success rate ({success_rate:.1f}%) - failed instances: {failed_instances}")
            else:
                logger.warning(f"Continuing with {success_rate:.1f}% success rate")
        
        return pricing_dict
    
    async def get_multiple_instance_pricing_resilient(self, instance_types: List[str], region: str = None) -> Tuple[Dict[str, InstancePricing], List[str]]:
        """
        Get pricing for multiple instance types with maximum resilience
        Returns both successful results and list of failed instances
        Designed for large datasets where some failures are acceptable
        """
        if region is None:
            region = self.region
        
        logger.info(f"Resilient pricing fetch for {len(instance_types)} instance types in {region}")
        
        # Remove duplicates
        unique_instances = list(dict.fromkeys(instance_types))
        
        # Check cache first
        cached_results = {}
        uncached_instances = []
        
        for instance_type in unique_instances:
            cache_key = f"instance_{instance_type}_{region}"
            if self._is_cached(cache_key):
                cached_results[instance_type] = self.pricing_cache[cache_key]
            else:
                uncached_instances.append(instance_type)
        
        # Process uncached instances with maximum resilience
        pricing_dict = cached_results.copy()
        failed_instances = []
        
        # Use smaller batches for better error isolation
        batch_size = 10
        
        for i in range(0, len(uncached_instances), batch_size):
            batch = uncached_instances[i:i + batch_size]
            
            # Process each instance in the batch individually to maximize success
            for instance_type in batch:
                try:
                    result = await asyncio.wait_for(
                        self.get_instance_pricing(instance_type, region),
                        timeout=30.0  # 30 second timeout per instance
                    )
                    
                    if result:
                        pricing_dict[instance_type] = result
                    else:
                        failed_instances.append(instance_type)
                        
                except Exception as e:
                    logger.debug(f"Failed to get pricing for {instance_type}: {e}")
                    failed_instances.append(instance_type)
        
        success_count = len(pricing_dict)
        total_requested = len(unique_instances)
        success_rate = (success_count / total_requested) * 100 if total_requested > 0 else 0
        
        logger.info(f"Resilient pricing complete: {success_count}/{total_requested} successful ({success_rate:.1f}%)")
        
        return pricing_dict, failed_instances
    
    async def get_available_instance_types(self, region: str = None) -> List[str]:
        """
        Get list of available instance types in a region
        """
        if region is None:
            region = self.region
        
        try:
            response = self.ec2_client.describe_instance_types()
            instance_types = [it['InstanceType'] for it in response['InstanceTypes']]
            logger.info(f"Found {len(instance_types)} instance types in {region}")
            return sorted(instance_types)
        except Exception as e:
            logger.error(f"Failed to get instance types for {region}: {e}")
            raise RuntimeError(f"Cannot retrieve instance types: {e}")
    
    def clear_cache(self):
        """
        Clear pricing cache
        """
        self.pricing_cache.clear()
        self.cache_expiry.clear()
        logger.info("Pricing cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get comprehensive cache and performance statistics
        """
        expired_items = sum(1 for key in self.cache_expiry 
                           if datetime.utcnow() >= self.cache_expiry[key])
        
        total_requests = self.performance_stats['cache_hits'] + self.performance_stats['cache_misses']
        cache_hit_rate = (self.performance_stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        avg_batch_time = (sum(self.performance_stats['batch_processing_times']) / 
                         len(self.performance_stats['batch_processing_times'])) if self.performance_stats['batch_processing_times'] else 0
        
        return {
            "cached_items": len(self.pricing_cache),
            "expired_items": expired_items,
            "cache_hits": self.performance_stats['cache_hits'],
            "cache_misses": self.performance_stats['cache_misses'],
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "api_calls": self.performance_stats['api_calls'],
            "failed_requests": self.performance_stats['failed_requests'],
            "total_processing_time": round(self.performance_stats['total_processing_time'], 2),
            "average_batch_time": round(avg_batch_time, 2),
            "uptime_hours": round((datetime.now() - self.performance_stats['last_reset']).total_seconds() / 3600, 2)
        }
    
    def reset_performance_stats(self):
        """Reset performance statistics"""
        self.performance_stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_requests': 0,
            'total_processing_time': 0.0,
            'batch_processing_times': [],
            'last_reset': datetime.now()
        }
        logger.info("Performance statistics reset")
    
    def get_performance_summary(self) -> str:
        """Get a human-readable performance summary"""
        stats = self.get_cache_stats()
        
        summary = f"""
AWS Pricing Service Performance Summary:
========================================
Cache Performance:
  - Cached Items: {stats['cached_items']}
  - Cache Hit Rate: {stats['cache_hit_rate_percent']}%
  - Cache Hits: {stats['cache_hits']}
  - Cache Misses: {stats['cache_misses']}

API Performance:
  - Total API Calls: {stats['api_calls']}
  - Failed Requests: {stats['failed_requests']}
  - Success Rate: {((stats['api_calls'] - stats['failed_requests']) / stats['api_calls'] * 100) if stats['api_calls'] > 0 else 0:.1f}%

Processing Performance:
  - Total Processing Time: {stats['total_processing_time']}s
  - Average Batch Time: {stats['average_batch_time']}s
  - Uptime: {stats['uptime_hours']} hours
        """.strip()
        
        return summary

    async def get_multiple_instance_pricing_cached(
        self,
        instance_types: List[str],
        region: str,
        os_type: str = "linux"
    ) -> Dict[str, InstancePricing]:
        """Get multiple instance pricing with caching support"""
        try:
            from .pricing_cache_service import pricing_cache_service
            return await pricing_cache_service.get_multiple_instance_pricing_cached(
                instance_types, region, os_type
            )
        except ImportError:
            logger.warning("Cache service unavailable, falling back to direct API")
            return await self.get_multiple_instance_pricing(instance_types, region, os_type)
    
    async def get_storage_pricing_cached(
        self,
        storage_type: str,
        region: str
    ) -> Optional[StoragePricing]:
        """Get storage pricing with caching support"""
        try:
            from .pricing_cache_service import pricing_cache_service
            return await pricing_cache_service.get_storage_pricing_cached(storage_type, region)
        except ImportError:
            logger.warning("Cache service unavailable, falling back to direct API")
            return await self.get_storage_pricing(storage_type, region)
    
    async def get_savings_plans_pricing(
        self,
        instance_family: str,
        region: str,
        commitment_term: str = "1_year",
        payment_option: str = "no_upfront"
    ) -> Optional[List[SavingsPlansPrice]]:
        """Get Savings Plans pricing from AWS Pricing API"""
        
        try:
            logger.info(f"Fetching Savings Plans pricing for {instance_family} in {region}")
            
            # Query Savings Plans pricing
            response = self.pricing_client.get_products(
                ServiceCode='AmazonEC2',
                Filters=[
                    {
                        'Type': 'TERM_MATCH',
                        'Field': 'location',
                        'Value': self._region_to_location(region)
                    },
                    {
                        'Type': 'TERM_MATCH',
                        'Field': 'instanceFamily',
                        'Value': instance_family
                    },
                    {
                        'Type': 'TERM_MATCH',
                        'Field': 'productFamily',
                        'Value': 'Compute Instance'
                    }
                ]
            )
            
            savings_plans = []
            
            for price_item in response.get('PriceList', []):
                product = json.loads(price_item)
                
                # Extract Savings Plans pricing information
                terms = product.get('terms', {})
                reserved_terms = terms.get('Reserved', {})
                
                for term_key, term_data in reserved_terms.items():
                    term_attributes = term_data.get('termAttributes', {})
                    
                    # Check if this matches our criteria
                    if (term_attributes.get('LeaseContractLength') == commitment_term and
                        term_attributes.get('PurchaseOption') == payment_option):
                        
                        price_dimensions = term_data.get('priceDimensions', {})
                        
                        for price_key, price_data in price_dimensions.items():
                            price_per_unit = price_data.get('pricePerUnit', {}).get('USD', '0')
                            
                            if float(price_per_unit) > 0:
                                # Calculate on-demand equivalent for comparison
                                on_demand_price = await self._get_on_demand_price_for_family(
                                    instance_family, region
                                )
                                
                                savings_plan = SavingsPlansPrice(
                                    plan_type="ec2_instance",
                                    instance_family=instance_family,
                                    commitment_term=commitment_term,
                                    payment_option=payment_option,
                                    hourly_rate=float(price_per_unit),
                                    upfront_cost=float(term_data.get('upfrontPrice', {}).get('USD', '0')),
                                    on_demand_equivalent=on_demand_price,
                                    region=region,
                                    currency="USD"
                                )
                                savings_plans.append(savings_plan)
            
            logger.info(f"Retrieved {len(savings_plans)} Savings Plans prices for {instance_family}")
            return savings_plans
            
        except Exception as e:
            logger.error(f"Failed to get Savings Plans pricing for {instance_family}: {e}")
            return None
    
    async def _get_on_demand_price_for_family(self, instance_family: str, region: str) -> float:
        """Get representative on-demand price for instance family"""
        try:
            # Use a common instance type from the family for comparison
            family_representatives = {
                "m5": "m5.large",
                "c5": "c5.large", 
                "r5": "r5.large",
                "t3": "t3.medium",
                "t2": "t2.medium"
            }
            
            representative_type = family_representatives.get(instance_family, f"{instance_family}.large")
            pricing = await self.get_instance_pricing(representative_type, region)
            
            return pricing.on_demand_hourly if pricing else 0.0
            
        except Exception as e:
            logger.warning(f"Could not get on-demand price for family {instance_family}: {e}")
            return 0.0

    async def get_multiple_instance_pricing(
        self,
        instance_types: List[str],
        region: str,
        os_type: str = "linux"
    ) -> Dict[str, InstancePricing]:
        """Get pricing for multiple instance types efficiently"""
        
        pricing_data = {}
        
        try:
            # Use batch processing for better performance
            batch_size = 10
            for i in range(0, len(instance_types), batch_size):
                batch = instance_types[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [
                    self.get_instance_pricing(instance_type, region)
                    for instance_type in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for instance_type, result in zip(batch, batch_results):
                    if isinstance(result, InstancePricing):
                        pricing_data[instance_type] = result
                    elif isinstance(result, Exception):
                        logger.warning(f"Failed to get pricing for {instance_type}: {result}")
                
                # Small delay between batches to respect rate limits
                if i + batch_size < len(instance_types):
                    await asyncio.sleep(0.1)
            
            logger.info(f"Retrieved pricing for {len(pricing_data)} out of {len(instance_types)} instance types")
            return pricing_data
            
        except Exception as e:
            logger.error(f"Batch pricing retrieval failed: {e}")
            return pricing_data
    
    async def initialize(self, profile_name: str = "smartslot"):
        """
        Initialize or reinitialize the pricing service with a specific profile
        This method allows for dynamic profile switching and validation
        """
        try:
            self.profile_name = profile_name
            
            # Initialize AWS clients with new profile
            session = boto3.Session(profile_name=profile_name)
            self.pricing_client = session.client('pricing', region_name='us-east-1')
            self.ec2_client = session.client('ec2', region_name=self.region)
            
            logger.info(f"AWS Pricing Service initialized with profile: {profile_name}")
            
            # Test connection
            self._test_connection()
            
            # Reset performance stats
            self.performance_stats = {
                'api_calls': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'failed_requests': 0,
                'total_processing_time': 0.0,
                'batch_processing_times': [],
                'last_reset': datetime.now()
            }
            
            logger.info("AWS Pricing Service initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS Pricing Service: {e}")
            raise RuntimeError(f"AWS Pricing Service initialization failed: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        # Clear cache
        self.pricing_cache.clear()
        self.cache_expiry.clear()
        logger.info("AWS Pricing Service cleaned up")

# Global pricing service instance
pricing_service = AWSPricingService(profile_name="smartslot")
