"""
Асинхронный VK-бот с интеграцией LLM GPT-4.1 через ProxyAPI.
Поддержка контекста диалога, отчётность и логирование.
"""

import logging
from pathlib import Path
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor
from typing import Dict, Any
from datetime import datetime

from config import settings
from context_manager import ContextManager
from api_client import APIClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('errors.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_main_keyboard() -> Keyboard:
    """Создаёт основную клавиатуру с кнопками."""
    keyboard = Keyboard(one_time=False)
    
    # Первая строка кнопок
    keyboard.row()
    keyboard.add({"command": "/start"}, color=KeyboardButtonColor.PRIMARY)
    keyboard.add({"command": "/clear"}, color=KeyboardButtonColor.PRIMARY)
    keyboard.add({"command": "/settings"}, color=KeyboardButtonColor.SECONDARY)
    keyboard.add({"command": "/report"}, color=KeyboardButtonColor.SECONDARY)
    
    # Вторая строка кнопок
    keyboard.row()
    keyboard.add({"command": "/rate creative"}, color=KeyboardButtonColor.POSITIVE)
    keyboard.add({"command": "/rate concise"}, color=KeyboardButtonColor.NEGATIVE)
    
    return keyboard


def create_empty_keyboard() -> Keyboard:
    """Создаёт пустую клавиатуру."""
    return Keyboard(one_time=False)


class ChatBot:
    """Класс для обработки сообщений и взаимодействия с LLM."""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.api_client = APIClient()
        self.report_file = Path("REPORT.md")
        
    async def handle_message(self, message: Message) -> None:
        """Обрабатывает входящее сообщение пользователя."""
        user_id = message.from_id
        text = message.text.strip() if message.text else ''
        
        logger.info(f"Received message from user {user_id}: '{text}'")
        
        # Игнорируем пустые сообщения
        if not text:
            return
        
        # Обработка команд
        if text.startswith('/'):
            await self.handle_command(message, text, user_id)
            return
        
        # Обработка обычного текста - диалог с LLM
        await self.handle_dialog(message, text, user_id)
    
    async def handle_command(self, message: Message, command: str, user_id: int) -> None:
        """Обрабатывает команды пользователя."""
        cmd = command.lower()
        
        if cmd == '/start':
            await self.cmd_start(message, user_id)
        elif cmd == '/clear':
            await self.cmd_clear(message, user_id)
        elif cmd == '/help':
            await self.cmd_help(message)
        elif cmd == '/report':
            await self.cmd_report(message)
        elif cmd == '/settings':
            await self.cmd_settings(message)
        elif cmd.startswith('/settemp'):
            await self.cmd_settemp(message, command, user_id)
        elif cmd.startswith('/settokens'):
            await self.cmd_settokens(message, command, user_id)
        elif cmd.startswith('/rate'):
            await self.cmd_rate(message, command, user_id)
        else:
            await message.answer("Неизвестная команда. Используйте /help для списка команд.")
    
    async def handle_dialog(self, message: Message, text: str, user_id: int) -> None:
        """Обрабатывает текстовое сообщение для диалога с LLM."""
        # Добавляем сообщение пользователя в контекст
        self.context_manager.add_message(user_id, "user", text)
        
        # Получаем настройки пользователя
        stats = self.context_manager.get_stats(user_id)
        user_temp = stats.get('temperature', settings.TEMPERATURE)
        user_max_tokens = stats.get('max_tokens', settings.MAX_TOKENS)
        
        # Получаем ответ от LLM
        try:
            response = await self.api_client.send_request(
                self.context_manager.get_messages(user_id),
                temperature=user_temp,
                max_tokens=user_max_tokens
            )
            
            # Добавляем ответ LLM в контекст
            self.context_manager.add_message(user_id, "assistant", response)
            
            # Обновляем статистику - УВЕЛИЧИВАЕМ run_number и tokens_used
            new_tokens = stats.get('tokens_used', 0) + 100
            new_run_number = stats.get('run_number', 0) + 1
            self.context_manager.update_stats(
                user_id,
                tokens_used=new_tokens, 
                run_number=new_run_number,
                temperature=user_temp,
                max_tokens=user_max_tokens
            )
            
            # Отправляем ответ пользователю
            await message.answer(response)
            
            # Обновляем отчёт
            self.update_report(user_id, response)
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")
    
    async def cmd_start(self, message: Message, user_id: int) -> None:
        """Обработка команды /start."""
        # Инициализируем сессию для пользователя
        self.context_manager.ensure_user(user_id)
        
        welcome_text = (
            "👋 Привет! Я бот с поддержкой LLM GPT-4.1.\n\n"
            "Я могу:\n"
            "• Отвечать на ваши вопросы\n"
            "• Поддерживать диалог с памятью контекста\n"
            "• Генерировать отчёты о работе\n\n"
            "Используйте кнопки или команды для управления."
        )
        
        await message.answer(welcome_text)
        logger.info(f"Sent welcome message to user {user_id}")
    
    async def cmd_clear(self, message: Message, user_id: int) -> None:
        """Обработка команды /clear."""
        self.context_manager.clear_context(user_id)
        await message.answer("🧹 Контекст диалога очищен. Давайте начнём заново!")
        logger.info(f"Context cleared for user {user_id}")
    
    async def cmd_help(self, message: Message) -> None:
        """Обработка команды /help."""
        help_text = (
            "📚 **Доступные команды:**\n\n"
            "/start — Начать диалог, приветствие\n"
            "/clear — Очистить контекст диалога\n"
            "/help — Показать эту справку\n"
            "/report — Показать отчёт о работе\n"
            "/settings — Показать настройки\n"
            "/settemp <0.1-1.0> — Установить температуру (например: /settemp 0.9)\n"
            "/settokens <100-4096> — Установить лимит токенов (например: /settokens 2000)\n"
            "/rate creative — Оценить эффект как креативный\n"
            "/rate concise — Оценить эффект как лаконичный\n\n"
            "💬 **Как общаться:**\n"
            "Просто отправьте сообщение текстом, и я отвечу с помощью GPT-4.1.\n\n"
            "📝 **Примечание:**\n"
            "Я работаю только с текстовыми сообщениями. Медиа и спецсимволы игнорируются."
        )
        
        await message.answer(help_text)
        logger.info("Sent help message")
    
    async def cmd_report(self, message: Message) -> None:
        """Обработка команды /report."""
        if self.report_file.exists():
            report_content = self.report_file.read_text(encoding='utf-8')
            # Укорачиваем если слишком длинный
            if len(report_content) > 3000:
                report_content = report_content[:2800] + "\n\n... (отчёт обрезан)"
            await message.answer(report_content)
        else:
            await message.answer("Отчёт пока не сформирован. Сделайте несколько запросов к боту.")
    
    async def cmd_settings(self, message: Message) -> None:
        """Обработка команды /settings - показать все настройки."""
        current_temp = settings.TEMPERATURE
        current_max_tokens = settings.MAX_TOKENS
        current_context_tokens = settings.MAX_TOKENS_IN_CONTEXT
        model = settings.MODEL
        
        settings_text = (
            f"⚙️ **Настройки бота**\n\n"
            f"**Модель:** {model}\n\n"
            f"🌡 **Температура:** {current_temp}\n"
            "• 0.1-0.3 — Точные, предсказуемые ответы\n"
            "• 0.4-0.7 — Сбалансированные ответы\n"
            "• 0.8-1.0 — Креативные, неожиданные ответы\n\n"
            f"📝 **Max Tokens в ответе:** {current_max_tokens}\n"
            f"📝 **Max Tokens в контексте:** {current_context_tokens}\n\n"
            "*Для изменения настроек используйте команды:*\n"
            "`/settemp <значение>` — изменить температуру (0.1-1.0)\n"
            "`/settokens <значение>` — изменить лимит токенов (100-4096)\n\n"
            "*Или отредактируйте файл `.env` и перезапустите бота.*"
        )
        await message.answer(settings_text)
        logger.info("User requested settings info")
    
    async def cmd_settemp(self, message: Message, command: str, user_id: int) -> None:
        """Обработка команды /settemp - установить температуру."""
        parts = command.split()
        if len(parts) < 2:
            await message.answer("Используйте: /settemp <значение>\nПример: /settemp 0.9")
            return
        
        try:
            new_temp = float(parts[1])
            if new_temp < 0.1 or new_temp > 1.0:
                await message.answer("Температура должна быть в диапазоне 0.1-1.0")
                return
            
            # Сохраняем настройку для пользователя
            stats = self.context_manager.get_stats(user_id)
            self.context_manager.update_stats(
                user_id,
                temperature=new_temp,
                max_tokens=stats.get('max_tokens', settings.MAX_TOKENS)
            )
            
            await message.answer(f"✅ Температура установлена: **{new_temp}**\n\nДля сброса используйте /settings")
            logger.info(f"User {user_id} set temperature to {new_temp}")
            
        except ValueError:
            await message.answer("Некорректное значение. Используйте число (например: 0.7)")
    
    async def cmd_settokens(self, message: Message, command: str, user_id: int) -> None:
        """Обработка команды /settokens - установить лимит токенов."""
        parts = command.split()
        if len(parts) < 2:
            await message.answer("Используйте: /settokens <значение>\nПример: /settokens 2000")
            return
        
        try:
            new_tokens = int(parts[1])
            if new_tokens < 100 or new_tokens > 4096:
                await message.answer("Max Tokens должен быть в диапазоне 100-4096")
                return
            
            # Сохраняем настройку для пользователя
            stats = self.context_manager.get_stats(user_id)
            self.context_manager.update_stats(
                user_id,
                temperature=stats.get('temperature', settings.TEMPERATURE),
                max_tokens=new_tokens
            )
            
            await message.answer(f"✅ Max Tokens установлен: **{new_tokens}**\n\nДля сброса используйте /settings")
            logger.info(f"User {user_id} set max_tokens to {new_tokens}")
            
        except ValueError:
            await message.answer("Некорректное значение. Используйте целое число (например: 1000)")
    
    async def cmd_temp(self, message: Message) -> None:
        """Обработка команды /temp - показать/изменить температуру."""
        current_temp = settings.TEMPERATURE
        temp_text = (
            f"🌡 **Текущая температура: {current_temp}**\n\n"
            "Температура влияет на креативность ответов:\n"
            "• 0.1-0.3 — Точные, предсказуемые ответы\n"
            "• 0.4-0.7 — Сбалансированные ответы\n"
            "• 0.8-1.0 — Креативные, неожиданные ответы\n\n"
            "Для изменения отредактируйте файл `.env`:\n"
            "`TEMPERATURE=0.7`\n\n"
            "После изменения перезапустите бота."
        )
        await message.answer(temp_text, keyboard=create_main_keyboard().to_json())
        logger.info(f"User requested temperature info: {current_temp}")
    
    async def cmd_tokens(self, message: Message) -> None:
        """Обработка команды /tokens - показать/изменить лимит токенов."""
        current_max_tokens = settings.MAX_TOKENS
        current_context_tokens = settings.MAX_TOKENS_IN_CONTEXT
        tokens_text = (
            f"📝 **Текущие настройки токенов:**\n\n"
            f"• Max Tokens в ответе: **{current_max_tokens}**\n"
            f"• Max Tokens в контексте: **{current_context_tokens}**\n\n"
            "Max Tokens в ответе — максимальная длина ответа от LLM.\n"
            "Max Tokens в контексте — память диалога (FIFO).\n\n"
            "Для изменения отредактируйте файл `.env`:\n"
            "`MAX_TOKENS=1000`\n"
            "`MAX_TOKENS_IN_CONTEXT=4000`\n\n"
            "После изменения перезапустите бота."
        )
        await message.answer(tokens_text, keyboard=create_main_keyboard().to_json())
        logger.info(f"User requested tokens info")
    
    async def cmd_rate(self, message: Message, command: str, user_id: int) -> None:
        """Обработка команды /rate."""
        parts = command.split()
        if len(parts) < 2:
            await message.answer("Используйте: /rate creative | /rate concise")
            return
        
        rating_type = parts[1].lower()
        if rating_type not in ['creative', 'concise']:
            await message.answer("Недопустимый тип оценки. Используйте 'creative' или 'concise'.")
            return
        
        # Обновляем отчёт с ручной оценкой (модифицируем последнюю запись)
        self.update_report(user_id, rating_type=rating_type, is_rate_only=True)
        await message.answer(f"✅ Оценка '{rating_type}' записана в отчёт.")
        logger.info(f"User {user_id} rated: {rating_type}")
    
    def update_report(self, user_id: int, response: str = None, rating_type: str = None, is_rate_only: bool = False) -> None:
        """Обновляет файл отчёта REPORT.md автоматически при каждом запросе."""
        try:
            # Получаем статистику из контекста
            stats = self.context_manager.get_stats(user_id)
            
            # Получаем настройки пользователя
            user_temp = stats.get('temperature', settings.TEMPERATURE)
            user_max_tokens = stats.get('max_tokens', settings.MAX_TOKENS)
            tokens_used = stats.get('tokens_used', 0)
            
            # run_number - это текущее значение + 1 для новой записи (если не rate)
            # Для /rate команда используем то же run_number что и у последнего запроса
            current_run = stats.get('run_number', 1)
            if current_run < 1:
                current_run = 1
            
            # Автооценка эффекта
            effect = self._calculate_effect(response or "", tokens_used)
            
            # Если есть ручная оценка, используем её
            if rating_type:
                effect = rating_type
            
            # Текущая дата
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Формируем или загружаем существующий отчёт
            if self.report_file.exists():
                report_content = self.report_file.read_text(encoding='utf-8')
            else:
                # Создаём заголовок отчёта
                report_content = self._create_report_header()
            
            # Если это только оценка (/rate), модифицируем последнюю запись
            if is_rate_only and rating_type:
                lines = report_content.split('\n')
                # Находим последнюю строку с данными (не заголовок и не разделитель)
                for i in range(len(lines) - 1, 1, -1):
                    if lines[i].startswith('|') and not lines[i].startswith('|---'):
                        # Заменяем эффект в последней строке
                        parts = lines[i].split('|')
                        if len(parts) >= 7:
                            # parts[5] - это эффект (индекс может отличаться, проверяем)
                            # Формат: | Дата | Модель | Temperature | Max Tokens | № прогона | Эффект | ...
                            # Индексы:  0       1         2             3          4           5
                            parts[5] = f" {rating_type}"
                            lines[i] = '|'.join(parts)
                        break
                
                report_content = '\n'.join(lines)
                logger.info(f"Report updated (rate only): run={current_run}, effect={rating_type}")
                self.report_file.write_text(report_content, encoding='utf-8')
                return
            
            # Добавляем строку в таблицу
            row = self._create_report_row(current_date, user_temp, user_max_tokens, effect, current_run, tokens_used)
            
            # Вставляем строку перед последней строкой (итоговой)
            lines = report_content.split('\n')
            if lines[-1].startswith('|---') or lines[-1].startswith('| Total'):
                lines.insert(-1, row)
            else:
                lines.append(row)
            
            # Обновляем файл
            self.report_file.write_text('\n'.join(lines), encoding='utf-8')
            
            logger.info(f"Report updated: date={current_date}, run={current_run}, tokens={tokens_used}, effect={effect}, temp={user_temp}")
            
        except Exception as e:
            logger.error(f"Error updating report: {e}")
    
    def _calculate_effect(self, response: str, tokens_used: int) -> str:
        """Автооценка эффекта на основе сжатости и лексического разнообразия."""
        if not response:
            return "neutral"
        
        # Простая метрика: отношение длины ответа к токенам
        response_length = len(response.split())
        if tokens_used > 0:
            compression = response_length / tokens_used
        else:
            compression = 0
        
        # Лексическое разнообразие (типы/токены)
        words = response.split()
        unique_words = len(set(words))
        diversity = unique_words / len(words) if words else 0
        
        # Оценка
        if compression > 0.8 and diversity > 0.6:
            return "creative"
        elif compression < 0.5 and diversity > 0.7:
            return "concise"
        else:
            return "balanced"
    
    def _create_report_header(self) -> str:
        """Создаёт заголовок отчёта с таблицей."""
        header = """# Отчёт о работе бота

| Дата | Модель | Temperature | Max Tokens | № прогона | Эффект | Использованные токены | Ориентировочная стоимость |
|------|--------|-------------|------------|-----------|--------|----------------------|--------------------------|
"""
        return header
    
    def _create_report_row(self, date: str, temperature: float, max_tokens: int, effect: str, run_number: int, tokens_used: int) -> str:
        """Создаёт строку таблицы отчёта."""
        model = settings.MODEL
        
        # Примерная стоимость ($0.01 за 1K токенов для GPT-4)
        estimated_cost = f"${tokens_used * 0.00001:.4f}"
        
        return f"| {date} | {model} | {temperature} | {max_tokens} | {run_number} | {effect} | {tokens_used} | {estimated_cost} |"


def run_bot():
    """Функция запуска бота."""
    # Загружаем переменные окружения
    load_dotenv()
    
    # Инициализируем бот
    bot = Bot(token=settings.VK_TOKEN)
    
    # Создаём экземпляр обработчика
    chat_bot = ChatBot()
    
    # Регистрируем обработчик сообщений
    @bot.on.message()
    async def message_handler(message: Message) -> None:
        await chat_bot.handle_message(message)
    
    logger.info("Starting VK Bot with LLM integration...")
    bot.run_forever()


def main():
    """Главная функция."""
    run_bot()


if __name__ == '__main__':
    main()
