"""Async SQLAlchemy models and session helpers for the Telegram bot."""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Invalid integer for %s: %s; using %s", name, value, default)
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y"}


POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE")

required_env = {
    "POSTGRES_HOST": POSTGRES_HOST,
    "POSTGRES_DB": POSTGRES_DB,
    "POSTGRES_USER": POSTGRES_USER,
    "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
}
missing = [name for name, value in required_env.items() if not value]

SQLALCHEMY_ECHO = _env_bool("SQLALCHEMY_ECHO", False)
disable_bot = not _env_bool("ENABLE_TELEGRAM_BOT", True)
cmd_basename = os.path.basename(sys.argv[0]) if sys.argv else ""
running_tests = (
    any(cmd in sys.argv for cmd in {"test", "collectstatic"})
    or cmd_basename in {"pytest", "py.test"}
)


class _SessionStub:
    async def __aenter__(self):
        raise RuntimeError("Database is not configured for the Telegram bot")

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _session_factory_stub(*args, **kwargs):
    return _SessionStub()


class _EngineStub:
    async def dispose(self):  # pragma: no cover - trivial
        return None


if missing and (disable_bot or running_tests):
    DATABASE_URL = None
    engine = _EngineStub()
    SessionLocal = _session_factory_stub
    logger.warning(
        "Telegram bot database configuration missing; using no-op session (missing env: %s)",
        ", ".join(missing),
    )
else:
    if missing:
        raise RuntimeError(
            "Missing database configuration for Telegram bot: " + ", ".join(missing)
        )

    DATABASE_URL = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    if POSTGRES_SSLMODE:
        DATABASE_URL += f"?sslmode={POSTGRES_SSLMODE}"

    SQLALCHEMY_POOL_SIZE = _env_int("SQLALCHEMY_POOL_SIZE", 20)
    SQLALCHEMY_MAX_OVERFLOW = _env_int("SQLALCHEMY_MAX_OVERFLOW", 10)
    SQLALCHEMY_POOL_TIMEOUT = _env_int("SQLALCHEMY_POOL_TIMEOUT", 30)
    SQLALCHEMY_POOL_RECYCLE = _env_int("SQLALCHEMY_POOL_RECYCLE", 1800)

    engine = create_async_engine(
        DATABASE_URL,
        echo=SQLALCHEMY_ECHO,
        pool_size=SQLALCHEMY_POOL_SIZE,
        max_overflow=SQLALCHEMY_MAX_OVERFLOW,
        pool_timeout=SQLALCHEMY_POOL_TIMEOUT,
        pool_recycle=SQLALCHEMY_POOL_RECYCLE,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


class CustomUser(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    registration_date = Column(DateTime, default=datetime.utcnow)
    qr_code = Column(String, nullable=True)
    bonuses = Column(Numeric(10, 2), default=0.0)
    referrer_id = Column(BigInteger, ForeignKey("customers.telegram_id"), nullable=True)
    referrals = relationship("CustomUser", backref="referrer", remote_side=[telegram_id])
    last_purchase_date = Column(DateTime, nullable=True)
    total_spent = Column(Numeric(10, 2), default=0.00)
    purchase_count = Column(Integer, default=0)
    personal_data_consent = Column(Boolean, default=False)

    transactions = relationship("Transaction", back_populates="customer")
    bot_activities = relationship("BotActivity", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    product_code = Column(String(50), unique=True)
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100))
    stock = Column(Integer, default=0)
    store_id = Column(Integer, nullable=False)
    is_promotional = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, default=1)
    total_amount = Column(Numeric(10, 2), nullable=False)
    bonus_earned = Column(Numeric(10, 2), default=0.0)
    purchase_date = Column(Date, default=date.today)
    purchase_time = Column(Time, default=lambda: datetime.now().time())
    store_id = Column(Integer, nullable=False)
    is_promotional = Column(Boolean, default=False)

    customer = relationship("CustomUser", back_populates="transactions")
    product = relationship("Product")


class BroadcastMessage(Base):
    __tablename__ = "broadcast_messages"

    id = Column(Integer, primary_key=True)
    message_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    send_to_all = Column(Boolean, default=True)
    target_user_ids = Column(String, nullable=True)


class BotActivity(Base):
    __tablename__ = "bot_activities"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("CustomUser", back_populates="bot_activities")


class OneCClientMap(Base):
    __tablename__ = "api_onec_client_map"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    one_c_guid = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


async def get_onec_guid_by_user_id(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(OneCClientMap.one_c_guid).where(OneCClientMap.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_onec_client_map(session: AsyncSession, user_id: int, onec_guid: str):
    result = await session.execute(
        select(OneCClientMap).where(OneCClientMap.user_id == user_id)
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        mapping.one_c_guid = onec_guid
    else:
        session.add(OneCClientMap(user_id=user_id, one_c_guid=onec_guid))
    await session.commit()


async def create_db():
    if not hasattr(engine, "begin"):
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
