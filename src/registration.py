from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import CustomUser
from qr_code import generate_qr_code


class UserRegistration:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, telegram_id: int) -> CustomUser | None:
        result = await self.session.execute(
            select(CustomUser).where(CustomUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
            self,
            telegram_id: int,
            first_name: str,
            last_name: str,
            full_name: str | None = None,
            birth_date: datetime | None = None,
            referrer_id: int | None = None,
            personal_data_consent: bool = False
    ) -> CustomUser:
        if not full_name:
            parts = [part for part in [first_name, last_name] if part]
            full_name = " ".join(parts) if parts else None

        qr_code = generate_qr_code(telegram_id)

        user = CustomUser(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            birth_date=birth_date,
            qr_code=qr_code,
            referrer_id=referrer_id,
            personal_data_consent=personal_data_consent
        )
        self.session.add(user)
        await self.session.commit()
        return user
