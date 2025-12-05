from sqlalchemy import create_engine, asc, Index, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy import event
from .models import User, UploadedFile, Base, Chat
import os
from app.config import DATABASE_URL
from app.utils.logger import log_info, log_error
import time

# Enhanced database configuration with connection pooling
# Use lazy connection - don't connect until first use
# This prevents connection attempts at import time
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  
    max_overflow=30,  
    pool_pre_ping=True,  
    pool_recycle=3600,  
    echo=False,  # Set to True for SQL query logging
    connect_args={"connect_timeout": 10}  # Add timeout to prevent hanging
)

# Create database indexes for performance
def create_database_indexes():
    """Create database indexes for better performance"""
    try:
        with engine.connect() as connection:
            # User indexes
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_email_verified 
                ON users(email_verified) WHERE email_verified = true;
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_created_at 
                ON users(created_at DESC);
            """))
            
            # UploadedFile indexes
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_uploaded_files_owner_status 
                ON uploaded_files(owner_id, processing_status);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_uploaded_files_type_date 
                ON uploaded_files(file_type, upload_date DESC);
            """))
            
            # Chat indexes
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chats_user_file_date 
                ON chats(user_id, uploaded_file_id, created_at DESC);
            """))
            
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chats_type_date 
                ON chats(chat_type, created_at DESC);
            """))
            
            connection.commit()
            log_info("Database indexes created successfully", context="database")
            
    except Exception as e:
        log_error(e, context="database_indexes")


# Database connection monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    log_info("New database connection established", context="database")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    log_info("Database connection checked out", context="database")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    log_info("Database connection checked in", context="database")

# Lazy table creation - only create tables when first database connection is made
# This prevents connection attempts at import time (which breaks Celery workers)
_tables_created = False

def ensure_tables_created():
    """Lazy table creation - only creates tables on first call"""
    global _tables_created
    if not _tables_created:
        try:
            Base.metadata.create_all(bind=engine)
            _tables_created = True
            log_info("Database tables created/verified", context="database")
        except Exception as e:
            # In lightweight Celery workers, database might not be available yet
            # This is OK - tables will be created when database is accessed
            log_error(e, context="database_table_creation", message="Failed to create tables (will retry on first use)")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database dependency with connection monitoring"""
    # Ensure tables are created on first database access
    ensure_tables_created()
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        yield db
    except Exception as e:
        log_error(e, context="database_session")
        raise
    finally:
        duration = time.time() - start_time
        if duration > 1.0:  # Log slow database sessions
            log_info(f"Slow database session: {duration:.3f}s", context="database")
        db.close()

def get_db_stats():
    """Get database connection pool statistics"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid()
    }