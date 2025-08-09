"""
Database configuration and connection management
Optimized for handling 2000+ VM datasets
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.aws')

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration class"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.database_host = os.getenv('DATABASE_HOST')
        self.database_port = os.getenv('DATABASE_PORT', '5432')
        self.database_name = os.getenv('DATABASE_NAME', 'rvtool')
        self.database_user = os.getenv('DATABASE_USER')
        self.database_password = os.getenv('DATABASE_PASSWORD')
        
        if not self.database_url:
            if all([self.database_host, self.database_user, self.database_password]):
                self.database_url = f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"
            else:
                raise ValueError("Database configuration incomplete. Please check .env.aws file.")
    
    def get_engine_config(self):
        """Get SQLAlchemy engine configuration optimized for large datasets"""
        return {
            'poolclass': QueuePool,
            'pool_size': 20,  # Increased for handling multiple concurrent requests
            'max_overflow': 30,  # Allow burst capacity
            'pool_pre_ping': True,  # Verify connections before use
            'pool_recycle': 3600,  # Recycle connections every hour
            'connect_args': {
                'connect_timeout': 30,
                'application_name': 'rvtool_backend',
                'options': '-c statement_timeout=300000'  # 5 minute statement timeout
            },
            'echo': os.getenv('DATABASE_ECHO', 'false').lower() == 'true'
        }

# Global database configuration
db_config = DatabaseConfig()

# Create engine with optimized settings for large datasets
engine = create_engine(
    db_config.database_url,
    **db_config.get_engine_config()
)

# Configure session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)

# Event listeners for performance optimization
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set PostgreSQL-specific optimizations"""
    if 'postgresql' in str(dbapi_connection):
        with dbapi_connection.cursor() as cursor:
            # Optimize for bulk operations
            cursor.execute("SET work_mem = '256MB'")  # Increase work memory for large sorts
            cursor.execute("SET maintenance_work_mem = '512MB'")  # Increase maintenance memory
            cursor.execute("SET effective_cache_size = '2GB'")  # Assume 2GB cache
            cursor.execute("SET random_page_cost = 1.1")  # Optimize for SSD storage
            cursor.execute("SET seq_page_cost = 1.0")
            cursor.execute("SET cpu_tuple_cost = 0.01")
            cursor.execute("SET cpu_index_tuple_cost = 0.005")
            cursor.execute("SET cpu_operator_cost = 0.0025")

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions
    Ensures proper cleanup and error handling
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session
    """
    with get_db_session() as session:
        yield session

class DatabaseManager:
    """Database manager for advanced operations"""
    
    @staticmethod
    def test_connection() -> bool:
        """Test database connection"""
        try:
            from sqlalchemy import text
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    @staticmethod
    def get_connection_info():
        """Get database connection information"""
        try:
            from sqlalchemy import text
            with get_db_session() as session:
                result = session.execute(text("""
                    SELECT 
                        current_database() as database,
                        current_user as user,
                        version() as version,
                        inet_server_addr() as host,
                        inet_server_port() as port
                """)).fetchone()
                
                return {
                    'database': result.database,
                    'user': result.user,
                    'version': result.version.split(',')[0],
                    'host': result.host,
                    'port': result.port,
                    'status': 'connected'
                }
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def get_table_stats():
        """Get statistics about database tables"""
        try:
            with get_db_session() as session:
                result = session.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                """).fetchall()
                
                return [
                    {
                        'schema': row.schemaname,
                        'table': row.tablename,
                        'inserts': row.inserts,
                        'updates': row.updates,
                        'deletes': row.deletes,
                        'live_tuples': row.live_tuples,
                        'dead_tuples': row.dead_tuples
                    }
                    for row in result
                ]
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return []
    
    @staticmethod
    def optimize_for_bulk_operations():
        """Optimize database settings for bulk operations"""
        try:
            with get_db_session() as session:
                # Temporarily adjust settings for bulk operations
                session.execute("SET synchronous_commit = OFF")
                session.execute("SET wal_buffers = '16MB'")
                session.execute("SET checkpoint_segments = 32")
                session.execute("SET checkpoint_completion_target = 0.9")
                session.commit()
                logger.info("Database optimized for bulk operations")
        except Exception as e:
            logger.error(f"Failed to optimize for bulk operations: {e}")
    
    @staticmethod
    def reset_optimization():
        """Reset database settings to default"""
        try:
            with get_db_session() as session:
                session.execute("RESET synchronous_commit")
                session.execute("RESET wal_buffers")
                session.execute("RESET checkpoint_segments")
                session.execute("RESET checkpoint_completion_target")
                session.commit()
                logger.info("Database settings reset to default")
        except Exception as e:
            logger.error(f"Failed to reset optimization: {e}")

# Initialize database manager
db_manager = DatabaseManager()

# Health check function
def health_check():
    """Database health check for monitoring"""
    try:
        connection_info = db_manager.get_connection_info()
        if connection_info.get('status') == 'connected':
            return {
                'status': 'healthy',
                'database': connection_info.get('database'),
                'version': connection_info.get('version'),
                'timestamp': os.getenv('TIMESTAMP', 'unknown')
            }
        else:
            return {
                'status': 'unhealthy',
                'error': connection_info.get('error'),
                'timestamp': os.getenv('TIMESTAMP', 'unknown')
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': os.getenv('TIMESTAMP', 'unknown')
        }
