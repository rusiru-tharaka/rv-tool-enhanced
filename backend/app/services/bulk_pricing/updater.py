"""
Pricing Updater Service
Handles daily updates of AWS pricing data
"""

import logging
import time
from datetime import datetime, date
from typing import Dict, List, Optional
import asyncio

from .downloader import BulkPriceDownloader
from .parser import AWSPricingParser
from .database import PricingDatabase

logger = logging.getLogger(__name__)

class PricingUpdater:
    """Manages daily pricing data updates"""
    
    def __init__(self, db_path: str = None, cache_dir: str = None):
        """Initialize pricing updater"""
        self.db = PricingDatabase(db_path)
        self.downloader = BulkPriceDownloader(cache_dir)
        self.parser = AWSPricingParser()
        
        logger.info("Pricing Updater initialized")
    
    async def update_all_pricing(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """Update all pricing data"""
        
        logger.info("Starting comprehensive pricing update")
        start_time = time.time()
        
        results = {
            'update_date': date.today().isoformat(),
            'start_time': datetime.now().isoformat(),
            'services': {},
            'summary': {}
        }
        
        # Services to update
        services = ['AmazonEC2', 'AmazonEBS']
        
        for service_code in services:
            service_result = await self._update_service_pricing(service_code, force_refresh)
            results['services'][service_code] = service_result
        
        # Calculate summary
        total_time = time.time() - start_time
        successful_services = sum(1 for result in results['services'].values() if result['status'] == 'SUCCESS')
        
        results['summary'] = {
            'total_services': len(services),
            'successful_services': successful_services,
            'failed_services': len(services) - successful_services,
            'total_duration_seconds': round(total_time, 2),
            'end_time': datetime.now().isoformat()
        }
        
        logger.info(f"Pricing update completed: {successful_services}/{len(services)} services in {total_time:.1f}s")
        
        return results
    
    async def _update_service_pricing(self, service_code: str, force_refresh: bool = False) -> Dict:
        """Update pricing for a specific service"""
        
        logger.info(f"Updating pricing for {service_code}")
        start_time = time.time()
        
        result = {
            'service_code': service_code,
            'status': 'FAILED',
            'records_updated': 0,
            'duration_seconds': 0,
            'error_message': None,
            'file_size_mb': 0
        }
        
        try:
            # Download pricing data
            pricing_data = self.downloader.download_service_pricing(service_code, force_refresh)
            
            if not pricing_data:
                result['error_message'] = f"Failed to download pricing data for {service_code}"
                return result
            
            # Estimate file size (rough approximation)
            import json
            result['file_size_mb'] = len(json.dumps(pricing_data, separators=(',', ':'))) / (1024 * 1024)
            
            # Parse and insert data
            if service_code == 'AmazonEC2':
                records_updated = await self._update_ec2_pricing(pricing_data)
            elif service_code == 'AmazonEBS':
                records_updated = await self._update_ebs_pricing(pricing_data)
            else:
                result['error_message'] = f"Unsupported service: {service_code}"
                return result
            
            result['records_updated'] = records_updated
            result['status'] = 'SUCCESS' if records_updated > 0 else 'PARTIAL'
            
            if records_updated == 0:
                result['error_message'] = "No records were updated"
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"Error updating {service_code}: {e}")
        
        finally:
            result['duration_seconds'] = round(time.time() - start_time, 2)
            
            # Record update in database
            self.db.record_update(
                service_code=service_code,
                records_updated=result['records_updated'],
                duration_seconds=result['duration_seconds'],
                status=result['status'],
                error_message=result['error_message'],
                file_size_mb=result['file_size_mb']
            )
        
        logger.info(f"{service_code} update: {result['status']} - {result['records_updated']} records in {result['duration_seconds']}s")
        
        return result
    
    async def _update_ec2_pricing(self, pricing_data: Dict) -> int:
        """Update EC2 pricing data"""
        
        logger.info("Parsing EC2 pricing data")
        self.parser.reset_stats()
        
        # Parse pricing data in batches
        batch_size = 1000
        batch = []
        total_records = 0
        
        for pricing_record in self.parser.parse_ec2_pricing(pricing_data):
            batch.append(pricing_record)
            
            if len(batch) >= batch_size:
                records_inserted = self.db.bulk_insert_ec2_pricing(batch)
                total_records += records_inserted
                batch = []
                
                # Log progress
                if total_records % 10000 == 0:
                    logger.info(f"EC2 pricing: {total_records} records processed")
        
        # Insert remaining records
        if batch:
            records_inserted = self.db.bulk_insert_ec2_pricing(batch)
            total_records += records_inserted
        
        parsing_stats = self.parser.get_parsing_stats()
        logger.info(f"EC2 pricing update completed: {total_records} records, {parsing_stats['errors']} errors")
        
        return total_records
    
    async def _update_ebs_pricing(self, pricing_data: Dict) -> int:
        """Update EBS pricing data"""
        
        logger.info("Parsing EBS pricing data")
        self.parser.reset_stats()
        
        # Parse pricing data in batches
        batch_size = 1000
        batch = []
        total_records = 0
        
        for pricing_record in self.parser.parse_ebs_pricing(pricing_data):
            batch.append(pricing_record)
            
            if len(batch) >= batch_size:
                records_inserted = self.db.bulk_insert_ebs_pricing(batch)
                total_records += records_inserted
                batch = []
        
        # Insert remaining records
        if batch:
            records_inserted = self.db.bulk_insert_ebs_pricing(batch)
            total_records += records_inserted
        
        parsing_stats = self.parser.get_parsing_stats()
        logger.info(f"EBS pricing update completed: {total_records} records, {parsing_stats['errors']} errors")
        
        return total_records
    
    def get_update_history(self, days: int = 7) -> List[Dict]:
        """Get recent update history"""
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        update_date,
                        service_code,
                        records_updated,
                        update_duration_seconds,
                        status,
                        error_message,
                        file_size_mb
                    FROM pricing_updates 
                    WHERE update_date >= date('now', '-{} days')
                    ORDER BY update_date DESC, service_code
                """.format(days))
                
                columns = ['update_date', 'service_code', 'records_updated', 
                          'duration_seconds', 'status', 'error_message', 'file_size_mb']
                
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting update history: {e}")
            return []
    
    def validate_pricing_data(self) -> Dict:
        """Validate current pricing data integrity"""
        
        logger.info("Validating pricing data integrity")
        
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'PASS',
            'checks': {}
        }
        
        try:
            # Check 1: Database connectivity
            stats = self.db.get_database_stats()
            validation_results['checks']['database_connectivity'] = {
                'status': 'PASS' if stats else 'FAIL',
                'details': stats
            }
            
            # Check 2: EC2 pricing data completeness
            ec2_records = stats.get('ec2_records', 0)
            ec2_regions = stats.get('ec2_regions', 0)
            ec2_instance_types = stats.get('ec2_instance_types', 0)
            
            ec2_check = {
                'status': 'PASS',
                'records': ec2_records,
                'regions': ec2_regions,
                'instance_types': ec2_instance_types,
                'issues': []
            }
            
            if ec2_records < 10000:  # Expect at least 10k EC2 pricing records
                ec2_check['status'] = 'WARN'
                ec2_check['issues'].append(f"Low EC2 record count: {ec2_records}")
            
            if ec2_regions < 15:  # Expect at least 15 regions
                ec2_check['status'] = 'WARN'
                ec2_check['issues'].append(f"Low region count: {ec2_regions}")
            
            if ec2_instance_types < 100:  # Expect at least 100 instance types
                ec2_check['status'] = 'WARN'
                ec2_check['issues'].append(f"Low instance type count: {ec2_instance_types}")
            
            validation_results['checks']['ec2_completeness'] = ec2_check
            
            # Check 3: EBS pricing data completeness
            ebs_records = stats.get('ebs_records', 0)
            ebs_regions = stats.get('ebs_regions', 0)
            
            ebs_check = {
                'status': 'PASS',
                'records': ebs_records,
                'regions': ebs_regions,
                'issues': []
            }
            
            if ebs_records < 100:  # Expect at least 100 EBS pricing records
                ebs_check['status'] = 'WARN'
                ebs_check['issues'].append(f"Low EBS record count: {ebs_records}")
            
            validation_results['checks']['ebs_completeness'] = ebs_check
            
            # Check 4: Recent updates
            recent_updates = stats.get('recent_updates', [])
            update_check = {
                'status': 'PASS',
                'recent_updates': recent_updates,
                'issues': []
            }
            
            if not recent_updates:
                update_check['status'] = 'FAIL'
                update_check['issues'].append("No recent updates found")
            else:
                # Check if updates are recent (within 2 days)
                latest_update = recent_updates[0] if recent_updates else None
                if latest_update:
                    update_date = datetime.strptime(latest_update[1], '%Y-%m-%d').date()
                    days_old = (date.today() - update_date).days
                    
                    if days_old > 2:
                        update_check['status'] = 'WARN'
                        update_check['issues'].append(f"Latest update is {days_old} days old")
            
            validation_results['checks']['recent_updates'] = update_check
            
            # Determine overall status
            check_statuses = [check['status'] for check in validation_results['checks'].values()]
            if 'FAIL' in check_statuses:
                validation_results['overall_status'] = 'FAIL'
            elif 'WARN' in check_statuses:
                validation_results['overall_status'] = 'WARN'
            
        except Exception as e:
            validation_results['overall_status'] = 'FAIL'
            validation_results['error'] = str(e)
            logger.error(f"Validation error: {e}")
        
        logger.info(f"Pricing data validation: {validation_results['overall_status']}")
        
        return validation_results
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old pricing data"""
        
        logger.info(f"Cleaning up pricing data older than {days_to_keep} days")
        
        try:
            self.db.cleanup_old_data(days_to_keep)
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def close(self):
        """Close all connections"""
        self.downloader.close()
        self.db.close()

# Create global instance
pricing_updater = PricingUpdater()
