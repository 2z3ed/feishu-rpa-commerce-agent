from tortoise import Tortoise
from src.config import config


async def init_db():
    """Initialize database connection"""
    await Tortoise.init(
        db_url=config.POSTGRES_URL,
        modules={"models": ["src.models"]}
    )
    # Generate schema
    await Tortoise.generate_schemas()


async def close_db():
    """Close database connection"""
    await Tortoise.close_connections()