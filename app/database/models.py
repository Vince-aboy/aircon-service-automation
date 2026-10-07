"""Relational model for the controlled aircon-service booking workflow."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, Time, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    address_line: Mapped[str] = mapped_column(String(255), nullable=False)
    barangay: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    coverage_area: Mapped[str] = mapped_column(String(100), nullable=False)
    service_area_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class ServiceType(Base):
    __tablename__ = "service_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (CheckConstraint("duration_minutes > 0", name="ck_service_types_positive_duration"),)


class BookingRequest(Base):
    __tablename__ = "booking_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False)
    service_type_id: Mapped[int] = mapped_column(ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False)
    aircon_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default="Window Type")
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_window: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("unit_count > 0", name="ck_booking_requests_positive_unit_count"),
        CheckConstraint(
            "status IN ('pending_review', 'waitlisted', 'approved_for_scheduling', 'scheduled', 'cancelled')",
            name="ck_booking_requests_status",
        ),
    )


class BookingRequestStatusHistory(Base):
    __tablename__ = "booking_request_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_request_id: Mapped[int] = mapped_column(ForeignKey("booking_requests.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="local_staff")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("actor_type = 'local_staff'", name="ck_booking_request_history_local_staff"),
    )


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class ServiceTeam(Base):
    __tablename__ = "service_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_team_id: Mapped[int] = mapped_column(ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=False)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id", ondelete="RESTRICT"), nullable=False)
    is_lead: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (UniqueConstraint("service_team_id", "technician_id", name="uq_team_memberships_team_technician"),)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_request_id: Mapped[int] = mapped_column(ForeignKey("booking_requests.id", ondelete="RESTRICT"), nullable=False, unique=True)
    service_team_id: Mapped[int] = mapped_column(ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=False)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id", ondelete="RESTRICT"), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="confirmed")

    __table_args__ = (
        CheckConstraint("scheduled_end > scheduled_start", name="ck_appointments_valid_time_range"),
        CheckConstraint(
            "status IN ('confirmed', 'en_route', 'in_progress', 'completed', 'cancelled')",
            name="ck_appointments_status",
        ),
        Index(
            "uq_appointments_active_team_scheduled_start",
            "service_team_id",
            "scheduled_start",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
            sqlite_where=text("status <> 'cancelled'"),
        ),
    )


class AppointmentStatusHistory(Base):
    __tablename__ = "appointment_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_request_id: Mapped[int] = mapped_column(ForeignKey("booking_requests.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, server_default="simulated")
    recipient_masked: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("channel = 'simulated'", name="ck_notification_outbox_simulated_channel"),
        CheckConstraint("status IN ('pending', 'recorded', 'failed')", name="ck_notification_outbox_status"),
    )


class ScheduleIntake(Base):
    """A raw staff schedule message awaiting review and confirmation."""

    __tablename__ = "schedule_intakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft")
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="manual_paste")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready', 'confirmed', 'cancelled')",
            name="ck_schedule_intakes_status",
        ),
        CheckConstraint(
            "source = 'manual_paste'",
            name="ck_schedule_intakes_manual_source",
        ),
        Index("ix_schedule_intakes_schedule_date", "schedule_date"),
    )


class ScheduleIntakeItem(Base):
    """One editable draft row extracted from a raw schedule intake."""

    __tablename__ = "schedule_intake_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_intake_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_intakes.id", ondelete="CASCADE"), nullable=False
    )
    source_line: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    service_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=True
    )
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    customer_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    service_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=True
    )
    raw_service_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    building_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unit_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    scheduled_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="needs_review")
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    booking_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("booking_requests.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    appointment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("building_number IS NULL OR building_number > 0", name="ck_schedule_items_positive_building"),
        CheckConstraint("price IS NULL OR price >= 0", name="ck_schedule_items_nonnegative_price"),
        CheckConstraint(
            "review_status IN ('needs_review', 'ready', 'confirmed', 'skipped')",
            name="ck_schedule_items_review_status",
        ),
        Index("ix_schedule_intake_items_intake_id", "schedule_intake_id"),
        Index("ix_schedule_intake_items_review_status", "review_status"),
    )
