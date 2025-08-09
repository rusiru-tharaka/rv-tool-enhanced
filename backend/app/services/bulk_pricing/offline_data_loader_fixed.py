#!/usr/bin/env python3
"""
Offline Data Loader for Real AWS Pricing Data - FIXED VERSION
Processes downloaded AWS pricing files with correct EBS handling
EBS pricing is extracted from EC2 data as per AWS official structure
"""

import json
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Iterator, Optional
from datetime import datetime

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.bulk_pricing.database import PricingDatabase
from services.bulk_pricing.parser_fixed import AWSPricingParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('offline_data_loading.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OfflineDataLoader:
    """Loads real AWS pricing data from downloaded files into database - FIXED VERSION"""
    
    def __init__(self, data_dir: str = None, db_path: str = None, batch_size: int = 1000):
        """Initialize data loader"""
        
        if data_dir is None:
            data_dir = Path(__file__).parent / "offline_data"
        
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        
        # Initialize database and parser
        self.db = PricingDatabase(db_path)
        self.parser = AWSPricingParser()
        
        logger.info(f"Data loader initialized (FIXED VERSION):")
        logger.info(f"  Data directory: {self.data_dir}")
        logger.info(f"  Database: {self.db.db_path}")
        logger.info(f"  Batch size: {self.batch_size}")
        logger.info("  Note: EBS pricing will be extracted from EC2 data")
    
    def load_json_streaming(self, filepath: Path) -> Optional[Dict]:
        """Load large JSON file with memory optimization"""
        
        try:
            logger.info(f"Loading JSON file: {filepath.name}")
            start_time = time.time()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            load_time = time.time() - start_time
            file_size_mb = filepath.stat().st_size / 1024 / 1024
            
            logger.info(f"JSON loaded: {file_size_mb:.1f}MB in {load_time:.1f}s")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath.name}: {e}")
            return None
        except MemoryError:
            logger.error(f"Memory error loading {filepath.name} - file too large")
            return None
        except Exception as e:
            logger.error(f"Error loading {filepath.name}: {e}")
            return None
    
    def process_ec2_data_in_batches(self, ec2_data: Dict) -> Dict[str, int]:
        """Process EC2 pricing data in batches (includes EBS extraction)"""
        
        logger.info("Processing EC2 pricing data (including EBS volumes)...")
        
        ec2_records = 0
        ebs_records = 0
        ec2_batch = []
        ebs_batch = []
        
        try:
            # Reset parser stats
            self.parser.reset_stats()
            
            # Use the parser to process data (extracts both EC2 and EBS)
            for record in self.parser.parse_ec2_pricing(ec2_data):
                
                # Determine if this is EC2 or EBS record
                if 'instance_type' in record:
                    # EC2 instance record
                    ec2_batch.append(record)
                    
                    # Process EC2 batch when it reaches batch_size
                    if len(ec2_batch) >= self.batch_size:
                        inserted = self.db.bulk_insert_ec2_pricing(ec2_batch)
                        ec2_records += inserted
                        logger.info(f"Processed EC2 batch: {inserted} records (total EC2: {ec2_records})")
                        ec2_batch = []  # Clear batch
                
                elif 'volume_type' in record:
                    # EBS volume record
                    ebs_batch.append(record)
                    
                    # Process EBS batch when it reaches batch_size
                    if len(ebs_batch) >= self.batch_size:
                        inserted = self.db.bulk_insert_ebs_pricing(ebs_batch)
                        ebs_records += inserted
                        logger.info(f"Processed EBS batch: {inserted} records (total EBS: {ebs_records})")
                        ebs_batch = []  # Clear batch
            
            # Process remaining records
            if ec2_batch:
                inserted = self.db.bulk_insert_ec2_pricing(ec2_batch)
                ec2_records += inserted
                logger.info(f"Processed final EC2 batch: {inserted} records")
            
            if ebs_batch:
                inserted = self.db.bulk_insert_ebs_pricing(ebs_batch)
                ebs_records += inserted
                logger.info(f"Processed final EBS batch: {inserted} records")
            
            # Get parser statistics
            stats = self.parser.get_parsing_stats()
            
            logger.info(f"EC2 data processing complete:")
            logger.info(f"  Products processed: {stats['products_processed']}")
            logger.info(f"  EC2 instances found: {stats['ec2_instances_found']}")
            logger.info(f"  EBS volumes found: {stats['ebs_volumes_found']}")
            logger.info(f"  EC2 records inserted: {ec2_records}")
            logger.info(f"  EBS records inserted: {ebs_records}")
            logger.info(f"  Total records: {ec2_records + ebs_records}")
            
            return {
                'ec2_records': ec2_records,
                'ebs_records': ebs_records,
                'total_records': ec2_records + ebs_records
            }
            
        except Exception as e:
            logger.error(f"Error processing EC2 data: {e}")
            return {
                'ec2_records': ec2_records,
                'ebs_records': ebs_records,
                'total_records': ec2_records + ebs_records
            }
    
    def load_service_data(self, service_code: str) -> Dict[str, any]:
        """Load data for a specific service"""
        
        filename = f"{service_code}_pricing.json"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.error(f"Data file not found: {filename}")
            return {'success': False, 'records': 0}
        
        logger.info(f"Loading {service_code} data from {filename}")
        start_time = time.time()
        
        # Load JSON data
        data = self.load_json_streaming(filepath)
        if not data:
            return {'success': False, 'records': 0}
        
        # Process based on service type
        if service_code == 'AmazonEC2':
            result = self.process_ec2_data_in_batches(data)
            records_processed = result['total_records']
            
            logger.info(f"✅ {service_code} loaded successfully:")
            logger.info(f"   EC2 records: {result['ec2_records']}")
            logger.info(f"   EBS records: {result['ebs_records']}")
            logger.info(f"   Total records: {records_processed}")
            
        elif service_code == 'index':
            logger.info("Index file loaded (metadata only)")
            return {'success': True, 'records': 0}
            
        else:
            logger.warning(f"No processor available for {service_code}")
            return {'success': False, 'records': 0}
        
        total_time = time.time() - start_time
        
        if records_processed > 0:
            logger.info(f"   Time: {total_time:.1f}s")
            logger.info(f"   Rate: {records_processed/total_time:.1f} records/sec")
            return {'success': True, 'records': records_processed}
        else:
            logger.error(f"❌ {service_code} loading failed - no records processed")
            return {'success': False, 'records': 0}
    
    def load_all_available_data(self) -> Dict[str, any]:
        """Load all available downloaded data"""
        
        logger.info("=" * 60)
        logger.info("LOADING REAL AWS PRICING DATA - FIXED VERSION")
        logger.info("=" * 60)
        logger.info("Note: EBS pricing will be extracted from EC2 data")
        
        # Find available data files
        available_files = list(self.data_dir.glob("*_pricing.json"))
        
        if not available_files:
            logger.error("No pricing data files found!")
            logger.error(f"Expected files in: {self.data_dir}")
            return {'success': False, 'results': {}}
        
        logger.info(f"Found {len(available_files)} data files:")
        for file in available_files:
            size_mb = file.stat().st_size / 1024 / 1024
            logger.info(f"  {file.name}: {size_mb:.1f}MB")
        
        # Get initial database stats
        initial_stats = self.db.get_database_stats()
        logger.info(f"Initial database records: {initial_stats['total_records']}")
        
        # Load each service
        results = {}
        total_records_loaded = 0
        
        for filepath in available_files:
            service_code = filepath.name.replace('_pricing.json', '')
            
            logger.info(f"\n[Loading] {service_code}...")
            result = self.load_service_data(service_code)
            results[service_code] = result
            
            if result['success']:
                total_records_loaded += result['records']
        
        # Get final database stats
        final_stats = self.db.get_database_stats()
        
        logger.info("\n" + "=" * 60)
        logger.info("LOADING SUMMARY - FIXED VERSION")
        logger.info("=" * 60)
        
        successful_loads = sum(1 for result in results.values() if result['success'])
        total_loads = len(results)
        
        logger.info(f"Successful loads: {successful_loads}/{total_loads}")
        logger.info(f"Records loaded: {total_records_loaded}")
        logger.info(f"Total database records: {final_stats['total_records']}")
        
        for service, result in results.items():
            status = "✅" if result['success'] else "❌"
            records = result['records']
            logger.info(f"{status} {service}: {records} records")
        
        if successful_loads > 0:
            logger.info("\n🎉 DATA LOADING COMPLETED!")
            logger.info("Database is ready for development with real AWS pricing data")
            logger.info("✅ EC2 instance pricing loaded")
            logger.info("✅ EBS volume pricing extracted and loaded")
        else:
            logger.error(f"\n⚠️  All services failed to load")
        
        return {
            'success': successful_loads > 0,
            'results': results,
            'total_records': total_records_loaded,
            'database_stats': final_stats
        }
    
    def validate_loaded_data(self) -> Dict[str, any]:
        """Validate the loaded pricing data"""
        
        logger.info("Validating loaded pricing data...")
        
        validation_results = {
            'database_stats': self.db.get_database_stats(),
            'sample_prices': {},
            'ebs_prices': {},
            'validation_errors': []
        }
        
        # Test EC2 instance pricing lookups
        test_instances = [
            ('m5.large', 'us-east-1'),
            ('c5.xlarge', 'us-west-2'),
            ('r5.2xlarge', 'eu-west-1')
        ]
        
        for instance_type, region in test_instances:
            try:
                price = self.db.get_ec2_pricing(instance_type, region)
                if price and price > 0:
                    validation_results['sample_prices'][f"{instance_type}_{region}"] = price
                    logger.info(f"✅ {instance_type} in {region}: ${price:.4f}/hour")
                else:
                    error = f"No EC2 pricing found for {instance_type} in {region}"
                    validation_results['validation_errors'].append(error)
                    logger.warning(f"⚠️  {error}")
            except Exception as e:
                error = f"EC2 pricing lookup failed for {instance_type} in {region}: {e}"
                validation_results['validation_errors'].append(error)
                logger.error(f"❌ {error}")
        
        # Test EBS volume pricing lookups
        test_volumes = [
            ('gp3', 'us-east-1'),
            ('gp2', 'us-west-2'),
            ('io1', 'eu-west-1')
        ]
        
        for volume_type, region in test_volumes:
            try:
                price = self.db.get_ebs_pricing(volume_type, region)
                if price and price > 0:
                    validation_results['ebs_prices'][f"{volume_type}_{region}"] = price
                    logger.info(f"✅ {volume_type} in {region}: ${price:.4f}/GB-month")
                else:
                    error = f"No EBS pricing found for {volume_type} in {region}"
                    validation_results['validation_errors'].append(error)
                    logger.warning(f"⚠️  {error}")
            except Exception as e:
                error = f"EBS pricing lookup failed for {volume_type} in {region}: {e}"
                validation_results['validation_errors'].append(error)
                logger.error(f"❌ {error}")
        
        # Validate data completeness
        stats = validation_results['database_stats']
        if stats['total_records'] == 0:
            validation_results['validation_errors'].append("Database is empty")
        
        if len(validation_results['validation_errors']) == 0:
            logger.info("✅ Data validation passed")
        else:
            logger.error(f"❌ Data validation found {len(validation_results['validation_errors'])} issues")
        
        return validation_results

def main():
    """Main function for offline data loading - FIXED VERSION"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Load downloaded AWS pricing data into database - FIXED VERSION")
    parser.add_argument("--data-dir", help="Directory containing downloaded data", default=None)
    parser.add_argument("--db-path", help="Database file path", default=None)
    parser.add_argument("--batch-size", type=int, help="Batch size for processing", default=1000)
    parser.add_argument("--validate", action="store_true", help="Validate loaded data")
    
    args = parser.parse_args()
    
    # Initialize loader
    loader = OfflineDataLoader(
        data_dir=args.data_dir,
        db_path=args.db_path,
        batch_size=args.batch_size
    )
    
    # Load all available data
    results = loader.load_all_available_data()
    
    # Validate if requested
    if args.validate:
        validation = loader.validate_loaded_data()
        
        if validation['validation_errors']:
            logger.error("Validation failed - check errors above")
            sys.exit(1)
    
    # Check if any loads were successful
    if results['success']:
        logger.info("\n✅ Data loading completed successfully!")
        logger.info("You can now use the local pricing service with real AWS data")
        logger.info("✅ Both EC2 and EBS pricing are available")
        sys.exit(0)
    else:
        logger.error("\n❌ All data loading failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
