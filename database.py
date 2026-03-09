import uuid
import enum
import logging
import secrets
from datetime import datetime, time, timezone
from typing import Optional, List

import config
from sqlalchemy import (
    text, select, update, BigInteger, Boolean, String, ForeignKey, DateTime, Time,
    Integer, Text, Enum as SAEnum, func, Float, CheckConstraint, UniqueConstraint, JSON, Index, desc
)
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from services.log_context import log_event

# Получение URL БД
DATABASE_URL = config.DATABASE_URL
logger = logging.getLogger(__name__)

# --- Настройка движка ---
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
log_event(logger, logging.INFO, event="db_engine_init", outcome="ok")

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
    awaiting_specialist_confirmation = "awaiting_specialist_confirmation"
    rejected_by_specialist = "rejected_by_specialist"
    failed = "failed"
    canceled_by_client = "canceled_by_client"
    canceled_by_specialist = "canceled_by_specialist"


class ReminderType(str, enum.Enum):
    h24 = "h24"
    h2 = "h2"

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

class TariffPlan(str, enum.Enum):
    free = "free"
    start = "start"
    pro = "pro"
    team = "team"


class BillingPeriod(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class BillingPurchaseStatus(str, enum.Enum):
    pending = "pending"
    awaiting_payment = "awaiting_payment"
    succeeded = "succeeded"
    canceled = "canceled"
    expired = "expired"
    error = "error"

# --- MODELS ---

class Specialist(Base):
    __tablename__ = "specialist"
    __table_args__ = (
        CheckConstraint(
            "NOT (is_system AND is_test)",
            name="specialist_test_system_exclusive",
        ),
    )

    specialist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[SpecialistStatus] = mapped_column(SAEnum(SpecialistStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    onboarding_master_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    onboarding_personal_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, default=lambda: secrets.token_hex(4).upper())
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    specialization: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=True, index=True)
    referral_bonus_awarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    auth_telegram: Mapped["SpecialistAuthTelegram"] = relationship(back_populates="specialist", uselist=False)
    profile: Mapped["SpecialistProfile"] = relationship(back_populates="specialist", uselist=False)
    google_oauth: Mapped["GoogleOAuth"] = relationship(back_populates="specialist", uselist=False)
    calendar_settings: Mapped["SpecialistCalendarSettings"] = relationship(back_populates="specialist", uselist=False)
    calendar_sync_states: Mapped[List["CalendarSyncState"]] = relationship(back_populates="specialist")
    weekly_availability: Mapped[List["WeeklyAvailability"]] = relationship(back_populates="specialist")
    working_hours: Mapped[List["SpecialistWorkingHours"]] = relationship(back_populates="specialist")
    working_intervals: Mapped[List["SpecialistWorkingInterval"]] = relationship(back_populates="specialist")
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
            "slot_step_min >= 5 AND slot_step_min <= session_duration_min AND MOD(slot_step_min, 5) = 0",
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
    tariff_plan: Mapped[TariffPlan] = mapped_column(
        SAEnum(TariffPlan),
        nullable=False,
        default=TariffPlan.start,
        server_default=TariffPlan.start.value,
    )
    tariff_paid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tariff_period: Mapped[Optional[BillingPeriod]] = mapped_column(SAEnum(BillingPeriod), nullable=True)
    tariff_last_paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    start_bonus_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_bonus_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    analytics_upsell_prompted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
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


class SpecialistPublicProfile(Base):
    __tablename__ = "specialist_public_profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialist.specialist_id", ondelete="CASCADE"),
        nullable=False,
    )
    public_slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    middle_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specialization: Mapped[str] = mapped_column(Text, nullable=False)
    hero_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    contact_telegram: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_whatsapp: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    client_bot_username: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    specialist: Mapped["Specialist"] = relationship()
    blocks: Mapped[List["SpecialistPublicBlock"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    media: Mapped[List["SpecialistPublicMedia"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class SpecialistPublicBlock(Base):
    __tablename__ = "specialist_public_block"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialist_public_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    profile: Mapped["SpecialistPublicProfile"] = relationship(back_populates="blocks")


class SpecialistPublicMedia(Base):
    __tablename__ = "specialist_public_media"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialist_public_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    profile: Mapped["SpecialistPublicProfile"] = relationship(back_populates="media")


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


class CalendarSyncState(Base):
    __tablename__ = "calendar_sync_state"

    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), primary_key=True)
    calendar_id: Mapped[str] = mapped_column(Text, primary_key=True)
    sync_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel_expiration: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_enqueued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="calendar_sync_states")


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


class SpecialistWorkingHours(Base):
    __tablename__ = "specialist_working_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_specialist_working_hours_weekday_range"),
        CheckConstraint("start_time < end_time", name="ck_specialist_working_hours_time_order"),
        Index("ix_specialist_working_hours_specialist_weekday", "specialist_id", "weekday"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialist.specialist_id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    specialist: Mapped["Specialist"] = relationship(back_populates="working_hours")

    def __repr__(self) -> str:
        return (
            f"SpecialistWorkingHours(id={self.id!r}, specialist_id={self.specialist_id!r}, "
            f"weekday={self.weekday!r}, start_time={self.start_time!r}, end_time={self.end_time!r})"
        )

    def __str__(self) -> str:
        return (
            f"SpecialistWorkingHours(specialist_id={self.specialist_id}, weekday={self.weekday}, "
            f"{self.start_time}-{self.end_time})"
        )


class SpecialistWorkingInterval(Base):
    __tablename__ = "specialist_working_intervals"
    __table_args__ = (
        UniqueConstraint("specialist_id", "idx", name="uq_specialist_working_intervals_specialist_idx"),
        CheckConstraint("idx IN (1, 2, 3)", name="ck_specialist_working_intervals_idx"),
        CheckConstraint("(start_min BETWEEN 0 AND 1439) OR start_min IS NULL", name="ck_specialist_working_intervals_start_min_range"),
        CheckConstraint("(end_min BETWEEN 1 AND 1440) OR end_min IS NULL", name="ck_specialist_working_intervals_end_min_range"),
        CheckConstraint(
            "(start_min IS NULL AND end_min IS NULL) OR (start_min IS NOT NULL AND end_min IS NOT NULL)",
            name="ck_specialist_working_intervals_pair_presence",
        ),
        CheckConstraint(
            "start_min IS NULL OR end_min IS NULL OR start_min < end_min",
            name="ck_specialist_working_intervals_order",
        ),
        Index("ix_specialist_working_intervals_specialist_id", "specialist_id"),
    )

    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialist.specialist_id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    start_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    specialist: Mapped["Specialist"] = relationship(back_populates="working_intervals")


class Client(Base):
    __tablename__ = "client"
    __table_args__ = (
        UniqueConstraint(
            "specialist_id",
            "tg_user_id",
            name="uq_client_specialist_tg_user_id",
        ),
    )

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
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    specialist: Mapped["Specialist"] = relationship(back_populates="appointments")
    client: Mapped["Client"] = relationship(back_populates="appointments")
    calendar_link: Mapped[Optional["AppointmentCalendarLink"]] = relationship(
        back_populates="appointment",
        uselist=False,
    )


class AppointmentCalendarLink(Base):
    __tablename__ = "appointment_calendar_link"
    __table_args__ = (
        UniqueConstraint("google_event_id", "calendar_id", name="uq_appointment_calendar_link_event_calendar"),
        UniqueConstraint("appointment_id", name="uq_appointment_calendar_link_appointment_id"),
    )

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointment.appointment_id", ondelete="CASCADE"),
        primary_key=True,
    )
    specialist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    calendar_id: Mapped[str] = mapped_column(Text, nullable=False)
    google_event_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ical_uid: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    event_etag: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="calendar_link")


