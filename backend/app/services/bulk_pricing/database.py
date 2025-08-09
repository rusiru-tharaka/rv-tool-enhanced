"""
SQLite Database Management for AWS Pricing Data
Handles database creation, schema management, and data operations
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
import json

logger = logging.getLogger(__name__)

class PricingDatabase:
    """SQLite database manager for AWS pricing data"""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            db_path = Path(__file__).parent.parent / "pricing_database.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        logger.info(f"Pricing database initialized at: {self.db_path}")
    
    def _init_database(self):
        """Create database tables and indexes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Main EC2 pricing table
                CREATE TABLE IF NOT EXISTS ec2_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_type VARCHAR(20) NOT NULL,
                    region VARCHAR(20) NOT NULL,
                    location VARCHAR(50) NOT NULL,
                    operating_system VARCHAR(20) NOT NULL,
                    tenancy VARCHAR(20) NOT NULL,
                    pricing_model VARCHAR(30) NOT NULL,
                    term_length VARCHAR(10), -- For reserved instances
                    payment_option VARCHAR(20), -- For reserved instances
                    price_per_hour DECIMAL(12,8) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    effective_date DATE NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(instance_type, region, operating_system, tenancy, pricing_model, term_length, payment_option)
                );

                -- EBS storage pricing table
                CREATE TABLE IF NOT EXISTS ebs_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    volume_type VARCHAR(20) NOT NULL,
                    region VARCHAR(20) NOT NULL,
                    location VARCHAR(50) NOT NULL,
                    price_per_gb_month DECIMAL(10,6) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    effective_date DATE NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(volume_type, region)
                );

                -- Update tracking table
                CREATE TABLE IF NOT EXISTS pricing_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_date DATE NOT NULL,
                    service_code VARCHAR(20) NOT NULL,
                    records_updated INTEGER NOT NULL,
                    update_duration_seconds INTEGER,
                    status VARCHAR(20) NOT NULL, -- SUCCESS, FAILED, PARTIAL
                    error_message TEXT,
                    file_size_mb DECIMAL(8,2),
                    UNIQUE(update_date, service_code)
                );

                -- Performance indexes
                CREATE INDEX IF NOT EXISTS idx_ec2_lookup ON ec2_pricing(instance_type, region, operating_system, tenancy, pricing_model);
                CREATE INDEX IF NOT EXISTS idx_ec2_region ON ec2_pricing(region);
                CREATE INDEX IF NOT EXISTS idx_ec2_instance ON ec2_pricing(instance_type);
                CREATE INDEX IF NOT EXISTS idx_ebs_lookup ON ebs_pricing(volume_type, region);
                CREATE INDEX IF NOT EXISTS idx_updates_date ON pricing_updates(update_date DESC);
            """)
            conn.commit()
    
    def get_ec2_pricing(self, 
                       instance_type: str, 
                       region: str, 
                       operating_system: str = 'Linux',
                       tenancy: str = 'Shared',
                       pricing_model: str = 'OnDemand',
                       term_length: str = None,
                       payment_option: str = None) -> Optional[float]:
        """Get EC2 instance pricing from local database"""
        
        query = """
            SELECT price_per_hour 
            FROM ec2_pricing 
            WHERE instance_type = ? 
            AND region = ? 
            AND operating_system = ? 
            AND tenancy = ? 
            AND pricing_model = ?
        """
        params = [instance_type, region, operating_system, tenancy, pricing_model]
        
        # Add optional parameters for reserved instances
        if term_length:
            query += " AND term_length = ?"
            params.append(term_length)
        if payment_option:
            query += " AND payment_option = ?"
            params.append(payment_option)
            
        query += " ORDER BY last_updated DESC LIMIT 1"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                result = cursor.fetchone()
                
                if result:
                    logger.debug(f"Found pricing for {instance_type} in {region}: ${result[0]:.6f}/hour")
                    return float(result[0])
                else:
                    logger.debug(f"No pricing found for {instance_type} in {region} with model {pricing_model}")
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"Database error getting EC2 pricing: {e}")
            return None
    
    def get_ebs_pricing(self, volume_type: str, region: str) -> Optional[float]:
        """Get EBS storage pricing from local database"""
        
        query = """
            SELECT price_per_gb_month 
            FROM ebs_pricing 
            WHERE volume_type = ? AND region = ?
            ORDER BY last_updated DESC LIMIT 1
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, [volume_type, region])
                result = cursor.fetchone()
                
                if result:
                    logger.debug(f"Found EBS pricing for {volume_type} in {region}: ${result[0]:.6f}/GB/month")
                    return float(result[0])
                else:
                    logger.debug(f"No EBS pricing found for {volume_type} in {region}")
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"Database error getting EBS pricing: {e}")
            return None
    
    def bulk_insert_ec2_pricing(self, pricing_data: List[Dict]) -> int:
        """Bulk insert EC2 pricing data"""
        
        insert_query = """
            INSERT OR REPLACE INTO ec2_pricing 
            (instance_type, region, location, operating_system, tenancy, pricing_model, 
             term_length, payment_option, price_per_hour, currency, effective_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.executemany(insert_query, [
                    (
                        item['instance_type'],
                        item['region'],
                        item['location'],
                        item['operating_system'],
                        item['tenancy'],
                        item['pricing_model'],
                        item.get('term_length'),
                        item.get('payment_option'),
                        item['price_per_hour'],
                        item['currency'],
                        item['effective_date']
                    ) for item in pricing_data
                ])
                
                rows_affected = cursor.rowcount
                conn.commit()
                logger.info(f"Bulk inserted {rows_affected} EC2 pricing records")
                return rows_affected
                
        except sqlite3.Error as e:
            logger.error(f"Database error bulk inserting EC2 pricing: {e}")
            return 0
    
    def bulk_insert_ebs_pricing(self, pricing_data: List[Dict]) -> int:
        """Bulk insert EBS pricing data"""
        
        insert_query = """
            INSERT OR REPLACE INTO ebs_pricing 
            (volume_type, region, location, price_per_gb_month, currency, effective_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.executemany(insert_query, [
                    (
                        item['volume_type'],
                        item['region'],
                        item['location'],
                        item['price_per_gb_month'],
                        item['currency'],
                        item['effective_date']
                    ) for item in pricing_data
                ])
                
                rows_affected = cursor.rowcount
                conn.commit()
                logger.info(f"Bulk inserted {rows_affected} EBS pricing records")
                return rows_affected
                
        except sqlite3.Error as e:
            logger.error(f"Database error bulk inserting EBS pricing: {e}")
            return 0
    
    def record_update(self, service_code: str, records_updated: int, 
                     duration_seconds: int, status: str, 
                     error_message: str = None, file_size_mb: float = None):
        """Record pricing update statistics"""
        
        insert_query = """
            INSERT OR REPLACE INTO pricing_updates 
            (update_date, service_code, records_updated, update_duration_seconds, 
             status, error_message, file_size_mb)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(insert_query, [
                    date.today(),
                    service_code,
                    records_updated,
                    duration_seconds,
                    status,
                    error_message,
                    file_size_mb
                ])
                conn.commit()
                logger.info(f"Recorded update for {service_code}: {status}")
                
        except sqlite3.Error as e:
            logger.error(f"Database error recording update: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                
                # EC2 pricing stats
                cursor = conn.execute("SELECT COUNT(*) FROM ec2_pricing")
                stats['ec2_records'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT region) FROM ec2_pricing")
                stats['ec2_regions'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT instance_type) FROM ec2_pricing")
                stats['ec2_instance_types'] = cursor.fetchone()[0]
                
                # EBS pricing stats
                cursor = conn.execute("SELECT COUNT(*) FROM ebs_pricing")
                stats['ebs_records'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT region) FROM ebs_pricing")
                stats['ebs_regions'] = cursor.fetchone()[0]
                
                # Last update info
                cursor = conn.execute("""
                    SELECT service_code, update_date, status 
                    FROM pricing_updates 
                    ORDER BY update_date DESC, id DESC 
                    LIMIT 5
                """)
                stats['recent_updates'] = cursor.fetchall()
                
                # Database file size
                stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old pricing data"""
        
        cutoff_date = date.today().replace(day=1)  # Keep current month
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clean up old update records
                cursor = conn.execute("""
                    DELETE FROM pricing_updates 
                    WHERE update_date < date('now', '-{} days')
                """.format(days_to_keep))
                
                deleted_updates = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_updates} old update records")
                
        except sqlite3.Error as e:
            logger.error(f"Database error during cleanup: {e}")
    
    def close(self):
        """Close database connection"""
        # SQLite connections are closed automatically with context managers
        pass
