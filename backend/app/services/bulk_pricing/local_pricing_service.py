"""
Local Pricing Service
Fast local pricing lookups using SQLite database
Replaces AWS Pricing API calls with local data
"""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
import time

from .database import PricingDatabase

logger = logging.getLogger(__name__)

@dataclass
class InstancePricing:
    """Instance pricing information (compatible with existing code)"""
    instance_type: str
    region: str
    on_demand_price_per_hour: float
    reserved_1yr_no_upfront: Optional[float] = None
    reserved_1yr_partial_upfront: Optional[float] = None
    reserved_1yr_all_upfront: Optional[float] = None
    reserved_3yr_no_upfront: Optional[float] = None
    reserved_3yr_partial_upfront: Optional[float] = None
    reserved_3yr_all_upfront: Optional[float] = None
    currency: str = "USD"
    last_updated: Optional[datetime] = None

@dataclass
class StoragePricing:
    """Storage pricing information (compatible with existing code)"""
    volume_type: str
    region: str
    price_per_gb_month: float
    currency: str = "USD"

class LocalPricingService:
    """Local pricing service using SQLite database"""
    
    def __init__(self, db_path: str = None):
        """Initialize local pricing service"""
        self.db = PricingDatabase(db_path)
        self.cache = {}  # In-memory cache for frequently accessed prices
        self.cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        
        logger.info("Local Pricing Service initialized")
    
    async def get_instance_pricing(self, instance_type: str, region: str = 'us-east-1') -> InstancePricing:
        """Get instance pricing (compatible with existing AWS pricing service)"""
        
        cache_key = f"ec2_{instance_type}_{region}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for {instance_type} in {region}")
                return cached_data
        
        start_time = time.time()
        
        # Get on-demand pricing
        on_demand_price = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='OnDemand'
        )
        
        if on_demand_price is None:
            logger.warning(f"No on-demand pricing found for {instance_type} in {region}")
            raise ValueError(f"Unable to retrieve pricing for {instance_type} in {region}")
        
        # Get reserved instance pricing
        reserved_1yr_no_upfront = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='Reserved',
            term_length='1yr',
            payment_option='No Upfront'
        )
        
        reserved_1yr_partial_upfront = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='Reserved',
            term_length='1yr',
            payment_option='Partial Upfront'
        )
        
        reserved_1yr_all_upfront = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='Reserved',
            term_length='1yr',
            payment_option='All Upfront'
        )
        
        reserved_3yr_no_upfront = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='Reserved',
            term_length='3yr',
            payment_option='No Upfront'
        )
        
        reserved_3yr_partial_upfront = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='Reserved',
            term_length='3yr',
            payment_option='Partial Upfront'
        )
        
        reserved_3yr_all_upfront = self.db.get_ec2_pricing(
            instance_type=instance_type,
            region=region,
            operating_system='Linux',
            tenancy='Shared',
            pricing_model='Reserved',
            term_length='3yr',
            payment_option='All Upfront'
        )
        
        # Create pricing object
        pricing = InstancePricing(
            instance_type=instance_type,
            region=region,
            on_demand_price_per_hour=on_demand_price,
            reserved_1yr_no_upfront=reserved_1yr_no_upfront,
            reserved_1yr_partial_upfront=reserved_1yr_partial_upfront,
            reserved_1yr_all_upfront=reserved_1yr_all_upfront,
            reserved_3yr_no_upfront=reserved_3yr_no_upfront,
            reserved_3yr_partial_upfront=reserved_3yr_partial_upfront,
            reserved_3yr_all_upfront=reserved_3yr_all_upfront,
            currency="USD",
            last_updated=datetime.now()
        )
        
        # Cache the result
        self.cache[cache_key] = (pricing, time.time())
        
        query_time = time.time() - start_time
        logger.debug(f"Retrieved pricing for {instance_type} in {region} in {query_time*1000:.1f}ms")
        
        return pricing
    
    async def get_storage_pricing(self, volume_type: str = 'gp3', region: str = 'us-east-1') -> StoragePricing:
        """Get storage pricing (compatible with existing AWS pricing service)"""
        
        cache_key = f"ebs_{volume_type}_{region}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for {volume_type} storage in {region}")
                return cached_data
        
        start_time = time.time()
        
        # Get storage pricing
        price_per_gb_month = self.db.get_ebs_pricing(volume_type=volume_type, region=region)
        
        if price_per_gb_month is None:
            logger.warning(f"No storage pricing found for {volume_type} in {region}")
            raise ValueError(f"Unable to retrieve storage pricing for {volume_type} in {region}")
        
        # Create storage pricing object
        pricing = StoragePricing(
            volume_type=volume_type,
            region=region,
            price_per_gb_month=price_per_gb_month,
            currency="USD"
        )
        
        # Cache the result
        self.cache[cache_key] = (pricing, time.time())
        
        query_time = time.time() - start_time
        logger.debug(f"Retrieved storage pricing for {volume_type} in {region} in {query_time*1000:.1f}ms")
        
        return pricing
    
    def get_available_instance_types(self, region: str = None) -> List[str]:
        """Get list of available instance types"""
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                if region:
                    cursor = conn.execute("""
                        SELECT DISTINCT instance_type 
                        FROM ec2_pricing 
                        WHERE region = ? 
                        ORDER BY instance_type
                    """, [region])
                else:
                    cursor = conn.execute("""
                        SELECT DISTINCT instance_type 
                        FROM ec2_pricing 
                        ORDER BY instance_type
                    """)
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting available instance types: {e}")
            return []
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions"""
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT region 
                    FROM ec2_pricing 
                    ORDER BY region
                """)
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting available regions: {e}")
            return []
    
    def get_pricing_summary(self, region: str = None) -> Dict:
        """Get pricing summary statistics"""
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                summary = {}
                
                # Instance type counts
                if region:
                    cursor = conn.execute("""
                        SELECT COUNT(DISTINCT instance_type) 
                        FROM ec2_pricing 
                        WHERE region = ?
                    """, [region])
                else:
                    cursor = conn.execute("""
                        SELECT COUNT(DISTINCT instance_type) 
                        FROM ec2_pricing
                    """)
                
                summary['instance_types'] = cursor.fetchone()[0]
                
                # Pricing model counts
                if region:
                    cursor = conn.execute("""
                        SELECT pricing_model, COUNT(*) 
                        FROM ec2_pricing 
                        WHERE region = ?
                        GROUP BY pricing_model
                    """, [region])
                else:
                    cursor = conn.execute("""
                        SELECT pricing_model, COUNT(*) 
                        FROM ec2_pricing 
                        GROUP BY pricing_model
                    """)
                
                summary['pricing_models'] = dict(cursor.fetchall())
                
                # Price ranges
                if region:
                    cursor = conn.execute("""
                        SELECT 
                            MIN(price_per_hour) as min_price,
                            MAX(price_per_hour) as max_price,
                            AVG(price_per_hour) as avg_price
                        FROM ec2_pricing 
                        WHERE region = ? AND pricing_model = 'OnDemand'
                    """, [region])
                else:
                    cursor = conn.execute("""
                        SELECT 
                            MIN(price_per_hour) as min_price,
                            MAX(price_per_hour) as max_price,
                            AVG(price_per_hour) as avg_price
                        FROM ec2_pricing 
                        WHERE pricing_model = 'OnDemand'
                    """)
                
                price_stats = cursor.fetchone()
                if price_stats:
                    summary['price_range'] = {
                        'min': float(price_stats[0]) if price_stats[0] else 0,
                        'max': float(price_stats[1]) if price_stats[1] else 0,
                        'avg': float(price_stats[2]) if price_stats[2] else 0
                    }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting pricing summary: {e}")
            return {}
    
    def health_check(self) -> Dict:
        """Perform health check on pricing service"""
        
        start_time = time.time()
        
        try:
            # Test database connection
            stats = self.db.get_database_stats()
            
            # Test sample pricing lookup
            sample_pricing = None
            try:
                # Try to get pricing for a common instance type
                sample_pricing = self.db.get_ec2_pricing('m5.large', 'us-east-1')
            except Exception as e:
                logger.warning(f"Sample pricing lookup failed: {e}")
            
            health_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time_ms': round(health_time * 1000, 2),
                'database_stats': stats,
                'sample_pricing_available': sample_pricing is not None,
                'cache_size': len(self.cache),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_cache(self):
        """Clear in-memory cache"""
        self.cache.clear()
        logger.info("Pricing cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for cache_key, (data, timestamp) in self.cache.items():
            if current_time - timestamp < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_ttl_seconds': self.cache_ttl
        }

# Create global instance (compatible with existing code)
local_pricing_service = LocalPricingService()
