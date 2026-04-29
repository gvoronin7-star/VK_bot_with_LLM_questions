"""
Клиент для работы с LLM через ProxyAPI.
Отправляет запросы к GPT-4.1 и обрабатывает ответы.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any
from pathlib import Path

from config import settings


logger = logging.getLogger(__name__)


class APIClient:
    """
    Клиент для взаимодействия с LLM через ProxyAPI.
    
    Особенности:
    - Асинхронные запросы
    - Логирование запросов/ответов/ошибок
    - Поддержка температуры и лимита токенов
    """
    
    def __init__(self):
        self.base_url = settings.PROXYAPI_URL
        self.api_key = settings.PROXYAPI_KEY
        self.model = settings.MODEL
        self.temperature = settings.TEMPERATURE
        self.max_tokens = settings.MAX_TOKENS
        self.log_file = Path("errors.log")
    
    async def send_request(self, messages: List[Dict[str, str]], temperature: float = None, max_tokens: int = None) -> str:
        """
        Отправляет запрос к LLM и получает ответ.
        
        Args:
            messages: Список сообщений в формате OpenAI API
            temperature: Температура (если None - используется настройка из config)
            max_tokens: Лимит токенов (если None - используется настройка из config)
        
        Returns:
            str: Текст ответа от LLM
        
        Raises:
            Exception: При ошибках запроса
        """
        # Используем переданные значения или настройки из config
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"Sending request to ProxyAPI: model={self.model}, "
                       f"messages={len(messages)}, temperature={temp}, max_tokens={tokens}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = f"API error: status={response.status}, body={error_text}"
                        logger.error(error_msg)
                        self._log_error(error_msg)
                        raise Exception(f"ProxyAPI returned status {response.status}")
                    
                    data = await response.json()
                    
                    # Логирование успешного ответа
                    logger.info(f"Received response from ProxyAPI")
                    self._log_request(messages, data, temp, tokens)
                    
                    # Извлекаем ответ
                    if 'choices' in data and len(data['choices']) > 0:
                        response_text = data['choices'][0]['message']['content']
                        
                        # Логируем токены если доступны
                        if 'usage' in data:
                            tokens_used = data['usage'].get('total_tokens', 0)
                            logger.info(f"Tokens used: {tokens_used}")
                        
                        return response_text
                    else:
                        error_msg = "Invalid response format from ProxyAPI"
                        logger.error(error_msg)
                        self._log_error(error_msg)
                        raise Exception(error_msg)
        
        except aiohttp.ClientError as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            self._log_error(error_msg)
            raise Exception(f"Network error: {e}")
        
        except asyncio.TimeoutError:
            error_msg = "Request timeout"
            logger.error(error_msg)
            self._log_error(error_msg)
            raise Exception("Request timeout")
        
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            self._log_error(error_msg)
            raise
    
    def _log_request(self, messages: List[Dict[str, str]], response: Dict[str, Any], temp: float, tokens: int) -> None:
        """
        Логирует запрос и ответ в файл errors.log.
        
        Args:
            messages: Отправленные сообщения
            response: Ответ от API
            temp: Температура
            tokens: Max tokens
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write("REQUEST LOG\n")
                f.write("=" * 80 + "\n")
                
                # Запрос
                f.write(f"Model: {self.model}\n")
                f.write(f"Temperature: {temp}\n")
                f.write(f"Max Tokens: {tokens}\n")
                f.write(f"Messages ({len(messages)}):\n")
                for msg in messages:
                    f.write(f"  [{msg['role'].upper()}]: {msg['content'][:200]}...\n")
                
                # Ответ
                f.write(f"\nResponse:\n")
                if 'choices' in response:
                    content = response['choices'][0]['message']['content']
                    f.write(f"  {content[:500]}...\n")
                
                # Использование токенов
                if 'usage' in response:
                    usage = response['usage']
                    f.write(f"\nUsage:\n")
                    f.write(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}\n")
                    f.write(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}\n")
                    f.write(f"  Total tokens: {usage.get('total_tokens', 'N/A')}\n")
                
                f.write("\n")
        
        except Exception as e:
            logger.error(f"Error writing to log file: {e}")
    
    def _log_error(self, error_msg: str) -> None:
        """
        Логирует ошибку в файл errors.log.
        
        Args:
            error_msg: Текст ошибки
        """
        try:
            from datetime import datetime
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[ERROR] {datetime.now().isoformat()}: {error_msg}\n")
        except Exception as e:
            logger.error(f"Error writing error to log: {e}")
