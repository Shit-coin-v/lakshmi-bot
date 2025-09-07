import os
from datetime import datetime, date

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Date, Time, Numeric, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from dotenv import load_dotenv
load_dotenv()


POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession, )
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
    one_c_guid = Column(String, unique=True, nullable=True)
    referrer_id = Column(BigInteger, ForeignKey('customers.telegram_id'), nullable=True)
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
    customer_id = Column(Integer, ForeignKey('customers.id'))
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
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
    customer_id = Column(Integer, ForeignKey('customers.id'))
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("CustomUser", back_populates="bot_activities")


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
