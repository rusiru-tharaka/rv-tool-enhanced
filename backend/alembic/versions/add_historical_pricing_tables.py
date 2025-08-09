"""Add historical pricing data tables

Revision ID: historical_pricing_001
Revises: enhanced_tco_001
Create Date: 2025-07-26 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'historical_pricing_001'
down_revision = 'enhanced_tco_001'
branch_labels = None
depends_on = None

def upgrade():
    """Add historical pricing data tables"""
    
    # Create historical_instance_pricing table
    op.create_table(
        'historical_instance_pricing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_type', sa.String(50), nullable=False),
        sa.Column('region', sa.String(20), nullable=False),
        sa.Column('os_type', sa.String(20), nullable=False, server_default='linux'),
        sa.Column('on_demand_hourly', sa.Numeric(10, 6), nullable=False),
        sa.Column('reserved_1yr_hourly', sa.Numeric(10, 6), nullable=True),
        sa.Column('reserved_3yr_hourly', sa.Numeric(10, 6), nullable=True),
        sa.Column('vcpu', sa.Integer(), nullable=True),
        sa.Column('memory_gb', sa.Numeric(8, 2), nullable=True),
        sa.Column('storage_type', sa.String(20), nullable=True),
        sa.Column('network_performance', sa.String(50), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_historical_instance_pricing_lookup', 'historical_instance_pricing', 
                   ['instance_type', 'region', 'os_type', 'price_date'])
    op.create_index('idx_historical_instance_pricing_date', 'historical_instance_pricing', ['price_date'])
    
    # Create historical_storage_pricing table
    op.create_table(
        'historical_storage_pricing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('storage_type', sa.String(20), nullable=False),
        sa.Column('region', sa.String(20), nullable=False),
        sa.Column('price_per_gb_month', sa.Numeric(8, 6), nullable=False),
        sa.Column('iops_price', sa.Numeric(8, 6), nullable=True),
        sa.Column('throughput_price', sa.Numeric(8, 6), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for storage pricing
    op.create_index('idx_historical_storage_pricing_lookup', 'historical_storage_pricing', 
                   ['storage_type', 'region', 'price_date'])
    op.create_index('idx_historical_storage_pricing_date', 'historical_storage_pricing', ['price_date'])
    
    # Create savings_plans_pricing table
    op.create_table(
        'savings_plans_pricing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_type', sa.String(20), nullable=False),
        sa.Column('instance_family', sa.String(20), nullable=True),
        sa.Column('region', sa.String(20), nullable=False),
        sa.Column('commitment_term', sa.String(10), nullable=False),
        sa.Column('payment_option', sa.String(20), nullable=False),
        sa.Column('hourly_rate', sa.Numeric(10, 6), nullable=False),
        sa.Column('upfront_cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('effective_hourly_rate', sa.Numeric(10, 6), nullable=False),
        sa.Column('on_demand_equivalent', sa.Numeric(10, 6), nullable=True),
        sa.Column('savings_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('break_even_hours', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('os_type', sa.String(20), nullable=False, server_default='linux'),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for savings plans
    op.create_index('idx_savings_plans_lookup', 'savings_plans_pricing', 
                   ['plan_type', 'instance_family', 'region', 'commitment_term', 'payment_option'])
    op.create_index('idx_savings_plans_date', 'savings_plans_pricing', ['price_date'])
    
    # Create pricing_cache_metadata table for cache management
    op.create_table(
        'pricing_cache_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False, unique=True),
        sa.Column('cache_type', sa.String(50), nullable=False),
        sa.Column('region', sa.String(20), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for cache metadata
    op.create_index('idx_pricing_cache_key', 'pricing_cache_metadata', ['cache_key'])
    op.create_index('idx_pricing_cache_expires', 'pricing_cache_metadata', ['expires_at'])
    op.create_index('idx_pricing_cache_type_region', 'pricing_cache_metadata', ['cache_type', 'region'])

def downgrade():
    """Remove historical pricing data tables"""
    
    # Drop indexes first
    op.drop_index('idx_pricing_cache_type_region', table_name='pricing_cache_metadata')
    op.drop_index('idx_pricing_cache_expires', table_name='pricing_cache_metadata')
    op.drop_index('idx_pricing_cache_key', table_name='pricing_cache_metadata')
    
    op.drop_index('idx_savings_plans_date', table_name='savings_plans_pricing')
    op.drop_index('idx_savings_plans_lookup', table_name='savings_plans_pricing')
    
    op.drop_index('idx_historical_storage_pricing_date', table_name='historical_storage_pricing')
    op.drop_index('idx_historical_storage_pricing_lookup', table_name='historical_storage_pricing')
    
    op.drop_index('idx_historical_instance_pricing_date', table_name='historical_instance_pricing')
    op.drop_index('idx_historical_instance_pricing_lookup', table_name='historical_instance_pricing')
    
    # Drop tables
    op.drop_table('pricing_cache_metadata')
    op.drop_table('savings_plans_pricing')
    op.drop_table('historical_storage_pricing')
    op.drop_table('historical_instance_pricing')
