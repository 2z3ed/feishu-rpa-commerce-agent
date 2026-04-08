import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # Feishu configuration
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
    
    # WooCommerce configuration
    WOOCOMMERCE_URL = os.getenv("WOOCOMMERCE_URL", "")
    WOOCOMMERCE_CONSUMER_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "")
    WOOCOMMERCE_CONSUMER_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "")
    
    # Odoo configuration
    ODOO_URL = os.getenv("ODOO_URL", "")
    ODOO_DB = os.getenv("ODOO_DB", "")
    ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
    ODOO_API_KEY = os.getenv("ODOO_API_KEY", "")
    
    # Chatwoot configuration
    CHATWOOT_API_URL = os.getenv("CHATWOOT_API_URL", "")
    CHATWOOT_API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "")
    
    # Database configuration
    POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://admin:password@localhost:5432/example_db")
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # LLM configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
    
    # Application configuration
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    PORT = int(os.getenv("PORT", "8000"))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # RPA configuration
    RPA_HEADLESS = os.getenv("RPA_HEADLESS", "True").lower() == "true"


config = Config()