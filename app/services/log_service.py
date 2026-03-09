from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models import AccessLog


class LogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        action: str,
        file_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        details: str = None,
    ) -> AccessLog:
        log = AccessLog(
            action=action,
            file_id=file_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_logs(
        self, skip: int = 0, limit: int = 50, action: str = None
    ) -> list[AccessLog]:
        query = select(AccessLog).order_by(desc(AccessLog.timestamp))
        if action:
            query = query.where(AccessLog.action == action)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_logs_by_file(self, file_id: str) -> list[AccessLog]:
        query = (
            select(AccessLog)
            .where(AccessLog.file_id == file_id)
            .order_by(desc(AccessLog.timestamp))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
