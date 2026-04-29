"""
Тесты для конфигурации и контекста.
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from config import settings
from context_manager import ContextManager, UserContext, Message


class TestSettings:
    """Тесты для конфигурации."""
    
    def test_settings_have_required_fields(self):
        """Проверка наличия обязательных полей в настройках."""
        assert hasattr(settings, 'VK_TOKEN')
        assert hasattr(settings, 'VK_GROUP_ID')
        assert hasattr(settings, 'PROXYAPI_URL')
        assert hasattr(settings, 'PROXYAPI_KEY')
    
    def test_settings_default_values(self):
        """Проверка значений по умолчанию."""
        assert settings.MODEL == "gpt-4.1"
        assert settings.TEMPERATURE == 0.7
        assert settings.MAX_TOKENS == 1000
        assert settings.MAX_TOKENS_IN_CONTEXT == 4000


class TestContextManager:
    """Тесты для менеджера контекста."""
    
    @pytest.fixture
    def temp_context_file(self, tmp_path):
        """Создаёт временный файл для контекста."""
        context_file = tmp_path / "context.json"
        return str(context_file)
    
    def test_create_new_user_context(self, temp_context_file):
        """Создание нового контекста пользователя."""
        manager = ContextManager(temp_context_file)
        context = manager.ensure_user(123)
        
        assert context is not None
        assert len(context.messages) == 0
        assert context.session_id != ""
    
    def test_add_message_to_context(self, temp_context_file):
        """Добавление сообщения в контекст."""
        manager = ContextManager(temp_context_file)
        manager.add_message(123, "user", "Привет!")
        
        messages = manager.get_messages(123)
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == 'Привет!'
    
    def test_clear_context(self, temp_context_file):
        """Очистка контекста."""
        manager = ContextManager(temp_context_file)
        manager.add_message(123, "user", "Привет!")
        manager.clear_context(123)
        
        messages = manager.get_messages(123)
        assert len(messages) == 0
    
    def test_context_persistence(self, temp_context_file):
        """Сохранение и загрузка контекста."""
        # Создаём менеджер и добавляем сообщение
        manager1 = ContextManager(temp_context_file)
        manager1.add_message(123, "user", "Тестовое сообщение")
        
        # Создаём новый менеджер - должен загрузить сохранённый контекст
        manager2 = ContextManager(temp_context_file)
        messages = manager2.get_messages(123)
        
        assert len(messages) == 1
        assert messages[0]['content'] == 'Тестовое сообщение'
    
    def test_context_limit(self, temp_context_file):
        """Ограничение контекста по токенам."""
        # Создаём менеджер с маленьким лимитом для теста
        manager = ContextManager(temp_context_file, max_tokens=50)
        
        # Добавляем длинные сообщения (каждое ~20 слов * 1.3 = ~26 токенов)
        long_text = "это очень длинное сообщение которое содержит много слов для тестирования лимита токенов в контексте диалога бота"
        for i in range(10):
            manager.add_message(123, "user", f"{long_text} номер {i}")
        
        messages = manager.get_messages(123)
        # При лимите 50 токенов и ~26 токенов на сообщение
        # должно остаться меньше 10 сообщений
        assert len(messages) < 10
    
    def test_get_stats(self, temp_context_file):
        """Получение статистики."""
        manager = ContextManager(temp_context_file)
        manager.add_message(123, "user", "Привет!")
        manager.update_stats(123, 50)
        
        stats = manager.get_stats(123)
        assert stats['run_number'] == 1
        assert stats['tokens_used'] == 50
        assert stats['message_count'] == 1


class TestUserContext:
    """Тесты для класса UserContext."""
    
    def test_user_context_initialization(self):
        """Инициализация контекста пользователя."""
        context = UserContext()
        
        assert context.messages == []
        assert context.session_id != ""
        assert context.run_number == 0
        assert context.tokens_used == 0
    
    def test_user_context_with_messages(self):
        """Контекст с сообщениями."""
        messages = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте!"}
        ]
        context = UserContext(messages=messages)
        
        assert len(context.messages) == 2
