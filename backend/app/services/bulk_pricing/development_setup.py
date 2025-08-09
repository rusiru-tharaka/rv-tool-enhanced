"""
Development Setup for Bulk Pricing
Sets up the bulk pricing system in development mode using mock data
Bypasses download issues and allows immediate development progress
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any

from .database import PricingDatabase
from .parser import AWSPricingParser
from .mock_downloader import MockBulkPriceDownloader
from .local_pricing_service import LocalPricingService
from .sample_data_generator import SampleDataGenerator

logger = logging.getLogger(__name__)

class DevelopmentSetup:
    """Sets up bulk pricing system for development"""
    
    def __init__(self, db_path: str = None, cache_dir: str = None):
        """Initialize development setup"""
        self.db_path = db_path
        self.cache_dir = cache_dir
        
        # Initialize components
        self.db = PricingDatabase(db_path)
        self.downloader = MockBulkPriceDownloader(cache_dir)
        self.parser = AWSPricingParser()
        self.generator = SampleDataGenerator()
        
        logger.info("Development setup initialized")
    
    async def setup_development_environment(self) -> Dict[str, Any]:
        """Complete development environment setup"""
        
        logger.info("🚀 Setting up bulk pricing development environment...")
        
        results = {
            'database_setup': False,
            'sample_data_loaded': False,
            'local_service_ready': False,
            'total_records': 0,
            'errors': []
        }
        
        try:
            # Step 1: Ensure database is ready
            logger.info("📊 Step 1: Database setup...")
            stats = self.db.get_database_stats()
            results['database_setup'] = True
            logger.info(f"✅ Database ready: {stats}")
            
            # Step 2: Load sample data if database is empty
            if stats['total_records'] == 0:
                logger.info("📥 Step 2: Loading sample data...")
                await self._load_sample_data()
                results['sample_data_loaded'] = True
                
                # Get updated stats
                stats = self.db.get_database_stats()
                results['total_records'] = stats['total_records']
                logger.info(f"✅ Sample data loaded: {stats['total_records']} records")
            else:
                logger.info(f"📊 Database already contains {stats['total_records']} records")
                results['total_records'] = stats['total_records']
                results['sample_data_loaded'] = True
            
            # Step 3: Test local pricing service
            logger.info("🏪 Step 3: Testing local pricing service...")
            local_service = LocalPricingService(self.db_path)
            
            # Test health check
            health = local_service.health_check()
            if health['status'] == 'healthy':
                results['local_service_ready'] = True
                logger.info(f"✅ Local pricing service ready: {health}")
            else:
                results['errors'].append(f"Local service health check failed: {health}")
            
            # Step 4: Validate pricing lookups
            logger.info("🔍 Step 4: Validating pricing lookups...")
            test_results = await self._test_pricing_lookups(local_service)
            
            if test_results['success']:
                logger.info(f"✅ Pricing lookups working: {test_results}")
            else:
                results['errors'].append(f"Pricing lookup validation failed: {test_results}")
            
            logger.info("🎉 Development environment setup complete!")
            
        except Exception as e:
            error_msg = f"Development setup failed: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    async def _load_sample_data(self):
        """Load sample data into database"""
        
        # Generate sample data
        sample_dataset = self.generator.generate_complete_sample_dataset()
        
        # Load EC2 pricing
        logger.info("Loading EC2 pricing data...")
        ec2_records = self.db.bulk_insert_ec2_pricing(sample_dataset['ec2_pricing'])
        logger.info(f"Loaded {ec2_records} EC2 pricing records")
        
        # Load EBS pricing
        logger.info("Loading EBS pricing data...")
        ebs_records = self.db.bulk_insert_ebs_pricing(sample_dataset['ebs_pricing'])
        logger.info(f"Loaded {ebs_records} EBS pricing records")
        
        # Load Savings Plans data
        logger.info("Loading Savings Plans data...")
        savings_records = self.db.bulk_insert_savings_plans(sample_dataset['savings_plans'])
        logger.info(f"Loaded {savings_records} Savings Plans records")
        
        total_loaded = ec2_records + ebs_records + savings_records
        logger.info(f"Total records loaded: {total_loaded}")
    
    async def _test_pricing_lookups(self, local_service: LocalPricingService) -> Dict[str, Any]:
        """Test pricing lookups with sample data"""
        
        test_cases = [
            {'instance_type': 'm5.large', 'region': 'us-east-1'},
            {'instance_type': 'c5.xlarge', 'region': 'us-west-2'},
            {'instance_type': 'r5.2xlarge', 'region': 'eu-west-1'}
        ]
        
        results = {
            'success': True,
            'test_results': [],
            'errors': []
        }
        
        for test_case in test_cases:
            try:
                pricing = await local_service.get_instance_pricing(
                    test_case['instance_type'], 
                    test_case['region']
                )
                
                if pricing and pricing.on_demand_price_per_hour > 0:
                    results['test_results'].append({
                        'instance_type': test_case['instance_type'],
                        'region': test_case['region'],
                        'price': pricing.on_demand_price_per_hour,
                        'status': 'success'
                    })
                else:
                    results['errors'].append(f"No pricing found for {test_case}")
                    results['success'] = False
                    
            except Exception as e:
                results['errors'].append(f"Pricing lookup failed for {test_case}: {e}")
                results['success'] = False
        
        return results
    
    def create_integration_example(self) -> str:
        """Create example code for integrating with existing services"""
        
        example_code = '''
# Example: Integrating Bulk Pricing with Existing Cost Estimates Service

from services.bulk_pricing.local_pricing_service import LocalPricingService

class CostEstimatesService:
    def __init__(self):
        # Replace AWS Pricing API with local pricing service
        self.pricing_service = LocalPricingService()
    
    async def get_instance_cost(self, instance_type: str, region: str) -> float:
        """Get instance cost using local pricing data"""
        try:
            pricing = await self.pricing_service.get_instance_pricing(instance_type, region)
            return pricing.on_demand_price_per_hour if pricing else 0.0
        except Exception as e:
            logger.error(f"Failed to get pricing for {instance_type} in {region}: {e}")
            return 0.0
    
    async def calculate_monthly_cost(self, instance_type: str, region: str, hours_per_month: int = 730) -> float:
        """Calculate monthly cost"""
        hourly_cost = await self.get_instance_cost(instance_type, region)
        return hourly_cost * hours_per_month

# Usage Example:
cost_service = CostEstimatesService()
monthly_cost = await cost_service.calculate_monthly_cost('m5.large', 'us-east-1')
print(f"Monthly cost: ${monthly_cost:.2f}")
'''
        
        example_file = Path(__file__).parent / "integration_example.py"
        with open(example_file, 'w') as f:
            f.write(example_code)
        
        logger.info(f"Integration example created: {example_file}")
        return str(example_file)
    
    def get_development_status(self) -> Dict[str, Any]:
        """Get current development status"""
        
        db_stats = self.db.get_database_stats()
        cache_info = self.downloader.get_cache_info()
        
        return {
            'database': {
                'path': str(self.db.db_path),
                'stats': db_stats
            },
            'cache': cache_info,
            'components': {
                'database': 'ready',
                'mock_downloader': 'ready',
                'parser': 'ready',
                'sample_generator': 'ready'
            },
            'next_steps': [
                'Run setup_development_environment()',
                'Test pricing lookups',
                'Integrate with existing cost calculation services',
                'Set up production data loading (when ready)'
            ]
        }

async def quick_setup() -> DevelopmentSetup:
    """Quick setup for development"""
    
    logger.info("🚀 Quick development setup starting...")
    
    setup = DevelopmentSetup()
    results = await setup.setup_development_environment()
    
    if results['local_service_ready'] and not results['errors']:
        logger.info("✅ Development environment ready!")
        logger.info(f"📊 Database contains {results['total_records']} pricing records")
        logger.info("🔧 You can now use LocalPricingService for development")
    else:
        logger.error("❌ Development setup had issues:")
        for error in results['errors']:
            logger.error(f"  - {error}")
    
    return setup

if __name__ == "__main__":
    # Run quick setup
    setup = asyncio.run(quick_setup())
    
    # Show status
    status = setup.get_development_status()
    print("\n📋 Development Status:")
    print(f"Database: {status['database']['stats']}")
    print(f"Components: {status['components']}")
    print("\n📝 Next Steps:")
    for step in status['next_steps']:
        print(f"  - {step}")
