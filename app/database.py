from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create database engine with optimized connection pool settings
engine = create_engine(
    settings.database_url,
    echo=settings.debug,

    # Connection Pool Settings - Fix for TimeoutError
    pool_size=settings.db_pool_size,        # Configurable pool size (default 20)
    max_overflow=settings.db_max_overflow,  # Configurable overflow (default 30)
    pool_timeout=settings.db_pool_timeout,  # Configurable timeout (default 60)
    pool_recycle=settings.db_pool_recycle,  # Configurable recycle (default 3600)
    pool_pre_ping=True,                     # Verify connections before use

    # Connection Settings
    connect_args={
        "connect_timeout": 10,              # Connection timeout
        "application_name": "CMSVS_Internal_System",
        "options": "-c timezone=UTC"
    },

    # Engine Settings
    echo_pool=settings.debug,               # Log pool events in debug mode
    future=True                             # Use SQLAlchemy 2.0 style
)

# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent lazy loading issues after commit
)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session with proper error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # Rollback on any exception to clean up the transaction
        try:
            db.rollback()
        except Exception as rollback_error:
            # Log rollback error but don't raise it
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during rollback: {rollback_error}")
        raise e
    finally:
        # Always close the session to return connection to pool
        try:
            db.close()
        except Exception as close_error:
            # Log close error but don't raise it
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error closing database session: {close_error}")


def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


def get_pool_status():
    """Get connection pool status for monitoring"""
    try:
        pool = engine.pool
        checked_in = pool.checkedin()
        checked_out = pool.checkedout()
        pool_size = pool.size()
        overflow = pool.overflow()

        return {
            "pool_size": pool_size,
            "checked_in": checked_in,
            "checked_out": checked_out,
            "overflow": overflow,
            "total_connections": checked_in + checked_out,
            "available_connections": max(0, pool_size - checked_out),
            "max_overflow": getattr(pool, '_max_overflow', 0),
            "pool_timeout": getattr(pool, '_timeout', 0)
        }
    except Exception as e:
        # Return safe defaults if pool status can't be retrieved
        return {
            "pool_size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total_connections": 0,
            "available_connections": 0,
            "max_overflow": 0,
            "pool_timeout": 0,
            "error": str(e)
        }


def close_all_connections():
    """Close all database connections - useful for cleanup"""
    engine.dispose()


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            # Use text() for raw SQL in SQLAlchemy 2.0
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                return True, "Connection successful"
            else:
                return False, "Connection test failed - unexpected result"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"
