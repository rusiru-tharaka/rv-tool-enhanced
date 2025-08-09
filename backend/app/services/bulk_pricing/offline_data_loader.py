#!/usr/bin/env python3
"""
Offline Data Loader for Real AWS Pricing Data
Processes downloaded AWS pricing files and loads them into SQLite database
Optimized for large files with memory-efficient processing
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
from services.bulk_pricing.parser import AWSPricingParser

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
    """Loads real AWS pricing data from downloaded files into database"""
    
    def __init__(self, data_dir: str = None, db_path: str = None, batch_size: int = 1000):
        """Initialize data loader"""
        
        if data_dir is None:
            data_dir = Path(__file__).parent / "offline_data"
        
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        
        # Initialize database and parser
        self.db = PricingDatabase(db_path)
        self.parser = AWSPricingParser()
        
        logger.info(f"Data loader initialized:")
        logger.info(f"  Data directory: {self.data_dir}")
        logger.info(f"  Database: {self.db.db_path}")
        logger.info(f"  Batch size: {self.batch_size}")
    
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
    
    def process_ec2_data_in_batches(self, ec2_data: Dict) -> int:
        """Process EC2 pricing data in batches to manage memory"""
        
        logger.info("Processing EC2 pricing data...")
        
        total_records = 0
        batch_records = []
        
        try:
            # Use the parser to process data
            for record in self.parser.parse_ec2_pricing(ec2_data):
                batch_records.append(record)
                
                # Process batch when it reaches batch_size
                if len(batch_records) >= self.batch_size:
                    inserted = self.db.bulk_insert_ec2_pricing(batch_records)
                    total_records += inserted
                    
                    logger.info(f"Processed batch: {inserted} records (total: {total_records})")
                    batch_records = []  # Clear batch
            
            # Process remaining records
            if batch_records:
                inserted = self.db.bulk_insert_ec2_pricing(batch_records)
                total_records += inserted
                logger.info(f"Processed final batch: {inserted} records")
            
            logger.info(f"EC2 processing complete: {total_records} total records")
            return total_records
            
        except Exception as e:
            logger.error(f"Error processing EC2 data: {e}")
            return total_records
    
    def process_ebs_data_in_batches(self, ebs_data: Dict) -> int:
        """Process EBS pricing data in batches"""
        
        logger.info("Processing EBS pricing data...")
        
        total_records = 0
        batch_records = []
        
        try:
            # Use the parser to process data
            for record in self.parser.parse_ebs_pricing(ebs_data):
                batch_records.append(record)
                
                # Process batch when it reaches batch_size
                if len(batch_records) >= self.batch_size:
                    inserted = self.db.bulk_insert_ebs_pricing(batch_records)
                    total_records += inserted
                    
                    logger.info(f"Processed EBS batch: {inserted} records (total: {total_records})")
                    batch_records = []  # Clear batch
            
            # Process remaining records
            if batch_records:
                inserted = self.db.bulk_insert_ebs_pricing(batch_records)
                total_records += inserted
                logger.info(f"Processed EBS final batch: {inserted} records")
            
            logger.info(f"EBS processing complete: {total_records} total records")
            return total_records
            
        except Exception as e:
            logger.error(f"Error processing EBS data: {e}")
            return total_records
    
    def load_service_data(self, service_code: str) -> bool:
        """Load data for a specific service"""
        
        filename = f"{service_code}_pricing.json"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.error(f"Data file not found: {filename}")
            return False
        
        logger.info(f"Loading {service_code} data from {filename}")
        start_time = time.time()
        
        # Load JSON data
        data = self.load_json_streaming(filepath)
        if not data:
            return False
        
        # Process based on service type
        records_processed = 0
        
        if service_code == 'AmazonEC2':
            records_processed = self.process_ec2_data_in_batches(data)
        elif service_code == 'AmazonEBS':
            records_processed = self.process_ebs_data_in_batches(data)
        elif service_code == 'index':
            logger.info("Index file loaded (metadata only)")
            return True
        else:
            logger.warning(f"No processor available for {service_code}")
            return False
        
        total_time = time.time() - start_time
        
        if records_processed > 0:
            logger.info(f"✅ {service_code} loaded successfully:")
            logger.info(f"   Records: {records_processed}")
            logger.info(f"   Time: {total_time:.1f}s")
            logger.info(f"   Rate: {records_processed/total_time:.1f} records/sec")
            return True
        else:
            logger.error(f"❌ {service_code} loading failed - no records processed")
            return False
    
    def load_all_available_data(self) -> Dict[str, bool]:
        """Load all available downloaded data"""
        
        logger.info("=" * 60)
        logger.info("LOADING REAL AWS PRICING DATA")
        logger.info("=" * 60)
        
        # Find available data files
        available_files = list(self.data_dir.glob("*_pricing.json"))
        
        if not available_files:
            logger.error("No pricing data files found!")
            logger.error(f"Expected files in: {self.data_dir}")
            return {}
        
        logger.info(f"Found {len(available_files)} data files:")
        for file in available_files:
            size_mb = file.stat().st_size / 1024 / 1024
            logger.info(f"  {file.name}: {size_mb:.1f}MB")
        
        # Get initial database stats
        initial_stats = self.db.get_database_stats()
        logger.info(f"Initial database records: {initial_stats['total_records']}")
        
        # Load each service
        results = {}
        
        for filepath in available_files:
            service_code = filepath.name.replace('_pricing.json', '')
            
            logger.info(f"\n[Loading] {service_code}...")
            results[service_code] = self.load_service_data(service_code)
        
        # Get final database stats
        final_stats = self.db.get_database_stats()
        records_added = final_stats['total_records'] - initial_stats['total_records']
        
        logger.info("\n" + "=" * 60)
        logger.info("LOADING SUMMARY")
        logger.info("=" * 60)
        
        successful_loads = sum(1 for success in results.values() if success)
        total_loads = len(results)
        
        logger.info(f"Successful loads: {successful_loads}/{total_loads}")
        logger.info(f"Records added: {records_added}")
        logger.info(f"Total database records: {final_stats['total_records']}")
        
        for service, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"{status} {service}")
        
        if successful_loads == total_loads:
            logger.info("\n🎉 ALL DATA LOADED SUCCESSFULLY!")
            logger.info("\nDatabase is ready for development with real AWS pricing data")
        else:
            logger.error(f"\n⚠️  {total_loads - successful_loads} services failed to load")
        
        return results
    
    def validate_loaded_data(self) -> Dict[str, any]:
        """Validate the loaded pricing data"""
        
        logger.info("Validating loaded pricing data...")
        
        validation_results = {
            'database_stats': self.db.get_database_stats(),
            'sample_prices': {},
            'validation_errors': []
        }
        
        # Test some sample pricing lookups
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
                    error = f"No pricing found for {instance_type} in {region}"
                    validation_results['validation_errors'].append(error)
                    logger.warning(f"⚠️  {error}")
            except Exception as e:
                error = f"Pricing lookup failed for {instance_type} in {region}: {e}"
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
    """Main function for offline data loading"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Load downloaded AWS pricing data into database")
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
    if any(results.values()):
        logger.info("\n✅ Data loading completed successfully!")
        logger.info("You can now use the local pricing service with real AWS data")
        sys.exit(0)
    else:
        logger.error("\n❌ All data loading failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
