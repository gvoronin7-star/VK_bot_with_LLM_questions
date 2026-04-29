# 🚀 Инструкция по деплою VK бота с LLM интеграцией

## 📁 Шаг 1: Подготовка проекта

Структура репозитория:

```
vk-bot-llm/
├── .env                    # ⚠️ НЕ коммитить! (токены, ключи)
├── .env.example            # Пример конфигурации
├── .gitignore              # Правила git
├── vk_bot.py               # Основной файл бота
├── config.py               # Конфигурация
├── context_manager.py      # Управление контекстом
├── api_client.py           # Клиент ProxyAPI
├── requirements.txt        # Зависимости
├── README.md               # Документация
├── DEPLOY.md               # Инструкция по деплою
├── LICENSE                 # Лицензия
├── pytest.ini              # Конфигурация тестов
├── data/                   # Данные (не коммитить context.json)
└── tests/                  # Тесты
```

## 📦 Шаг 2: Создать репозиторий на GitHub

1. Перейдите на [github.com](https://github.com/)
2. Нажмите **"New repository"**
3. Заполните:
   - **Repository name:** `vk-bot-llm`
   - **Description:** "VK бот с интеграцией LLM GPT-4.1"
   - **Public/Private:** По выбору
4. Нажмите **"Create repository"**

### GitLab (альтернатива)

1. Перейдите на [gitlab.com](https://gitlab.com/)
2. Нажмите **"New project"**
3. Заполните аналогично

## 📤 Шаг 3: Загрузить код в репозиторий

### Локальный запуск

```bash
# Перейдите в папку проекта
cd "C:\Users\gvoro\OneDrive\Документы\02 ЗЕРОКОТ\Интересные наработки\2026-04-08 чат бот в ВК"

# Инициализируйте git (если ещё не сделано)
git init

# Добавьте все файлы
git add .

# Проверьте что добавилось (файлы в .gitignore не должны быть добавлены)
git status

# Сделайте первый коммит
git commit -m "Initial commit: VK bot with LLM integration"

# Добавьте удалённый репозиторий (замените URL на свой)
git remote add origin https://github.com/ВАШ_НИК/vk-bot-llm.git

# Отправьте в репозиторий
git branch -M main
git push -u origin main
```

### Через GUI (GitHub Desktop)

1. Откройте **GitHub Desktop**
2. **File → Add Local Repository**
3. Выберите папку проекта
4. Сделайте **Commit**
5. Нажмите **Push origin**

## 🔐 Шаг 4: Настройка переменных окружения

### Для GitHub (рекомендуется)

1. В репозитории: **Settings → Secrets and variables → Actions**
2. Нажмите **"New repository secret"**
3. Добавьте переменные:
   - **Name:** `VK_ACCESS_TOKEN`
   - **Value:** [вставьте токен VK]
   - **Name:** `VK_GROUP_ID`
   - **Value:** [вставьте ID группы]
   - **Name:** `PROXYAPI_KEY`
   - **Value:** [вставьте ключ ProxyAPI]
4. **Важно:** Никогда не коммитьте `.env` файл!

### Для GitLab

1. **Settings → CI/CD → Variables**
2. Добавьте переменные аналогично

## ⚙️ Шаг 5: Автоматический запуск (опционально)

### Через GitHub Actions

Создайте файл `.github/workflows/deploy.yml`:

```yaml
name: Deploy Bot

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Configure environment
        run: |
          echo "VK_ACCESS_TOKEN=${{ secrets.VK_ACCESS_TOKEN }}" >> .env
          echo "VK_GROUP_ID=${{ secrets.VK_GROUP_ID }}" >> .env
          echo "PROXYAPI_KEY=${{ secrets.PROXYAPI_KEY }}" >> .env
      
      - name: Start bot
        run: |
          # Запускает бот, который работает 24/7
          nohup python vk_bot.py > bot.log 2>&1 &
```

### Через Docker

Создайте `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "vk_bot.py"]
```

## 🌐 Шаг 6: Хостинг

### Вариант 1: VPS (рекомендуется для продакшена)

1. Арендуйте VPS (например, на DigitalOcean, Hetzner)
2. Установите Python:
   ```bash
   sudo apt update
   sudo apt install python3-pip
   ```
3. Загрузите проект:
   ```bash
   git clone https://github.com/ВАШ_НИК/vk-bot.git
   cd vk-bot
   ```
4. Установите зависимости:
   ```bash
   pip3 install -r requirements.txt
   ```
5. Создайте `.env` вручную на сервере

### Вариант 2: Render/Railway (бесплатно)

1. Зарегистрируйтесь на [render.com](https://render.com/)
2. Создайте **Web Service**
3. Подключите репозиторий
4. Добавьте переменные окружения
5. Deploy

### Вариант 3: Домашний ПК

1. Бот будет работать пока включён ПК
2. Используйте `systemd` (Linux) или **Task Scheduler** (Windows)

## 🔍 Шаг 7: Проверка работы

### В VK

1. Откройте группу
2. Нажмите **"Написать сообщение"**
3. Отправьте `/start`
4. Бот должен ответить с приветствием

### Проверка команд

```
/settemp 0.9     # Изменить температуру
/settokens 2000  # Изменить лимит токенов
/settings        # Показать настройки
/help            # Показать справку
```

### Логи

Все запросы и ответы логируются в `errors.log`

## 🛠️ Шаг 8: Отладка

### Просмотр логов

```bash
# Локально (Windows)
Get-Content errors.log -Tail 50

# Локально (Linux/Mac)
tail -f errors.log

# На сервере
journalctl -u bot -f
```

### Перезапуск

```bash
# Остановить все процессы (Windows)
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force

# Запустить снова
python vk_bot.py

# Linux
pkill -f vk_bot.py
nohup python vk_bot.py > bot.log 2>&1 &
```

### Проверка зависимостей

```bash
pip install -r requirements.txt
python -m py_compile vk_bot.py
```

## 📞 Контакты

При проблемах:
1. Проверьте логи
2. Проверьте токен и ID группы
3. Убедитесь, что Long Poll включён
4. Проверьте права доступа токена

---

**Успешного деплоя! 🎉**
