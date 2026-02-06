import os
import uuid
import enum
from datetime import datetime, time
from typing import Optional, List

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger, Boolean, String, ForeignKey, DateTime, Time, 
    Integer, Text, Enum as SAEnum, func, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Загрузка переменных окружения
load_dotenv()
load_dotenv(".env.local")

# Получение URL БД
DATABASE_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./mvp.db")

# --- Настройка движка ---
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# --- ENUMS ---

class SpecialistStatus(str, enum.Enum):
    onboarding = "onboarding"
    active = "active"
    suspended = "suspended"

class TelegramBotStatus(str, enum.Enum):
    active = "active"
    error = "error"

class GoogleOAuthStatus(str, enum.Enum):
    connected = "connected"
    revoked = "revoked"
    error = "error"

class SpecialistCalendarSource(str, enum.Enum):
    selected = "selected"
    created = "created"

class ClientTimezoneSource(str, enum.Enum):
    default_from_specialist = "default_from_specialist"
    client_selected = "client_selected"

class BookingState(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"
    canceled_by_client = "canceled_by_client"
    canceled_by_specialist = "canceled_by_specialist"

class OAuthStateType(str, enum.Enum):
    google_connect = "google_connect"
    google_reconnect = "google_reconnect"

class LogDirection(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"

# --- MODELS ---

class Specialist(Base):
    __tablename__ = "specialist"

    specialist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[SpecialistStatus] = mapped_column(SAEnum(SpecialistStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    auth_telegram: Mapped["SpecialistAuthTelegram"] = relationship(back_populates="specialist", uselist=False)
    profile: Mapped["SpecialistProfile"] = relationship(back_populates="specialist", uselist=False)
    google_oauth: Mapped["GoogleOAuth"] = relationship(back_populates="specialist", uselist=False)
    calendar: Mapped["SpecialistCalendar"] = relationship(back_populates="specialist", uselist=False)
    weekly_availability: Mapped[List["WeeklyAvailability"]] = relationship(back_populates="specialist")
    clients: Mapped[List["Client"]] = relationship(back_populates="specialist")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="specialist")
    telegram_bots: Mapped[List["TelegramBot"]] = relationship(back_populates="specialist")


class SpecialistAuthTelegram(Base):
    __tablename__ = "specialist_auth_telegram"

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    tg_username: Mapped[Optional[str]] = mapped_column(String)
    tg_first_name: Mapped[Optional[str]] = mapped_column(String)
    tg_last_name: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="auth_telegram")


class SpecialistProfile(Base):
    __tablename__ = "specialist_profile"

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    public_name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    owner_tg_username: Mapped[Optional[str]] = mapped_column(String)
    specialist_timezone: Mapped[str] = mapped_column(String, nullable=False)
    session_duration_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    cancel_window_hours: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="profile")


class TelegramBot(Base):
    __tablename__ = "telegram_bot"

    telegram_bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=True, index=True)
    
    bot_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    bot_username: Mapped[str] = mapped_column(String, nullable=False)
    bot_name: Mapped[str] = mapped_column(String, nullable=False)
    bot_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_secret: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TelegramBotStatus] = mapped_column(SAEnum(TelegramBotStatus), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="telegram_bots")


class GoogleOAuth(Base):
    __tablename__ = "google_oauth"

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GoogleOAuthStatus] = mapped_column(SAEnum(GoogleOAuthStatus), default=GoogleOAuthStatus.connected, nullable=False)
    token_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="google_oauth")


class SpecialistCalendar(Base):
    __tablename__ = "specialist_calendar"

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    calendar_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    calendar_title: Mapped[str] = mapped_column(String, nullable=False)
    calendar_timezone: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[SpecialistCalendarSource] = mapped_column(SAEnum(SpecialistCalendarSource), nullable=False)
    timezone_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="calendar")


class WeeklyAvailability(Base):
    __tablename__ = "weekly_availability"

    weekly_availability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False, index=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_working: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    interval_1_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_1_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_2_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_2_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="weekly_availability")


class Client(Base):
    __tablename__ = "client"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False, index=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String)
    display_name: Mapped[Optional[str]] = mapped_column(String)
    client_code: Mapped[str] = mapped_column(String, nullable=False)
    
    client_timezone: Mapped[str] = mapped_column(String, nullable=False)
    timezone_source: Mapped[ClientTimezoneSource] = mapped_column(SAEnum(ClientTimezoneSource), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="clients")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="client")


class Appointment(Base):
    __tablename__ = "appointment"

    appointment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.client_id"), nullable=False)
    
    start_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    booking_state: Mapped[BookingState] = mapped_column(SAEnum(BookingState), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    
    gcal_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    specialist_private_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="appointments")
    client: Mapped["Client"] = relationship(back_populates="appointments")


class OAuthState(Base):
    __tablename__ = "oauth_state"

    oauth_state_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[OAuthStateType] = mapped_column(SAEnum(OAuthStateType), nullable=False)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    specialist_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=True)
    bot_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    bot_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    specialist_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    direction: Mapped[LogDirection] = mapped_column(SAEnum(LogDirection), nullable=False)
    message_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    fsm_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    handler_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


# --- Dependency Helper ---

async def get_db_session() -> AsyncSession:
    """Dependency helper for FastAPI/Aiogram handlers"""
    async with async_session_factory() as session:
        yield session

async def init_db():
    """Helper to create tables (for MVP startup)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
