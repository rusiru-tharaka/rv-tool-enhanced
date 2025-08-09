"""
Enhanced Database Methods
Adds missing methods for storing and retrieving pricing data
"""

import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedPricingDatabase:
    """Enhanced pricing database with additional methods"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = "pricing_database.db"
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
        logger.info(f"Enhanced database initialized: {db_path}")
    
    def store_ec2_pricing(
        self,
        instance_type: str,
        region: str,
        pricing_model: str,
        price_per_hour: float,
        term_length: str = None,
        payment_option: str = None,
        operating_system: str = 'Linux',
        tenancy: str = 'Shared'
    ):
        """Store EC2 pricing data in database with conflict resolution"""
        
        location = self._get_region_location(region)
        
        # Use INSERT OR REPLACE to handle duplicates
        query = """
        INSERT OR REPLACE INTO ec2_pricing 
        (instance_type, region, location, operating_system, tenancy, 
         pricing_model, term_length, payment_option, price_per_hour, 
         currency, effective_date, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'USD', date('now'), datetime('now'))
        """
        
        try:
            self.cursor.execute(query, (
                instance_type, region, location, operating_system, tenancy,
                pricing_model, term_length, payment_option, price_per_hour
            ))
            self.conn.commit()
            
            logger.debug(f"Stored pricing: {instance_type} {region} {pricing_model} ${price_per_hour:.4f}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to store pricing data: {e}")
            raise
    
    def store_storage_pricing(
        self,
        volume_type: str,
        region: str,
        price_per_gb_month: float
    ):
        """Store EBS storage pricing data"""
        
        location = self._get_region_location(region)
        
        query = """
        INSERT OR REPLACE INTO ebs_pricing 
        (volume_type, region, location, price_per_gb_month, currency, effective_date, last_updated)
        VALUES (?, ?, ?, ?, 'USD', date('now'), datetime('now'))
        """
        
        try:
            self.cursor.execute(query, (volume_type, region, location, price_per_gb_month))
            self.conn.commit()
            
            logger.debug(f"Stored storage pricing: {volume_type} {region} ${price_per_gb_month:.4f}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to store storage pricing: {e}")
            raise
    
    def get_region_pricing_summary(self, region: str) -> Dict:
        """Get comprehensive pricing coverage summary for a region"""
        
        try:
            # Get EC2 pricing summary
            ec2_query = """
            SELECT 
                pricing_model,
                term_length,
                payment_option,
                COUNT(*) as count,
                COUNT(DISTINCT instance_type) as unique_instances,
                MIN(price_per_hour) as min_price,
                MAX(price_per_hour) as max_price,
                AVG(price_per_hour) as avg_price
            FROM ec2_pricing 
            WHERE region = ?
            GROUP BY pricing_model, term_length, payment_option
            ORDER BY pricing_model, term_length
            """
            
            self.cursor.execute(ec2_query, (region,))
            ec2_results = self.cursor.fetchall()
            
            # Get storage pricing summary
            storage_query = """
            SELECT 
                volume_type,
                price_per_gb_month,
                last_updated
            FROM ebs_pricing 
            WHERE region = ?
            ORDER BY volume_type
            """
            
            self.cursor.execute(storage_query, (region,))
            storage_results = self.cursor.fetchall()
            
            # Get unique instance count
            instance_query = "SELECT COUNT(DISTINCT instance_type) FROM ec2_pricing WHERE region = ?"
            self.cursor.execute(instance_query, (region,))
            unique_instances = self.cursor.fetchone()[0]
            
            # Get total record count
            total_query = "SELECT COUNT(*) FROM ec2_pricing WHERE region = ?"
            self.cursor.execute(total_query, (region,))
            total_records = self.cursor.fetchone()[0]
            
            summary = {
                'region': region,
                'location': self._get_region_location(region),
                'last_updated': datetime.now().isoformat(),
                'ec2_pricing': {
                    'total_records': total_records,
                    'unique_instances': unique_instances,
                    'pricing_models': []
                },
                'storage_pricing': {
                    'volume_types': len(storage_results),
                    'volumes': []
                }
            }
            
            # Process EC2 pricing models
            for row in ec2_results:
                model_info = {
                    'pricing_model': row[0],
                    'term_length': row[1],
                    'payment_option': row[2],
                    'record_count': row[3],
                    'unique_instances': row[4],
                    'price_range': {
                        'min': round(row[5], 4) if row[5] else None,
                        'max': round(row[6], 4) if row[6] else None,
                        'avg': round(row[7], 4) if row[7] else None
                    }
                }
                summary['ec2_pricing']['pricing_models'].append(model_info)
            
            # Process storage pricing
            for row in storage_results:
                volume_info = {
                    'volume_type': row[0],
                    'price_per_gb_month': round(row[1], 4),
                    'last_updated': row[2]
                }
                summary['storage_pricing']['volumes'].append(volume_info)
            
            return summary
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get region summary: {e}")
            raise
    
    def get_missing_pricing_report(self, region: str, required_instances: List[str]) -> Dict:
        """Generate report of missing pricing data for required instances"""
        
        report = {
            'region': region,
            'required_instances': len(required_instances),
            'analysis': {
                'complete': [],
                'partial': [],
                'missing': []
            },
            'summary': {
                'complete_count': 0,
                'partial_count': 0,
                'missing_count': 0,
                'completion_rate': 0.0
            }
        }
        
        for instance_type in required_instances:
            # Check what pricing data exists
            pricing_check = self._check_instance_pricing_completeness(instance_type, region)
            
            if pricing_check['complete']:
                report['analysis']['complete'].append({
                    'instance_type': instance_type,
                    'available_models': pricing_check['available_models']
                })
                report['summary']['complete_count'] += 1
                
            elif pricing_check['partial']:
                report['analysis']['partial'].append({
                    'instance_type': instance_type,
                    'available_models': pricing_check['available_models'],
                    'missing_models': pricing_check['missing_models']
                })
                report['summary']['partial_count'] += 1
                
            else:
                report['analysis']['missing'].append({
                    'instance_type': instance_type,
                    'reason': 'No pricing data found'
                })
                report['summary']['missing_count'] += 1
        
        # Calculate completion rate
        total = len(required_instances)
        if total > 0:
            report['summary']['completion_rate'] = (report['summary']['complete_count'] / total) * 100
        
        return report
    
    def _check_instance_pricing_completeness(self, instance_type: str, region: str) -> Dict:
        """Check completeness of pricing data for a specific instance"""
        
        query = """
        SELECT pricing_model, term_length, payment_option, price_per_hour
        FROM ec2_pricing 
        WHERE instance_type = ? AND region = ?
        ORDER BY pricing_model, term_length, payment_option
        """
        
        self.cursor.execute(query, (instance_type, region))
        results = self.cursor.fetchall()
        
        available_models = []
        for row in results:
            model_key = f"{row[0]}"
            if row[1]:  # term_length
                model_key += f"_{row[1]}"
            if row[2]:  # payment_option
                model_key += f"_{row[2].replace(' ', '_')}"
            
            available_models.append({
                'model': model_key,
                'pricing_model': row[0],
                'term_length': row[1],
                'payment_option': row[2],
                'price_per_hour': row[3]
            })
        
        # Define required models for completeness
        required_models = [
            'OnDemand',
            'Reserved_1yr_No_Upfront',
            'Reserved_3yr_No_Upfront'
        ]
        
        available_model_keys = [model['model'] for model in available_models]
        missing_models = [model for model in required_models if model not in available_model_keys]
        
        return {
            'complete': len(missing_models) == 0,
            'partial': len(available_models) > 0 and len(missing_models) > 0,
            'available_models': available_models,
            'missing_models': missing_models
        }
    
    def _get_region_location(self, region: str) -> str:
        """Map region code to location name"""
        region_map = {
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'Europe (Ireland)',
            'eu-west-2': 'Europe (London)',
            'eu-west-3': 'Europe (Paris)',
            'eu-central-1': 'Europe (Frankfurt)',
            'ca-central-1': 'Canada (Central)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            'ap-northeast-2': 'Asia Pacific (Seoul)',
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'sa-east-1': 'South America (São Paulo)'
        }
        return region_map.get(region, region)
    
    def vacuum_database(self):
        """Optimize database by running VACUUM"""
        try:
            self.cursor.execute("VACUUM")
            logger.info("Database vacuum completed")
        except sqlite3.Error as e:
            logger.error(f"Database vacuum failed: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get overall database statistics"""
        
        stats = {
            'database_path': self.db_path,
            'timestamp': datetime.now().isoformat(),
            'tables': {}
        }
        
        # Get table statistics
        tables = ['ec2_pricing', 'ebs_pricing', 'pricing_updates']
        
        for table in tables:
            try:
                # Get row count
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = self.cursor.fetchone()[0]
                
                # Get table info
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = self.cursor.fetchall()
                
                stats['tables'][table] = {
                    'row_count': row_count,
                    'column_count': len(columns),
                    'columns': [col[1] for col in columns]  # Column names
                }
                
            except sqlite3.Error as e:
                logger.error(f"Failed to get stats for table {table}: {e}")
                stats['tables'][table] = {'error': str(e)}
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# Extend the original database class
def enhance_database_class():
    """Add enhanced methods to the original PricingDatabase class"""
    
    from .database import PricingDatabase
    
    # Add new methods to the existing class
    PricingDatabase.store_ec2_pricing = EnhancedPricingDatabase.store_ec2_pricing
    PricingDatabase.store_storage_pricing = EnhancedPricingDatabase.store_storage_pricing
    PricingDatabase.get_region_pricing_summary = EnhancedPricingDatabase.get_region_pricing_summary
    PricingDatabase.get_missing_pricing_report = EnhancedPricingDatabase.get_missing_pricing_report
    PricingDatabase._check_instance_pricing_completeness = EnhancedPricingDatabase._check_instance_pricing_completeness
    PricingDatabase._get_region_location = EnhancedPricingDatabase._get_region_location
    PricingDatabase.vacuum_database = EnhancedPricingDatabase.vacuum_database
    PricingDatabase.get_database_stats = EnhancedPricingDatabase.get_database_stats
    
    logger.info("Enhanced database methods added to PricingDatabase class")

# Auto-enhance when imported
enhance_database_class()
