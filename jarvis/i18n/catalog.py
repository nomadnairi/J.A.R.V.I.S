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
        "cmd_menu": "Open the menu",
        "menu_title": "🤖 <b>J.A.R.V.I.S. — menu</b>\nChoose an action:",
        "menu_profile": "👤 Profile",
        "menu_usage": "📊 Usage",
        "menu_subscription": "💳 Subscription",
        "menu_help": "❓ Help",
        "menu_back": "⬅️ Back",
        "profile_title": "Profile",
        "profile_name": "Name",
        "profile_account": "Account",
        "profile_no_account": "not linked",
        "profile_verified": "Verified",
        "profile_language": "Language",
        "profile_model": "Model",
        "profile_messages": "Messages",
        "profile_tokens": "Tokens used",
        "usage_title": "Token report",
        "usage_today": "Today",
        "usage_month": "Last 30 days",
        "usage_all": "All time",
        "usage_tokens": "tokens",
        "sub_title": "Subscription",
        "sub_none": "You have no account. Buy access with /buy.",
        "sub_active": "Active plan",
        "sub_inactive": "No active license — renew with /buy.",
        "sub_perpetual": "Lifetime access",
        "sub_until": "Valid until",
        "sub_days": "days left",
        "cmd_model": "Switch the AI model",
        "model_choose": "🤖 Choose the AI to chat with:",
        "model_set": "✅ Switched to {model}.",
        "model_none": "ℹ️ Only one AI is configured on this server.",
        "cmd_admin_sales": "Sales report (owner)",
        "cmd_admin": "Admin panel (owner)",
        "admin_needs_auth": "⚙️ The admin panel needs AUTH_ENABLED=true on the server.",
        "admin_post_usage": "Usage: /admin_post your post text",
        "admin_no_channel": "⚙️ Set TELEGRAM_CHANNEL on the server to publish posts.",
        "admin_posted": "✅ Posted to {channel}.",
        "admin_unknown": "Unknown admin command. Send /admin for the list.",
        "cmd_buy": "Buy a J.A.R.V.I.S. license",
        "buy_invoice_title": "J.A.R.V.I.S. license",
        "buy_invoice_desc": (
            "Access to J.A.R.V.I.S. on desktop and mobile: your personal "
            "account, license and shared memory across devices."
        ),
        "buy_disabled": "ℹ️ Purchases are not enabled on this server.",
        "buy_thanks_new": (
            "✅ Payment received — welcome aboard!\n\n"
            "Your J.A.R.V.I.S. account:\n"
            "• Login: <code>{username}</code>\n"
            "• Password: <code>{password}</code>\n\n"
            "Sign in from the desktop or mobile app. Keep the password safe — "
            "it is shown only once."
        ),
        "buy_thanks_existing": (
            "✅ Payment received — your license has been extended for account "
            "<code>{username}</code>. Enjoy, Sir."
        ),
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
        "voice_unavailable": "🎤 Voice needs an OpenAI API key configured on the server.",
        "cmd_help": "Show help",
        "cmd_reset": "Clear the conversation",
        "cmd_forget": "Wipe memory about you",
        "cmd_language": "Change language",
        "cmd_link": "Link your J.A.R.V.I.S. account",
        "link_usage": (
            "🔗 To link your account, get a pairing code in the app "
            "(Settings → Link Telegram) and send: /link CODE"
        ),
        "link_success": "✅ Telegram linked to your account <b>{username}</b>.",
        "link_invalid": "❌ That code is invalid or has expired. Get a new one in the app.",
        "link_disabled": "ℹ️ Account linking is not enabled on this server.",
    },
    "ru": {
        "cmd_menu": "Открыть меню",
        "menu_title": "🤖 <b>J.A.R.V.I.S. — меню</b>\nВыберите действие:",
        "menu_profile": "👤 Профиль",
        "menu_usage": "📊 Статистика",
        "menu_subscription": "💳 Подписка",
        "menu_help": "❓ Помощь",
        "menu_back": "⬅️ Назад",
        "profile_title": "Профиль",
        "profile_name": "Имя",
        "profile_account": "Аккаунт",
        "profile_no_account": "не привязан",
        "profile_verified": "Подтверждён",
        "profile_language": "Язык",
        "profile_model": "Модель",
        "profile_messages": "Сообщений",
        "profile_tokens": "Токенов использовано",
        "usage_title": "Отчёт по токенам",
        "usage_today": "Сегодня",
        "usage_month": "За 30 дней",
        "usage_all": "За всё время",
        "usage_tokens": "токенов",
        "sub_title": "Подписка",
        "sub_none": "У вас нет аккаунта. Купите доступ через /buy.",
        "sub_active": "Активный план",
        "sub_inactive": "Нет активной лицензии — продлите через /buy.",
        "sub_perpetual": "Бессрочный доступ",
        "sub_until": "Действует до",
        "sub_days": "дн. осталось",
        "cmd_model": "Сменить ИИ-модель",
        "model_choose": "🤖 Выберите ИИ для общения:",
        "model_set": "✅ Переключено на {model}.",
        "model_none": "ℹ️ На этом сервере настроен только один ИИ.",
        "cmd_admin_sales": "Отчёт продаж (владелец)",
        "cmd_admin": "Админ-панель (владелец)",
        "admin_needs_auth": "⚙️ Для админ-панели нужен AUTH_ENABLED=true на сервере.",
        "admin_post_usage": "Использование: /admin_post текст поста",
        "admin_no_channel": "⚙️ Укажите TELEGRAM_CHANNEL на сервере, чтобы публиковать посты.",
        "admin_posted": "✅ Опубликовано в {channel}.",
        "admin_unknown": "Неизвестная админ-команда. Отправьте /admin для списка.",
        "cmd_buy": "Купить лицензию J.A.R.V.I.S.",
        "buy_invoice_title": "Лицензия J.A.R.V.I.S.",
        "buy_invoice_desc": (
            "Доступ к J.A.R.V.I.S. на компьютере и телефоне: личный аккаунт, "
            "лицензия и общая память на всех устройствах."
        ),
        "buy_disabled": "ℹ️ Покупки на этом сервере не включены.",
        "buy_thanks_new": (
            "✅ Оплата получена — добро пожаловать!\n\n"
            "Ваш аккаунт J.A.R.V.I.S.:\n"
            "• Логин: <code>{username}</code>\n"
            "• Пароль: <code>{password}</code>\n\n"
            "Входите из десктопного или мобильного приложения. Сохраните "
            "пароль — он показывается только один раз."
        ),
        "buy_thanks_existing": (
            "✅ Оплата получена — лицензия аккаунта <code>{username}</code> "
            "продлена. Приятного пользования!"
        ),
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
        "voice_unavailable": "🎤 Для голоса нужен настроенный на сервере ключ OpenAI.",
        "cmd_help": "Показать помощь",
        "cmd_reset": "Очистить диалог",
        "cmd_forget": "Стереть память о вас",
        "cmd_language": "Сменить язык",
        "cmd_link": "Привязать аккаунт J.A.R.V.I.S.",
        "link_usage": (
            "🔗 Чтобы привязать аккаунт, получите код в приложении "
            "(Настройки → Привязать Telegram) и отправьте: /link КОД"
        ),
        "link_success": "✅ Telegram привязан к вашему аккаунту <b>{username}</b>.",
        "link_invalid": "❌ Код неверный или истёк. Получите новый в приложении.",
        "link_disabled": "ℹ️ Привязка аккаунтов на этом сервере не включена.",
    },
    "uz": {
        "cmd_menu": "Menyuni ochish",
        "menu_title": "🤖 <b>J.A.R.V.I.S. — menyu</b>\nAmalni tanlang:",
        "menu_profile": "👤 Profil",
        "menu_usage": "📊 Statistika",
        "menu_subscription": "💳 Obuna",
        "menu_help": "❓ Yordam",
        "menu_back": "⬅️ Orqaga",
        "profile_title": "Profil",
        "profile_name": "Ism",
        "profile_account": "Hisob",
        "profile_no_account": "bog'lanmagan",
        "profile_verified": "Tasdiqlangan",
        "profile_language": "Til",
        "profile_model": "Model",
        "profile_messages": "Xabarlar",
        "profile_tokens": "Ishlatilgan tokenlar",
        "usage_title": "Token hisoboti",
        "usage_today": "Bugun",
        "usage_month": "30 kun ichida",
        "usage_all": "Umumiy",
        "usage_tokens": "token",
        "sub_title": "Obuna",
        "sub_none": "Sizda hisob yo'q. /buy orqali sotib oling.",
        "sub_active": "Faol reja",
        "sub_inactive": "Faol litsenziya yo'q — /buy orqali yangilang.",
        "sub_perpetual": "Muddatsiz kirish",
        "sub_until": "Amal qiladi",
        "sub_days": "kun qoldi",
        "cmd_model": "AI modelini almashtirish",
        "model_choose": "🤖 Suhbat uchun AIni tanlang:",
        "model_set": "✅ {model} ga o'tkazildi.",
        "model_none": "ℹ️ Bu serverda faqat bitta AI sozlangan.",
        "cmd_admin_sales": "Sotuvlar hisoboti (egasi)",
        "cmd_admin": "Admin panel (egasi)",
        "admin_needs_auth": "⚙️ Admin panel uchun serverda AUTH_ENABLED=true kerak.",
        "admin_post_usage": "Foydalanish: /admin_post post matni",
        "admin_no_channel": "⚙️ Post joylash uchun serverda TELEGRAM_CHANNEL ni belgilang.",
        "admin_posted": "✅ {channel} kanaliga joylandi.",
        "admin_unknown": "Noma'lum admin buyruq. Ro'yxat uchun /admin yuboring.",
        "cmd_buy": "J.A.R.V.I.S. litsenziyasini sotib olish",
        "buy_invoice_title": "J.A.R.V.I.S. litsenziyasi",
        "buy_invoice_desc": (
            "Kompyuter va telefonda J.A.R.V.I.S.: shaxsiy hisob, litsenziya "
            "va barcha qurilmalarda umumiy xotira."
        ),
        "buy_disabled": "ℹ️ Bu serverda xaridlar yoqilmagan.",
        "buy_thanks_new": (
            "✅ To'lov qabul qilindi — xush kelibsiz!\n\n"
            "J.A.R.V.I.S. hisobingiz:\n"
            "• Login: <code>{username}</code>\n"
            "• Parol: <code>{password}</code>\n\n"
            "Desktop yoki mobil ilovadan kiring. Parolni saqlab qo'ying — "
            "u faqat bir marta ko'rsatiladi."
        ),
        "buy_thanks_existing": (
            "✅ To'lov qabul qilindi — <code>{username}</code> hisobining "
            "litsenziyasi uzaytirildi!"
        ),
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
        "voice_unavailable": "🎤 Ovoz uchun serverda sozlangan OpenAI kaliti kerak.",
        "cmd_help": "Yordamni ko'rsatish",
        "cmd_reset": "Suhbatni tozalash",
        "cmd_forget": "Xotirani o'chirish",
        "cmd_language": "Tilni o'zgartirish",
        "cmd_link": "J.A.R.V.I.S. hisobini bog'lash",
        "link_usage": (
            "🔗 Hisobingizni bog'lash uchun ilovada kod oling "
            "(Sozlamalar → Telegram bog'lash) va yuboring: /link KOD"
        ),
        "link_success": "✅ Telegram <b>{username}</b> hisobingizga bog'landi.",
        "link_invalid": "❌ Kod noto'g'ri yoki muddati o'tgan. Ilovada yangisini oling.",
        "link_disabled": "ℹ️ Bu serverda hisob bog'lash yoqilmagan.",
    },
}