class AppointmentReminder(Base):
    __tablename__ = "appointment_reminder"
    __table_args__ = (
        UniqueConstraint("appointment_id", "reminder_type", name="uq_appointment_reminder_appointment_type"),
        CheckConstraint("reminder_type IN ('h24', 'h2')", name="ck_appointment_reminder_type"),
        Index("ix_appointment_reminder_due_at_utc", "due_at_utc"),
        Index("ix_appointment_reminder_sent_due", "sent_at_utc", "due_at_utc"),
        Index(
            "ix_appointment_reminder_due_unsent",
            "due_at_utc",
            postgresql_where=text("sent_at_utc IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointment.appointment_id", ondelete="CASCADE"),
        nullable=False,
    )
    specialist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reminder_type: Mapped[ReminderType] = mapped_column(
        SAEnum(ReminderType, native_enum=False),
        nullable=False,
    )
    due_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


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


class BillingPurchase(Base):
    __tablename__ = "billing_purchase"

    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specialist.specialist_id"), nullable=False)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan: Mapped[TariffPlan] = mapped_column(SAEnum(TariffPlan), nullable=False)
    period: Mapped[BillingPeriod] = mapped_column(SAEnum(BillingPeriod), nullable=False)
    amount_rub_int: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[BillingPurchaseStatus] = mapped_column(SAEnum(BillingPurchaseStatus), nullable=False)
    pay_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    yookassa_payment_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True, unique=True)
    yookassa_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    __table_args__ = (
        Index("ix_admin_audit_log_created_at_desc", desc("created_at")),
        Index(
            "ix_admin_audit_log_target_type_target_id_created_at_desc",
            "target_type",
            "target_id",
            desc("created_at"),
        ),
        Index("ix_admin_audit_log_action_created_at_desc", "action", desc("created_at")),
    )

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_subject: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    error_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("outbox_event_id", "target", name="uq_notification_log_outbox_event_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbox_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdminBulkCleanupJob(Base):
    __tablename__ = "admin_bulk_cleanup_job"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'partial')",
            name="admin_bulk_cleanup_job_status_chk",
        ),
        CheckConstraint("total_specialists >= 0", name="admin_bulk_cleanup_job_total_specialists_nonnegative_chk"),
        CheckConstraint("processed_specialists >= 0", name="admin_bulk_cleanup_job_processed_specialists_nonnegative_chk"),
        CheckConstraint("error_count >= 0", name="admin_bulk_cleanup_job_error_count_nonnegative_chk"),
        CheckConstraint(
            "processed_specialists <= total_specialists",
            name="admin_bulk_cleanup_job_processed_lte_total_chk",
        ),
        Index("ix_admin_bulk_cleanup_job_status", "status"),
        Index("ix_admin_bulk_cleanup_job_created_at", "created_at"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    total_specialists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_specialists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# --- Dependency Helper ---

async def get_db_session() -> AsyncSession:
    """Dependency helper for FastAPI/Aiogram handlers"""
    try:
        async with async_session_factory() as session:
            yield session
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            event="db_error",
            stage="get_db_session",
            exception_class=exc.__class__.__name__,
        )
        raise

