<div align="center">

# 🤖 J.A.R.V.I.S.

### Just A Rather Very Intelligent System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/Version-0.16.0-orange)](https://github.com/nomadnairi/J.A.R.V.I.S)
[![Status](https://img.shields.io/badge/Status-Early%20Development-yellow)](https://github.com/nomadnairi/J.A.R.V.I.S)

**Modulli shaxsiy AI-yordamchi frameworki — Toni Starkning yordamchisidan ilhomlangan.**

[English](README.md) · [Русский](README.ru.md) · **O'zbek**

</div>

---

## Loyiha haqida

J.A.R.V.I.S. — shaxsiy AI-yordamchi yaratish uchun ochiq kodli framework:
LLM asosidagi intellektual yadro, plagin/ko'nikma tizimi, tool calling
(funksiya chaqirish) va ovoz, aqlli uy hamda avtomatlashtirish tomon
kengayishga mo'ljallangan qatlamli arxitektura.

> **Loyiha holati:** dastlabki bosqich. Yadro tayyor va ishlayapti — async-dvigatel,
> LLM integratsiyasi (Anthropic / OpenAI), ko'nikma va tool tizimi, oqimli
> javoblar, interaktiv CLI va **xotira tizimi** (doimiy tarix + semantik recall).
> Ovoz, integratsiyalar, avtomatlashtirish va web/API — rejalarda. Aniq holat
> uchun [Rejalar](#rejalar) bo'limiga qarang.

---

## Hozir nima ishlaydi

- **🧠 LLM yadrosi** — **Anthropic (Claude)** va **OpenAI (GPT)** uchun
  provayderdan mustaqil klient; avtomatik qayta urinish va provayderlar
  o'rtasida almashinuv.
- **🔧 Tool / funksiya chaqirish** — agentik sikl: model o'zi toollarni
  (ko'nikmalarni) chaqiradi, ishlarni bajaradi va natijaga ko'ra javob beradi.
- **🧩 Ko'nikma/plagin tizimi** — tez-tez uchraydigan so'rovlarni (sana/vaqt,
  kalkulyator, tizim diagnostikasi) LLMga murojaat qilmasdan deterministik
  bajarish.
- **🧠 Xotira** — suhbat tarixi doimiy saqlanadi (qayta ishga tushirishdan omon
  qoladi) hamda semantik recall (RAG): LLM har bir suhbatdan **barqaror
  faktlarni** ajratib oladi va keyin keraklilarini eslaydi. Async, SQLite
  asosida, o'xshashlik chegarasi va yangilik og'irligi bilan; ulanadigan
  embeddinglar (offline / lokal / OpenAI).
- **⚡ Oqim (streaming)** — CLIda tokenma-token oqimli javoblar.
- **💬 Telegram bot** — Telegram orqali yordamchi bilan suhbat; har bir
  foydalanuvchi o'z doimiy sessiyasi va xotirasiga ega. Lokalizatsiyalangan
  interfeys (ingliz / rus / o'zbek), buyruqlar menyusi va til tanlash tugmalari
  bilan; yordamchi tanlangan tilda javob beradi.
- **🎙 Ovoz (botda)** — ovozli xabar yuboring: u OpenAI Whisper API orqali
  matnga o'giriladi, yordamchi javob beradi va (xohishga ko'ra) OpenAI TTS
  bilan javobni ovozda aytadi. Ko'p tilli: siz gapirgan tilda javob beradi.
- **🔌 Integratsiyalar** — tashqi xizmatlar LLM uchun tool sifatida: **ob-havo**
  (Open-Meteo, bepul, kalitsiz) va **aqlli uy** (Home Assistant). Ulanadigan
  karkas (connect/health/tool-ko'prik) — yana qo'shish oson.
- **👥 Ko'p sessiya** — sessiya menejeri orqali ko'plab mustaqil suhbatlar.
- **📡 Hodisaga asoslangan** — ichki pub/sub shina va passiv telemetriya.
- **🖥️ Interaktiv CLI** — suhbat, shuningdek `/skills`, `/stats`, `/state`, `/reset`.

Yuqoridagilarning barchasi lokal ishlaydi; ko'nikma/tool buyruqlari API kalitisiz
ham ishlaydi.

---

## Arxitektura

```
┌───────────────────────────────────────────────┐
│  Interfeyslar:  CLI (hozir)  ·  Web / API (reja)│
└───────────────────────────┬───────────────────┘
                           │  So'rov
┌───────────────────────────▼───────────────────┐
│                   JarvisEngine                 │
│   StateMachine · Pipeline · SessionManager     │
│        ┌───────────────┴───────────────┐       │
│        ▼                               ▼       │
│  SkillRegistry (tools)          LLMClient (AI) │
│   tezkor yo'l + tools         retry + fallback │
└───────────────────────────┬───────────────────┘
                           │ hodisalar
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   EventBus            Telemetry          Memory /
   (pub/sub)           (metrikalar)      Integrations
                                          (reja)
```

Batafsil — [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) da.

---

## Texnologiyalar

| Soha | Vositalar |
|------|-----------|
| Til | Python 3.10+ |
| Konfiguratsiya | pydantic-settings |
| LLM | Anthropic SDK, OpenAI SDK |
| CLI | rich |
| Testlar | pytest, pytest-asyncio |
| Linter / CI | ruff, GitHub Actions |

Ixtiyoriy bog'liqliklar (vektor bazasi, ovoz, FastAPI) ro'yxatda, ammo kerakli
imkoniyat yoqilmaguncha faol emas.

---

## Loyiha tuzilishi

```
jarvis/
├── __main__.py        # interaktiv CLI (python -m jarvis)
├── config/            # tiplangan sozlamalar va konstantalar
├── core/              # dvigatel, DI-konteyner, pipeline, holat, sessiyalar
├── llm/               # provayderdan mustaqil klient + Anthropic/OpenAI + tools
├── skills/            # ko'nikma/tool tizimi + o'rnatilganlar
├── events/            # pub/sub hodisa shinasi
├── telemetry/         # metrikalar yig'uvchi
├── interfaces/        # Telegram bot (CLI — __main__.py da)
├── i18n/              # lokalizatsiya (en/ru/uz)
├── models/            # Message/Conversation, Request/Response
├── memory/            # doimiy tarix + semantik recall (SQLite + vektorlar)
├── integrations/      # kontraktlar (amalga oshirish rejada)
└── utils/             # loglash, retry, vaqt, istisnolar, matn
tests/                 # pytest testlar to'plami
docs/                  # arxitektura hujjatlari
```

---

## Tez boshlash

**Talablar:** Python 3.10+

```bash
# Klonlash
git clone https://github.com/nomadnairi/J.A.R.V.I.S.git
cd J.A.R.V.I.S

# O'rnatish
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Sozlash (API kalitingizni qo'shing)
cp .env.example .env            # ANTHROPIC_API_KEY yoki OPENAI_API_KEY ni kiriting

# Ishga tushirish
python -m jarvis
```

`make` ni afzal ko'rasizmi? `make install`, `make run`, `make test`, `make lint`.

---

## Foydalanish

CLI ichida:

```
Sir › calc (12.5/100)*320
J.A.R.V.I.S. › (12.5/100)*320 = 40

Sir › what time is it
J.A.R.V.I.S. › It is 14:05.

Sir › system status
J.A.R.V.I.S. › All systems nominal. …

Sir › /skills      # ko'nikmalar va qaysilari LLMga tool sifatida ochiq
Sir › /stats       # sessiya telemetriyasi
Sir › /memory      # xotira statistikasi
Sir › /reset       # suhbatni tozalash (uzoq muddatli xotira saqlanadi)
Sir › /forget      # tarix va uzoq muddatli xotirani o'chirish
```

Ko'nikma hal qila olmagan har qanday narsaga LLM javob beradi (kerak bo'lsa
toollarni chaqirib).

---

## Telegram bot

J.A.R.V.I.S. bilan Telegram orqali suhbatlashing. Har bir foydalanuvchi o'z
doimiy sessiyasiga ega, shuning uchun yordamchi har bir kishini alohida eslaydi.

```bash
pip install aiogram            # interfeys uchun ixtiyoriy bog'liqlik

# .env faylingizda:
#   TELEGRAM_BOT_TOKEN=...      (@BotFather dan)
#   ANTHROPIC_API_KEY=...       (yoki OPENAI_API_KEY)

python -m jarvis.interfaces.telegram_bot     # yoki: jarvis-bot
```

Buyruqlar: `/language` (interfeys va javob tilini almashtirish), `/reset`
(joriy suhbatni tozalash), `/forget` (siz haqingizda eslab qolingan hamma
narsani o'chirish), `/help`. Menyu va interfeys **ingliz, rus va o'zbek**
tillarida, yordamchi foydalanuvchi tanlagan tilda javob beradi. Kirishni
`TELEGRAM_ALLOWED_USERS` orqali muayyan user ID lar bilan cheklash mumkin.

---

## Rejalar

| Soha | Holat |
|------|-------|
| Yadro: async-dvigatel, LLM, ko'nikma/tool, streaming, CLI, testlar, CI | ✅ tayyor |
| Xotira: doimiy tarix + semantik recall | ✅ tayyor |
| Telegram bot (foydalanuvchi bo'yicha sessiyalar + xotira) | ✅ tayyor |
| Botda ovoz: nutqni tanish (Whisper API) / sintez (OpenAI), ko'p tilli | ✅ tayyor |
| Integratsiyalar: karkas + ob-havo + aqlli uy (Home Assistant) | ✅ tayyor |
| Desktop / Raspberry Pi ovoz (mikrofon va karnay) | reja |
| Yana integratsiyalar: taqvim, pochta | reja |
| Integratsiyalar: aqlli uy, taqvim, pochta | reja |
| Vazifalarni avtomatlashtirish: rejalashtiruvchi, ssenariylar | reja |
| API qatlami: FastAPI + WebSocket | reja |
| Veb-boshqaruv paneli | reja |

---

## Hissa qo'shish

Hissangiz xush kelibsiz. Sozlash, qatlamlar tuzilishi va ko'nikma qo'shish
bo'yicha [CONTRIBUTING.md](CONTRIBUTING.md) ga qarang. Pull request ochishdan
oldin `make test` va `make lint` ni ishga tushiring.

---

## Aloqa

- Telegram (shaxsiy): [@deathgu11](https://t.me/deathgu11)
- Telegram (kanal): [@jar_v1_s](https://t.me/jar_v1_s)
- Xatolar va takliflar: [GitHub Issues](https://github.com/nomadnairi/J.A.R.V.I.S/issues)

---

## Litsenziya

[MIT litsenziyasi](LICENSE) ostida tarqatiladi.

<div align="center">

*Aqlli avtomatlashtirish uchun yaratilgan.* 🤖

</div>
