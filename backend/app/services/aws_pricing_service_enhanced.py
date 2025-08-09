"""
Enhanced AWS Pricing Service with Advanced Error Handling
Production-ready pricing service with comprehensive resilience features
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import time
import random
from dataclasses import dataclass
from .functools import wraps
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.config import Config

# Import base service
from .aws_pricing_service import pricing_service, InstancePricing, StoragePricing

logger = logging.getLogger(__name__)

@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern"""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = Exception

class CircuitBreaker:
    """Circuit breaker implementation for AWS API calls"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN - too many failures")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.config.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

def retry_with_backoff(config: RetryConfig = None):
    """Decorator for retry logic with exponential backoff"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (ClientError, BotoCoreError, ConnectionError, TimeoutError) as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                
                except Exception as e:
                    # Don't retry for non-transient errors
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise e
            
            raise last_exception
        
        return wrapper
    return decorator

class EnhancedPricingService:
    """Enhanced pricing service with advanced error handling and resilience"""
    
    def __init__(self):
        self.base_service = pricing_service
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        self.health_status = {
            "last_successful_call": None,
            "consecutive_failures": 0,
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0
        }
        
        # Enhanced boto3 config for resilience
        self.boto_config = Config(
            region_name='us-east-1',
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50,
            connect_timeout=10,
            read_timeout=30
        )
    
    async def initialize_with_validation(self, profile_name: str = "smartslot"):
        """Initialize service with comprehensive validation"""
        try:
            # Initialize base service
            await self.base_service.initialize(profile_name)
            
            # Validate connectivity with test call
            await self._validate_connectivity()
            
            logger.info("Enhanced pricing service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced pricing service: {e}")
            raise RuntimeError(f"Enhanced pricing service initialization failed: {e}")
    
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=2.0))
    async def _validate_connectivity(self):
        """Validate AWS API connectivity with test call"""
        try:
            # Test with a simple pricing call
            test_result = await self.base_service.get_instance_pricing(
                "t3.micro", "us-east-1", "linux"
            )
            
            if test_result is None:
                raise RuntimeError("Test pricing call returned no data")
            
            self._update_health_status(success=True)
            logger.info("AWS Pricing API connectivity validated")
            
        except Exception as e:
            self._update_health_status(success=False)
            logger.error(f"AWS Pricing API connectivity validation failed: {e}")
            raise e
    
    @circuit_breaker
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=1.0))
    async def get_instance_pricing_resilient(
        self, 
        instance_type: str, 
        region: str, 
        os_type: str = "linux"
    ) -> Optional[InstancePricing]:
        """Get instance pricing with enhanced error handling"""
        
        try:
            self.health_status["total_calls"] += 1
            
            # Validate inputs
            if not instance_type or not region:
                raise ValueError("Instance type and region are required")
            
            # Call base service
            result = await self.base_service.get_instance_pricing(
                instance_type, region, os_type
            )
            
            if result:
                self._update_health_status(success=True)
                return result
            else:
                logger.warning(f"No pricing data found for {instance_type} in {region}")
                return None
                
        except Exception as e:
            self._update_health_status(success=False)
            logger.error(f"Enhanced pricing call failed for {instance_type}: {e}")
            raise e
    
    @circuit_breaker
    @retry_with_backoff(RetryConfig(max_attempts=2, base_delay=2.0))
    async def get_multiple_instance_pricing_resilient(
        self,
        instance_types: List[str],
        region: str,
        os_type: str = "linux",
        batch_size: int = 10
    ) -> Dict[str, InstancePricing]:
        """Get multiple instance pricing with enhanced batch processing"""
        
        if not instance_types:
            return {}
        
        try:
            self.health_status["total_calls"] += 1
            
            # Process in smaller batches for better resilience
            results = {}
            failed_instances = []
            
            for i in range(0, len(instance_types), batch_size):
                batch = instance_types[i:i + batch_size]
                
                try:
                    batch_results = await self._process_pricing_batch(
                        batch, region, os_type
                    )
                    results.update(batch_results)
                    
                except Exception as e:
                    logger.warning(f"Batch processing failed for instances {batch}: {e}")
                    failed_instances.extend(batch)
            
            # Calculate success rate
            total_requested = len(instance_types)
            successful = len(results)
            success_rate = (successful / total_requested) * 100 if total_requested > 0 else 0
            
            logger.info(f"Batch pricing completed: {successful}/{total_requested} successful ({success_rate:.1f}%)")
            
            if success_rate >= 70:  # Accept if we have 70%+ success rate
                self._update_health_status(success=True)
            else:
                self._update_health_status(success=False)
                logger.error(f"Low success rate: {success_rate:.1f}%")
            
            return results
            
        except Exception as e:
            self._update_health_status(success=False)
            logger.error(f"Enhanced batch pricing failed: {e}")
            raise e
    
    async def _process_pricing_batch(
        self, 
        batch: List[str], 
        region: str, 
        os_type: str
    ) -> Dict[str, InstancePricing]:
        """Process a single batch of pricing requests"""
        
        tasks = []
        for instance_type in batch:
            task = self.get_instance_pricing_resilient(instance_type, region, os_type)
            tasks.append(task)
        
        # Execute batch with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=45.0  # 45 second timeout per batch
            )
            
            # Process results
            batch_results = {}
            for i, result in enumerate(results):
                instance_type = batch[i]
                
                if isinstance(result, InstancePricing):
                    batch_results[instance_type] = result
                elif isinstance(result, Exception):
                    logger.warning(f"Failed to get pricing for {instance_type}: {result}")
            
            return batch_results
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout processing batch: {batch}")
            raise TimeoutError(f"Batch processing timeout for {len(batch)} instances")
    
    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=1.5))
    async def get_storage_pricing_resilient(
        self,
        storage_type: str,
        region: str
    ) -> Optional[StoragePricing]:
        """Get storage pricing with enhanced error handling"""
        
        try:
            self.health_status["total_calls"] += 1
            
            if not storage_type or not region:
                raise ValueError("Storage type and region are required")
            
            result = await self.base_service.get_storage_pricing(storage_type, region)
            
            if result:
                self._update_health_status(success=True)
                return result
            else:
                logger.warning(f"No storage pricing found for {storage_type} in {region}")
                return None
                
        except Exception as e:
            self._update_health_status(success=False)
            logger.error(f"Enhanced storage pricing call failed: {e}")
            raise e
    
    def _update_health_status(self, success: bool):
        """Update service health status"""
        if success:
            self.health_status["successful_calls"] += 1
            self.health_status["consecutive_failures"] = 0
            self.health_status["last_successful_call"] = datetime.utcnow()
        else:
            self.health_status["failed_calls"] += 1
            self.health_status["consecutive_failures"] += 1
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        total_calls = self.health_status["total_calls"]
        success_rate = (
            (self.health_status["successful_calls"] / total_calls * 100) 
            if total_calls > 0 else 0
        )
        
        return {
            **self.health_status,
            "success_rate_percent": round(success_rate, 2),
            "circuit_breaker_state": self.circuit_breaker.state,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "is_healthy": (
                self.health_status["consecutive_failures"] < 3 and
                self.circuit_breaker.state != "OPEN"
            )
        }
    
    async def reset_circuit_breaker(self):
        """Manually reset circuit breaker"""
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.state = "CLOSED"
        self.circuit_breaker.last_failure_time = None
        logger.info("Circuit breaker manually reset")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.base_service.cleanup()
        logger.info("Enhanced pricing service cleaned up")

# Global enhanced service instance
enhanced_pricing_service = EnhancedPricingService()
