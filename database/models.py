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

engine = create_async_engine(DATABASE_URL, echo=True, future=True, echo_pool=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
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
    referrer_id = Column(BigInteger, ForeignKey('customers.telegram_id'), nullable=True)
    referrals = relationship("CustomUser", backref="referrer", remote_side=[telegram_id])

    transactions = relationship("Transaction", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    product_code = Column(String(50), unique=True)
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100))
    stock = Column(Integer, default=0)
    store_id = Column(Integer, ForeignKey('stores.id'))
    is_promotional = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship("Store", back_populates="products")


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
    store_id = Column(Integer, ForeignKey('stores.id'), nullable=False)
    is_promotional = Column(Boolean, default=False)

    customer = relationship("CustomUser", back_populates="transactions")
    product = relationship("Product")
    store = relationship("Store")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    type_id = Column(Integer, ForeignKey('store_types.id'))

    products = relationship("Product", back_populates="store")
    transactions = relationship("Transaction")


class StoreType(Base):
    __tablename__ = "store_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    percent = Column(Numeric(5, 2), nullable=False)


class BroadcastMessage(Base):
    __tablename__ = "broadcast_messages"

    id = Column(Integer, primary_key=True)
    message_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sent = Column(Boolean, default=False)
    send_to_all = Column(Boolean, default=True)
    target_user_id = Column(BigInteger, nullable=True)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
