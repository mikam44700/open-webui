import logging
import time
from typing import Literal, Optional
from uuid import uuid4

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Index, Text, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


####################
# Hermes Activity DB Schema
####################

# Every treatment the engine performs, whatever the channel it came from.
#
# The engine's own API cannot answer this: /v1/runs is POST-only, so runs
# cannot be enumerated after the fact. Work triggered from Telegram or from a
# schedule would otherwise leave no trace an operator can consult. This table
# is that trace, written by the backend proxy, which is the single point every
# call already goes through.

# Where the treatment was triggered from.
SOURCES = ('interface', 'telegram', 'scheduled', 'api')

# Outcome of the treatment. Deliberately four values, not two: `unknown` means
# the engine was unreachable or answered without a usable status, which is NOT
# a failure of the treatment itself and must never be reported as one. Only
# `error` is a real failure. `pending` is the one that carries the product:
# the engine prepared something and a human has to sign it off.
STATUSES = ('ok', 'pending', 'error', 'unknown')


class HermesActivity(Base):
    __tablename__ = 'hermes_activity'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=True)  # null when triggered by a schedule
    source = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    reference = Column(Text, nullable=True)  # order number, document id, ...
    error = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    decided_by = Column(Text, nullable=True)
    decided_at = Column(BigInteger, nullable=True)

    __table_args__ = (
        Index('ix_hermes_activity_created', 'created_at'),
        Index('ix_hermes_activity_status_created', 'status', 'created_at'),
        Index('ix_hermes_activity_user_created', 'user_id', 'created_at'),
    )


####################
# Pydantic Models
####################


class HermesActivityModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    source: str
    action: str
    status: str
    summary: Optional[str] = None
    reference: Optional[str] = None
    error: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    decided_by: Optional[str] = None
    decided_at: Optional[int] = None


class HermesActivityForm(BaseModel):
    source: str
    action: str
    status: str
    summary: Optional[str] = None
    reference: Optional[str] = None
    error: Optional[str] = None
    meta: Optional[dict] = None


class HermesActivityCounts(BaseModel):
    ok: int = 0
    pending: int = 0
    error: int = 0
    unknown: int = 0
    total: int = 0


####################
# Table
####################


class HermesActivityTable:
    async def insert(
        self,
        form: HermesActivityForm,
        user_id: Optional[str] = None,
    ) -> Optional[HermesActivityModel]:
        source = form.source if form.source in SOURCES else 'api'
        status = form.status if form.status in STATUSES else 'unknown'

        entry = HermesActivityModel(
            id=str(uuid4()),
            user_id=user_id,
            source=source,
            action=form.action,
            status=status,
            summary=form.summary,
            reference=form.reference,
            error=form.error,
            meta=form.meta,
            created_at=int(time.time()),
        )

        try:
            async with get_async_db_context() as db:
                row = HermesActivity(**entry.model_dump())
                db.add(row)
                await db.commit()
                return entry
        except Exception:
            # Journalling must never break the treatment it is recording.
            log.exception('failed to record hermes activity')
            return None

    async def list(
        self,
        limit: int = 50,
        skip: int = 0,
        status: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[int] = None,
    ) -> list[HermesActivityModel]:
        async with get_async_db_context() as db:
            query = select(HermesActivity)

            if status in STATUSES:
                query = query.where(HermesActivity.status == status)
            if source in SOURCES:
                query = query.where(HermesActivity.source == source)
            if since is not None:
                query = query.where(HermesActivity.created_at >= since)

            query = query.order_by(HermesActivity.created_at.desc()).offset(skip).limit(limit)

            result = await db.execute(query)
            return [HermesActivityModel.model_validate(row) for row in result.scalars().all()]

    async def counts(self, since: Optional[int] = None) -> HermesActivityCounts:
        async with get_async_db_context() as db:
            query = select(HermesActivity.status, func.count(HermesActivity.id))
            if since is not None:
                query = query.where(HermesActivity.created_at >= since)
            query = query.group_by(HermesActivity.status)

            result = await db.execute(query)
            tally = {status: count for status, count in result.all()}

        return HermesActivityCounts(
            ok=tally.get('ok', 0),
            pending=tally.get('pending', 0),
            error=tally.get('error', 0),
            unknown=tally.get('unknown', 0),
            total=sum(tally.values()),
        )

    async def decide(
        self,
        id: str,
        issue: str,
        user_id: str,
        motif: Optional[str] = None,
    ) -> Optional[HermesActivityModel]:
        """Records a human decision on a treatment awaiting signature.

        Only `pending` rows can be decided, and a decision is final. Re-deciding
        an already-decided treatment is refused rather than silently applied:
        the second signature would overwrite the first, and the record of who
        approved what is the whole point of these columns.

        Returns None when the row is absent or no longer pending — the caller
        turns that into a 404 or a 409, which are different answers.
        """
        if issue not in ('ok', 'error'):
            return None

        async with get_async_db_context() as db:
            result = await db.execute(select(HermesActivity).where(HermesActivity.id == id))
            row = result.scalars().first()

            if row is None or row.status != 'pending':
                return None

            row.status = issue
            row.decided_by = user_id
            row.decided_at = int(time.time())
            if motif:
                row.error = motif

            await db.commit()
            await db.refresh(row)
            return HermesActivityModel.model_validate(row)

    async def get_by_id(self, id: str) -> Optional[HermesActivityModel]:
        async with get_async_db_context() as db:
            result = await db.execute(select(HermesActivity).where(HermesActivity.id == id))
            row = result.scalars().first()
            return HermesActivityModel.model_validate(row) if row else None

    async def delete_older_than(self, cutoff: int) -> int:
        async with get_async_db_context() as db:
            result = await db.execute(delete(HermesActivity).where(HermesActivity.created_at < cutoff))
            await db.commit()
            return result.rowcount or 0


HermesActivities = HermesActivityTable()
