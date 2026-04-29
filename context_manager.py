"""
Менеджер контекста диалога.
Хранит историю сообщений, управляет токенами и сохраняет состояние.
"""

import json
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Сообщение в контексте диалога."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class UserContext:
    """Контекст диалога для одного пользователя."""
    messages: List[Dict[str, str]] = field(default_factory=list)
    session_id: str = ""
    run_number: int = 0
    tokens_used: int = 0
    temperature: float = 0.7
    max_tokens: int = 1000
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())


class ContextManager:
    """
    Управляет контекстом диалога для пользователей.
    
    Особенности:
    - Хранение в оперативной памяти
    - Автосохранение в data/context.json
    - Ограничение контекста 4000 токенами (FIFO)
    """
    
    def __init__(self, context_file: str = "data/context.json", max_tokens: int = 4000):
        self.context_file = Path(context_file)
        self.contexts: Dict[int, UserContext] = {}
        self.max_tokens = max_tokens
        
        # Создаём директорию если не существует
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем существующий контекст
        self._load_context()
    
    def ensure_user(self, user_id: int) -> UserContext:
        """
        Создаёт или возвращает существующий контекст для пользователя.
        
        Args:
            user_id: ID пользователя VK
            
        Returns:
            UserContext: Контекст пользователя
        """
        if user_id not in self.contexts:
            self.contexts[user_id] = UserContext()
            logger.info(f"Created new context for user {user_id}")
        
        return self.contexts[user_id]
    
    def add_message(self, user_id: int, role: str, content: str) -> None:
        """
        Добавляет сообщение в контекст пользователя.
        
        Args:
            user_id: ID пользователя
            role: Роль сообщения ("user", "assistant", "system")
            content: Текст сообщения
        """
        context = self.ensure_user(user_id)
        
        # Добавляем сообщение
        context.messages.append({
            "role": role,
            "content": content
        })
        
        # Ограничиваем контекст по токенам
        self._limit_context(user_id)
        
        # Автосохранение
        self._save_context()
        
        logger.debug(f"Added {role} message for user {user_id}: '{content[:50]}...'")
    
    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """
        Получает историю сообщений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict[str, str]]: История сообщений
        """
        context = self.ensure_user(user_id)
        return context.messages.copy()
    
    def clear_context(self, user_id: int) -> None:
        """
        Очищает контекст пользователя.
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self.contexts:
            self.contexts[user_id] = UserContext()
            self._save_context()
            logger.info(f"Cleared context for user {user_id}")
    
    def _limit_context(self, user_id: int) -> None:
        """
        Ограничивает контекст максимальным числом токенов (FIFO).
        
        Удаляет самые старые сообщения при превышении лимита.
        """
        context = self.contexts.get(user_id)
        if not context:
            return
        
        # Подсчитываем токены (приближённо: 1 слово ≈ 1.3 токена)
        total_tokens = self._count_tokens(context.messages)
        
        # Удаляем старые сообщения пока не уложимся в лимит
        while total_tokens > self.max_tokens and context.messages:
            # Удаляем самые старые сообщения (кроме system если есть)
            if len(context.messages) > 1 and context.messages[0]['role'] == 'system':
                context.messages.pop(1)
            else:
                context.messages.pop(0)
            
            total_tokens = self._count_tokens(context.messages)
        
        if total_tokens > self.max_tokens:
            logger.warning(f"Context for user {user_id} still exceeds limit after truncation")
    
    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Приближённо подсчитывает количество токенов в сообщениях.
        
        Args:
            messages: Список сообщений
            
        Returns:
            int: Примерное количество токенов
        """
        total = 0
        for msg in messages:
            content = msg.get('content', '')
            # Приближённый подсчёт: 1 слово ≈ 1.3 токена
            words = len(content.split())
            total += int(words * 1.3)
        return total
    
    def update_stats(self, user_id: int, tokens_used: int = None, run_number: int = None, temperature: float = None, max_tokens: int = None) -> None:
        """
        Обновляет статистику использования токенов и настройки.
        
        Args:
            user_id: ID пользователя
            tokens_used: Количество использованных токенов (если None - инкремент)
            run_number: Номер прогона (если None - инкремент)
            temperature: Температура (если None - не меняется)
            max_tokens: Max tokens (если None - не меняется)
        """
        context = self.ensure_user(user_id)
        
        if run_number is not None:
            context.run_number = run_number
        else:
            context.run_number += 1
            
        if tokens_used is not None:
            context.tokens_used = tokens_used
        else:
            context.tokens_used += 100  # Дефолтное значение
            
        if temperature is not None:
            context.temperature = temperature
            
        if max_tokens is not None:
            context.max_tokens = max_tokens
            
        self._save_context()
    
    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику использования для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict[str, Any]: Статистика
        """
        context = self.ensure_user(user_id)
        return {
            "run_number": context.run_number,
            "tokens_used": context.tokens_used,
            "session_id": context.session_id,
            "message_count": len(context.messages),
            "temperature": context.temperature,
            "max_tokens": context.max_tokens
        }
    
    def _load_context(self) -> None:
        """Загружает контекст из файла."""
        if not self.context_file.exists():
            logger.info("No existing context file found, starting fresh")
            return
        
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for user_id_str, context_data in data.items():
                user_id = int(user_id_str)
                self.contexts[user_id] = UserContext(
                    messages=context_data.get('messages', []),
                    session_id=context_data.get('session_id', ''),
                    run_number=context_data.get('run_number', 0),
                    tokens_used=context_data.get('tokens_used', 0),
                    temperature=context_data.get('temperature', 0.7),
                    max_tokens=context_data.get('max_tokens', 1000)
                )
            
            logger.info(f"Loaded contexts for {len(self.contexts)} users")
            
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            self.contexts = {}
    
    def _save_context(self) -> None:
        """Сохраняет контекст в файл."""
        try:
            data = {}
            for user_id, context in self.contexts.items():
                data[str(user_id)] = {
                    "messages": context.messages,
                    "session_id": context.session_id,
                    "run_number": context.run_number,
                    "tokens_used": context.tokens_used,
                    "temperature": context.temperature,
                    "max_tokens": context.max_tokens
                }
            
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug("Context saved to file")
            
        except Exception as e:
            logger.error(f"Error saving context: {e}")

