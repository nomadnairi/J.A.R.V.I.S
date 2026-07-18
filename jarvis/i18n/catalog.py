"""Message catalogs for supported locales (English, Russian, Uzbek)."""

from __future__ import annotations

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "ru", "uz")

#: Human-readable language names, used to instruct the LLM which language to
#: reply in.
LANGUAGE_NAMES = {
    "en": "English",
    "ru": "Russian",
    "uz": "Uzbek",
}

CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "👋 Hello, Sir. I am <b>{name}</b> — your personal assistant.\n\n"
            "Just talk to me naturally; I remember our conversations.\n\n"
            "• /language — change language\n"
            "• /reset — clear our conversation\n"
            "• /forget — wipe what I remember about you\n"
            "• /help — show this message"
        ),
        "reset_done": "🧹 Conversation cleared. I still remember key facts about you.",
        "forget_done": "🗑 Done — I've wiped everything I remembered about you.",
        "not_authorized": "⛔️ Sorry, you're not authorised to use this bot.",
        "choose_language": "🌐 Please choose your language:",
        "language_set": "✅ Language set to English. 🇬🇧",
        "error": "⚠️ I ran into a problem: {error}",
        "cmd_help": "Show help",
        "cmd_reset": "Clear the conversation",
        "cmd_forget": "Wipe memory about you",
        "cmd_language": "Change language",
    },
    "ru": {
        "welcome": (
            "👋 Здравствуйте. Я <b>{name}</b> — ваш персональный ассистент.\n\n"
            "Просто общайтесь со мной как обычно — я помню наши разговоры.\n\n"
            "• /language — сменить язык\n"
            "• /reset — очистить диалог\n"
            "• /forget — стереть всё, что я о вас помню\n"
            "• /help — показать это сообщение"
        ),
        "reset_done": "🧹 Диалог очищен. Ключевые факты о вас я по-прежнему помню.",
        "forget_done": "🗑 Готово — я стёр всё, что о вас помнил.",
        "not_authorized": "⛔️ Извините, у вас нет доступа к этому боту.",
        "choose_language": "🌐 Пожалуйста, выберите язык:",
        "language_set": "✅ Язык переключён на русский. 🇷🇺",
        "error": "⚠️ Возникла проблема: {error}",
        "cmd_help": "Показать помощь",
        "cmd_reset": "Очистить диалог",
        "cmd_forget": "Стереть память о вас",
        "cmd_language": "Сменить язык",
    },
    "uz": {
        "welcome": (
            "👋 Assalomu alaykum. Men <b>{name}</b> — sizning shaxsiy "
            "yordamchingizman.\n\n"
            "Men bilan bemalol suhbatlashing — men suhbatlarimizni eslab "
            "qolaman.\n\n"
            "• /language — tilni o'zgartirish\n"
            "• /reset — suhbatni tozalash\n"
            "• /forget — men eslab qolgan narsalarni o'chirish\n"
            "• /help — ushbu xabarni ko'rsatish"
        ),
        "reset_done": (
            "🧹 Suhbat tozalandi. Siz haqingizdagi asosiy ma'lumotlarni "
            "hali ham eslayman."
        ),
        "forget_done": "🗑 Bajarildi — siz haqingizdagi hamma narsani o'chirdim.",
        "not_authorized": "⛔️ Kechirasiz, sizda ushbu botdan foydalanish huquqi yo'q.",
        "choose_language": "🌐 Iltimos, tilni tanlang:",
        "language_set": "✅ Til o'zbekchaga o'zgartirildi. 🇺🇿",
        "error": "⚠️ Muammoga duch keldim: {error}",
        "cmd_help": "Yordamni ko'rsatish",
        "cmd_reset": "Suhbatni tozalash",
        "cmd_forget": "Xotirani o'chirish",
        "cmd_language": "Tilni o'zgartirish",
    },
}
