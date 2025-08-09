"""
Historical Pricing Service
Manages historical pricing data storage and retrieval
Provides trend analysis and pricing history capabilities
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import asyncio
from dataclasses import dataclass
import asyncpg
from .sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

from .aws_pricing_service import InstancePricing, StoragePricing, SavingsPlansPrice
from .database import get_database_url

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PricingTrend:
    """Pricing trend analysis data"""
    instance_type: str
    region: str
    current_price: float
    price_30_days_ago: Optional[float]
    price_90_days_ago: Optional[float]
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_percentage: float
    volatility_score: float  # 0-100, higher = more volatile
    
@dataclass
class PricingForecast:
    """Pricing forecast data"""
    instance_type: str
    region: str
    forecast_30_days: float
    forecast_90_days: float
    confidence_score: float  # 0-1
    forecast_method: str

class HistoricalPricingService:
    """
    Service for managing historical pricing data and trend analysis
    """
    
    def __init__(self):
        self.database_url = get_database_url()
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info("Historical Pricing Service initialized")
    
    async def store_instance_pricing(
        self,
        pricing_data: Dict[str, InstancePricing],
        region: str,
        price_date: date = None
    ) -> bool:
        """Store instance pricing data for historical analysis"""
        
        if price_date is None:
            price_date = date.today()
        
        try:
            with self.SessionLocal() as session:
                for instance_type, pricing in pricing_data.items():
                    # Check if record already exists for this date
                    existing_query = text("""
                        SELECT id FROM historical_instance_pricing 
                        WHERE instance_type = :instance_type 
                        AND region = :region 
                        AND price_date = :price_date
                        AND os_type = :os_type
                    """)
                    
                    existing = session.execute(existing_query, {
                        'instance_type': instance_type,
                        'region': region,
                        'price_date': price_date,
                        'os_type': 'linux'  # Default to linux for now
                    }).fetchone()
                    
                    if existing:
                        # Update existing record
                        update_query = text("""
                            UPDATE historical_instance_pricing 
                            SET on_demand_hourly = :on_demand_hourly,
                                reserved_1yr_hourly = :reserved_1yr_hourly,
                                reserved_3yr_hourly = :reserved_3yr_hourly,
                                vcpu = :vcpu,
                                memory_gb = :memory_gb,
                                storage_type = :storage_type,
                                network_performance = :network_performance,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        
                        session.execute(update_query, {
                            'id': existing.id,
                            'on_demand_hourly': pricing.on_demand_hourly,
                            'reserved_1yr_hourly': pricing.reserved_1yr_hourly,
                            'reserved_3yr_hourly': pricing.reserved_3yr_hourly,
                            'vcpu': pricing.vcpu,
                            'memory_gb': pricing.memory_gb,
                            'storage_type': pricing.storage_type,
                            'network_performance': pricing.network_performance
                        })
                    else:
                        # Insert new record
                        insert_query = text("""
                            INSERT INTO historical_instance_pricing (
                                instance_type, region, os_type, on_demand_hourly,
                                reserved_1yr_hourly, reserved_3yr_hourly, vcpu,
                                memory_gb, storage_type, network_performance,
                                currency, price_date
                            ) VALUES (
                                :instance_type, :region, :os_type, :on_demand_hourly,
                                :reserved_1yr_hourly, :reserved_3yr_hourly, :vcpu,
                                :memory_gb, :storage_type, :network_performance,
                                :currency, :price_date
                            )
                        """)
                        
                        session.execute(insert_query, {
                            'instance_type': instance_type,
                            'region': region,
                            'os_type': 'linux',
                            'on_demand_hourly': pricing.on_demand_hourly,
                            'reserved_1yr_hourly': pricing.reserved_1yr_hourly,
                            'reserved_3yr_hourly': pricing.reserved_3yr_hourly,
                            'vcpu': pricing.vcpu,
                            'memory_gb': pricing.memory_gb,
                            'storage_type': pricing.storage_type,
                            'network_performance': pricing.network_performance,
                            'currency': pricing.currency,
                            'price_date': price_date
                        })
                
                session.commit()
                logger.info(f"Stored {len(pricing_data)} instance pricing records for {price_date}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store instance pricing data: {e}")
            return False
    
    async def store_storage_pricing(
        self,
        storage_pricing: StoragePricing,
        region: str,
        price_date: date = None
    ) -> bool:
        """Store storage pricing data for historical analysis"""
        
        if price_date is None:
            price_date = date.today()
        
        try:
            with self.SessionLocal() as session:
                # Check if record already exists
                existing_query = text("""
                    SELECT id FROM historical_storage_pricing 
                    WHERE storage_type = :storage_type 
                    AND region = :region 
                    AND price_date = :price_date
                """)
                
                existing = session.execute(existing_query, {
                    'storage_type': storage_pricing.storage_type,
                    'region': region,
                    'price_date': price_date
                }).fetchone()
                
                if existing:
                    # Update existing record
                    update_query = text("""
                        UPDATE historical_storage_pricing 
                        SET price_per_gb_month = :price_per_gb_month,
                            iops_price = :iops_price,
                            throughput_price = :throughput_price,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    
                    session.execute(update_query, {
                        'id': existing.id,
                        'price_per_gb_month': storage_pricing.price_per_gb_month,
                        'iops_price': storage_pricing.iops_price,
                        'throughput_price': storage_pricing.throughput_price
                    })
                else:
                    # Insert new record
                    insert_query = text("""
                        INSERT INTO historical_storage_pricing (
                            storage_type, region, price_per_gb_month,
                            iops_price, throughput_price, currency, price_date
                        ) VALUES (
                            :storage_type, :region, :price_per_gb_month,
                            :iops_price, :throughput_price, :currency, :price_date
                        )
                    """)
                    
                    session.execute(insert_query, {
                        'storage_type': storage_pricing.storage_type,
                        'region': region,
                        'price_per_gb_month': storage_pricing.price_per_gb_month,
                        'iops_price': storage_pricing.iops_price,
                        'throughput_price': storage_pricing.throughput_price,
                        'currency': storage_pricing.currency,
                        'price_date': price_date
                    })
                
                session.commit()
                logger.info(f"Stored storage pricing for {storage_pricing.storage_type} on {price_date}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store storage pricing data: {e}")
            return False
    
    async def store_savings_plans_pricing(
        self,
        savings_plans: List[SavingsPlansPrice],
        region: str,
        price_date: date = None
    ) -> bool:
        """Store Savings Plans pricing data"""
        
        if price_date is None:
            price_date = date.today()
        
        try:
            with self.SessionLocal() as session:
                for savings_plan in savings_plans:
                    # Check if record already exists
                    existing_query = text("""
                        SELECT id FROM savings_plans_pricing 
                        WHERE plan_type = :plan_type 
                        AND instance_family = :instance_family
                        AND region = :region 
                        AND commitment_term = :commitment_term
                        AND payment_option = :payment_option
                        AND price_date = :price_date
                    """)
                    
                    existing = session.execute(existing_query, {
                        'plan_type': savings_plan.plan_type,
                        'instance_family': savings_plan.instance_family,
                        'region': region,
                        'commitment_term': savings_plan.commitment_term,
                        'payment_option': savings_plan.payment_option,
                        'price_date': price_date
                    }).fetchone()
                    
                    if existing:
                        # Update existing record
                        update_query = text("""
                            UPDATE savings_plans_pricing 
                            SET hourly_rate = :hourly_rate,
                                upfront_cost = :upfront_cost,
                                effective_hourly_rate = :effective_hourly_rate,
                                on_demand_equivalent = :on_demand_equivalent,
                                savings_percentage = :savings_percentage,
                                break_even_hours = :break_even_hours,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        
                        session.execute(update_query, {
                            'id': existing.id,
                            'hourly_rate': savings_plan.hourly_rate,
                            'upfront_cost': savings_plan.upfront_cost,
                            'effective_hourly_rate': savings_plan.effective_hourly_rate,
                            'on_demand_equivalent': savings_plan.on_demand_equivalent,
                            'savings_percentage': savings_plan.savings_percentage,
                            'break_even_hours': savings_plan.break_even_hours
                        })
                    else:
                        # Insert new record
                        insert_query = text("""
                            INSERT INTO savings_plans_pricing (
                                plan_type, instance_family, region, commitment_term,
                                payment_option, hourly_rate, upfront_cost,
                                effective_hourly_rate, on_demand_equivalent,
                                savings_percentage, break_even_hours, currency,
                                os_type, price_date
                            ) VALUES (
                                :plan_type, :instance_family, :region, :commitment_term,
                                :payment_option, :hourly_rate, :upfront_cost,
                                :effective_hourly_rate, :on_demand_equivalent,
                                :savings_percentage, :break_even_hours, :currency,
                                :os_type, :price_date
                            )
                        """)
                        
                        session.execute(insert_query, {
                            'plan_type': savings_plan.plan_type,
                            'instance_family': savings_plan.instance_family,
                            'region': region,
                            'commitment_term': savings_plan.commitment_term,
                            'payment_option': savings_plan.payment_option,
                            'hourly_rate': savings_plan.hourly_rate,
                            'upfront_cost': savings_plan.upfront_cost,
                            'effective_hourly_rate': savings_plan.effective_hourly_rate,
                            'on_demand_equivalent': savings_plan.on_demand_equivalent,
                            'savings_percentage': savings_plan.savings_percentage,
                            'break_even_hours': savings_plan.break_even_hours,
                            'currency': savings_plan.currency,
                            'os_type': savings_plan.os_type,
                            'price_date': price_date
                        })
                
                session.commit()
                logger.info(f"Stored {len(savings_plans)} Savings Plans pricing records for {price_date}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store Savings Plans pricing data: {e}")
            return False
    
    async def get_pricing_trend(
        self,
        instance_type: str,
        region: str,
        days_back: int = 90
    ) -> Optional[PricingTrend]:
        """Analyze pricing trends for an instance type"""
        
        try:
            with self.SessionLocal() as session:
                # Get pricing history
                query = text("""
                    SELECT price_date, on_demand_hourly
                    FROM historical_instance_pricing
                    WHERE instance_type = :instance_type
                    AND region = :region
                    AND price_date >= :start_date
                    ORDER BY price_date DESC
                """)
                
                start_date = date.today() - timedelta(days=days_back)
                
                results = session.execute(query, {
                    'instance_type': instance_type,
                    'region': region,
                    'start_date': start_date
                }).fetchall()
                
                if not results:
                    return None
                
                # Convert to pandas for analysis
                df = pd.DataFrame(results, columns=['price_date', 'on_demand_hourly'])
                df['price_date'] = pd.to_datetime(df['price_date'])
                df = df.sort_values('price_date')
                
                current_price = float(df.iloc[-1]['on_demand_hourly'])
                
                # Calculate trend metrics
                price_30_days_ago = None
                price_90_days_ago = None
                
                # Find price 30 days ago
                date_30_days_ago = datetime.now() - timedelta(days=30)
                df_30_days = df[df['price_date'] <= date_30_days_ago]
                if not df_30_days.empty:
                    price_30_days_ago = float(df_30_days.iloc[-1]['on_demand_hourly'])
                
                # Find price 90 days ago
                date_90_days_ago = datetime.now() - timedelta(days=90)
                df_90_days = df[df['price_date'] <= date_90_days_ago]
                if not df_90_days.empty:
                    price_90_days_ago = float(df_90_days.iloc[-1]['on_demand_hourly'])
                
                # Calculate trend direction and percentage
                trend_direction = "stable"
                trend_percentage = 0.0
                
                if price_30_days_ago:
                    trend_percentage = ((current_price - price_30_days_ago) / price_30_days_ago) * 100
                    if trend_percentage > 1:
                        trend_direction = "increasing"
                    elif trend_percentage < -1:
                        trend_direction = "decreasing"
                
                # Calculate volatility score
                price_changes = df['on_demand_hourly'].pct_change().dropna()
                volatility_score = float(price_changes.std() * 100) if len(price_changes) > 1 else 0.0
                
                return PricingTrend(
                    instance_type=instance_type,
                    region=region,
                    current_price=current_price,
                    price_30_days_ago=price_30_days_ago,
                    price_90_days_ago=price_90_days_ago,
                    trend_direction=trend_direction,
                    trend_percentage=trend_percentage,
                    volatility_score=min(volatility_score, 100.0)  # Cap at 100
                )
                
        except Exception as e:
            logger.error(f"Failed to analyze pricing trend for {instance_type}: {e}")
            return None
    
    async def get_pricing_history(
        self,
        instance_type: str,
        region: str,
        days_back: int = 30
    ) -> List[Dict]:
        """Get pricing history for visualization"""
        
        try:
            with self.SessionLocal() as session:
                query = text("""
                    SELECT price_date, on_demand_hourly, reserved_1yr_hourly, reserved_3yr_hourly
                    FROM historical_instance_pricing
                    WHERE instance_type = :instance_type
                    AND region = :region
                    AND price_date >= :start_date
                    ORDER BY price_date ASC
                """)
                
                start_date = date.today() - timedelta(days=days_back)
                
                results = session.execute(query, {
                    'instance_type': instance_type,
                    'region': region,
                    'start_date': start_date
                }).fetchall()
                
                return [
                    {
                        'date': result.price_date.isoformat(),
                        'on_demand': float(result.on_demand_hourly),
                        'reserved_1yr': float(result.reserved_1yr_hourly) if result.reserved_1yr_hourly else None,
                        'reserved_3yr': float(result.reserved_3yr_hourly) if result.reserved_3yr_hourly else None
                    }
                    for result in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to get pricing history for {instance_type}: {e}")
            return []
    
    async def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up old pricing data to manage storage"""
        
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            
            with self.SessionLocal() as session:
                # Clean up instance pricing
                instance_delete = text("""
                    DELETE FROM historical_instance_pricing 
                    WHERE price_date < :cutoff_date
                """)
                
                # Clean up storage pricing
                storage_delete = text("""
                    DELETE FROM historical_storage_pricing 
                    WHERE price_date < :cutoff_date
                """)
                
                # Clean up savings plans pricing
                savings_delete = text("""
                    DELETE FROM savings_plans_pricing 
                    WHERE price_date < :cutoff_date
                """)
                
                instance_deleted = session.execute(instance_delete, {'cutoff_date': cutoff_date}).rowcount
                storage_deleted = session.execute(storage_delete, {'cutoff_date': cutoff_date}).rowcount
                savings_deleted = session.execute(savings_delete, {'cutoff_date': cutoff_date}).rowcount
                
                session.commit()
                
                logger.info(f"Cleaned up old pricing data: {instance_deleted} instance records, "
                           f"{storage_deleted} storage records, {savings_deleted} savings plans records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old pricing data: {e}")

# Global historical pricing service instance
historical_pricing_service = HistoricalPricingService()
