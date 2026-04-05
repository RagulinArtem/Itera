# Itera Bot — Задание для Claude Code

## Контекст

Ты получаешь задание переписать существующий Telegram-бот **Itera** с n8n-workflow на полноценное Python-приложение. Бот уже работает и имеет реальных пользователей. Цель — сохранить 100% продуктовой логики, UX и данных, но заменить хрупкую n8n-архитектуру на надёжный, асинхронный, масштабируемый сервис.

Все исходные файлы лежат рядом с этим документом:
- `ITERA_MVP_DEMO.json` — экспорт основного n8n-workflow (вся бизнес-логика)
- `NOTIFICATIONS.json` — экспорт workflow уведомлений
- `DB_SCHEMA.csv` — схема Supabase/Postgres
- `prompts.md` — все LLM-промпты дословно
- `.env` — credentials (Telegram, Supabase, OpenAI)
- `schema.sql` — DDL базы данных

---

## Суть продукта Itera

Itera — персональный AI-дневник развития в Telegram. Пользователь:
1. Задаёт цели (текстом, AI строит структурированный план)
2. Делает ежедневные check-in'ы (свободный текст)
3. Получает AI-аналитику: «слепок дня» в двух режимах — **Менеджер** (строгий, про результат) и **Психолог** (мягкий, про возврат без вины)
4. Запрашивает отчёты за 3/7/30 дней
5. Набирает XP и streak за регулярные check-in'ы
6. Получает напоминания в 21:00 MSK если не сделал check-in

---

## Технический стек — СТРОГО СЛЕДОВАТЬ

```
Python 3.11+
aiogram 3.x          # Telegram Bot framework (async)
asyncpg              # Async PostgreSQL client
openai               # OpenAI Python SDK (async client)
apscheduler          # Для cron-задачи уведомлений
aiohttp              # HTTP server для webhook
python-dotenv        # Env vars
pydantic v2          # Модели данных
```

**Режим работы:** webhook (не polling). Telegram шлёт апдейты на HTTPS-эндпоинт.

**Хостинг:** Dockerfile + docker-compose. Деплой на Railway или любой VPS с публичным HTTPS.

---

## Структура проекта

```
itera/
├── bot/
│   ├── main.py                 # Entry point: webhook сервер + регистрация хендлеров
│   ├── config.py               # Settings (pydantic BaseSettings, читает .env)
│   ├── database.py             # asyncpg connection pool, CRUD-методы
│   ├── fsm/
│   │   └── states.py           # aiogram FSM states
│   ├── handlers/
│   │   ├── start.py            # /start, /help, /menu, /cancel
│   │   ├── checkin.py          # check-in flow
│   │   ├── goals.py            # цели: список, создание, done/pause/delete
│   │   ├── reports.py          # отчёты 3/7/30 дней
│   │   ├── profile.py          # профиль: имя, email
│   │   ├── mode.py             # переключение AI-режима
│   │   ├── settings.py         # напоминания on/off
│   │   └── feedback.py         # фидбек
│   ├── keyboards/
│   │   ├── main_menu.py
│   │   ├── goals_kb.py
│   │   └── reports_kb.py
│   ├── services/
│   │   ├── llm_client.py       # OpenAI async wrapper с retry
│   │   ├── checkin_ai.py       # Менеджер-режим: анализ дня
│   │   ├── psychologist_ai.py  # Психолог-режим: мягкий возврат
│   │   ├── report_ai.py        # Периодические отчёты 3/7/30
│   │   ├── goal_ai.py          # Генерация плана цели
│   │   └── scheduler.py        # APScheduler: напоминания в 21:00 MSK
│   └── utils/
│       ├── formatters.py       # Форматирование сообщений (слепок, отчёт, цель)
│       └── idempotency.py      # Трекинг update_id для дедупликации
├── migrations/
│   └── 001_initial.sql         # DDL (из schema.sql)
├── .env                        # Credentials (НЕ коммитить)
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## База данных — существующие таблицы Supabase/Postgres

### Profiles (уже существует, не пересоздавать)
```sql
id               uuid        PK, gen_random_uuid()
nickname         text        default ''
email            text        default ''
created_at       timestamptz default now()
telegram_id      bigint      NOT NULL, UNIQUE
state            text        NULL  -- FSM state (хранить здесь)
xp               integer     default 0
streak           integer     default 0
last_checkin_date date       NULL
reminder_enabled boolean     default true, NOT NULL
last_reminder_date date      NULL
ai_mode          text        default 'manager', NOT NULL  -- 'manager' | 'psychologist'
```

### Goals (уже существует)
```sql
id               uuid        PK
created_at       timestamptz default now()
user_id          uuid        FK → Profiles.id
status           text        -- 'active' | 'completed' | 'archived'
goal             text        -- текст цели
progress         bigint      default 0
plan             jsonb       default '{}'  -- структурированный план от AI
plan_updated_at  timestamptz default now()
completed_at     timestamptz NULL
```

### journal_entries (уже существует)
```sql
id               uuid        PK
user_id          uuid        FK → Profiles.id
entry_date       date        NOT NULL
checkin_text     text        -- сырой текст пользователя
analysis         jsonb       -- результат LLM анализа (полный JSON)
created_at       timestamptz default now()
```

> **ВАЖНО:** Не пересоздавать таблицы. Использовать существующую схему. Только добавить недостающие индексы если нужно.

---

## FSM States — все состояния бота

```python
class IteraStates(StatesGroup):
    idle = State()                    # нет активного действия
    awaiting_checkin = State()        # ждём текст чек-ина
    awaiting_goal_text = State()      # ждём описание новой цели
    awaiting_nickname = State()       # профиль: ждём имя
    awaiting_email = State()          # профиль: ждём email
    awaiting_feedback = State()       # ждём текст фидбека
