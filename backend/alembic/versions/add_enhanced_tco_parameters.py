"""Add enhanced TCO parameters support

Revision ID: enhanced_tco_001
Revises: c4ab614708ac
Create Date: 2025-07-26 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'enhanced_tco_001'
down_revision = 'c4ab614708ac'
branch_labels = None
depends_on = None

def upgrade():
    """Add enhanced TCO parameters columns"""
    
    # Add new columns to cost_analysis table
    op.add_column('cost_analysis', 
        sa.Column('production_pricing_model', sa.String(50), 
                 nullable=False, server_default='reserved'))
    
    op.add_column('cost_analysis', 
        sa.Column('non_production_pricing_model', sa.String(50), 
                 nullable=False, server_default='on_demand'))
    
    op.add_column('cost_analysis', 
        sa.Column('savings_plan_commitment', sa.String(20), 
                 nullable=False, server_default='1_year'))
    
    op.add_column('cost_analysis', 
        sa.Column('savings_plan_payment', sa.String(20), 
                 nullable=False, server_default='no_upfront'))
    
    op.add_column('cost_analysis', 
        sa.Column('production_utilization_percent', sa.Integer(), 
                 nullable=False, server_default='100'))
    
    op.add_column('cost_analysis', 
        sa.Column('non_production_utilization_percent', sa.Integer(), 
                 nullable=False, server_default='50'))
    
    op.add_column('cost_analysis', 
        sa.Column('default_os_type', sa.String(20), 
                 nullable=False, server_default='linux'))
    
    op.add_column('cost_analysis', 
        sa.Column('production_ri_years', sa.Integer(), 
                 nullable=False, server_default='3'))
    
    op.add_column('cost_analysis', 
        sa.Column('non_production_ri_years', sa.Integer(), 
                 nullable=False, server_default='1'))
    
    op.add_column('cost_analysis', 
        sa.Column('enable_spot_instances', sa.Boolean(), 
                 nullable=False, server_default='false'))
    
    op.add_column('cost_analysis', 
        sa.Column('spot_interruption_tolerance', sa.String(20), 
                 nullable=False, server_default='low'))
    
    # Add indexes for performance
    op.create_index('idx_cost_analysis_prod_pricing', 'cost_analysis', 
                   ['production_pricing_model'])
    op.create_index('idx_cost_analysis_nonprod_pricing', 'cost_analysis', 
                   ['non_production_pricing_model'])
    op.create_index('idx_cost_analysis_os_type', 'cost_analysis', 
                   ['default_os_type'])
    op.create_index('idx_cost_analysis_savings_commitment', 'cost_analysis', 
                   ['savings_plan_commitment'])

def downgrade():
    """Remove enhanced TCO parameters columns"""
    
    # Drop indexes
    op.drop_index('idx_cost_analysis_savings_commitment', table_name='cost_analysis')
    op.drop_index('idx_cost_analysis_os_type', table_name='cost_analysis')
    op.drop_index('idx_cost_analysis_nonprod_pricing', table_name='cost_analysis')
    op.drop_index('idx_cost_analysis_prod_pricing', table_name='cost_analysis')
    
    # Drop columns
    op.drop_column('cost_analysis', 'spot_interruption_tolerance')
    op.drop_column('cost_analysis', 'enable_spot_instances')
    op.drop_column('cost_analysis', 'non_production_ri_years')
    op.drop_column('cost_analysis', 'production_ri_years')
    op.drop_column('cost_analysis', 'default_os_type')
    op.drop_column('cost_analysis', 'non_production_utilization_percent')
    op.drop_column('cost_analysis', 'production_utilization_percent')
    op.drop_column('cost_analysis', 'savings_plan_payment')
    op.drop_column('cost_analysis', 'savings_plan_commitment')
    op.drop_column('cost_analysis', 'non_production_pricing_model')
    op.drop_column('cost_analysis', 'production_pricing_model')
