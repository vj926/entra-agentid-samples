import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    JSON,
    Enum as SAEnum,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=0,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Set SQLite journal mode to DELETE for Azure Files compatibility
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=DELETE")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Agent Blueprint ──────────────────────────────────────────────
class BlueprintRow(Base):
    __tablename__ = "blueprints"

    id = Column(String, primary_key=True, default=new_id)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    agent_type = Column(String, nullable=False)  # copilot_studio | foundry | custom
    permission_mode = Column(String, default="inheritable")  # inheritable | manual
    default_permissions = Column(JSON, default=list)
    required_apis = Column(JSON, default=list)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    status = Column(String, default="active")  # active | deprecated
    linked_identity_request_id = Column(String, nullable=True)
    provisioned_app_id = Column(String, nullable=True)
    provisioned_object_id = Column(String, nullable=True)


# ── Identity Request ────────────────────────────────────────────
class IdentityRequestRow(Base):
    __tablename__ = "identity_requests"

    id = Column(String, primary_key=True, default=new_id)
    blueprint_id = Column(String, nullable=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, default="")
    agent_type = Column(String, nullable=False)
    environment = Column(String, default="dev")  # dev | staging | production
    justification = Column(Text, default="")
    requested_by = Column(String, nullable=False)
    requested_at = Column(DateTime, default=utcnow)
    status = Column(String, default="pending")  # pending | approved | rejected | provisioned | failed
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    provisioned_app_id = Column(String, nullable=True)
    provisioned_object_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)


# ── Permission Request ──────────────────────────────────────────
class PermissionRequestRow(Base):
    __tablename__ = "permission_requests"

    id = Column(String, primary_key=True, default=new_id)
    identity_app_id = Column(String, nullable=False)
    identity_display_name = Column(String, nullable=False)
    requested_permissions = Column(JSON, default=list)  # [{resource, scope, type}]
    justification = Column(Text, default="")
    requested_by = Column(String, nullable=False)
    requested_at = Column(DateTime, default=utcnow)
    status = Column(String, default="pending")  # pending | approved | rejected | granted | failed
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)


# ── Audit Log ───────────────────────────────────────────────────
class AuditLogRow(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=new_id)
    entity_type = Column(String, nullable=False)  # blueprint | identity_request | permission_request
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    performed_by = Column(String, nullable=False)
    performed_at = Column(DateTime, default=utcnow)
    details = Column(JSON, default=dict)


def init_db():
    import os, sqlite3 as _sqlite3, logging as _logging
    _log = _logging.getLogger("database")

    # On Azure Files, SQLite lock files can become stale after container restarts.
    db_path = settings.database_url.replace("sqlite:///", "")
    for suffix in ["-journal", "-wal", "-shm"]:
        lock_file = db_path + suffix
        if os.path.exists(lock_file):
            _log.warning("Removing stale SQLite lock file: %s", lock_file)
            try:
                os.remove(lock_file)
            except OSError as e:
                _log.warning("Could not remove %s: %s", lock_file, e)

    # Use a direct SQLite connection for DDL to avoid SQLAlchemy pool lock contention.
    conn = _sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS blueprints (
                id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, description TEXT,
                agent_type VARCHAR NOT NULL, permission_mode VARCHAR DEFAULT 'inheritable',
                default_permissions JSON, required_apis JSON, created_by VARCHAR NOT NULL,
                created_at DATETIME, status VARCHAR DEFAULT 'active',
                linked_identity_request_id VARCHAR,
                provisioned_app_id VARCHAR, provisioned_object_id VARCHAR);
            CREATE TABLE IF NOT EXISTS identity_requests (
                id VARCHAR PRIMARY KEY, blueprint_id VARCHAR, display_name VARCHAR NOT NULL,
                description TEXT, agent_type VARCHAR NOT NULL, environment VARCHAR DEFAULT 'dev',
                justification TEXT, requested_by VARCHAR NOT NULL, requested_at DATETIME,
                status VARCHAR DEFAULT 'pending', approved_by VARCHAR, approved_at DATETIME,
                provisioned_app_id VARCHAR, provisioned_object_id VARCHAR, rejection_reason TEXT);
            CREATE TABLE IF NOT EXISTS permission_requests (
                id VARCHAR PRIMARY KEY, identity_app_id VARCHAR NOT NULL,
                identity_display_name VARCHAR NOT NULL, requested_permissions JSON,
                justification TEXT, requested_by VARCHAR NOT NULL, requested_at DATETIME,
                status VARCHAR DEFAULT 'pending', approved_by VARCHAR, approved_at DATETIME,
                rejection_reason TEXT);
            CREATE TABLE IF NOT EXISTS audit_log (
                id VARCHAR PRIMARY KEY, entity_type VARCHAR NOT NULL, entity_id VARCHAR NOT NULL,
                action VARCHAR NOT NULL, performed_by VARCHAR NOT NULL, performed_at DATETIME,
                details JSON);
        """)
        conn.commit()
        _log.info("Database tables verified via direct SQLite connection.")

        # ── Schema migrations — add columns that may be missing on older DBs ──
        migrations = [
            ("blueprints", "provisioned_app_id", "VARCHAR"),
            ("blueprints", "provisioned_object_id", "VARCHAR"),
            ("blueprints", "linked_identity_request_id", "VARCHAR"),
            ("blueprints", "permission_mode", "VARCHAR DEFAULT 'inheritable'"),
        ]
        for table, col, col_type in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                conn.commit()
                _log.info("Migration: added column %s.%s", table, col)
            except _sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    pass  # Column already exists
                else:
                    _log.warning("Migration failed for %s.%s: %s", table, col, e)

    except Exception as exc:
        _log.warning("Failed to create tables (will retry): %s", exc)
    finally:
        conn.close()