```

**Хранение FSM:** использовать `Profiles.state` в БД (не в памяти). При рестарте состояние сохраняется. Написать кастомный `FSMContext` storage на asyncpg.

---

## Команды и callback_data — полный список

### Команды
| Команда | Действие |
|---------|----------|
| `/start` | Приветствие + upsert профиля + показать главное меню |
| `/menu` | Показать главное меню |
| `/help` | Краткая справка |
| `/cancel` | Сбросить текущее действие → idle → меню |
| `/mygoals` | Список активных целей |

### Callback_data
| Паттерн | Действие |
|---------|----------|
| `menu:home` | Главное меню |
| `menu:checkin` | Запустить check-in flow |
| `menu:goals` | Список целей |
| `menu:reports` | Выбор периода отчёта |
| `menu:mode` | Переключение AI режима |
| `menu:profile` | Просмотр/редактирование профиля |
| `menu:settings` | Настройки напоминаний |
| `menu:feedback` | Оставить фидбек |
| `menu:cancel` | Отмена → главное меню |
| `report:3` | Отчёт за 3 дня |
| `report:7` | Отчёт за 7 дней |
| `report:30` | Отчёт за 30 дней |
| `goal:done:{id}` | Отметить цель выполненной |
| `goal:pause:{id}` | Поставить цель на паузу |
| `goal:resume:{id}` | Возобновить цель |
| `goal:delete:{id}` | Удалить цель |
| `goal:view:{id}` | Просмотр карточки цели |
| `goals:refresh` | Обновить список целей |
| `mode:set:manager` | Установить режим Менеджер |
| `mode:set:psychologist` | Установить режим Психолог |
| `settings:reminder:on` | Включить напоминания |
| `settings:reminder:off` | Выключить напоминания |
| `auth:set_name` | Установить никнейм |
| `auth:set_email` | Установить email |

---

## Главное меню — точный текст и кнопки

```
🏠 Itera — Home

👤 Профиль: {nickname}
🧠 Режим: {mode_label}

🏅 XP: {xp}
🔥 Streak: {streak} дн.

Выбирай действие кнопками ниже 👇
```

Кнопки (inline_keyboard, 2 колонки):
```
[✅ Check-in]  [🎯 Цели]
[📊 Отчёты]   [🧠 Режим]
[👤 Профиль]  [⚙️ Настройки]
[🗣 Фидбек]
```

Режимы: `manager` → `"Менеджер 📌 (результат)"`, `psychologist` → `"Психолог 🧠 (мягкий режим)"`

---

## Check-in Flow

1. Пользователь нажимает `menu:checkin`
2. Бот проверяет есть ли активные цели (`Goals WHERE user_id = ? AND status = 'active'`)
   - Если нет → сообщение: `"Пока нет целей. Опиши первую цель с помощью /goal"`  → меню
3. Устанавливает `Profiles.state = 'awaiting_checkin'`
4. Показывает prompt для check-in'а (зависит от `ai_mode` и `last_checkin_date`):
   - Если `ai_mode = 'manager'`: строгий промпт с 4 пунктами включая "1-3 действия на завтра"
   - Если `ai_mode = 'psychologist'`: мягкий промпт, если пропуск — "Пропуск — не провал. Возвращаемся мягко."
5. Ждёт текстовое сообщение от пользователя
6. При получении текста:
   a. Собирает контекст: активные цели + последние 10 journal_entries
   b. Вызывает LLM (см. prompts.md — `MANAGER_CHECKIN_PROMPT` или `PSYCHOLOGIST_PROMPT`)
   c. Парсит JSON-ответ
   d. Сохраняет в `journal_entries`: `entry_date=today, checkin_text=raw_text, analysis=llm_json`
   e. Обновляет `Profiles`: `last_checkin_date=today, xp += 100, streak = calculated`
   f. Форматирует и отправляет «слепок дня» пользователю
   g. Сбрасывает `state = null`

### Логика streak
```python
def calculate_streak(last_checkin_date, current_streak):
    today = date.today()
    if last_checkin_date is None:
        return 1
    delta = (today - last_checkin_date).days
    if delta == 1:
        return current_streak + 1  # продолжаем серию
    elif delta == 0:
        return current_streak  # уже был check-in сегодня
    else:
        return 1  # серия прервалась
