from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import config.config as config

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String)
    user_first_name = Column(String)
    user_last_name = Column(String)
    set_tag = Column(Boolean)
    set_thumb = Column(Boolean)
    dl_count = Column(Integer, default=0)
    dl_size = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint('user_id', name='_user_user_id_uc'),)


class SqliteAccessor:
    def __init__(self) -> None:
        self.engine = None
        self.session = None

    async def on_connect(self):
        self.engine = create_async_engine(
            f'sqlite+aiosqlite:///{config.DATABASE_FILE}?cache=shared',
            echo=False,
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def on_disconnect(self):
        await self.engine.dispose()
