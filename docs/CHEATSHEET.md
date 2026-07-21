# J.A.R.V.I.S. — шпаргалка (сервер)

Всё меняется в файле **`.env`** в папке проекта. После правок — **пересобрать**.

## Открыть настройки

```bash
nano .env          # редактируем
# Ctrl+O, Enter — сохранить; Ctrl+X — выйти
```

## Пересобрать после изменений (главная команда)

```bash
bash deploy/redeploy.sh
```

Делает: `git pull` → сборка без кэша → пересоздание контейнеров → печатает лог.
Вручную: `docker compose build --no-cache && docker compose up -d --force-recreate`.

---

## Сменить провайдера / модель

**Только Claude:**
```ini
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**Только ChatGPT:**
```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

**Только OpenRouter (много моделей одним ключом):**
```ini
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
```

> Задал несколько ключей — в боте появится переключатель Claude / GPT / OpenRouter.

---

## Включить фичи

| Хочу | В `.env` |
|---|---|
| Подписка на канал обязательна | `TELEGRAM_REQUIRED_CHANNEL=@jar_v1_s` (бот должен быть админом канала) |
| Тарифы + лимиты | `AUTH_ENABLED=true` и `BILLING_ENABLED=true` |
| Каталог моделей | `OPENROUTER_API_KEY=sk-or-...` |
| Генерация картинок 🎨 | `IMAGE_ENABLED=true` (+ ключ OpenAI, или `IMAGE_API_KEY=`) |
| Голос | `VOICE_ENABLED=true` |
| Второй (личный) бот | см. `docs/DEPLOY.md`, `--profile personal` |

## Настроить лимиты и цены

```ini
PLAN_FREE_DAILY=10          # сообщений/день на Free
PLAN_PLUS_DAILY=100         # на Plus
PLAN_PRO_DAILY=0            # 0 = безлимит (Pro)
PLAN_PLUS_PRICE_STARS=2500  # цена Plus в Stars
PLAN_PRO_PRICE_STARS=8000   # цена Pro
REFERRAL_BONUS_DAILY=20     # +сообщений/день за друга
```

## Кто админ бота

```ini
TELEGRAM_ADMIN_USERS=123456789   # твой Telegram ID (@userinfobot покажет)
```

---

## Проверить, что работает

```bash
docker compose ps                    # статус контейнеров
docker compose logs --tail=40 bot    # лог бота (версия + SUBSCRIPTION GATE: ON/OFF)
docker compose logs -f bot           # смотреть лог в реальном времени (Ctrl-C выйти)
```

## Обновить только exe (десктоп)

GitHub → **Actions → Desktop builds → Run workflow** (targets: `windows`).
Готовый файл — во вкладке **Releases** (если делать через тег `vX.Y.Z`) или в
**Artifacts** прогона.

---

## Если «изменения не подхватились»

Почти всегда — старый образ. Лечится:

```bash
bash deploy/redeploy.sh
```

и проверь лог: строка `J.A.R.V.I.S. bot X.Y.Z` покажет живую версию,
`SUBSCRIPTION GATE: ON/OFF` — включён ли гейт.
