from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv('.env.aws')

# Import our models
from models.base import Base
from models.vm_inventory import VMInventory
from models.session import Session
from models.migration_analysis import MigrationAnalysis, MigrationBlocker
from models.cost_analysis import CostAnalysis, CostEstimate
from models.modernization_analysis import ModernizationAnalysis, ModernizationOpportunity

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from environment variable
database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)
else:
    raise ValueError("DATABASE_URL environment variable not set")

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create engine with optimized settings for migrations
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = database_url
    
    # Add connection arguments for better performance during migrations
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            'connect_timeout': 60,
            'application_name': 'rvtool_migrations'
        }
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Include object names in migrations for better tracking
            include_object=include_object,
            # Render item for better migration scripts
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Should we include this object in the migration?
    """
    # Skip temporary tables
    if type_ == "table" and name.startswith("temp_"):
        return False
    
    # Skip system tables
    if type_ == "table" and name.startswith("pg_"):
        return False
        
    return True


def render_item(type_, obj, autogen_context):
    """
    Apply custom rendering for migration items
    """
    if type_ == "type" and hasattr(obj, "impl"):
        # Handle custom types
        return obj.impl.__class__.__name__
    
    # Default rendering
    return False


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
