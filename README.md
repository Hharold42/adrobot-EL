# Keitaro Campaign Manager

Тестовое задание Adrobot. Сервис вокруг Keitaro Admin API:

1. **Создаватор кампаний** — принимает название, гео-код страны и ID оффера.
   Создаёт кампанию с двумя потоками:
   - поток 1 ловит трафик из указанной страны и редиректит на Google;
   - поток 2 отправляет остальной трафик на выбранный оффер.

   Домен, группа кампаний и источник трафика подставляются автоматически
   (берутся из Keitaro API). Названию добавляется префикс `test_negimatjanov_`.

   Гео и офферы связаны: список стран собирается из офферов Keitaro
   (`GET /api/offers/countries`, в Keitaro нет справочника стран), офферы
   в форме фильтруются по выбранному гео, а при выборе оффера первым гео
   подставляется автоматически.
2. **Редактор кампании** — добавление/удаление офферов в потоке кампании.
   Доли (%) пересчитываются автоматически и поровну, сумма всегда 100.
   Доли можно выставить вручную (кнопка «Сохранить доли») или выровнять
   («Выровнять поровну»).

## Стек

- **Backend:** FastAPI + SQLAlchemy + Alembic, клиент Keitaro на httpx
- **DB:** PostgreSQL (docker-compose), локально храним связь
  «кампания ↔ id потоков в Keitaro»
- **Frontend:** React (Vite) + Radix Themes (тёмная тема, акцент — зелёный
  в стиле Keitaro), react-router. Меню — сайдбар слева с индикатором
  доступности Keitaro API

### Ключ Keitaro API

Backend берёт ключ из `backend/.env` (`KEITARO_API_KEY`), но его можно
переопределить без перезапуска: страница **«Настройки»** на фронте сохраняет
ключ в `localStorage` браузера и шлёт его заголовком `X-Keitaro-Key`
с каждым запросом. Проверка ключа вживую: `GET /api/keitaro/status`.

## Структура

```
backend/            FastAPI-приложение
  app/
    main.py         точка входа, CORS, lifespan
    config.py       настройки из .env (pydantic-settings)
    database.py     engine + сессии SQLAlchemy
    models.py       таблица campaigns
    keitaro.py      асинхронный клиент Keitaro Admin API v1
    schemas.py      pydantic-схемы
    routers/        /api/campaigns, /api/offers
  alembic/          миграции
frontend/           React (Vite), dev-сервер проксирует /api на :8000
docker-compose.yml  PostgreSQL 16
```

## Запуск

Требования: Python 3.12+, Node.js 20+, Docker.

### 1. PostgreSQL

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # и вписать свой KEITARO_API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Backend поднимется на http://localhost:8000, OpenAPI — на
http://localhost:8000/docs.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Интерфейс: http://localhost:5173 (запросы `/api` проксируются на backend).

## Переменные окружения (backend/.env)

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | DSN PostgreSQL для SQLAlchemy |
| `KEITARO_BASE_URL` | Базовый URL Keitaro Admin API v1 |
| `KEITARO_API_KEY` | Ключ API (берётся в админке Keitaro) |
| `CAMPAIGN_NAME_PREFIX` | Обязательный префикс названий кампаний |
| `GEO_REDIRECT_URL` | Куда редиректит гео-поток (по умолчанию Google) |

## API сервиса

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/campaigns` | Создать кампанию (`name`, `geo_code`, `offer_ids` — один или несколько офферов, доли поровну; одиночный `offer_id` тоже принимается) |
| GET | `/api/campaigns` | Список созданных кампаний |
| GET | `/api/campaigns/keitaro` | Кампании из Keitaro с отметкой, какие уже импортированы |
| POST | `/api/campaigns/import` | Бэкфилл: импорт кампаний, созданных прямо в Keitaro (`keitaro_ids`), вместе с потоками и офферами |
| GET | `/api/campaigns/{id}` | Кампания + её потоки (при первом открытии подтягиваются из Keitaro) |
| POST | `/api/campaigns/{id}/fetch` | Fetch streams: синхронизация потоков с Keitaro (черновики сбрасываются, пропавшие в Keitaro офферы уходят в архив `removed`) |
| POST | `/api/streams/{id}/offers` | Добавить оффер в черновик потока (удалённый — вернуть); веса пересчитываются |
| DELETE | `/api/streams/{id}/offers/{offer_id}` | Remove: оффер получает 0% и уходит в архив |
| POST | `/api/streams/{id}/offers/{offer_id}/restore` | Bring back: вернуть оффер из архива |
| PATCH | `/api/streams/{id}/offers/{offer_id}` | Пин веса (`pinned`) или установка веса (`share`, оффер запинивается) |
| POST | `/api/streams/{id}/push` | Push to Keitaro: опубликовать черновик потока |
| POST | `/api/streams/{id}/cancel` | Cancel: откатить неопубликованные изменения |
| GET | `/api/offers?search=` | Поиск офферов Keitaro (для селектов) |
| GET | `/api/offers/countries` | Гео из офферов: код, число офферов, регион |
| GET | `/api/keitaro/status` | Проверка доступности Keitaro API с текущим ключом |

## Логика редактора потоков

Воспроизводит поведение из видео ТЗ:

- **Fetch streams** подтягивает потоки кампании. Потоки без офферов показываются просто как поток, без содержимого редиректа и фильтров.
- Добавление, удаление и пины — **черновые**: поток становится жёлтым («Не опубликован»), в Keitaro пока ничего не меняется. **Push to Keitaro** публикует, **Cancel** откатывает (добавленные до публикации офферы удаляются).
- **Remove** серит оффер и ставит 0%; после Push он исчезает из Keitaro, но остаётся в нашей БД в архиве (`removed`). **Bring back** возвращает его в поток.
- Оффер, удалённый руками в Keitaro, после повторного Fetch streams тоже уходит в `removed`.
- **Пин веса**: запиненные веса не меняются, остальные офферы делят остаток поровну (сумма всегда 100%). Правка значения в поле веса тоже запинивает оффер.

Проверка сценария из видео сквозным тестом (backend должен быть запущен):

```bash
cd backend
python scripts/e2e_video_scenario.py
```
