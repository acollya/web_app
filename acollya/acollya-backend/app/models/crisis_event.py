import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CrisisEvent(Base):
    """
    Audit log for crisis detection events.

    Purpose: probatório — allows Acollya to demonstrate in any legal proceeding
    that the crisis protocol was followed (CVV shown, level recorded).

    Privacy: user_id links to the users row, which is anonymised on account
    deletion. After anonymisation, this row is pseudonymous (no remaining PII
    linkage). source_message_id references chat_messages and is preserved per
    the same LGPD Art. 12 strategy as other content tables.
    """
    __tablename__ = "crisis_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    crisis_level: Mapped[str] = mapped_column(Text, nullable=False)  # none / medium / high / critical
    cvv_shown: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # chat / journal
    source_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
