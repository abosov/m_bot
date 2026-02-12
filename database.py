import uuid
import enum
from datetime import datetime, time
from typing import Optional, List

import config
from sqlalchemy import (
    BigInteger, Boolean, String, ForeignKey, DateTime, Time, 
    Integer, Text, Enum as SAEnum, func, Float, CheckConstraint
)
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Получение URL БД
DATABASE_URL = config.DATABASE_URL

# --- Настройка движка ---
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# --- Validation helpers ---
def _validate_int_range(value: int, min_value: int, max_value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < min_value or value > max_value:
        raise ValueError(f"{field_name} must be between {min_value} and {max_value}")
    return value

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

class BotHealthCheckStatus(str, enum.Enum):
    ok = "ok"
    unauthorized = "unauthorized"
    temp_error = "temp_error"

# --- MODELS ---

class Specialist(Base):
    __tablename__ = "specialist"

    specialist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[SpecialistStatus] = mapped_column(SAEnum(SpecialistStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    master_onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    full_onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    auth_telegram: Mapped["SpecialistAuthTelegram"] = relationship(back_populates="specialist", uselist=False)
    profile: Mapped["SpecialistProfile"] = relationship(back_populates="specialist", uselist=False)
    google_oauth: Mapped["GoogleOAuth"] = relationship(back_populates="specialist", uselist=False)
    calendar_settings: Mapped["SpecialistCalendarSettings"] = relationship(back_populates="specialist", uselist=False)
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
    __table_args__ = (
        CheckConstraint(
            "session_duration_min >= 15 AND session_duration_min <= 480",
            name="ck_specialist_profile_session_duration_min",
        ),
        CheckConstraint(
            "session_buffer_min >= 0 AND session_buffer_min <= 120",
            name="ck_specialist_profile_session_buffer_min",
        ),
        CheckConstraint(
            "max_sessions_per_day >= 1 AND max_sessions_per_day <= 20",
            name="ck_specialist_profile_max_sessions_per_day",
        ),
        CheckConstraint(
            "slot_step_min IN (60, 30, 15, 10)",
            name="ck_specialist_profile_slot_step_min",
        ),
    )

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    public_name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    owner_tg_username: Mapped[Optional[str]] = mapped_column(String)
    specialist_timezone: Mapped[str] = mapped_column(String, nullable=False)
    session_duration_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    session_buffer_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_sessions_per_day: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    slot_step_min: int = Column(Integer, nullable=False, server_default="15", default=15)
    cancel_window_hours: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="profile")

    @validates("session_duration_min")
    def validate_session_duration_min(self, key: str, value: int) -> int:
        return _validate_int_range(value, 15, 480, key)

    @validates("session_buffer_min")
    def validate_session_buffer_min(self, key: str, value: int) -> int:
        return _validate_int_range(value, 0, 120, key)

    @validates("max_sessions_per_day")
    def validate_max_sessions_per_day(self, key: str, value: int) -> int:
        return _validate_int_range(value, 1, 20, key)


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


class SpecialistCalendarSettings(Base):
    __tablename__ = "specialist_calendar_settings"

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    calendar_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    calendar_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    calendar_time_zone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[SpecialistCalendarSource] = mapped_column(SAEnum(SpecialistCalendarSource), nullable=False)
    last_smoke_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_smoke_test_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_smoke_test_error: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="calendar_settings")


class WeeklyAvailability(Base):
    __tablename__ = "weekly_availability"
    __table_args__ = (
        CheckConstraint(
            "((interval_1_start IS NULL AND interval_1_end IS NULL) OR (interval_1_start IS NOT NULL AND interval_1_end IS NOT NULL AND interval_1_start < interval_1_end))",
            name="ck_weekly_availability_interval_1_pair",
        ),
        CheckConstraint(
            "((interval_2_start IS NULL AND interval_2_end IS NULL) OR (interval_2_start IS NOT NULL AND interval_2_end IS NOT NULL AND interval_2_start < interval_2_end))",
            name="ck_weekly_availability_interval_2_pair",
        ),
        CheckConstraint(
            "((interval_3_start IS NULL AND interval_3_end IS NULL) OR (interval_3_start IS NOT NULL AND interval_3_end IS NOT NULL AND interval_3_start < interval_3_end))",
            name="ck_weekly_availability_interval_3_pair",
        ),
    )

    weekly_availability_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False, index=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    is_working: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    interval_1_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_1_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_2_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_2_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_3_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    interval_3_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
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


class BotHealthCheck(Base):
    __tablename__ = "bot_health_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False, index=True)
    bot_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[BotHealthCheckStatus] = mapped_column(SAEnum(BotHealthCheckStatus), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    db_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    loop_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# --- Dependency Helper ---

async def get_db_session() -> AsyncSession:
    """Dependency helper for FastAPI/Aiogram handlers"""
    async with async_session_factory() as session:
        yield session

async def init_db():
    """Helper to create tables for local/dev environments.

    Note: in production, schema updates for existing databases must be applied
    explicitly before restart (DDL scripts/migrations), then this helper can run
    safely as a no-op for already existing tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
