from typing import Optional
from sqlalchemy import delete, update, insert, func
from sqlalchemy.future import select
from app.store.database.accessor import SqliteAccessor, User
from app.store.database.tools import row_to_dict

db = SqliteAccessor()


async def get_user(user_id) -> Optional[dict]:
    async with db.session() as session:
        stmt = select(User).where(user_id == User.user_id)
        result = await session.execute(stmt)
        return row_to_dict(result.first())


async def insert_user(user):
    async with db.session() as session:
        async with session.begin():
            stmt = insert(User).values(**user)
            await session.execute(stmt)
        await session.commit()


async def update_user(user):
    async with db.session() as session:
        async with session.begin():
            stmt = update(User).values(**user).where(user['user_id'] == User.user_id)
            await session.execute(stmt)
        await session.commit()


async def delete_user(user_id):
    async with db.session() as session:
        async with session.begin():
            stmt = delete(User).where(user_id == User.user_id)
            await session.execute(stmt)
        await session.commit()


async def get_stat():
    async with db.session() as session:
        stmt = select(func.sum(User.dl_count), func.sum(User.dl_size)).select_from(User)
        result = await session.execute(stmt)
        return result.first()
