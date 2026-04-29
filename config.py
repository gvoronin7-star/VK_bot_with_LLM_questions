"""
Конфигурация бота - настройки VK API и LLM ProxyAPI.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass
class Settings:
    """Настройки бота."""
    
    # VK API
    VK_TOKEN: str
    VK_GROUP_ID: str
    PROXYAPI_URL: str
    PROXYAPI_KEY: str
    
    # Optional with defaults
    API_VERSION: str = "5.199"
    MODEL: str = "gpt-4.1"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1000
    CONTEXT_FILE: str = "data/context.json"
    MAX_TOKENS_IN_CONTEXT: int = 4000


# Загружаем переменные окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Создаём экземпляр настроек
settings = Settings(
    VK_TOKEN=os.environ.get('VK_ACCESS_TOKEN', ''),
    VK_GROUP_ID=os.environ.get('VK_GROUP_ID', ''),
    PROXYAPI_URL=os.environ.get('PROXYAPI_URL', 'https://proxy-api.example.com/v1/chat'),
    PROXYAPI_KEY=os.environ.get('PROXYAPI_KEY', ''),
    API_VERSION=os.environ.get('API_VERSION', '5.199'),
    MODEL=os.environ.get('LLM_MODEL', 'gpt-4.1'),
    TEMPERATURE=float(os.environ.get('TEMPERATURE', '0.7')),
    MAX_TOKENS=int(os.environ.get('MAX_TOKENS', '1000')),
    CONTEXT_FILE=os.environ.get('CONTEXT_FILE', 'data/context.json'),
    MAX_TOKENS_IN_CONTEXT=int(os.environ.get('MAX_TOKENS_IN_CONTEXT', '4000'))
)
