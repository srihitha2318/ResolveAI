import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import Engine

_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.config import settings
from app.core.logging_config import logger
from app.database.db import engine as default_engine
from app.database.models import Base


def migrate_orders_schema(engine: Engine) -> None:
    """
    Performs an additive, non-destructive schema migration for the orders table.
    Ensures 'seller_id' and 'category' columns exist on existing databases.
    """
    try:
        with engine.connect() as conn:
            # Check existing columns in orders table
            result = conn.execute(text("PRAGMA table_info(orders)"))
            columns = {row[1] for row in result.fetchall()}

            if columns:  # table exists
                if "seller_id" not in columns:
                    logger.info("Applying additive migration: adding 'seller_id' to orders")
                    conn.execute(text("ALTER TABLE orders ADD COLUMN seller_id VARCHAR(64)"))
                    conn.commit()

                if "category" not in columns:
                    logger.info("Applying additive migration: adding 'category' to orders")
                    conn.execute(text("ALTER TABLE orders ADD COLUMN category VARCHAR(64)"))
                    conn.commit()
    except Exception as e:
        logger.warning("Additive migration check failed or not required: %s", e)


def migrate_approval_requests_schema(engine: Engine) -> None:
    """
    Performs an additive, non-destructive schema migration for the approval_requests table.
    Ensures Level 5 human approval columns and indexes exist on existing databases.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(approval_requests)"))
            columns = {row[1] for row in result.fetchall()}

            if columns:  # table exists
                if "thread_id" not in columns:
                    logger.info("Applying additive migration: adding 'thread_id' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN thread_id VARCHAR(128)"))
                    conn.commit()

                if "workflow_status" not in columns:
                    logger.info("Applying additive migration: adding 'workflow_status' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN workflow_status VARCHAR(64) DEFAULT 'pending_review'"))
                    conn.commit()

                if "proposed_resolution" not in columns:
                    logger.info("Applying additive migration: adding 'proposed_resolution' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN proposed_resolution TEXT"))
                    conn.commit()

                if "policy_evidence" not in columns:
                    logger.info("Applying additive migration: adding 'policy_evidence' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN policy_evidence TEXT"))
                    conn.commit()

                if "reviewer_id" not in columns:
                    logger.info("Applying additive migration: adding 'reviewer_id' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN reviewer_id VARCHAR(128)"))
                    conn.commit()

                if "decision_timestamp" not in columns:
                    logger.info("Applying additive migration: adding 'decision_timestamp' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN decision_timestamp DATETIME"))
                    conn.commit()

                # Level 6: Approval SLA Management fields
                if "expires_at" not in columns:
                    logger.info("Applying additive migration: adding 'expires_at' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN expires_at DATETIME"))
                    conn.commit()

                if "sla_priority" not in columns:
                    logger.info("Applying additive migration: adding 'sla_priority' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN sla_priority VARCHAR(32) DEFAULT 'standard'"))
                    conn.commit()

                if "required_role" not in columns:
                    logger.info("Applying additive migration: adding 'required_role' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN required_role VARCHAR(64) DEFAULT 'tier2_supervisor'"))
                    conn.commit()

                if "is_expired" not in columns:
                    logger.info("Applying additive migration: adding 'is_expired' to approval_requests")
                    conn.execute(text("ALTER TABLE approval_requests ADD COLUMN is_expired BOOLEAN DEFAULT 0"))
                    conn.commit()

                # Add indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_approval_requests_thread_id ON approval_requests(thread_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_approval_requests_expires_at ON approval_requests(expires_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_approval_requests_is_expired ON approval_requests(is_expired)"))
                conn.commit()
    except Exception as e:
        logger.warning("Approval requests additive migration check failed or not required: %s", e)


def init_db(engine: Engine = default_engine) -> None:
    """
    Initializes all database tables idempotently using SQLAlchemy metadata.
    Applies non-destructive additive migrations to existing databases.
    Does not drop or delete existing tables or data.
    """
    logger.info("Initializing database schema at: %s", settings.resolved_database_url)
    try:
        Base.metadata.create_all(bind=engine)
        migrate_orders_schema(engine)
        migrate_approval_requests_schema(engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database schema: %s", e)
        raise


if __name__ == "__main__":
    try:
        init_db()
        print("Database schema successfully created/verified.")
        sys.exit(0)
    except Exception as err:
        print(f"Error initializing database: {err}", file=sys.stderr)
        sys.exit(1)