```

---

## Goals Flow

### Создание цели
1. `menu:goals` → показать список + кнопку "➕ Новая цель"
2. `goal:new` → `state = 'awaiting_goal_text'`, просим описать цель
3. Получаем текст → вызываем LLM для генерации `plan` (jsonb)
4. Сохраняем в `Goals`: `status='active', goal=text, plan=llm_plan, progress=0`
5. `xp += 100`, показываем карточку цели

### Карточка цели
```
🎯 *Цель:* {goal}
📌 *Статус:* 🟢 Active

🧩 *План / шаги:*
🧩 *Шаг 1:* ...
   _signal1 · signal2_
   Определение шага
```

Кнопки: `✅ Done` | `⏸ Pause/▶️ Resume` | `🗑 Delete` | `↩️ Назад к списку`

### Goal Plan — JSON-структура (из существующих данных)
```json
{
  "type": "sequence",
  "items": [
    {
      "id": "step1",
      "kind": "step",
      "label": "Название шага",
      "signals": ["ключевое слово1", "ключевое слово2"],
      "definition": "Детальное описание шага"
    }
  ]
}
```

---

## Reports Flow

1. `menu:reports` → кнопки: `📋 3 дня` | `📊 7 дней` | `📈 30 дней`
2. `report:{days}` → берём последние N journal_entries + активные цели
3. Вызываем LLM (см. prompts.md — `REPORT_PROMPT`)
4. Форматируем и отправляем **два сообщения**:
   - **Сообщение 1 (Panel):** TL;DR + 3 факта + 3 приоритета + риски + рычаги
   - **Сообщение 2 (Drilldown):** Прогресс по целям + паттерны + план + вопросы

---

## Scheduler — Напоминания

Запускать через APScheduler каждый день в **21:00 Europe/Moscow**:

```python
async def send_reminders():
    # SQL запрос:
    # SELECT id, telegram_id FROM "Profiles"
    # WHERE reminder_enabled = true
    #   AND telegram_id IS NOT NULL
    #   AND COALESCE(last_checkin_date, '1900-01-01') < CURRENT_DATE AT TIME ZONE 'Europe/Moscow'
    #   AND COALESCE(last_reminder_date, '1900-01-01') < CURRENT_DATE AT TIME ZONE 'Europe/Moscow'

    # Для каждого пользователя:
    # 1. Отправить сообщение:
    #    "Привет! Как ты? Сегодня ты еще не делился своим днем.
    #     Напиши короткий чек-ин для получения обратной связи
    #     и продления стрика (1–3 предложения — достаточно)"
    # 2. UPDATE Profiles SET last_reminder_date = CURRENT_DATE WHERE id = ?
