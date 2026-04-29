"""
Тесты для API клиента.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp

from api_client import APIClient


class TestAPIClient:
    """Тесты для клиента ProxyAPI."""
    
    @pytest.fixture
    def api_client(self):
        """Создаёт экземпляр API клиента."""
        with patch('config.settings') as mock_settings:
            mock_settings.PROXYAPI_URL = "https://test-api.example.com/v1/chat"
            mock_settings.PROXYAPI_KEY = "test_key"
            mock_settings.MODEL = "gpt-4.1"
            mock_settings.TEMPERATURE = 0.7
            mock_settings.MAX_TOKENS = 1000
            
            client = APIClient()
            return client
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, api_client):
        """Успешный запрос к API."""
        # Мокируем ответ API
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [
                {
                    "message": {
                        "content": "Это тестовый ответ от LLM"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            messages = [
                {"role": "user", "content": "Привет"}
            ]
            response = await api_client.send_request(messages)
            
            assert response == "Это тестовый ответ от LLM"
    
    @pytest.mark.asyncio
    async def test_send_request_error(self, api_client):
        """Обработка ошибки API."""
        # Мокируем ошибку API
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            messages = [
                {"role": "user", "content": "Привет"}
            ]
            
            with pytest.raises(Exception) as exc_info:
                await api_client.send_request(messages)
            
            assert "401" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_request_timeout(self, api_client):
        """Обработка таймаута запроса."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            messages = [
                {"role": "user", "content": "Привет"}
            ]
            
            with pytest.raises(Exception) as exc_info:
                await api_client.send_request(messages)
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_log_request(self, api_client, tmp_path):
        """Логирование запроса."""
        log_file = tmp_path / "errors.log"
        api_client.log_file = log_file
        
        messages = [
            {"role": "user", "content": "Тестовое сообщение"}
        ]
        response = {
            "choices": [
                {
                    "message": {
                        "content": "Тестовый ответ"
                    }
                }
            ],
            "usage": {
                "total_tokens": 25
            }
        }
        
        api_client._log_request(messages, response)
        
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert "REQUEST LOG" in content
        assert "Тестовое сообщение" in content
        assert "Тестовый ответ" in content
    
    @pytest.mark.asyncio
    async def test_log_error(self, api_client, tmp_path):
        """Логирование ошибки."""
        log_file = tmp_path / "errors.log"
        api_client.log_file = log_file
        
        api_client._log_error("Тестовая ошибка")
        
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert "[ERROR]" in content
        assert "Тестовая ошибка" in content
