"""
Phase 1 Performance Testing Suite
Comprehensive testing for pricing service performance and reliability
Tests realistic dataset sizes and validates Phase 1 completion criteria
"""

import asyncio
import pytest
import time
import logging
from typing import Dict, List, Any
from datetime import datetime
import statistics
import json

# Import services to test
from services.aws_pricing_service import pricing_service
from services.pricing_cache_service import pricing_cache_service
from services.cost_estimates_service import cost_estimates_service
from services.aws_pricing_service_enhanced import enhanced_pricing_service
from models.core_models import TCOParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTestSuite:
    """Comprehensive performance testing suite for Phase 1 validation"""
    
    def __init__(self):
        self.test_results = {
            "test_start_time": None,
            "test_end_time": None,
            "total_duration": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "performance_metrics": {},
            "error_handling_tests": {},
            "cache_performance": {},
            "scalability_tests": {}
        }
        
        # Test datasets of varying sizes
        self.test_datasets = {
            "small": self._generate_test_instances(50),
            "medium": self._generate_test_instances(200),
            "large": self._generate_test_instances(500),
            "xlarge": self._generate_test_instances(1000)
        }
        
        # Test regions
        self.test_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        
        # Performance thresholds (Phase 1 completion criteria)
        self.performance_thresholds = {
            "single_instance_max_time": 5.0,  # 5 seconds max for single instance
            "batch_50_max_time": 30.0,        # 30 seconds max for 50 instances
            "batch_200_max_time": 120.0,      # 2 minutes max for 200 instances
            "cache_hit_rate_min": 80.0,       # 80% minimum cache hit rate
            "error_rate_max": 5.0,            # 5% maximum error rate
            "memory_usage_max_mb": 500,       # 500MB max memory usage
        }
    
    def _generate_test_instances(self, count: int) -> List[str]:
        """Generate realistic test instance types"""
        instance_families = [
            "t3", "t3a", "m5", "m5a", "m5n", "m5zn",
            "c5", "c5a", "c5n", "r5", "r5a", "r5n",
            "i3", "i3en", "d3", "d3en", "x1e", "z1d"
        ]
        
        instance_sizes = [
            "nano", "micro", "small", "medium", "large", "xlarge",
            "2xlarge", "4xlarge", "8xlarge", "12xlarge", "16xlarge"
        ]
        
        instances = []
        for i in range(count):
            family = instance_families[i % len(instance_families)]
            size = instance_sizes[i % len(instance_sizes)]
            
            # Skip invalid combinations
            if family in ["x1e", "z1d"] and size in ["nano", "micro"]:
                size = "large"
            
            instances.append(f"{family}.{size}")
        
        return instances
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete Phase 1 performance test suite"""
        
        logger.info("Starting Phase 1 Performance Test Suite")
        self.test_results["test_start_time"] = datetime.utcnow()
        
        try:
            # Initialize services
            await self._initialize_services()
            
            # Run performance tests
            await self._test_single_instance_performance()
            await self._test_batch_processing_performance()
            await self._test_cache_performance()
            await self._test_error_handling_resilience()
            await self._test_memory_usage()
            await self._test_concurrent_requests()
            
            # Generate final report
            await self._generate_performance_report()
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            self.test_results["tests_failed"] += 1
        
        finally:
            self.test_results["test_end_time"] = datetime.utcnow()
            if self.test_results["test_start_time"]:
                duration = self.test_results["test_end_time"] - self.test_results["test_start_time"]
                self.test_results["total_duration"] = duration.total_seconds()
        
        return self.test_results
    
    async def _initialize_services(self):
        """Initialize all services for testing"""
        logger.info("Initializing services for testing...")
        
        try:
            # Initialize pricing service
            await pricing_service.initialize("smartslot")
            
            # Initialize cache service
            await pricing_cache_service.initialize()
            
            # Initialize enhanced service
            await enhanced_pricing_service.initialize_with_validation("smartslot")
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise e
    
    async def _test_single_instance_performance(self):
        """Test single instance pricing performance"""
        logger.info("Testing single instance pricing performance...")
        
        test_instances = self.test_datasets["small"][:10]  # Test with 10 instances
        response_times = []
        
        for instance_type in test_instances:
            start_time = time.time()
            
            try:
                result = await pricing_service.get_instance_pricing(
                    instance_type, "us-east-1", "linux"
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if result:
                    logger.debug(f"✅ {instance_type}: {response_time:.2f}s")
                else:
                    logger.warning(f"❌ {instance_type}: No pricing data")
                
            except Exception as e:
                logger.error(f"❌ {instance_type}: {e}")
                self.test_results["tests_failed"] += 1
        
        # Calculate metrics
        if response_times:
            metrics = {
                "avg_response_time": statistics.mean(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "median_response_time": statistics.median(response_times),
                "total_requests": len(response_times),
                "threshold_passed": max(response_times) <= self.performance_thresholds["single_instance_max_time"]
            }
            
            self.test_results["performance_metrics"]["single_instance"] = metrics
            
            if metrics["threshold_passed"]:
                self.test_results["tests_passed"] += 1
                logger.info(f"✅ Single instance test PASSED - Max time: {metrics['max_response_time']:.2f}s")
            else:
                self.test_results["tests_failed"] += 1
                logger.error(f"❌ Single instance test FAILED - Max time: {metrics['max_response_time']:.2f}s")
    
    async def _test_batch_processing_performance(self):
        """Test batch processing performance with different dataset sizes"""
        logger.info("Testing batch processing performance...")
        
        batch_tests = [
            ("small_batch", self.test_datasets["small"], "batch_50_max_time"),
            ("medium_batch", self.test_datasets["medium"], "batch_200_max_time")
        ]
        
        for test_name, instances, threshold_key in batch_tests:
            logger.info(f"Testing {test_name} with {len(instances)} instances...")
            
            start_time = time.time()
            
            try:
                results = await pricing_service.get_multiple_instance_pricing(
                    instances, "us-east-1", "linux"
                )
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Calculate metrics
                successful_count = len(results)
                success_rate = (successful_count / len(instances)) * 100
                avg_time_per_instance = total_time / len(instances)
                
                metrics = {
                    "total_time": total_time,
                    "instances_requested": len(instances),
                    "instances_successful": successful_count,
                    "success_rate": success_rate,
                    "avg_time_per_instance": avg_time_per_instance,
                    "threshold_passed": total_time <= self.performance_thresholds[threshold_key]
                }
                
                self.test_results["performance_metrics"][test_name] = metrics
                
                if metrics["threshold_passed"] and success_rate >= 90:
                    self.test_results["tests_passed"] += 1
                    logger.info(f"✅ {test_name} PASSED - Time: {total_time:.2f}s, Success: {success_rate:.1f}%")
                else:
                    self.test_results["tests_failed"] += 1
                    logger.error(f"❌ {test_name} FAILED - Time: {total_time:.2f}s, Success: {success_rate:.1f}%")
                
            except Exception as e:
                logger.error(f"❌ {test_name} failed with exception: {e}")
                self.test_results["tests_failed"] += 1
    
    async def _test_cache_performance(self):
        """Test caching performance and hit rates"""
        logger.info("Testing cache performance...")
        
        test_instances = self.test_datasets["small"][:20]
        
        # First pass - populate cache
        logger.info("First pass - populating cache...")
        start_time = time.time()
        
        first_pass_results = await pricing_cache_service.get_multiple_instance_pricing_cached(
            test_instances, "us-east-1", "linux"
        )
        
        first_pass_time = time.time() - start_time
        
        # Second pass - test cache hits
        logger.info("Second pass - testing cache hits...")
        start_time = time.time()
        
        second_pass_results = await pricing_cache_service.get_multiple_instance_pricing_cached(
            test_instances, "us-east-1", "linux"
        )
        
        second_pass_time = time.time() - start_time
        
        # Calculate cache performance
        cache_stats = await pricing_cache_service.get_cache_stats()
        
        cache_metrics = {
            "first_pass_time": first_pass_time,
            "second_pass_time": second_pass_time,
            "cache_speedup": first_pass_time / second_pass_time if second_pass_time > 0 else 0,
            "cache_hit_rate": cache_stats.get("hit_rate_percent", 0),
            "cache_stats": cache_stats,
            "threshold_passed": cache_stats.get("hit_rate_percent", 0) >= self.performance_thresholds["cache_hit_rate_min"]
        }
        
        self.test_results["cache_performance"] = cache_metrics
        
        if cache_metrics["threshold_passed"]:
            self.test_results["tests_passed"] += 1
            logger.info(f"✅ Cache performance PASSED - Hit rate: {cache_metrics['cache_hit_rate']:.1f}%")
        else:
            self.test_results["tests_failed"] += 1
            logger.error(f"❌ Cache performance FAILED - Hit rate: {cache_metrics['cache_hit_rate']:.1f}%")
    
    async def _test_error_handling_resilience(self):
        """Test error handling and resilience features"""
        logger.info("Testing error handling and resilience...")
        
        error_tests = []
        
        # Test 1: Invalid instance types
        logger.info("Testing invalid instance types...")
        invalid_instances = ["invalid.type", "fake.instance", "nonexistent.size"]
        
        try:
            results = await enhanced_pricing_service.get_multiple_instance_pricing_resilient(
                invalid_instances, "us-east-1", "linux"
            )
            
            error_tests.append({
                "test": "invalid_instances",
                "passed": len(results) == 0,  # Should return empty dict
                "details": f"Returned {len(results)} results for invalid instances"
            })
            
        except Exception as e:
            error_tests.append({
                "test": "invalid_instances",
                "passed": False,
                "details": f"Exception raised: {e}"
            })
        
        # Test 2: Invalid region
        logger.info("Testing invalid region...")
        try:
            result = await enhanced_pricing_service.get_instance_pricing_resilient(
                "t3.micro", "invalid-region", "linux"
            )
            
            error_tests.append({
                "test": "invalid_region",
                "passed": result is None,  # Should return None
                "details": f"Result: {result}"
            })
            
        except Exception as e:
            error_tests.append({
                "test": "invalid_region",
                "passed": True,  # Exception is acceptable
                "details": f"Exception properly raised: {type(e).__name__}"
            })
        
        # Test 3: Circuit breaker functionality
        logger.info("Testing circuit breaker...")
        health_status = await enhanced_pricing_service.get_health_status()
        
        error_tests.append({
            "test": "circuit_breaker",
            "passed": "circuit_breaker_state" in health_status,
            "details": f"Circuit breaker state: {health_status.get('circuit_breaker_state', 'Unknown')}"
        })
        
        # Calculate overall error handling score
        passed_tests = sum(1 for test in error_tests if test["passed"])
        total_tests = len(error_tests)
        error_handling_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        self.test_results["error_handling_tests"] = {
            "tests": error_tests,
            "passed_count": passed_tests,
            "total_count": total_tests,
            "score_percent": error_handling_score,
            "threshold_passed": error_handling_score >= 80.0
        }
        
        if error_handling_score >= 80.0:
            self.test_results["tests_passed"] += 1
            logger.info(f"✅ Error handling PASSED - Score: {error_handling_score:.1f}%")
        else:
            self.test_results["tests_failed"] += 1
            logger.error(f"❌ Error handling FAILED - Score: {error_handling_score:.1f}%")
    
    async def _test_memory_usage(self):
        """Test memory usage during operations"""
        logger.info("Testing memory usage...")
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # Baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Process large dataset
            large_instances = self.test_datasets["large"]
            
            start_memory = process.memory_info().rss / 1024 / 1024
            
            results = await pricing_service.get_multiple_instance_pricing(
                large_instances[:100], "us-east-1", "linux"  # Test with 100 instances
            )
            
            end_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = end_memory - start_memory
            
            memory_metrics = {
                "baseline_memory_mb": baseline_memory,
                "start_memory_mb": start_memory,
                "end_memory_mb": end_memory,
                "memory_increase_mb": memory_increase,
                "threshold_passed": memory_increase <= self.performance_thresholds["memory_usage_max_mb"]
            }
            
            self.test_results["performance_metrics"]["memory_usage"] = memory_metrics
            
            if memory_metrics["threshold_passed"]:
                self.test_results["tests_passed"] += 1
                logger.info(f"✅ Memory usage PASSED - Increase: {memory_increase:.1f}MB")
            else:
                self.test_results["tests_failed"] += 1
                logger.error(f"❌ Memory usage FAILED - Increase: {memory_increase:.1f}MB")
                
        except ImportError:
            logger.warning("psutil not available - skipping memory usage test")
        except Exception as e:
            logger.error(f"Memory usage test failed: {e}")
            self.test_results["tests_failed"] += 1
    
    async def _test_concurrent_requests(self):
        """Test concurrent request handling"""
        logger.info("Testing concurrent request handling...")
        
        test_instances = self.test_datasets["small"][:30]
        concurrent_tasks = 5
        
        start_time = time.time()
        
        # Create concurrent tasks
        tasks = []
        for i in range(concurrent_tasks):
            batch_start = i * 6
            batch_end = batch_start + 6
            batch = test_instances[batch_start:batch_end]
            
            task = pricing_service.get_multiple_instance_pricing(
                batch, "us-east-1", "linux"
            )
            tasks.append(task)
        
        # Execute concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_tasks = sum(1 for r in results if not isinstance(r, Exception))
            total_instances_processed = sum(len(r) for r in results if isinstance(r, dict))
            
            concurrency_metrics = {
                "concurrent_tasks": concurrent_tasks,
                "total_time": total_time,
                "successful_tasks": successful_tasks,
                "total_instances_processed": total_instances_processed,
                "avg_time_per_task": total_time / concurrent_tasks,
                "threshold_passed": successful_tasks >= (concurrent_tasks * 0.8)  # 80% success rate
            }
            
            self.test_results["scalability_tests"]["concurrency"] = concurrency_metrics
            
            if concurrency_metrics["threshold_passed"]:
                self.test_results["tests_passed"] += 1
                logger.info(f"✅ Concurrency test PASSED - {successful_tasks}/{concurrent_tasks} tasks successful")
            else:
                self.test_results["tests_failed"] += 1
                logger.error(f"❌ Concurrency test FAILED - {successful_tasks}/{concurrent_tasks} tasks successful")
                
        except Exception as e:
            logger.error(f"Concurrency test failed: {e}")
            self.test_results["tests_failed"] += 1
    
    async def _generate_performance_report(self):
        """Generate comprehensive performance report"""
        logger.info("Generating performance report...")
        
        total_tests = self.test_results["tests_passed"] + self.test_results["tests_failed"]
        success_rate = (self.test_results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        # Phase 1 completion assessment
        phase1_criteria = {
            "single_instance_performance": self.test_results["performance_metrics"].get("single_instance", {}).get("threshold_passed", False),
            "batch_processing_performance": all(
                metrics.get("threshold_passed", False) 
                for key, metrics in self.test_results["performance_metrics"].items() 
                if "batch" in key
            ),
            "cache_performance": self.test_results["cache_performance"].get("threshold_passed", False),
            "error_handling": self.test_results["error_handling_tests"].get("threshold_passed", False),
            "overall_success_rate": success_rate >= 80.0
        }
        
        phase1_passed = all(phase1_criteria.values())
        
        report = {
            "phase1_completion_status": "PASSED" if phase1_passed else "FAILED",
            "phase1_criteria": phase1_criteria,
            "overall_success_rate": success_rate,
            "total_tests": total_tests,
            "tests_passed": self.test_results["tests_passed"],
            "tests_failed": self.test_results["tests_failed"],
            "test_duration_seconds": self.test_results["total_duration"],
            "detailed_results": self.test_results
        }
        
        self.test_results["final_report"] = report
        
        # Log summary
        logger.info("=" * 60)
        logger.info("PHASE 1 PERFORMANCE TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Status: {report['phase1_completion_status']}")
        logger.info(f"Overall Success Rate: {success_rate:.1f}%")
        logger.info(f"Tests Passed: {self.test_results['tests_passed']}")
        logger.info(f"Tests Failed: {self.test_results['tests_failed']}")
        logger.info(f"Duration: {self.test_results['total_duration']:.1f} seconds")
        logger.info("=" * 60)
        
        if phase1_passed:
            logger.info("🎉 PHASE 1 COMPLETION CRITERIA MET!")
        else:
            logger.error("❌ Phase 1 completion criteria not met")
            logger.error("Failed criteria:")
            for criterion, passed in phase1_criteria.items():
                if not passed:
                    logger.error(f"  - {criterion}")

# Test execution function
async def run_phase1_performance_tests():
    """Run Phase 1 performance tests"""
    test_suite = PerformanceTestSuite()
    return await test_suite.run_all_tests()

if __name__ == "__main__":
    # Run tests if executed directly
    asyncio.run(run_phase1_performance_tests())
