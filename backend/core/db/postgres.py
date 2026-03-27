import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from dotenv import load_dotenv

load_dotenv(r"C:\Users\soura\ethos\Ethos\backend\.env")

POSTGRES_URL = os.getenv("POSTGRES_URL")
engine = create_async_engine(POSTGRES_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    url = Column(String, unique=True, index=True)
    source = Column(String, index=True)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    category = Column(String, nullable=True)

class UserConstitution(Base):
    __tablename__ = "user_constitutions"

    user_id = Column(String, primary_key=True, index=True)
    constitution = Column(JSONB)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def save_article(article_data: dict):
    async with AsyncSessionLocal() as session:
        try:
            pub_date = article_data.get('published_at')
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except ValueError:
                    pub_date = datetime.utcnow()
            elif not pub_date:
                pub_date = datetime.utcnow()

            new_article = Article(
                id=str(article_data['id']),
                title=article_data.get('title', 'Unknown Title'),
                content=article_data.get('content', ''),
                url=article_data['url'],
                source=article_data.get('source', ''),
                image_url=article_data.get('image_url'),
                published_at=pub_date,
                category=article_data.get('category')
            )
            session.add(new_article)
            await session.commit()
        except Exception as e:
            await session.rollback()
            pass