```

---

## LLM-интеграция — важные детали

**Модели:**
- Check-in (manager): `gpt-4.1-mini`
- Check-in (psychologist): `gpt-4.1-mini`
- Report: `gpt-5-mini`  ← именно эта модель, не менять
- Goal plan: `gpt-4.1-mini`

**Async wrapper с retry:**
```python
async def call_llm(system_prompt: str, user_message: str, model: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            response = await openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                timeout=60.0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

**Контекст для check-in LLM:**
```
ЦЕЛИ ПОЛЬЗОВАТЕЛЯ:
{активные цели с планами}

ЧЕК-ИН СЕГОДНЯ:
{текст пользователя}

ИСТОРИЯ (последние 5 check-in'ов):
{entry_date}: {checkin_text}
...

ИГРОВЫЕ ДАННЫЕ:
xp: {xp}
xp_gained_today: 100
streak_days: {новый streak}
```

---

## Идемпотентность и дедупликация

Telegram может повторно доставить один и тот же update. Защита:

```python
# Таблица processed_updates (создать если нет):
# CREATE TABLE processed_updates (update_id bigint PRIMARY KEY, processed_at timestamptz default now());

async def is_duplicate(update_id: int) -> bool:
    try:
        await db.execute(
            "INSERT INTO processed_updates (update_id) VALUES ($1) ON CONFLICT DO NOTHING RETURNING update_id",
            update_id
        )
        return False  # успешно вставили — новый апдейт
    except:
        return True  # уже есть — дубль
```

---

## Критические исправления относительно n8n-версии

1. **State хранить как NULL** (не строку `"null"`). При сбросе: `UPDATE Profiles SET state = NULL`
2. **UPSERT при создании пользователя:**
   ```sql
   INSERT INTO "Profiles" (telegram_id) VALUES ($1)
   ON CONFLICT (telegram_id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id
   RETURNING *
   ```
3. **Только asyncpg** для всех БД-запросов (никаких смешений Supabase REST + прямой Postgres)
4. **Обработка ошибок LLM:** если timeout/ошибка → отправить пользователю `"⚠️ Сервис временно недоступен. Попробуй через минуту."`, не зависать
5. **Check-in уже был сегодня:** проверять `last_checkin_date == today` перед сохранением, не дублировать запись
6. **Команды с аргументами:** `/goal` или просто текст — оба варианта работают для создания цели

---

## Webhook Setup

```python
# main.py
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    scheduler.start()

async def on_shutdown(app):
    await bot.delete_webhook()
    scheduler.shutdown()
    await db_pool.close()
```

---

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "-m", "bot.main"]
```

---

## docker-compose.yml

```yaml
version: "3.9"
services:
  bot:
    build: .
    env_file: .env
    ports:
      - "8080:8080"
    restart: unless-stopped
```

---

## requirements.txt

```
aiogram==3.13.1
asyncpg==0.29.0
openai==1.51.0
apscheduler==3.10.4
aiohttp==3.10.5
python-dotenv==1.0.1
pydantic==2.9.2
pydantic-settings==2.5.2
pytz==2024.1
```

---

## Переменные окружения (.env)

```
TELEGRAM_BOT_TOKEN=<из .env файла>
OPENAI_API_KEY=<из .env файла>
DATABASE_URL=postgresql://postgres.fqhadxcntgzddkthgtfx:<password>@aws-1-eu-central-2.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://fqhadxcntgzddkthgtfx.supabase.co
SUPABASE_SERVICE_KEY=<из .env файла>
WEBHOOK_DOMAIN=<твой домен, например https://itera-bot.railway.app>
PORT=8080
```

---

## Что делать по шагам

1. **Прочитай все файлы** в этой папке: `prompts.md`, `schema.sql`, `.env`, `ITERA_MVP_DEMO.json`
2. **Создай структуру проекта** согласно схеме выше
3. **Реализуй database.py** — asyncpg pool, все CRUD-методы (get_or_create_user, save_checkin, get_active_goals, update_xp_streak, get_journal_entries, create_goal, update_goal_status и т.д.)
4. **Реализуй services/llm_client.py** — async OpenAI wrapper с retry
5. **Реализуй services/checkin_ai.py и psychologist_ai.py** — берут промпты из prompts.md ДОСЛОВНО
6. **Реализуй services/report_ai.py** — берёт промпт из prompts.md ДОСЛОВНО
7. **Реализуй services/goal_ai.py** — генерация плана цели
8. **Реализуй handlers/** — все хендлеры по таблице команд выше
9. **Реализуй services/scheduler.py** — APScheduler reminder в 21:00 MSK
10. **Реализуй main.py** — webhook сервер, регистрация всего
11. **Создай Dockerfile и docker-compose.yml**
12. **Протестируй** каждый flow руками в тестовом боте (token в .env)

---

## Тестирование

Используй тестовый бот (отдельный token в .env) для разработки. Основной бот — только после полного тестирования.

Проверить обязательно:
- [ ] /start для нового пользователя
- [ ] /start для существующего пользователя
- [ ] Check-in с режимом Менеджер
- [ ] Check-in с режимом Психолог
- [ ] Check-in без целей (должен попросить создать цель)
- [ ] Создание цели
- [ ] Просмотр, Done, Pause, Delete цели
- [ ] Отчёт 3/7/30 дней
- [ ] Переключение режима
- [ ] Напоминания (проверить SQL-запрос)
- [ ] Дубль апдейта (отправить один update дважды)
- [ ] Таймаут OpenAI (замокать)

---

## Чего НЕЛЬЗЯ менять

- Тексты кнопок и меню (точь-в-точь как в этом документе)
- LLM-промпты (дословно из prompts.md)
- Схему БД (добавлять можно, менять существующие колонки нельзя)
- JSON-схему ответов LLM
- Логику XP (+100 за check-in, +100 за создание цели)
- Логику streak (см. выше)
- Текст напоминания
