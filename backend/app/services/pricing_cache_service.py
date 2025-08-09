"""
Pricing Cache Service
High-performance caching layer for AWS pricing data
Implements intelligent caching strategies with TTL and invalidation
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import redis
from redis.asyncio import Redis
import pickle

from .aws_pricing_service import (
    InstancePricing, 
    StoragePricing, 
    EnhancedInstancePricing,
    SavingsPlansPrice,
    pricing_service
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    cache_key: str = ""
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_stale(self, stale_threshold_minutes: int = 30) -> bool:
        """Check if cache entry is stale (old but not expired)"""
        stale_time = datetime.utcnow() - timedelta(minutes=stale_threshold_minutes)
        return self.created_at < stale_time

class PricingCacheService:
    """
    High-performance pricing cache service with intelligent caching strategies
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[Redis] = None
        self.local_cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "errors": 0
        }
        
        # Cache configuration
        self.default_ttl_hours = 4  # 4 hours default TTL
        self.max_local_cache_size = 1000
        self.stale_threshold_minutes = 30
        
        logger.info("Pricing Cache Service initialized")
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = Redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.warning(f"Redis connection failed, using local cache only: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate consistent cache key from parameters"""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        
        # Create hash for long parameter strings
        if len(param_string) > 100:
            param_hash = hashlib.md5(param_string.encode()).hexdigest()
            return f"{prefix}:{param_hash}"
        
        return f"{prefix}:{param_string}"
    
    async def get_instance_pricing_cached(
        self, 
        instance_type: str, 
        region: str,
        os_type: str = "linux"
    ) -> Optional[InstancePricing]:
        """Get instance pricing with caching"""
        
        cache_key = self._generate_cache_key(
            "instance_pricing",
            instance_type=instance_type,
            region=region,
            os_type=os_type
        )
        
        # Try to get from cache
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            self.cache_stats["hits"] += 1
            return cached_data
        
        # Cache miss - fetch from AWS
        self.cache_stats["misses"] += 1
        try:
            pricing_data = await pricing_service.get_instance_pricing(
                instance_type, region, os_type
            )
            
            if pricing_data:
                await self._set_cache(cache_key, pricing_data, ttl_hours=self.default_ttl_hours)
            
            return pricing_data
            
        except Exception as e:
            logger.error(f"Failed to fetch instance pricing for {instance_type}: {e}")
            self.cache_stats["errors"] += 1
            return None
    
    async def get_multiple_instance_pricing_cached(
        self,
        instance_types: List[str],
        region: str,
        os_type: str = "linux"
    ) -> Dict[str, InstancePricing]:
        """Get multiple instance pricing with batch caching"""
        
        results = {}
        uncached_types = []
        
        # Check cache for each instance type
        for instance_type in instance_types:
            cache_key = self._generate_cache_key(
                "instance_pricing",
                instance_type=instance_type,
                region=region,
                os_type=os_type
            )
            
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                results[instance_type] = cached_data
                self.cache_stats["hits"] += 1
            else:
                uncached_types.append(instance_type)
                self.cache_stats["misses"] += 1
        
        # Fetch uncached data in batch
        if uncached_types:
            try:
                batch_pricing = await pricing_service.get_multiple_instance_pricing(
                    uncached_types, region, os_type
                )
                
                # Cache the results
                cache_tasks = []
                for instance_type, pricing_data in batch_pricing.items():
                    cache_key = self._generate_cache_key(
                        "instance_pricing",
                        instance_type=instance_type,
                        region=region,
                        os_type=os_type
                    )
                    cache_tasks.append(
                        self._set_cache(cache_key, pricing_data, ttl_hours=self.default_ttl_hours)
                    )
                
                # Execute cache operations in parallel
                await asyncio.gather(*cache_tasks, return_exceptions=True)
                
                # Add to results
                results.update(batch_pricing)
                
            except Exception as e:
                logger.error(f"Failed to fetch batch instance pricing: {e}")
                self.cache_stats["errors"] += 1
        
        return results
    
    async def get_storage_pricing_cached(
        self,
        storage_type: str,
        region: str
    ) -> Optional[StoragePricing]:
        """Get storage pricing with caching"""
        
        cache_key = self._generate_cache_key(
            "storage_pricing",
            storage_type=storage_type,
            region=region
        )
        
        # Try to get from cache
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            self.cache_stats["hits"] += 1
            return cached_data
        
        # Cache miss - fetch from AWS
        self.cache_stats["misses"] += 1
        try:
            pricing_data = await pricing_service.get_storage_pricing(storage_type, region)
            
            if pricing_data:
                await self._set_cache(cache_key, pricing_data, ttl_hours=self.default_ttl_hours)
            
            return pricing_data
            
        except Exception as e:
            logger.error(f"Failed to fetch storage pricing for {storage_type}: {e}")
            self.cache_stats["errors"] += 1
            return None
    
    async def get_savings_plans_pricing_cached(
        self,
        instance_family: str,
        region: str,
        commitment_term: str = "1_year",
        payment_option: str = "no_upfront"
    ) -> Optional[List[SavingsPlansPrice]]:
        """Get Savings Plans pricing with caching"""
        
        cache_key = self._generate_cache_key(
            "savings_plans",
            instance_family=instance_family,
            region=region,
            commitment_term=commitment_term,
            payment_option=payment_option
        )
        
        # Try to get from cache
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            self.cache_stats["hits"] += 1
            return cached_data
        
        # Cache miss - fetch from AWS
        self.cache_stats["misses"] += 1
        try:
            pricing_data = await pricing_service.get_savings_plans_pricing(
                instance_family, region, commitment_term, payment_option
            )
            
            if pricing_data:
                await self._set_cache(cache_key, pricing_data, ttl_hours=self.default_ttl_hours)
            
            return pricing_data
            
        except Exception as e:
            logger.error(f"Failed to fetch Savings Plans pricing: {e}")
            self.cache_stats["errors"] += 1
            return None
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache (Redis first, then local)"""
        
        # Try Redis first
        if self.redis_client:
            try:
                cached_bytes = await self.redis_client.get(cache_key)
                if cached_bytes:
                    cache_entry = pickle.loads(cached_bytes)
                    if not cache_entry.is_expired():
                        cache_entry.access_count += 1
                        cache_entry.last_accessed = datetime.utcnow()
                        return cache_entry.data
                    else:
                        # Remove expired entry
                        await self.redis_client.delete(cache_key)
                        
            except Exception as e:
                logger.warning(f"Redis cache get failed for {cache_key}: {e}")
        
        # Try local cache
        if cache_key in self.local_cache:
            cache_entry = self.local_cache[cache_key]
            if not cache_entry.is_expired():
                cache_entry.access_count += 1
                cache_entry.last_accessed = datetime.utcnow()
                return cache_entry.data
            else:
                # Remove expired entry
                del self.local_cache[cache_key]
        
        return None
    
    async def _set_cache(self, cache_key: str, data: Any, ttl_hours: int = 4):
        """Set data in cache (both Redis and local)"""
        
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        cache_entry = CacheEntry(
            data=data,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            cache_key=cache_key
        )
        
        # Set in Redis
        if self.redis_client:
            try:
                cached_bytes = pickle.dumps(cache_entry)
                await self.redis_client.setex(
                    cache_key,
                    int(ttl_hours * 3600),  # Convert to seconds
                    cached_bytes
                )
            except Exception as e:
                logger.warning(f"Redis cache set failed for {cache_key}: {e}")
        
        # Set in local cache with size management
        self.local_cache[cache_key] = cache_entry
        await self._manage_local_cache_size()
    
    async def _manage_local_cache_size(self):
        """Manage local cache size by evicting old entries"""
        if len(self.local_cache) <= self.max_local_cache_size:
            return
        
        # Sort by last accessed time (LRU eviction)
        sorted_entries = sorted(
            self.local_cache.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        # Remove oldest entries
        entries_to_remove = len(self.local_cache) - self.max_local_cache_size
        for i in range(entries_to_remove):
            cache_key = sorted_entries[i][0]
            del self.local_cache[cache_key]
            self.cache_stats["evictions"] += 1
    
    async def invalidate_cache(self, pattern: str = "*"):
        """Invalidate cache entries matching pattern"""
        
        # Clear local cache
        if pattern == "*":
            self.local_cache.clear()
        else:
            keys_to_remove = [k for k in self.local_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.local_cache[key]
        
        # Clear Redis cache
        if self.redis_client:
            try:
                if pattern == "*":
                    await self.redis_client.flushdb()
                else:
                    # Use SCAN to find matching keys
                    cursor = 0
                    while True:
                        cursor, keys = await self.redis_client.scan(
                            cursor=cursor, 
                            match=f"*{pattern}*"
                        )
                        if keys:
                            await self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                            
            except Exception as e:
                logger.warning(f"Redis cache invalidation failed: {e}")
        
        logger.info(f"Cache invalidated for pattern: {pattern}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            **self.cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
            "local_cache_size": len(self.local_cache),
            "redis_connected": self.redis_client is not None
        }
        
        # Add Redis stats if available
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info("memory")
                stats["redis_memory_used"] = redis_info.get("used_memory_human", "Unknown")
                stats["redis_keys"] = await self.redis_client.dbsize()
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        self.local_cache.clear()
        logger.info("Pricing cache service cleaned up")

# Global cache service instance
pricing_cache_service = PricingCacheService()