async def init_db():
    """Helper to create tables for local/dev environments.

    Note: in production, schema updates for existing databases must be applied
    explicitly before restart (DDL scripts/migrations), then this helper can run
    safely as a no-op for already existing tables.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            event="db_error",
            stage="init_db",
            exception_class=exc.__class__.__name__,
        )
        raise


async def get_billing_purchase_by_token_hash(
    session: AsyncSession,
    token_hash: str,
) -> Optional[BillingPurchase]:
    stmt = select(BillingPurchase).where(BillingPurchase.pay_token_hash == token_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def mark_billing_purchase_used(
    session: AsyncSession,
    purchase_id: uuid.UUID,
    *,
    used_at: Optional[datetime] = None,
) -> None:
    used_at_value = used_at or datetime.now(timezone.utc)
    stmt = (
        update(BillingPurchase)
        .where(BillingPurchase.purchase_id == purchase_id)
        .values(used_at=used_at_value, updated_at=used_at_value)
    )
    await session.execute(stmt)


async def set_billing_purchase_yookassa_fields(
    session: AsyncSession,
    purchase_id: uuid.UUID,
    *,
    yookassa_payment_id: Optional[str],
    yookassa_status: Optional[str],
) -> None:
    stmt = (
        update(BillingPurchase)
        .where(BillingPurchase.purchase_id == purchase_id)
        .values(
            yookassa_payment_id=yookassa_payment_id,
            yookassa_status=yookassa_status,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await session.execute(stmt)


async def set_billing_purchase_status(
    session: AsyncSession,
    purchase_id: uuid.UUID,
    status: BillingPurchaseStatus,
) -> None:
    stmt = (
        update(BillingPurchase)
        .where(BillingPurchase.purchase_id == purchase_id)
        .values(status=status, updated_at=datetime.now(timezone.utc))
    )
    await session.execute(stmt)


async def get_billing_purchase_by_yookassa_payment_id(
    session: AsyncSession,
    yookassa_payment_id: str,
) -> Optional[BillingPurchase]:
    stmt = select(BillingPurchase).where(BillingPurchase.yookassa_payment_id == yookassa_payment_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_billing_purchase_for_tg_user(
    session: AsyncSession,
    tg_user_id: int,
) -> Optional[BillingPurchase]:
    stmt = (
        select(BillingPurchase)
        .where(BillingPurchase.tg_user_id == tg_user_id)
        .order_by(BillingPurchase.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# --- ensure all SQLAlchemy mappers are configured after model declarations ---
from sqlalchemy.orm import configure_mappers

configure_mappers()