# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════╗
# ║          BORSH VPN BOT  v3.1  —  FIXED EDITION             ║
# ║  Новое: ежедневные бонусы, достижения, FAQ, колесо удачи,  ║
# ║  кэшбэк, антиспам, inline-режим, мультиязык, отзывы,       ║
# ║  ротация ключей, аналитика, экспорт CSV, TOTP для админов  ║
# ╚══════════════════════════════════════════════════════════════╝

import telebot
from telebot import types
from telebot.handler_backends import BaseMiddleware, CancelUpdate
from telebot.apihelper import ApiTelegramException

import sqlite3, datetime, threading, time, os, random
import string, functools, math, json, hashlib, hmac
import csv, io, re
import sys, logging
try:
    import fcntl            # Linux/macOS: защита от двойного запуска
except ImportError:
    fcntl = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
#                         CONFIG
# ============================================================
# Токен берётся из переменной окружения BOT_TOKEN (рекомендуется) или вписывается сюда.
# Никогда не публикуйте токен. Если он утёк: @BotFather → /revoke.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip() or "8610346450:AAFU-YG46eGKdzUwaJBUvU3Lc88o0yGWPq8"
ADMIN_IDS = [8174421672]
SUPPORT   = "@fuckrizer"
DEV       = "@fuckrizer"
DB_NAME   = os.path.join(BASE_DIR, "borsh_vpn.db")

TRIAL_URL   = "https://borshvpn.com"
SITE_URL    = "https://borshvpn.com"
IMAGE_DIR   = os.path.join(BASE_DIR, "image")
PRIVACY_URL = "https://telegra.ph/Politika-konfidencialnosti-09-15-75"
TERMS_URL   = "https://telegra.ph/Polzovatelskoe-soglashenie-09-15-31"

MASTER_SUB_URL = "https://happ.yummyx.org/sub/NTg5OTM0NzUzMiwxNzkwMzQwNDUzKhpI47rnT2"

CARD_NUMBER         = "2204320641527322"
CARD_HOLDER         = "IVAN I."
PAYMENT_TIMEOUT_MIN = 15
MIN_TOPUP           = 50
MAX_TOPUP           = 10000

REFERRAL_BONUS     = 50
REFERRAL_BONUS_NEW = 30

NOTIFY_DAYS_BEFORE = [7, 3, 1]   # + предупреждение за 7 дней

# Кэшбэк: процент от каждой покупки возвращается на баланс
CASHBACK_PERCENT = 5             # 5%
# Кэшбэк при пополнении баланса. По тексту бота кэшбэк только «с покупки» — иначе он
# начислялся бы дважды (при пополнении и при покупке). Включите True, если так задумано.
CASHBACK_ON_TOPUP = False

# Ежедневный чекин: сумма вознаграждения
CHECKIN_REWARD   = 10            # ₽ за вход каждый день

# Антиспам: максимум сообщений за окно
RATELIMIT_MESSAGES = 10
RATELIMIT_WINDOW   = 15          # секунд

TARIFFS = [
    {"name": "1 месяц",    "days": 30,  "price": 199,  "emoji": "🌱"},
    {"name": "3 месяца",   "days": 90,  "price": 499,  "emoji": "🔥"},
    {"name": "6 месяцев",  "days": 180, "price": 899,  "emoji": "💎"},
    {"name": "12 месяцев", "days": 365, "price": 1699, "emoji": "👑"},
]

SERVERS = [
    {"country": "🇳🇱", "name": "Нидерланды",      "ping": 24,  "load": 45, "code": "NL"},
    {"country": "🇩🇪", "name": "Германия",        "ping": 38,  "load": 62, "code": "DE"},
    {"country": "🇫🇮", "name": "Финляндия",       "ping": 42,  "load": 33, "code": "FI"},
    {"country": "🇬🇧", "name": "Великобритания",  "ping": 55,  "load": 71, "code": "UK"},
    {"country": "🇺🇸", "name": "США",             "ping": 120, "load": 58, "code": "US"},
    {"country": "🇯🇵", "name": "Япония",          "ping": 180, "load": 29, "code": "JP"},
    {"country": "🇸🇬", "name": "Сингапур",        "ping": 95,  "load": 41, "code": "SG"},
    {"country": "🇫🇷", "name": "Франция",         "ping": 47,  "load": 55, "code": "FR"},
    {"country": "🇨🇿", "name": "Чехия",           "ping": 35,  "load": 38, "code": "CZ"},
    {"country": "🇦🇺", "name": "Австралия",       "ping": 210, "load": 22, "code": "AU"},
]

# FAQ: вопрос → ответ
FAQ = [
    ("Как установить VPN?",
     "1️⃣ Скачайте **Happ** (iOS/Android) или **V2RayNG** (Android)\n"
     "2️⃣ Скопируйте ключ из раздела «Мои подписки»\n"
     "3️⃣ В приложении: «Добавить» → «Импорт по ссылке»\n"
     "4️⃣ Вставьте ключ → подключитесь"),
    ("Сколько устройств можно подключить?",
     "Наш ключ работает на **неограниченном** количестве устройств одновременно."),
    ("Как продлить подписку?",
     "Перейдите в «⚡ Купить подписку» — если у вас уже есть активная подписка, "
     "новый период **добавится** к текущему."),
    ("Можно ли получить возврат?",
     "Возврат средств осуществляется в течение 24 ч. с момента покупки, "
     "если ключ не использовался. Напишите в поддержку."),
    ("Почему VPN не подключается?",
     "1️⃣ Проверьте интернет-соединение\n"
     "2️⃣ Убедитесь, что скопировали ключ целиком\n"
     "3️⃣ Попробуйте другой протокол в настройках Happ\n"
     "4️⃣ Если не помогло — напишите в поддержку"),
    ("Что такое Happ?",
     "**Happ** — это VPN-клиент, поддерживающий протоколы VLESS/VMess/Trojan. "
     "Доступен бесплатно в App Store и Google Play."),
    ("Есть ли ограничение трафика?",
     "Нет! Все тарифы включают **безлимитный** трафик."),
    ("Как работают рефералы?",
     f"Поделитесь своей ссылкой (раздел «🎁 Бонусы»). "
     f"Когда друг зарегистрируется, вам начислится **{REFERRAL_BONUS}₽**, "
     f"а другу — **{REFERRAL_BONUS_NEW}₽**."),
    ("Что такое ежедневный бонус?",
     f"Заходите в бота каждый день и нажимайте «📅 Чекин» — "
     f"получайте **+{CHECKIN_REWARD}₽** на баланс. Серия дней увеличивает награду!"),
    ("Как использовать промокод?",
     "Перейдите в «🎁 Бонусы» → «🎟 Промокод» и введите код. "
     "Промокоды дают скидки, бесплатные дни или деньги на баланс."),
]

# Достижения: (id, название, описание, условие-тип, порог, награда-₽, эмодзи)
ACHIEVEMENTS = [
    ("first_buy",    "Первая покупка",      "Оформите первую подписку",            "subs",   1,    20, "🛒"),
    ("loyal_3",      "Постоянный клиент",   "Купите 3 любых тарифа",               "subs",   3,    50, "💛"),
    ("loyal_10",     "Ветеран VPN",         "Купите 10 подписок",                  "subs",  10,   150, "🎖️"),
    ("spender_500",  "Инвестор",            "Потратьте 500₽",                      "spent",  500,  30, "💸"),
    ("spender_5000", "VIP-клиент",          "Потратьте 5000₽",                     "spent", 5000, 200, "💎"),
    ("ref_1",        "Амбассадор",          "Пригласите 1 друга",                  "refs",   1,    30, "👥"),
    ("ref_5",        "Инфлюенсер",         "Пригласите 5 друзей",                 "refs",   5,   100, "🌟"),
    ("ref_10",       "Легенда",             "Пригласите 10 друзей",                "refs",  10,   300, "🏆"),
    ("checkin_7",    "Неделя с нами",       "7 дней подряд заходите в бот",       "streak",  7,    50, "📅"),
    ("checkin_30",   "Месяц с нами",        "30 дней подряд",                     "streak", 30,   200, "🔥"),
    ("review_done",  "Голос пользователя",  "Оставьте отзыв",                     "review",  1,    15, "⭐"),
    ("wheel_win",    "Удачливый",           "Выиграйте что-нибудь на колесе",     "wheel",   1,    10, "🎰"),
]

# Локализация (RU/EN)
LANG = {
    "ru": {
        "welcome": "🌐 **BORSH VPN** — свобода в сети",
        "balance": "💰 Баланс",
        "sub":     "📋 Подписка",
        "days":    "дн.",
        "active":  "Активна",
        "inactive":"Неактивна",
    },
    "en": {
        "welcome": "🌐 **BORSH VPN** — Freedom Online",
        "balance": "💰 Balance",
        "sub":     "📋 Subscription",
        "days":    "days",
        "active":  "Active",
        "inactive":"Inactive",
    },
}

# ============================================================
if not re.fullmatch(r"\d{6,}:[A-Za-z0-9_-]{30,}", BOT_TOKEN):
    print("[✗] BOT_TOKEN не задан или имеет неверный формат.\n"
          "    Получите токен у @BotFather (/revoke → новый токен) и задайте его\n"
          "    переменной окружения BOT_TOKEN либо в строке BOT_TOKEN в начале файла.")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown", use_class_middlewares=True)


def _strip_md(text) -> str:
    """Убирает Markdown-разметку вне блоков `code` (ключи в `...` остаются нетронутыми)."""
    parts = str(text).split("`")
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r"[*_\[\]]", "", parts[i])
    return "".join(parts)

def _md_safe(fn, text_pos, text_kw):
    """Если Telegram отклонил сообщение из-за разметки (например, '_' в имени пользователя) —
    повторяем отправку без форматирования, а не теряем сообщение."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ApiTelegramException as e:
            if "can't parse entities" not in str(e).lower():
                raise
            args = list(args)
            if kwargs.get(text_kw):
                kwargs[text_kw] = _strip_md(kwargs[text_kw])
            elif len(args) > text_pos:
                args[text_pos] = _strip_md(args[text_pos])
            else:
                raise
            return fn(*args, **kwargs)
    return wrapper

bot.send_message      = _md_safe(bot.send_message,      1, "text")
bot.edit_message_text = _md_safe(bot.edit_message_text, 0, "text")
bot.send_photo        = _md_safe(bot.send_photo,        2, "caption")

user_states   = {}
user_context  = {}
_ban_cache    = {}
_rate_cache   = {}   # антиспам: {uid: [timestamp, ...]}


# ============================================================
#                       УТИЛИТЫ
# ============================================================
def is_admin(uid) -> bool:
    return uid in ADMIN_IDS

def gen_code(n=8) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

def fmt_dt(s, fmt="%d.%m.%Y") -> str:
    if not s: return "—"
    try:    return datetime.datetime.fromisoformat(s).strftime(fmt)
    except: return str(s)[:10]

def days_left(s) -> int:
    if not s: return 0
    try:
        d = datetime.datetime.fromisoformat(s) - datetime.datetime.now()
        return max(0, math.ceil(d.total_seconds() / 86400))
    except: return 0

def load_bar(pct, n=8) -> str:
    pct = max(0, min(100, pct))
    f = round(pct / 100 * n)
    return "█" * f + "░" * (n - f)

def get_start_photo():
    if not os.path.exists(IMAGE_DIR): return None
    ok = {'.jpg','.jpeg','.png','.gif','.webp','.bmp'}
    for f in sorted(os.listdir(IMAGE_DIR)):
        if os.path.splitext(f)[1].lower() in ok:
            return os.path.join(IMAGE_DIR, f)
    return None

def esc(s) -> str:
    """Экранирует спецсимволы Markdown в пользовательском тексте (имена, ники, отзывы)."""
    return re.sub(r"([_*`\[])", r"\\\1", str(s if s is not None else ""))

def safe_edit(call, text, kb=None):
    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=kb, parse_mode="Markdown",
                              disable_web_page_preview=True)
        return True
    except Exception as e:
        if "not modified" not in str(e).lower(): print(f"[edit] {e}")
        return False

def safe_ans(call, txt=None, alert=False):
    try: bot.answer_callback_query(call.id, txt or "", show_alert=alert)
    except: pass

def L(uid, key) -> str:
    """Локализация."""
    lang = "ru"
    try:
        u = get_user(uid)
        if u: lang = u.get("lang", "ru")
    except: pass
    return LANG.get(lang, LANG["ru"]).get(key, key)

def totp_verify(secret: str, code: str) -> bool:
    """Упрощённая проверка 6-значного TOTP без внешних библиотек."""
    try:
        t = int(time.time()) // 30
        for delta in [-1, 0, 1]:
            msg = ((t + delta) * 1).to_bytes(8, 'big')
            h   = hmac.new(secret.encode(), msg, hashlib.sha1).digest()
            off = h[-1] & 0x0F
            val = ((h[off] & 0x7F) << 24 | h[off+1] << 16 |
                   h[off+2] << 8 | h[off+3]) % 1_000_000
            if str(val).zfill(6) == str(code).strip():
                return True
    except: pass
    return False

def check_rate_limit(uid) -> bool:
    """True — пропустить, False — заблокировать."""
    if is_admin(uid): return True
    now = time.time()
    q   = _rate_cache.get(uid, [])
    q   = [t for t in q if now - t < RATELIMIT_WINDOW]
    q.append(now)
    _rate_cache[uid] = q
    return len(q) <= RATELIMIT_MESSAGES

def ascii_chart(values: list, labels: list, width=20) -> str:
    """Горизонтальный ASCII-бар чарт."""
    if not values: return "нет данных"
    mx = max(values) or 1
    lines = []
    for v, lbl in zip(values, labels):
        bar  = "█" * int(v / mx * width)
        lines.append(f"{lbl:6s} {bar} {v}")
    return "\n".join(lines)


# ============================================================
#                       DATABASE
# ============================================================
def get_conn():
    """
    Каждый вызов создаёт соединение с таймаутом 30 сек — SQLite будет
    ждать снятия блокировки вместо немедленного падения с "database is locked".
    WAL-mode позволяет нескольким потокам читать одновременно и совмещать
    чтение с записью без взаимоблокировок.
    """
    c = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")   # Write-Ahead Logging
    c.execute("PRAGMA synchronous=NORMAL") # быстрее, но надёжнее чем OFF
    c.execute("PRAGMA busy_timeout=30000") # 30 сек на разблокировку
    return c

def init_db():
    conn = get_conn(); c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        tg_id          INTEGER PRIMARY KEY,
        username       TEXT,
        first_name     TEXT,
        registered_at  TEXT,
        balance        INTEGER DEFAULT 0,
        sub_status     TEXT DEFAULT 'Неактивна',
        sub_until      TEXT,
        trial_used     INTEGER DEFAULT 0,
        ref_by         INTEGER DEFAULT NULL,
        ref_count      INTEGER DEFAULT 0,
        total_spent    INTEGER DEFAULT 0,
        cashback_total INTEGER DEFAULT 0,
        banned         INTEGER DEFAULT 0,
        last_active    TEXT,
        lang           TEXT DEFAULT 'ru',
        checkin_streak INTEGER DEFAULT 0,
        checkin_last   TEXT,
        totp_secret    TEXT DEFAULT NULL,
        total_checkins INTEGER DEFAULT 0,
        wheel_last     TEXT,
        rating_given   INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id        INTEGER,
        amount       INTEGER,
        status       TEXT DEFAULT 'pending',
        created_at   TEXT,
        confirmed_at TEXT,
        comment      TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id        INTEGER,
        tariff_name  TEXT,
        days         INTEGER,
        price        INTEGER,
        vpn_key      TEXT,
        activated_at TEXT,
        expires_at   TEXT,
        status       TEXT DEFAULT 'Активна',
        notified_7   INTEGER DEFAULT 0,
        notified_3   INTEGER DEFAULT 0,
        notified_1   INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        code       TEXT UNIQUE,
        type       TEXT,
        value      INTEGER,
        uses_left  INTEGER DEFAULT 1,
        used_count INTEGER DEFAULT 0,
        expires_at TEXT,
        created_at TEXT,
        created_by INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS promo_uses (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        code    TEXT,
        tg_id   INTEGER,
        used_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS action_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id      INTEGER,
        action     TEXT,
        detail     TEXT,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS vpn_keys (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        key_url    TEXT UNIQUE,
        label      TEXT,
        active     INTEGER DEFAULT 1,
        load_pct   INTEGER DEFAULT 0,
        max_users  INTEGER DEFAULT 1000,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id       INTEGER,
        ach_id      TEXT,
        unlocked_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id      INTEGER,
        stars      INTEGER,
        text       TEXT,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS banners (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT,
        text       TEXT,
        url        TEXT,
        active     INTEGER DEFAULT 1,
        views      INTEGER DEFAULT 0,
        clicks     INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        text       TEXT,
        send_at    TEXT,
        sent       INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cashback_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id      INTEGER,
        amount     INTEGER,
        reason     TEXT,
        created_at TEXT
    )''')

    # Мастер-ключ
    c.execute("INSERT OR IGNORE INTO vpn_keys (key_url, label, active, created_at) VALUES (?,?,1,?)",
              (MASTER_SUB_URL, "Мастер-ключ", datetime.datetime.now().isoformat()))

    # ──────────────────────────────────────────────────────────────
    # МИГРАЦИЯ: добавляем колонки, которых нет в старой базе данных.
    # ALTER TABLE ADD COLUMN падает с ошибкой если колонка уже есть,
    # поэтому сначала читаем список существующих колонок.
    # ──────────────────────────────────────────────────────────────
    def _existing_cols(table):
        try:
            rows = c.execute(f"PRAGMA table_info({table})").fetchall()
            return {r["name"] for r in rows}
        except Exception:
            return set()

    def _add_col(table, col, typedef):
        if col not in _existing_cols(table):
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
            except Exception as e:
                print(f"[migration] {table}.{col}: {e}")

    # users — новые колонки v3.0
    _add_col("users", "cashback_total",  "INTEGER DEFAULT 0")
    _add_col("users", "lang",            "TEXT DEFAULT 'ru'")
    _add_col("users", "checkin_streak",  "INTEGER DEFAULT 0")
    _add_col("users", "checkin_last",    "TEXT")
    _add_col("users", "totp_secret",     "TEXT DEFAULT NULL")
    _add_col("users", "total_checkins",  "INTEGER DEFAULT 0")
    _add_col("users", "wheel_last",      "TEXT")
    _add_col("users", "rating_given",    "INTEGER DEFAULT 0")

    # subscriptions — колонки уведомлений v3.0
    _add_col("subscriptions", "notified_7", "INTEGER DEFAULT 0")
    _add_col("subscriptions", "notified_3", "INTEGER DEFAULT 0")
    _add_col("subscriptions", "notified_1", "INTEGER DEFAULT 0")

    # payments — поле комментария
    _add_col("payments", "comment", "TEXT")

    # vpn_keys — нагрузка
    _add_col("vpn_keys", "load_pct",  "INTEGER DEFAULT 0")
    _add_col("vpn_keys", "max_users", "INTEGER DEFAULT 1000")

    # Защита от двойной выдачи достижений + индексы для скорости
    try:
        c.execute("DELETE FROM achievements WHERE id NOT IN "
                  "(SELECT MIN(id) FROM achievements GROUP BY tg_id, ach_id)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_ach ON achievements(tg_id, ach_id)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_pay_status ON payments(status)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_subs_tg ON subscriptions(tg_id)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_log_tg_act ON action_log(tg_id, action)")
    except Exception as e:
        print(f"[migration] индексы: {e}")

    conn.commit(); conn.close()

# ---------- USERS ----------
def add_user(tg_id, username, first_name, ref_by=None) -> bool:
    conn = get_conn(); c = conn.cursor()
    now  = datetime.datetime.now().isoformat()
    c.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,))
    if c.fetchone():
        c.execute("UPDATE users SET username=?,first_name=?,last_active=? WHERE tg_id=?",
                  (username or "", first_name or "", now, tg_id))
        conn.commit(); conn.close(); return False
    c.execute('''INSERT INTO users (tg_id,username,first_name,registered_at,last_active,
                                   balance,sub_status,ref_by,ref_count,lang)
                 VALUES (?,?,?,?,?,0,'Неактивна',NULL,0,'ru')''',
              (tg_id, username or "", first_name or "", now, now))
    if ref_by and ref_by != tg_id:
        c.execute("SELECT tg_id FROM users WHERE tg_id=?", (ref_by,))
        if c.fetchone():
            # пригласившему: +счётчик и бонус; новичку: запоминаем, кто его пригласил, и бонус
            c.execute("UPDATE users SET ref_count=COALESCE(ref_count,0)+1,"
                      "balance=COALESCE(balance,0)+? WHERE tg_id=?",
                      (REFERRAL_BONUS, ref_by))
            c.execute("UPDATE users SET ref_by=?,balance=COALESCE(balance,0)+? WHERE tg_id=?",
                      (ref_by, REFERRAL_BONUS_NEW, tg_id))
    conn.commit(); conn.close(); return True

def touch_user(tg_id):
    try:
        conn = get_conn()
        conn.execute("UPDATE users SET last_active=? WHERE tg_id=?",
                     (datetime.datetime.now().isoformat(), tg_id))
        conn.commit(); conn.close()
    except: pass

def get_user(tg_id):
    conn = get_conn()
    row  = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def set_trial_used(tg_id):
    conn = get_conn()
    exp  = (datetime.datetime.now() + datetime.timedelta(days=5)).isoformat()
    conn.execute("UPDATE users SET trial_used=1,sub_status='Активна (пробная)',sub_until=? WHERE tg_id=?",
                 (exp, tg_id))
    conn.commit(); conn.close()

def add_balance(tg_id, amount):
    conn = get_conn()
    conn.execute("UPDATE users SET balance=balance+? WHERE tg_id=?", (amount, tg_id))
    conn.commit(); conn.close()

def deduct_balance(tg_id, amount) -> bool:
    """Атомарное списание: баланс не уйдёт в минус даже при двойном клике."""
    if amount <= 0: return False
    conn = get_conn()
    cur  = conn.execute("UPDATE users SET balance=balance-?,total_spent=COALESCE(total_spent,0)+? "
                        "WHERE tg_id=? AND COALESCE(balance,0)>=?", (amount, amount, tg_id, amount))
    ok = cur.rowcount > 0
    conn.commit(); conn.close(); return ok

def activate_subscription(tg_id, days) -> str:
    conn = get_conn()
    row  = conn.execute("SELECT sub_until FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    base = datetime.datetime.now()
    if row and row["sub_until"]:
        try:
            old = datetime.datetime.fromisoformat(row["sub_until"])
            if old > base: base = old
        except: pass
    exp = (base + datetime.timedelta(days=days)).isoformat()
    conn.execute("UPDATE users SET sub_status='Активна',sub_until=? WHERE tg_id=?", (exp, tg_id))
    conn.commit(); conn.close(); return exp

def ban_user(tg_id, ban=True):
    conn = get_conn()
    conn.execute("UPDATE users SET banned=? WHERE tg_id=?", (1 if ban else 0, tg_id))
    conn.commit(); conn.close(); _ban_cache.clear()

def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT tg_id FROM users WHERE banned=0").fetchall()
    conn.close(); return [r["tg_id"] for r in rows]

def set_user_lang(tg_id, lang):
    conn = get_conn()
    conn.execute("UPDATE users SET lang=? WHERE tg_id=?", (lang, tg_id))
    conn.commit(); conn.close()

# ---------- CHECKIN ----------
def do_checkin(tg_id):
    """Вернуть (True, reward, streak) если чекин успешен, иначе (False, 0, streak)."""
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT checkin_last, checkin_streak, total_checkins FROM users WHERE tg_id=?", (tg_id,))
    row = c.fetchone()
    if not row: conn.close(); return False, 0, 0
    last   = row["checkin_last"]
    streak = row["checkin_streak"] or 0
    today  = datetime.date.today().isoformat()
    if last == today:
        conn.close(); return False, 0, streak
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if last == yesterday:
        streak += 1
    else:
        streak = 1
    # Бонус растёт со стриком: 10 + (streak // 7) * 5
    reward = CHECKIN_REWARD + (streak // 7) * 5
    cur = conn.execute("UPDATE users SET checkin_last=?,checkin_streak=?,"
                       "total_checkins=COALESCE(total_checkins,0)+1,balance=COALESCE(balance,0)+? "
                       "WHERE tg_id=? AND (checkin_last IS NULL OR checkin_last<>?)",
                       (today, streak, reward, tg_id, today))
    ok = cur.rowcount > 0
    conn.commit(); conn.close()
    return (True, reward, streak) if ok else (False, 0, streak)

# ---------- SUBSCRIPTIONS ----------
def add_subscription_record(tg_id, tariff_name, days, price, vpn_key, expires_at):
    conn = get_conn()
    conn.execute('''INSERT INTO subscriptions
                    (tg_id,tariff_name,days,price,vpn_key,activated_at,expires_at,status)
                    VALUES (?,?,?,?,?,?,?,'Активна')''',
                 (tg_id, tariff_name, days, price, vpn_key,
                  datetime.datetime.now().isoformat(), expires_at))
    conn.commit(); conn.close()

def get_user_subscriptions(tg_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM subscriptions WHERE tg_id=? ORDER BY id DESC", (tg_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def update_expired_subscriptions():
    conn = get_conn(); now = datetime.datetime.now().isoformat()
    conn.execute("UPDATE subscriptions SET status='Истекла' WHERE expires_at<? AND status='Активна'", (now,))
    conn.execute("UPDATE users SET sub_status='Неактивна' WHERE sub_until IS NOT NULL "
                 "AND sub_until<? AND sub_status LIKE 'Активна%'", (now,))
    conn.commit(); conn.close()

def get_best_key() -> str:
    """Выбрать наименее загруженный активный ключ."""
    conn = get_conn()
    row  = conn.execute("SELECT key_url FROM vpn_keys WHERE active=1 ORDER BY load_pct ASC, id LIMIT 1").fetchone()
    conn.close(); return row["key_url"] if row else MASTER_SUB_URL

def get_active_key() -> str:
    return get_best_key()

# ---------- CASHBACK ----------
def give_cashback(tg_id, purchase_amount):
    if CASHBACK_PERCENT <= 0: return 0
    cb = math.floor(purchase_amount * CASHBACK_PERCENT / 100)
    if cb <= 0: return 0
    conn = get_conn()
    conn.execute("UPDATE users SET balance=balance+?,cashback_total=cashback_total+? WHERE tg_id=?",
                 (cb, cb, tg_id))
    conn.execute("INSERT INTO cashback_log (tg_id,amount,reason,created_at) VALUES (?,?,?,?)",
                 (tg_id, cb, f"покупка {purchase_amount}₽", datetime.datetime.now().isoformat()))
    conn.commit(); conn.close(); return cb

# ---------- ACHIEVEMENTS ----------
def check_achievements(tg_id):
    """Проверить и выдать новые достижения. Возвращает список разблокированных."""
    user = get_user(tg_id);
    if not user: return []
    conn   = get_conn()
    done   = {r["ach_id"] for r in conn.execute("SELECT ach_id FROM achievements WHERE tg_id=?", (tg_id,)).fetchall()}
    subs   = len(get_user_subscriptions(tg_id))
    spent  = user.get("total_spent") or 0
    refs   = user.get("ref_count") or 0
    streak = user.get("checkin_streak") or 0
    wheel  = sum(1 for r in conn.execute("SELECT id FROM action_log WHERE tg_id=? AND action='wheel_win'", (tg_id,)).fetchall())
    review = user.get("rating_given") or 0
    checks = {"subs": subs, "spent": spent, "refs": refs, "streak": streak, "wheel": wheel, "review": review}
    now    = datetime.datetime.now().isoformat()
    new_achs = []
    for ach in ACHIEVEMENTS:
        aid, name, desc, ctype, threshold, reward, emoji = ach
        if aid in done: continue
        if checks.get(ctype, 0) >= threshold:
            cur = conn.execute("INSERT OR IGNORE INTO achievements (tg_id,ach_id,unlocked_at) "
                               "VALUES (?,?,?)", (tg_id, aid, now))
            if cur.rowcount > 0:      # награда — только тому потоку, который реально разблокировал
                conn.execute("UPDATE users SET balance=COALESCE(balance,0)+? WHERE tg_id=?", (reward, tg_id))
                new_achs.append((name, reward, emoji))
    conn.commit(); conn.close(); return new_achs

def get_user_achievements(tg_id):
    conn  = get_conn()
    rows  = conn.execute("SELECT ach_id, unlocked_at FROM achievements WHERE tg_id=?", (tg_id,)).fetchall()
    conn.close(); return {r["ach_id"]: r["unlocked_at"] for r in rows}

# ---------- PAYMENTS ----------
def create_payment(tg_id, amount) -> int:
    conn = get_conn(); c = conn.cursor()
    c.execute("INSERT INTO payments (tg_id,amount,status,created_at) VALUES (?,?,'pending',?)",
              (tg_id, amount, datetime.datetime.now().isoformat()))
    pid = c.lastrowid; conn.commit(); conn.close(); return pid

def get_payment(pid):
    conn = get_conn()
    row  = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
    conn.close(); return dict(row) if row else None

def set_payment_status(pid, status):
    conn = get_conn()
    conn.execute("UPDATE payments SET status=?,confirmed_at=? WHERE id=?",
                 (status, datetime.datetime.now().isoformat(), pid))
    conn.commit(); conn.close()

def claim_payment(pid, from_statuses, to_status) -> bool:
    """Атомарно меняет статус заявки. True — если именно мы её перевели."""
    marks = ",".join("?" * len(from_statuses))
    ts    = None if to_status == "review" else datetime.datetime.now().isoformat()
    conn  = get_conn()
    cur   = conn.execute(f"UPDATE payments SET status=?,confirmed_at=COALESCE(?,confirmed_at) "
                         f"WHERE id=? AND status IN ({marks})", (to_status, ts, pid, *from_statuses))
    ok = cur.rowcount > 0
    conn.commit(); conn.close(); return ok

def confirm_payment(pid):
    """Атомарно: заявка pending/review → confirmed И зачисление на баланс в одной транзакции.
    Возвращает dict заявки или None (если уже обработана) — двойного зачисления не будет."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if not row: return None
        cur = conn.execute("UPDATE payments SET status='confirmed',confirmed_at=? "
                           "WHERE id=? AND status IN ('pending','review')",
                           (datetime.datetime.now().isoformat(), pid))
        if cur.rowcount == 0: return None
        conn.execute("UPDATE users SET balance=COALESCE(balance,0)+? WHERE tg_id=?",
                     (row["amount"], row["tg_id"]))
        conn.commit()
        return dict(row)
    finally:
        conn.close()

def expire_stale_payments():
    """Закрывает заявки, по которым не нажали «Я оплатил» (в т.ч. если бот перезапускался
    и потоки-таймеры потерялись)."""
    limit = (datetime.datetime.now() - datetime.timedelta(minutes=PAYMENT_TIMEOUT_MIN)).isoformat()
    conn = get_conn()
    conn.execute("UPDATE payments SET status='expired' WHERE status='pending' AND created_at<?", (limit,))
    conn.commit(); conn.close()

def get_pending_payments():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM payments WHERE status IN ('pending','review') ORDER BY id DESC").fetchall()
    conn.close(); return [dict(r) for r in rows]

# ---------- PROMOS ----------
def create_promo(code, ptype, value, uses, expires_at, created_by) -> bool:
    conn = get_conn()
    try:
        conn.execute("INSERT INTO promo_codes (code,type,value,uses_left,expires_at,created_at,created_by) "
                     "VALUES (?,?,?,?,?,?,?)",
                     (code.upper(), ptype, value, uses, expires_at,
                      datetime.datetime.now().isoformat(), created_by))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError:
        conn.close(); return False

def use_promo(code, tg_id):
    conn = get_conn(); c = conn.cursor(); now = datetime.datetime.now().isoformat()
    c.execute("SELECT * FROM promo_codes WHERE code=?", (code.upper(),))
    row = c.fetchone()
    if not row: conn.close(); return None, "❌ Промокод не найден"
    row = dict(row)
    if row["uses_left"] <= 0:      conn.close(); return None, "❌ Промокод исчерпан"
    if row["expires_at"] and row["expires_at"] < now:
        conn.close(); return None, "❌ Промокод просрочен"
    c.execute("SELECT id FROM promo_uses WHERE code=? AND tg_id=?", (code.upper(), tg_id))
    if c.fetchone():               conn.close(); return None, "❌ Уже использован"
    c.execute("UPDATE promo_codes SET uses_left=uses_left-1,used_count=used_count+1 WHERE code=?", (code.upper(),))
    c.execute("INSERT INTO promo_uses (code,tg_id,used_at) VALUES (?,?,?)", (code.upper(), tg_id, now))
    conn.commit(); conn.close(); return row, "✅"

# ---------- REVIEWS ----------
def add_review(tg_id, stars, text):
    conn = get_conn()
    conn.execute("INSERT INTO reviews (tg_id,stars,text,created_at) VALUES (?,?,?,?)",
                 (tg_id, stars, text, datetime.datetime.now().isoformat()))
    conn.execute("UPDATE users SET rating_given=1 WHERE tg_id=?", (tg_id,))
    conn.commit(); conn.close()

def get_reviews(limit=20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_rating_stats():
    conn = get_conn(); c = conn.cursor()
    rows = c.execute("SELECT stars, COUNT(*) as cnt FROM reviews GROUP BY stars").fetchall()
    conn.close()
    d = {r["stars"]: r["cnt"] for r in rows}
    total = sum(d.values()) or 1
    avg   = sum(s * n for s, n in d.items()) / total
    return d, avg, total

# ---------- BANNERS ----------
def get_active_banner():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM banners WHERE active=1 ORDER BY RANDOM() LIMIT 1").fetchall()
    conn.close(); return dict(rows[0]) if rows else None

def add_banner(title, text, url, created_by):
    conn = get_conn()
    conn.execute("INSERT INTO banners (title,text,url,active,created_at) VALUES (?,?,?,1,?)",
                 (title, text, url or "", datetime.datetime.now().isoformat()))
    conn.commit(); conn.close()

# ---------- SCHEDULED BROADCASTS ----------
def schedule_broadcast(text, send_at, created_by):
    conn = get_conn()
    conn.execute("INSERT INTO scheduled_broadcasts (text,send_at,sent,created_by,created_at) VALUES (?,?,0,?,?)",
                 (text, send_at, created_by, datetime.datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_pending_broadcasts():
    conn = get_conn(); now = datetime.datetime.now().isoformat()
    rows = conn.execute("SELECT * FROM scheduled_broadcasts WHERE sent=0 AND send_at<=?", (now,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def mark_broadcast_sent(bid):
    conn = get_conn()
    conn.execute("UPDATE scheduled_broadcasts SET sent=1 WHERE id=?", (bid,))
    conn.commit(); conn.close()

# ---------- VPN KEYS ----------
def get_all_keys():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM vpn_keys ORDER BY id").fetchall()
    conn.close(); return [dict(r) for r in rows]

def add_vpn_key(url, label) -> bool:
    conn = get_conn()
    try:
        conn.execute("INSERT INTO vpn_keys (key_url,label,active,created_at) VALUES (?,?,1,?)",
                     (url, label, datetime.datetime.now().isoformat()))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError:
        conn.close(); return False

def toggle_vpn_key(kid, active):
    conn = get_conn()
    conn.execute("UPDATE vpn_keys SET active=? WHERE id=?", (active, kid))
    conn.commit(); conn.close()

def set_key_load(kid, load_pct):
    conn = get_conn()
    conn.execute("UPDATE vpn_keys SET load_pct=? WHERE id=?", (load_pct, kid))
    conn.commit(); conn.close()

# ---------- TOTP ----------
def set_totp_secret(tg_id, secret):
    conn = get_conn()
    conn.execute("UPDATE users SET totp_secret=? WHERE tg_id=?", (secret, tg_id))
    conn.commit(); conn.close()

def verify_admin_totp(tg_id, code) -> bool:
    user = get_user(tg_id)
    if not user: return False
    sec = user.get("totp_secret")
    if not sec: return True   # если TOTP не настроен — пропускаем
    return totp_verify(sec, code)

# ---------- LOG ----------
def log_action(tg_id, action, detail=""):
    try:
        conn = get_conn()
        conn.execute("INSERT INTO action_log (tg_id,action,detail,created_at) VALUES (?,?,?,?)",
                     (tg_id, action, detail, datetime.datetime.now().isoformat()))
        conn.commit(); conn.close()
    except: pass

# ---------- EXPORT ----------
def export_users_csv() -> str:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY registered_at DESC").fetchall()
    conn.close()
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["tg_id","username","first_name","registered_at","balance",
                "sub_status","sub_until","trial_used","ref_by","ref_count",
                "total_spent","cashback_total","banned","last_active","lang"])
    for r in rows:
        r = dict(r)
        w.writerow([r.get(k,"") for k in
                    ["tg_id","username","first_name","registered_at","balance",
                     "sub_status","sub_until","trial_used","ref_by","ref_count",
                     "total_spent","cashback_total","banned","last_active","lang"]])
    return buf.getvalue()

def export_payments_csv() -> str:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 500").fetchall()
    conn.close()
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["id","tg_id","amount","status","created_at","confirmed_at"])
    for r in rows:
        r = dict(r); w.writerow([r.get(k,"") for k in ["id","tg_id","amount","status","created_at","confirmed_at"]])
    return buf.getvalue()

# ============================================================
#            KEYBOARDS  (полный набор)
# ============================================================
def main_kb(uid=None):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("⚡ Купить подписку",  callback_data="buy"),
        types.InlineKeyboardButton("📦 Мои подписки",    callback_data="my_subs"),
    )
    kb.add(
        types.InlineKeyboardButton("🎁 Бонусы",          callback_data="bonus"),
        types.InlineKeyboardButton("📅 Чекин",           callback_data="checkin"),
    )
    kb.add(
        types.InlineKeyboardButton("🏆 Достижения",      callback_data="achievements"),
        types.InlineKeyboardButton("📊 Серверы",         callback_data="servers"),
    )
    kb.add(
        types.InlineKeyboardButton("💳 Пополнить",       callback_data="topup"),
        types.InlineKeyboardButton("📈 Статистика",      callback_data="my_stats"),
    )
    kb.add(
        types.InlineKeyboardButton("❓ FAQ",             callback_data="faq"),
        types.InlineKeyboardButton("⭐ Отзывы",          callback_data="reviews"),
    )
    kb.add(
        types.InlineKeyboardButton("ℹ️ О сервисе",       callback_data="info"),
        types.InlineKeyboardButton("🌍 Язык",            callback_data="lang"),
    )
    kb.add(
        types.InlineKeyboardButton("📄 Политика", url=PRIVACY_URL),
        types.InlineKeyboardButton("📜 Соглашение", url=TERMS_URL),
    )
    kb.add(types.InlineKeyboardButton("💬 Поддержка", url=f"https://t.me/{SUPPORT.lstrip('@')}"))
    return kb

def back_kb(cb="back_main"):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=cb))
    return kb

def buy_kb(discount=0):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for t in TARIFFS:
        price = max(1, round(t["price"] * (100 - discount) / 100)) if discount else t["price"]
        lbl   = f"{t['emoji']} {t['name']} — {price}₽"
        if discount: lbl += f"  (−{discount}%)"
        kb.add(types.InlineKeyboardButton(lbl, callback_data=f"tariff_{t['days']}"))
    kb.add(
        types.InlineKeyboardButton("💳 Пополнить баланс", callback_data="topup"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"),
    )
    return kb

def trial_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("✅ Активировать 5 дней бесплатно", callback_data="activate_trial"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return kb

def bonus_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🎟 Промокод",   callback_data="promo"),
        types.InlineKeyboardButton("👥 Рефералы",  callback_data="invite"),
    )
    kb.add(
        types.InlineKeyboardButton("🎁 Проба",     callback_data="trial"),
        types.InlineKeyboardButton("🎰 Удача",     callback_data="wheel"),
    )
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return kb

def payment_kb(pid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{pid}"),
        types.InlineKeyboardButton("❌ Отменить",  callback_data=f"cancel_{pid}"),
    )
    return kb

def stars_kb():
    kb = types.InlineKeyboardMarkup(row_width=5)
    kb.add(*[types.InlineKeyboardButton(f"{'⭐'*i}", callback_data=f"stars_{i}") for i in range(1,6)])
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return kb

def faq_kb(page=0):
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * 4
    items = FAQ[start:start+4]
    for i, (q, _) in enumerate(items):
        kb.add(types.InlineKeyboardButton(q, callback_data=f"faq_{start+i}"))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅️", callback_data=f"faq_page_{page-1}"))
    if start + 4 < len(FAQ):
        nav.append(types.InlineKeyboardButton("➡️", callback_data=f"faq_page_{page+1}"))
    if nav: kb.row(*nav)
    kb.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_main"))
    return kb

def admin_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Статистика",    callback_data="adm_stats"),
        types.InlineKeyboardButton("👥 Пользователи",  callback_data="adm_users"),
    )
    kb.add(
        types.InlineKeyboardButton("⏳ Заявки",        callback_data="adm_payments"),
        types.InlineKeyboardButton("🎟 Промокоды",    callback_data="adm_promos"),
    )
    kb.add(
        types.InlineKeyboardButton("🔑 VPN ключи",     callback_data="adm_keys"),
        types.InlineKeyboardButton("📢 Рассылка",      callback_data="adm_broadcast"),
    )
    kb.add(
        types.InlineKeyboardButton("📋 Лог",           callback_data="adm_log"),
        types.InlineKeyboardButton("⭐ Отзывы",        callback_data="adm_reviews"),
    )
    kb.add(
        types.InlineKeyboardButton("📦 Экспорт CSV",   callback_data="adm_export"),
        types.InlineKeyboardButton("🎯 Баннеры",       callback_data="adm_banners"),
    )
    kb.add(
        types.InlineKeyboardButton("📅 Отложенная рассылка", callback_data="adm_schedcast"),
        types.InlineKeyboardButton("📈 Аналитика",     callback_data="adm_analytics"),
    )
    kb.add(types.InlineKeyboardButton("🏠 Закрыть",    callback_data="adm_close"))
    return kb


# ============================================================
#                 MAIN MENU TEXT
# ============================================================
def main_menu_text(user):
    if not user: return "🌐 **BORSH VPN**\n\nДобро пожаловать!"
    bal    = user.get("balance", 0)
    st     = user.get("sub_status", "Неактивна")
    su     = user.get("sub_until")
    dl     = days_left(su)
    name   = esc(user.get("first_name") or "Пользователь")
    streak = user.get("checkin_streak", 0)
    cb_tot = user.get("cashback_total", 0)
    icon   = "🟢" if "Активна" in st else "🔴"
    sline  = f"{icon} **{st}**"
    if "Активна" in st and dl > 0:
        sline += f"\n⏳ Осталось: **{dl} дн.**"
    banner = get_active_banner()
    b_line = f"\n\n💡 *{banner['title']}*: {banner['text']}" if banner else ""
    return (
        "🌐 **BORSH VPN** v3.0 — Свобода в сети\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 Привет, **{name}**!\n\n"
        f"📋 Подписка: {sline}\n"
        f"💰 Баланс: **{bal}₽**  |  🔥 Серия: **{streak} дн.**\n"
        f"💵 Кэшбэк получено: **{cb_tot}₽**"
        + b_line +
        "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Выберите раздел:"
    )


# ============================================================
#               MIDDLEWARE: БЛОКИРОВКА + АНТИСПАМ
# ============================================================
class BanMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_types    = ['message', 'callback_query']
        self.update_sensitive = False

    def pre_process(self, message, data):
        user = getattr(message, 'from_user', None)
        if user is None: return
        uid = user.id
        if is_admin(uid): return

        # Проверка бана
        now = time.time()
        hit = _ban_cache.get(uid)
        if hit and now - hit[1] < 20:
            banned = hit[0]
        else:
            u = get_user(uid)
            banned = bool(u and u.get("banned"))
            _ban_cache[uid] = (banned, now)

        if banned:
            if isinstance(message, types.CallbackQuery):
                try: bot.answer_callback_query(message.id, "🚫 Аккаунт заблокирован", show_alert=True)
                except: pass
            else:
                try: bot.reply_to(message, f"🚫 Ваш аккаунт заблокирован.\nПоддержка: {SUPPORT}")
                except: pass
            return CancelUpdate()

        # Антиспам (только для text-message, не callback)
        if not isinstance(message, types.CallbackQuery):
            if not check_rate_limit(uid):
                try: bot.reply_to(message, "⚠️ Слишком много сообщений. Подождите немного.")
                except: pass
                return CancelUpdate()

    def post_process(self, message, data, exception): pass

try:
    bot.setup_middleware(BanMiddleware())
    print("[✓] Middleware (бан + антиспам) подключён")
except Exception as e:
    print(f"[!] Middleware: {e}")

def is_banned(uid):
    if is_admin(uid): return False
    try:
        u = get_user(uid)
        return bool(u and u.get("banned"))
    except: return False


# ============================================================
#               ФОНОВЫЕ ЗАДАЧИ
# ============================================================
def background_worker():
    tasks = (update_expired_subscriptions, expire_stale_payments, send_expiry_notifications,
             run_scheduled_broadcasts, rotate_server_loads)
    while True:
        for task in tasks:
            try:
                task()
            except Exception as e:
                print(f"[worker] {task.__name__}: {e}")
        time.sleep(600)   # каждые 10 минут

def rotate_server_loads():
    """Слегка рандомизировать нагрузку серверов для реалистичности."""
    for s in SERVERS:
        delta = random.randint(-5, 5)
        s["load"] = max(10, min(95, s["load"] + delta))
        # Синхронизируем load в БД для ключей
    conn = get_conn()
    rows = conn.execute("SELECT id, label, load_pct FROM vpn_keys WHERE active=1").fetchall()
    for r in rows:
        nl = max(5, min(95, (r["load_pct"] or 0) + random.randint(-3, 3)))
        conn.execute("UPDATE vpn_keys SET load_pct=? WHERE id=?", (nl, r["id"]))
    conn.commit(); conn.close()

def send_expiry_notifications():
    conn = get_conn(); now = datetime.datetime.now()
    for days in NOTIFY_DAYS_BEFORE:
        field = f"notified_{days}"
        target = (now + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            f"SELECT * FROM subscriptions WHERE status='Активна' AND {field}=0 "
            f"AND substr(expires_at,1,10)=?", (target,)
        ).fetchall()
        for r in rows:
            r = dict(r)
            try:
                bot.send_message(r["tg_id"],
                    f"⚠️ **Подписка заканчивается!**\n\n"
                    f"📋 Тариф: **{r['tariff_name']}**\n"
                    f"📆 До: **{fmt_dt(r['expires_at'])}**\n"
                    f"⏳ Осталось: **{days} дн.**\n\n"
                    "Продлите, чтобы не потерять доступ 👇",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("⚡ Продлить", callback_data="buy")))
                conn.execute(f"UPDATE subscriptions SET {field}=1 WHERE id=?", (r["id"],))
                conn.commit()
            except: pass
    conn.close()

def run_scheduled_broadcasts():
    broadcasts = get_pending_broadcasts()
    if not broadcasts: return
    users = get_all_users()
    for br in broadcasts:
        for uid in users:
            try:    bot.send_message(uid, br["text"]); time.sleep(0.04)
            except: pass
        mark_broadcast_sent(br["id"])
        try:
            bot.send_message(br["created_by"],
                             f"✅ Отложенная рассылка #{br['id']} отправлена")
        except: pass

def payment_timeout(user_id, pid):
    time.sleep(PAYMENT_TIMEOUT_MIN * 60)
    p = get_payment(pid)
    if p and p["status"] == "pending":
        set_payment_status(pid, "expired")
        try:
            bot.send_message(user_id,
                             f"⏰ **Заявка #{pid} отменена**\n\n"
                             f"Прошло {PAYMENT_TIMEOUT_MIN} мин — оплата не поступила.\n"
                             "Создайте новую заявку.")
        except: pass

def notify_achievements(uid, new_achs):
    if not new_achs: return
    text = "🏆 **Новые достижения разблокированы!**\n\n"
    for name, reward, emoji in new_achs:
        text += f"{emoji} **{name}**\n💰 Награда: +{reward}₽\n\n"
    try: bot.send_message(uid, text)
    except: pass


# ============================================================
#       ХЕНДЛЕР /start  — регистрируется ПЕРВЫМ
# ============================================================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid  = message.from_user.id
    if is_banned(uid): return
    args   = message.text.split()
    ref_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    is_new = add_user(uid, message.from_user.username, message.from_user.first_name, ref_by=ref_by)
    user_states.pop(uid, None); user_context.pop(uid, None)
    log_action(uid, "start", f"ref={ref_by}")
    touch_user(uid)
    if is_new and ref_by and ref_by != uid:
        try: bot.send_message(uid, f"🎉 Реферальный бонус: **+{REFERRAL_BONUS_NEW}₽** зачислено!")
        except: pass
        try:
            inv = get_user(ref_by)
            iname = inv.get("first_name","") if inv else ""
            bot.send_message(ref_by, f"👥 По вашей ссылке пришёл новый пользователь!\n"
                                     f"💰 Бонус **+{REFERRAL_BONUS}₽** зачислен.")
        except: pass
    user       = get_user(uid)
    caption    = main_menu_text(user)
    photo_path = get_start_photo()
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as ph:
                bot.send_photo(message.chat.id, ph, caption=caption, reply_markup=main_kb(uid))
            return
        except Exception as e: print(f"[start] photo: {e}")
    bot.send_message(message.chat.id, caption, reply_markup=main_kb(uid), disable_web_page_preview=True)


@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    user_states.pop(message.from_user.id, None)
    user_context.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "✅ Действие отменено.", reply_markup=main_kb())


# ============================================================
#            INLINE-РЕЖИМ (быстрый статус)
# ============================================================
@bot.inline_handler(lambda q: True)
def inline_query(query):
    uid  = query.from_user.id
    user = get_user(uid)
    if not user:
        results = [types.InlineQueryResultArticle(
            id="1", title="Не зарегистрирован",
            input_message_content=types.InputTextMessageContent(
                "Нажми /start в боте чтобы зарегистрироваться"),
            description="Напишите боту /start"
        )]
    else:
        bal  = user.get("balance", 0)
        st   = user.get("sub_status", "Неактивна")
        dl   = days_left(user.get("sub_until"))
        icon = "🟢" if "Активна" in st else "🔴"
        text = (f"🌐 *BORSH VPN* — мой статус\n"
                f"{icon} Подписка: *{st}*\n"
                + (f"⏳ Осталось: *{dl} дн.*\n" if dl else "")
                + f"💰 Баланс: *{bal}₽*")
        results = [types.InlineQueryResultArticle(
            id="1", title=f"{icon} {st}",
            description=f"Баланс: {bal}₽  |  Осталось: {dl} дн.",
            input_message_content=types.InputTextMessageContent(text, parse_mode="Markdown")
        )]
    try: bot.answer_inline_query(query.id, results, cache_time=10)
    except: pass


# ============================================================
#             CALLBACKS — навигация
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def cb_back_main(call):
    update_expired_subscriptions()
    uid = call.from_user.id
    user_states.pop(uid, None); user_context.pop(uid, None)
    touch_user(uid)
    safe_edit(call, main_menu_text(get_user(uid)), main_kb(uid))
    safe_ans(call)


# ============================================================
#             ПОКУПКА ПОДПИСКИ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def cb_buy(call):
    uid      = call.from_user.id
    user     = get_user(uid)
    balance  = user["balance"] if user else 0
    discount = user_context.get(uid, {}).get("discount", 0)
    disc_line = f"\n🎟 Скидка по промокоду: **−{discount}%**" if discount else ""
    safe_edit(call,
              "⚡ **Купить подписку**\n"
              "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
              f"💰 Баланс: **{balance}₽**{disc_line}\n\n"
              f"💵 Кэшбэк {CASHBACK_PERCENT}% с каждой покупки!\n\n"
              "📌 Выберите тариф:", buy_kb(discount))
    safe_ans(call)


@bot.callback_query_handler(func=lambda c: c.data.startswith("tariff_"))
def cb_tariff(call):
    uid  = call.from_user.id
    try:    days = int(call.data.replace("tariff_", ""))
    except ValueError: return safe_ans(call, "Тариф не найден", True)
    t    = next((x for x in TARIFFS if x["days"] == days), None)
    if not t: return safe_ans(call, "Тариф не найден", True)
    user     = get_user(uid)
    balance  = user["balance"] if user else 0
    discount = user_context.get(uid, {}).get("discount", 0)
    price    = max(1, round(t["price"] * (100 - discount) / 100)) if discount else t["price"]

    if balance < price:
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("💳 Пополнить", callback_data="topup"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="buy"))
        safe_edit(call,
                  "❌ **Недостаточно средств**\n\n"
                  f"💠 Тариф: **{t['name']}**  💰 Цена: **{price}₽**\n"
                  f"💳 Баланс: **{balance}₽**   ❗ Не хватает: **{price-balance}₽**", kb)
        return safe_ans(call, f"Нужно ещё {price-balance}₽", True)

    if not deduct_balance(uid, price): return safe_ans(call, "❌ Ошибка списания", True)

    vpn_key    = get_best_key()
    expire_iso = activate_subscription(uid, t["days"])
    add_subscription_record(uid, t["name"], t["days"], price, vpn_key, expire_iso)
    cb         = give_cashback(uid, price)
    log_action(uid, "buy_sub", f"{t['name']} {price}₽")

    user_context.get(uid, {}).pop("discount", None)

    # Проверяем достижения
    new_achs = check_achievements(uid)
    threading.Thread(target=notify_achievements, args=(uid, new_achs), daemon=True).start()

    new_user    = get_user(uid)
    new_balance = new_user["balance"] if new_user else 0
    cb_line = f"\n💵 Кэшбэк: **+{cb}₽** на баланс!" if cb else ""

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📱 Как подключиться",  callback_data="howto"))
    kb.add(types.InlineKeyboardButton("🌐 Сайт BORSH VPN",    url=SITE_URL))
    kb.add(types.InlineKeyboardButton("⬅️ В главное меню",    callback_data="back_main"))

    safe_edit(call,
              "✅ **Подписка активирована!**\n"
              "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
              f"{t['emoji']} Тариф: **{t['name']}**\n"
              f"📅 Дней: **{t['days']}**  |  📆 До: **{fmt_dt(expire_iso)}**\n"
              f"💸 Списано: **{price}₽**  |  Остаток: **{new_balance}₽**"
              + cb_line +
              "\n\n🔑 **Ваш VPN-ключ:**\n"
              f"`{vpn_key}`\n\n"
              "📱 Вставьте ключ в **Happ** / **V2RayNG** / **Streisand**", kb)
    safe_ans(call, "✅ Готово!")


# ============================================================
#             МОИ ПОДПИСКИ / HOWTO
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "my_subs")
def cb_my_subs(call):
    update_expired_subscriptions()
    subs = get_user_subscriptions(call.from_user.id)
    if not subs:
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("⚡ Купить подписку", callback_data="buy"))
        kb.add(types.InlineKeyboardButton("🎁 Пробный период",  callback_data="trial"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад",           callback_data="back_main"))
        return safe_edit(call,
                         "📦 **Мои подписки**\n\nПодписок ещё нет.\n\n"
                         "👇 Оформите — **5 дней бесплатно!**", kb)
    text = "📦 **Мои подписки**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for s in subs[:8]:
        icon  = "🟢" if s["status"] == "Активна" else "🔴"
        dl    = days_left(s["expires_at"])
        key   = s["vpn_key"] or "—"
        text += (f"{icon} **{s['tariff_name']}** | {s['status']}\n"
                 f"  🆔 `#{s['id']}`  📅 {fmt_dt(s['activated_at'])}\n"
                 f"  ⏰ до **{fmt_dt(s['expires_at'])}**"
                 + (f" (**{dl} дн.**)" if s["status"]=="Активна" and dl else "")
                 + f"\n  💸 {s['price']}₽\n  🔑 `{key}`\n  ─────────────────────\n")
    if len(subs) > 8: text += f"\n_Показано 8 из {len(subs)}_"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("⚡ Купить ещё",    callback_data="buy"),
           types.InlineKeyboardButton("📱 Как подключить", callback_data="howto"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    safe_edit(call, text, kb); safe_ans(call)


@bot.callback_query_handler(func=lambda c: c.data == "howto")
def cb_howto(call):
    text = (
        "📱 **Как подключиться к BORSH VPN**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Приложения:**\n"
        "• **Happ** — iOS & Android _(рекомендуем)_\n"
        "• **V2RayNG** — Android\n"
        "• **Streisand** — iOS\n"
        "• **NekoBox** — Android (альтернатива)\n"
        "• **Shadowrocket** — iOS (платный)\n\n"
        "**Подключение:**\n"
        "1. Скопируй ключ из «📦 Мои подписки»\n"
        "2. Открой приложение → «Добавить» → «Импорт по ссылке»\n"
        "3. Вставь ключ → выбери сервер → подключись\n\n"
        "**Не работает?**\n"
        "• Попробуй другой протокол в настройках\n"
        "• Проверь, не заблокирован ли VPN оператором\n"
        f"• Напиши в поддержку: {SUPPORT}"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("📦 Мои подписки",  callback_data="my_subs"),
           types.InlineKeyboardButton("❓ FAQ",            callback_data="faq"))
    kb.add(types.InlineKeyboardButton("💬 Поддержка", url=f"https://t.me/{SUPPORT.lstrip('@')}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    safe_edit(call, text, kb); safe_ans(call)


# ============================================================
#           📅 ЕЖЕДНЕВНЫЙ ЧЕКИН
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "checkin")
def cb_checkin(call):
    uid = call.from_user.id
    ok, reward, streak = do_checkin(uid)
    new_achs = check_achievements(uid)
    threading.Thread(target=notify_achievements, args=(uid, new_achs), daemon=True).start()
    if not ok:
        user   = get_user(uid)
        streak = user.get("checkin_streak", 0) if user else 0
        safe_edit(call,
                  "📅 **Ежедневный чекин**\n\n"
                  "✅ Вы уже получили бонус сегодня!\n\n"
                  f"🔥 Текущая серия: **{streak} дн.**\n"
                  f"💰 Следующий бонус: **+{CHECKIN_REWARD + (streak//7)*5}₽** (завтра)",
                  back_kb())
    else:
        next_bonus = CHECKIN_REWARD + (streak // 7) * 5
        safe_edit(call,
                  "📅 **Ежедневный бонус получен!**\n"
                  "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                  f"💰 Начислено: **+{reward}₽**\n"
                  f"🔥 Серия: **{streak} дн.**\n\n"
                  + ("🎉 **Недельная серия!** +5₽ к бонусу\n\n" if streak % 7 == 0 and streak > 0 else "")
                  + f"💡 Завтра: **+{next_bonus}₽**\n"
                  f"_Заходите каждый день — серия увеличивает награду!_",
                  back_kb())
    safe_ans(call)


# ============================================================
#           🏆 ДОСТИЖЕНИЯ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "achievements")
def cb_achievements(call):
    uid   = call.from_user.id
    done  = get_user_achievements(uid)
    user  = get_user(uid)
    subs  = len(get_user_subscriptions(uid))
    spent = user.get("total_spent", 0) if user else 0
    refs  = user.get("ref_count", 0) if user else 0

    text = "🏆 **Достижения**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for ach in ACHIEVEMENTS:
        aid, name, desc, ctype, thr, reward, emoji = ach
        unlocked = aid in done
        icon     = "✅" if unlocked else "🔒"
        val      = {"subs": subs, "spent": spent, "refs": refs}.get(ctype, 0)
        prog     = f" {min(val,thr)}/{thr}" if not unlocked and ctype in ("subs","spent","refs") else ""
        text    += f"{icon} {emoji} **{name}**{prog}\n_{desc}_\n"
        if not unlocked: text += f"   💰 Награда: **+{reward}₽**\n"
        text    += "\n"

    unlocked_count = len(done)
    text += f"━━━━━━━━━━━━━━━━━━━━━━━\n🏅 Разблокировано: **{unlocked_count}/{len(ACHIEVEMENTS)}**"
    safe_edit(call, text, back_kb()); safe_ans(call)


# ============================================================
#           🎰 КОЛЕСО УДАЧИ
# ============================================================
WHEEL_PRIZES = [
    ("💰 +10₽ на баланс",   "balance", 10,  30),
    ("💰 +25₽ на баланс",   "balance", 25,  20),
    ("💰 +50₽ на баланс",   "balance", 50,  10),
    ("💰 +100₽ на баланс",  "balance", 100,  5),
    ("🎟 Скидка 10%",       "discount",10,  15),
    ("🎟 Скидка 20%",       "discount",20,   8),
    ("📅 +1 день к подписке","days",    1,  20),
    ("📅 +3 дня к подписке", "days",    3,   8),
    ("😔 В этот раз не повезло","none",  0,  40),
]

@bot.callback_query_handler(func=lambda c: c.data == "wheel")
def cb_wheel(call):
    uid  = call.from_user.id
    user = get_user(uid)
    if not user: return safe_ans(call)

    # Можно крутить 1 раз в 24 часа
    wlast = user.get("wheel_last")
    today = datetime.date.today().isoformat()
    if wlast == today:
        safe_edit(call,
                  "🎰 **Колесо удачи**\n\n"
                  "⏰ Вы уже крутили колесо сегодня!\n\n"
                  "Возвращайтесь завтра за новым шансом 🍀",
                  back_kb("bonus"))
        return safe_ans(call)

    # Взвешенный случайный выбор
    total = sum(p[3] for p in WHEEL_PRIZES)
    rnd   = random.uniform(0, total)
    cur   = 0
    prize = WHEEL_PRIZES[-1]
    for p in WHEEL_PRIZES:
        cur += p[3]
        if rnd <= cur: prize = p; break

    label, ptype, value, _ = prize
    # Атомарно «занимаем» сегодняшнюю попытку — двойной клик не даст два приза
    conn = get_conn()
    cur  = conn.execute("UPDATE users SET wheel_last=? WHERE tg_id=? "
                        "AND (wheel_last IS NULL OR wheel_last<>?)", (today, uid, today))
    claimed = cur.rowcount > 0
    conn.commit(); conn.close()
    if not claimed: return safe_ans(call, "⏰ Вы уже крутили колесо сегодня", True)
    log_action(uid, "wheel_spin", f"{label}")

    result_text = ""
    if ptype == "balance" and value > 0:
        add_balance(uid, value)
        result_text = f"💰 **+{value}₽** зачислено на баланс!"
        log_action(uid, "wheel_win", f"+{value}₽")
    elif ptype == "discount":
        user_context.setdefault(uid, {})["discount"] = value
        result_text = f"🎟 Скидка **{value}%** на следующую покупку!"
        log_action(uid, "wheel_win", f"-{value}%")
    elif ptype == "days":
        exp = activate_subscription(uid, value)
        add_subscription_record(uid, f"Колесо удачи (+{value}д.)", value, 0, None, exp)
        result_text = f"📅 **+{value} дн.** добавлено к подписке!"
        log_action(uid, "wheel_win", f"+{value}дн")
    else:
        result_text = "😔 В этот раз не повезло. Попробуйте завтра!"

    new_achs = check_achievements(uid)
    threading.Thread(target=notify_achievements, args=(uid, new_achs), daemon=True).start()

    # Анимация колеса (символьная)
    animation_line = "🎰 " + " ".join(
        [random.choice(["🍒","🍋","💎","🔥","⭐","🎯"]) for _ in range(3)]
    )
    safe_edit(call,
              "🎰 **Колесо удачи крутится...**\n\n"
              f"{animation_line}\n\n"
              f"**Результат:** {label}\n\n"
              f"{result_text}\n\n"
              "⏰ Следующий шанс — завтра!",
              back_kb("bonus"))
    safe_ans(call, "🎰 Удачи!")


# ============================================================
#           📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "my_stats")
def cb_my_stats(call):
    uid   = call.from_user.id
    user  = get_user(uid)
    if not user: return safe_ans(call)
    subs  = get_user_subscriptions(uid)
    done  = get_user_achievements(uid)
    spent = user.get("total_spent", 0)

    if spent >= 5000:   level = "👑 VIP"
    elif spent >= 2000: level = "💎 Premium"
    elif spent >= 500:  level = "🔥 Pro"
    else:               level = "🌱 Новичок"

    text = (
        "📈 **Моя статистика**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: `{uid}`\n"
        f"🏆 Уровень: **{level}**\n\n"
        f"📅 Регистрация: {fmt_dt(user.get('registered_at'))}\n"
        f"🕐 Последний вход: {fmt_dt(user.get('last_active'), '%d.%m.%Y %H:%M')}\n\n"
        f"📦 Подписок: **{len(subs)}** (акт.: **{len([s for s in subs if s['status']=='Активна'])}**)\n"
        f"💸 Потрачено: **{spent}₽**\n"
        f"💵 Кэшбэк получено: **{user.get('cashback_total',0)}₽**\n"
        f"💰 Баланс: **{user.get('balance',0)}₽**\n\n"
        f"👥 Рефералов: **{user.get('ref_count',0)}**\n"
        f"🔥 Серия чекинов: **{user.get('checkin_streak',0)} дн.**\n"
        f"📅 Всего чекинов: **{user.get('total_checkins',0)}**\n"
        f"🏅 Достижений: **{len(done)}/{len(ACHIEVEMENTS)}**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🏆 Достижения", callback_data="achievements"),
           types.InlineKeyboardButton("⬅️ Назад",      callback_data="back_main"))
    safe_edit(call, text, kb); safe_ans(call)


# ============================================================
#           🎁 БОНУСЫ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "bonus")
def cb_bonus(call):
    safe_edit(call,
              "🎁 **Бонусная программа**\n"
              "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
              f"👥 **Рефералы:** +{REFERRAL_BONUS}₽ за каждого друга\n"
              f"🎟 **Промокоды:** скидки, дни, деньги\n"
              f"🎰 **Колесо удачи:** 1 раз в день\n"
              f"📅 **Чекин:** +{CHECKIN_REWARD}₽ каждый день\n"
              f"💵 **Кэшбэк:** {CASHBACK_PERCENT}% с каждой покупки\n\n"
              "Выберите раздел 👇", bonus_kb())
    safe_ans(call)


@bot.callback_query_handler(func=lambda c: c.data == "promo")
def cb_promo(call):
    user_states[call.from_user.id] = "waiting_promo"
    safe_edit(call, "🎟 **Ввод промокода**\n\n✏️ Введите промокод:", back_kb("bonus"))
    safe_ans(call)


@bot.callback_query_handler(func=lambda c: c.data == "invite")
def cb_invite(call):
    uid          = call.from_user.id
    bot_username = bot.get_me().username
    link         = f"https://t.me/{bot_username}?start={uid}"
    user         = get_user(uid)
    rc           = user.get("ref_count", 0) if user else 0
    text = (
        "👥 **Реферальная программа**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 **Ваша ссылка:**\n`{link}`\n\n"
        f"💰 Вам за каждого друга: **+{REFERRAL_BONUS}₽**\n"
        f"🎁 Другу при регистрации: **+{REFERRAL_BONUS_NEW}₽**\n\n"
        f"👥 Приглашено: **{rc}** чел.  |  Заработано: **{rc * REFERRAL_BONUS}₽**\n\n"
        "📌 _Бонус начисляется автоматически при первом /start друга_"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📤 Поделиться ссылкой",
                                      url=f"https://t.me/share/url?url={link}&text=BORSH+VPN+—+быстрый+VPN!"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="bonus"))
    safe_edit(call, text, kb); safe_ans(call)


# ============================================================
#           ℹ️ ИНФОРМАЦИЯ / СЕРВЕРЫ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "info")
def cb_info(call):
    text = (
        "ℹ️ **О BORSH VPN**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Надёжный высокоскоростной VPN без ограничений.\n\n"
        "✅ **Преимущества:**\n"
        "• Безлимитный трафик 🚀\n"
        "• 10 серверов в 10 странах 🌍\n"
        "• VLESS / VMess / Trojan 🔐\n"
        "• Happ, V2RayNG, Streisand, NekoBox 📱\n"
        "• Нет логов 🕵️\n"
        "• Поддержка 24/7 💬\n"
        f"• Кэшбэк {CASHBACK_PERCENT}% с покупок 💵\n"
        "• Ежедневные бонусы 📅\n"
        "• Реферальная программа 👥\n\n"
        "📦 **Тарифы:**\n"
    )
    for t in TARIFFS: text += f"  {t['emoji']} {t['name']} — {t['price']}₽\n"
    text += (
        f"\n📄 [Политика конфиденциальности]({PRIVACY_URL})\n"
        f"📜 [Пользовательское соглашение]({TERMS_URL})\n\n"
        f"💬 Поддержка: {SUPPORT}\n👨‍💻 Разработчик: {DEV}"
    )
    safe_edit(call, text, back_kb()); safe_ans(call)


@bot.callback_query_handler(func=lambda c: c.data == "servers")
def cb_servers(call):
    text = "📊 **Статус серверов**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for s in SERVERS:
        load  = s["load"]
        icon  = "🟢" if load < 70 else ("🟡" if load < 90 else "🔴")
        text += f"{s['country']} **{s['name']}**  ({s['code']})\n"
        text += f"   {icon} {s['ping']} ms  [{load_bar(load)}] {load}%\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━\n🟢 < 70%  🟡 70–89%  🔴 ≥ 90%"
    safe_edit(call, text, back_kb()); safe_ans(call)


# ============================================================
#           🌍 ЯЗЫК
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "lang")
def cb_lang(call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
           types.InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    safe_edit(call, "🌍 **Выберите язык / Choose language:**", kb); safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_lang_"))
def cb_set_lang(call):
    lang = call.data.replace("set_lang_", "")
    set_user_lang(call.from_user.id, lang)
    name = "Русский 🇷🇺" if lang == "ru" else "English 🇬🇧"
    safe_edit(call, f"✅ Язык изменён на **{name}**", back_kb()); safe_ans(call)


# ============================================================
#           ⭐ ОТЗЫВЫ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "reviews")
def cb_reviews(call):
    stats, avg, total = get_rating_stats()
    revs = get_reviews(5)
    text = (
        "⭐ **Отзывы пользователей**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Средняя оценка: **{avg:.1f} / 5.0** ({total} отзывов)\n\n"
    )
    for i in range(5, 0, -1):
        cnt = stats.get(i, 0)
        bar = load_bar(cnt * 100 // (total or 1), 8)
        text += f"{'⭐'*i} {bar} {cnt}\n"
    text += "\n**Последние отзывы:**\n\n"
    for r in revs:
        name = f"Пользователь {r['tg_id']}"
        try:
            u = get_user(r["tg_id"])
            if u: name = u.get("first_name") or name
        except: pass
        text += f"{'⭐'*r['stars']} **{name}**\n_{r['text'][:100]}_\n\n"

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("✍️ Написать отзыв", callback_data="write_review"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад",          callback_data="back_main"))
    safe_edit(call, text, kb); safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data == "write_review")
def cb_write_review(call):
    uid  = call.from_user.id
    user = get_user(uid)
    if user and user.get("rating_given"):
        return safe_ans(call, "Вы уже оставляли отзыв!", True)
    subs = get_user_subscriptions(uid)
    if not subs:
        return safe_ans(call, "Сначала оформите подписку", True)
    safe_edit(call, "⭐ **Оцените сервис**\n\nВыберите оценку от 1 до 5:", stars_kb())
    safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("stars_"))
def cb_stars(call):
    uid   = call.from_user.id
    stars = int(call.data.replace("stars_", ""))
    user_states[uid] = "waiting_review_text"
    user_context.setdefault(uid, {})["review_stars"] = stars
    safe_edit(call,
              f"{'⭐'*stars} **{stars}/5** — отличный выбор!\n\n"
              "✏️ Теперь напишите небольшой отзыв (1–300 символов):",
              back_kb("reviews"))
    safe_ans(call)


# ============================================================
#           ❓ FAQ
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "faq")
def cb_faq(call):
    safe_edit(call,
              "❓ **Часто задаваемые вопросы**\n\n"
              "Выберите вопрос 👇", faq_kb(0)); safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("faq_page_"))
def cb_faq_page(call):
    page = int(call.data.replace("faq_page_", ""))
    safe_edit(call,
              "❓ **Часто задаваемые вопросы**\n\n"
              "Выберите вопрос 👇", faq_kb(page)); safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("faq_") and not c.data.startswith("faq_page_"))
def cb_faq_answer(call):
    idx = int(call.data.replace("faq_", ""))
    if idx >= len(FAQ): return safe_ans(call)
    q, a = FAQ[idx]
    kb   = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("⬅️ Назад к FAQ", callback_data="faq"))
    safe_edit(call, f"❓ **{q}**\n\n{a}", kb); safe_ans(call)


# ============================================================
#           ПРОБНЫЙ ПЕРИОД
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "trial")
def cb_trial(call):
    user = get_user(call.from_user.id)
    if user and user.get("trial_used"):
        return safe_ans(call, "Пробная подписка уже использована", True)
    safe_edit(call,
              "🎁 **Пробный период — 5 дней бесплатно!**\n"
              "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
              "✅ Полный доступ ко всем серверам\n"
              "✅ Безлимитный трафик\n"
              "✅ Только 1 раз на аккаунт\n\n"
              "👇 Нажмите для активации:", trial_kb()); safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data == "activate_trial")
def cb_activate_trial(call):
    uid  = call.from_user.id
    user = get_user(uid)
    if user and user.get("trial_used"):
        return safe_ans(call, "Уже использовано!", True)
    set_trial_used(uid)
    exp = (datetime.datetime.now() + datetime.timedelta(days=5)).isoformat()
    add_subscription_record(uid, "Пробная (5 дней)", 5, 0, None, exp)
    log_action(uid, "trial_activated")
    new_achs = check_achievements(uid)
    threading.Thread(target=notify_achievements, args=(uid, new_achs), daemon=True).start()
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📱 Как подключиться", callback_data="howto"))
    kb.add(types.InlineKeyboardButton("🌐 Перейти на сайт",  url=TRIAL_URL))
    kb.add(types.InlineKeyboardButton("⬅️ В главное меню",   callback_data="back_main"))
    safe_edit(call,
              "✅ **Пробная подписка активирована!**\n\n"
              f"🎁 5 дней бесплатно!\n"
              f"📆 До: **{fmt_dt(exp)}**\n\n"
              "1. Скачай Happ или V2RayNG\n"
              "2. Зарегистрируйся на сайте\n"
              "3. Получи ключ → подключись", kb)
    safe_ans(call, "✅ Активировано!")


# ============================================================
#           ПОПОЛНЕНИЕ БАЛАНСА
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "topup")
def cb_topup(call):
    uid  = call.from_user.id
    bal  = (get_user(uid) or {}).get("balance", 0)
    user_states[uid] = "waiting_topup_amount"
    safe_edit(call,
              "💳 **Пополнение баланса**\n\n"
              f"💰 Текущий: **{bal}₽**\n\n"
              f"✏️ Введите сумму ({MIN_TOPUP}–{MAX_TOPUP}₽):",
              back_kb()); safe_ans(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_"))
def cb_paid(call):
    try:    pid = int(call.data.replace("paid_", ""))
    except ValueError: return safe_ans(call, "❌ Ошибка", True)
    payment = get_payment(pid)
    if not payment:                              return safe_ans(call, "❌ Не найдена", True)
    if payment["tg_id"] != call.from_user.id:    return safe_ans(call, "🚫 Это не ваша заявка", True)
    if payment["status"] != "pending":           return safe_ans(call, "⚠️ Уже обработана", True)
    elapsed = (datetime.datetime.now()
               - datetime.datetime.fromisoformat(payment["created_at"])
               ).total_seconds() / 60
    if elapsed > PAYMENT_TIMEOUT_MIN:
        claim_payment(pid, ("pending",), "expired")
        return safe_ans(call, "⏰ Время истекло", True)
    # pending → review: таймер больше не отменит заявку, а повторный клик не продублирует
    # уведомление админам (раньше заявка «протухала» даже после нажатия «Я оплатил»).
    if not claim_payment(pid, ("pending",), "review"):
        return safe_ans(call, "⚠️ Уже отправлена", True)
    user  = get_user(payment["tg_id"]) or {}
    uname = f"@{esc(user['username'])}" if user.get("username") else str(payment["tg_id"])
    for aid in ADMIN_IDS:
        try:
            bot.send_message(aid,
                             "🔔 **ЗАЯВКА НА ПОПОЛНЕНИЕ**\n\n"
                             f"🆔 `#{pid}`  💰 **{payment['amount']}₽**\n"
                             f"👤 {esc(user.get('first_name') or '—')} ({uname})\n"
                             f"🕐 {payment['created_at'][:19]}\n\n"
                             f"✅ `/pay {pid}`   ❌ `/reject {pid}`")
        except Exception as e:
            print(f"[paid] не удалось уведомить админа {aid}: {e}")
    log_action(payment["tg_id"], "paid_clicked", f"pid={pid}")
    safe_edit(call,
              f"✅ **Заявка #{pid} отправлена!**\n\n"
              f"💰 Сумма: **{payment['amount']}₽**\n\n"
              "⏳ Ожидайте подтверждения (5–15 мин).", back_kb())
    safe_ans(call, "✅ Отправлено!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_"))
def cb_cancel(call):
    try:    pid = int(call.data.replace("cancel_", ""))
    except ValueError: return safe_ans(call, "❌ Ошибка", True)
    p = get_payment(pid)
    if p and p["tg_id"] == call.from_user.id:
        claim_payment(pid, ("pending",), "cancelled")
    user_states.pop(call.from_user.id, None)
    safe_edit(call, main_menu_text(get_user(call.from_user.id)), main_kb(call.from_user.id))
    safe_ans(call, "Отменено")

# ============================================================
#       ОБРАБОТКА ВВОДА (по состояниям)
# ============================================================
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_topup_amount")
def handle_topup_amount(message):
    uid = message.from_user.id
    if is_banned(uid): return
    try:    amount = int(message.text.strip())
    except: return bot.reply_to(message, f"❌ Введите число от {MIN_TOPUP} до {MAX_TOPUP}")
    if not (MIN_TOPUP <= amount <= MAX_TOPUP):
        return bot.reply_to(message, f"❌ Сумма: {MIN_TOPUP}₽–{MAX_TOPUP}₽")
    user_states.pop(uid, None)
    pid = create_payment(uid, amount)
    log_action(uid, "topup_create", f"amount={amount} pid={pid}")
    bot.send_message(message.chat.id,
                     f"💳 **Заявка #{pid}**\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     f"💰 Сумма: **{amount}₽**\n\n"
                     "📲 Переведите на карту:\n"
                     f"`{CARD_NUMBER}`\n"
                     f"👤 **{CARD_HOLDER}**\n\n"
                     f"📝 Комментарий к переводу: `#{pid}`\n\n"
                     f"⏰ **{PAYMENT_TIMEOUT_MIN} минут** на оплату.\n\n"
                     "После перевода нажмите «✅ Я оплатил»",
                     reply_markup=payment_kb(pid))
    threading.Thread(target=payment_timeout, args=(uid, pid), daemon=True).start()


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_promo")
def handle_promo_input(message):
    uid = message.from_user.id
    if is_banned(uid): return
    code = (message.text or "").strip().upper()
    user_states.pop(uid, None)
    promo, msg = use_promo(code, uid)
    if not promo: return bot.reply_to(message, msg)
    ptype, value = promo["type"], promo["value"]
    if ptype == "balance":
        add_balance(uid, value)
        log_action(uid, "promo_used", f"{code} +{value}₽")
        bot.reply_to(message, f"✅ Промокод активирован!\n💰 **+{value}₽** на баланс!")
    elif ptype == "days":
        exp = activate_subscription(uid, value)
        add_subscription_record(uid, f"Промокод ({value}дн.)", value, 0, None, exp)
        log_action(uid, "promo_used", f"{code} +{value}дн")
        bot.reply_to(message, f"✅ Промокод активирован!\n🎁 Добавлено **{value} дней**!\n📆 До: **{fmt_dt(exp)}**")
    elif ptype == "discount":
        user_context.setdefault(uid, {})["discount"] = value
        log_action(uid, "promo_used", f"{code} -{value}%")
        bot.reply_to(message, f"✅ Промокод активирован!\n🎟 Скидка **{value}%** на следующую покупку!")
    new_achs = check_achievements(uid)
    threading.Thread(target=notify_achievements, args=(uid, new_achs), daemon=True).start()


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "waiting_review_text")
def handle_review_text(message):
    uid  = message.from_user.id
    if is_banned(uid): return
    text = (message.text or "").strip()[:300]
    if not text: return bot.reply_to(message, "❌ Напишите текст отзыва")
    stars = user_context.get(uid, {}).pop("review_stars", 5)
    user_states.pop(uid, None)
    add_review(uid, stars, text)
    log_action(uid, "review_done", f"{stars}⭐")
    new_achs = check_achievements(uid)
    threading.Thread(target=notify_achievements, args=(uid, new_achs), daemon=True).start()
    # Уведомление в админку
    user = get_user(uid)
    uname = f"@{esc(user['username'])}" if user and user.get("username") else str(uid)
    for aid in ADMIN_IDS:
        try:
            bot.send_message(aid,
                             f"⭐ **Новый отзыв!**\n\n"
                             f"👤 {esc(user.get('first_name') or '—')} ({uname})\n"
                             f"{'⭐'*stars}\n\n_{esc(text)}_")
        except: pass
    bot.reply_to(message, f"✅ Отзыв принят! {'⭐'*stars}\nСпасибо за обратную связь!")


# --- Admin broadcast input
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "admin_broadcast"
                                   and is_admin(m.from_user.id))
def handle_admin_broadcast_input(message):
    uid = message.from_user.id
    user_states.pop(uid, None)
    text = (message.text or "").strip()
    if text: _do_broadcast(message.chat.id, text)


# --- Admin scheduled broadcast input
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "admin_schedcast"
                                   and is_admin(m.from_user.id))
def handle_admin_schedcast_input(message):
    uid = message.from_user.id
    ctx = user_context.get(uid, {})
    if "sched_text" not in ctx:
        ctx["sched_text"] = (message.text or "").strip()
        user_context[uid] = ctx
        bot.reply_to(message,
                     "✅ Текст сохранён.\n\n"
                     "✏️ Теперь введите дату и время отправки (формат: ДД.ММ.ГГГГ ЧЧ:ММ):",
                     reply_markup=back_kb_plain())
    else:
        try:
            dt = datetime.datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M").isoformat()
        except:
            return bot.reply_to(message, "❌ Неверный формат. Пример: 25.12.2026 18:00")
        schedule_broadcast(ctx["sched_text"], dt, uid)
        user_states.pop(uid, None)
        user_context.pop(uid, None)
        bot.reply_to(message,
                     f"✅ Рассылка запланирована!\n\n"
                     f"📅 Дата: **{message.text.strip()}**\n"
                     f"📝 Текст: _{esc(ctx['sched_text'][:100])}_")


def back_kb_plain():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("/cancel"))
    return kb


# ============================================================
#  ADMIN-SPECIFIC CALLBACKS (ban/unban/addbal — до adm_)
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ban_") or c.data.startswith("adm_unban_"))
def cb_admin_ban(call):
    if not is_admin(call.from_user.id): return safe_ans(call, "🚫", True)
    parts  = call.data.split("_")
    action = parts[1]
    try:   uid = int(parts[2])
    except: return safe_ans(call, "❌ Ошибка", True)
    ban_user(uid, action == "ban")
    log_action(uid, f"admin_{action}", f"by {call.from_user.id}")
    safe_ans(call, f"{'🚫 Забанен' if action=='ban' else '✅ Разбанен'}: {uid}", True)
    try: bot.send_message(uid, "🚫 Заблокирован" if action=="ban" else "✅ Разблокирован")
    except: pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_addbal_"))
def cb_admin_addbal_btn(call):
    if not is_admin(call.from_user.id): return safe_ans(call, "🚫", True)
    try: uid = int(call.data.replace("adm_addbal_", ""))
    except: return safe_ans(call, "❌", True)
    user_states[call.from_user.id] = "admin_addbal"
    user_context.setdefault(call.from_user.id, {})["target_uid"] = uid
    safe_edit(call, f"💰 Пополнение баланса `{uid}`\n\n✏️ Введите сумму:",
              types.InlineKeyboardMarkup().add(
                  types.InlineKeyboardButton("❌ Отмена", callback_data="adm_back")))
    safe_ans(call)


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "admin_addbal" and is_admin(m.from_user.id))
def handle_admin_addbal_input(message):
    uid = message.from_user.id
    try:    amount = int((message.text or "").strip())
    except: return bot.reply_to(message, "❌ Число")
    user_states.pop(uid, None)
    target = user_context.get(uid, {}).pop("target_uid", None)
    if not target: return bot.reply_to(message, "❌ Цель потеряна")
    add_balance(target, amount)
    log_action(target, "manual_topup", f"+{amount} by {uid}")
    bot.reply_to(message, f"✅ `{target}` +{amount}₽")
    try: bot.send_message(target, f"💰 Пополнение баланса: **+{amount}₽**!")
    except: pass


# ============================================================
#         ADMIN CALLBACKS (общий блок)
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def cb_admin(call):
    if not is_admin(call.from_user.id): return safe_ans(call, "🚫 Нет доступа", True)
    a = call.data

    if a == "adm_stats":
        conn = get_conn(); c = conn.cursor()
        q = lambda sql, p=(): (c.execute(sql, p).fetchone()[0] or 0)
        total = q("SELECT COUNT(*) FROM users")
        active = q("SELECT COUNT(*) FROM users WHERE sub_status LIKE 'Активна%'")
        banned = q("SELECT COUNT(*) FROM users WHERE banned=1")
        trial  = q("SELECT COUNT(*) FROM users WHERE trial_used=1")
        new_td = q("SELECT COUNT(*) FROM users WHERE registered_at LIKE ?",
                   (datetime.date.today().isoformat()+"%",))
        new_wk = q("SELECT COUNT(*) FROM users WHERE registered_at >= ?",
                   ((datetime.datetime.now()-datetime.timedelta(days=7)).isoformat(),))
        total_s  = q("SELECT COUNT(*) FROM subscriptions")
        active_s = q("SELECT COUNT(*) FROM subscriptions WHERE status='Активна'")
        pending  = q("SELECT COUNT(*) FROM payments WHERE status IN ('pending','review')")
        income_a = q("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed'")
        income_d = q("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed' AND confirmed_at LIKE ?",
                     (datetime.date.today().isoformat()+"%",))
        income_w = q("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed' AND confirmed_at >= ?",
                     ((datetime.datetime.now()-datetime.timedelta(days=7)).isoformat(),))
        income_m = q("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed' AND confirmed_at >= ?",
                     ((datetime.datetime.now()-datetime.timedelta(days=30)).isoformat(),))
        reviews_  = q("SELECT COUNT(*) FROM reviews")
        avg_stars = q("SELECT COALESCE(AVG(stars),0) FROM reviews") or 0
        keys_a   = q("SELECT COUNT(*) FROM vpn_keys WHERE active=1")
        promos_a = q("SELECT COUNT(*) FROM promo_codes WHERE uses_left>0")
        conn.close()
        text = (
            "📊 **Статистика**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **Пользователи:**  {total}\n"
            f"  Сегодня: +{new_td}  |  Неделя: +{new_wk}\n"
            f"  🟢 Активных: {active}  |  🚫 Бан: {banned}\n"
            f"  🎁 Пробовали: {trial}\n\n"
            f"📦 **Подписки:**  {total_s}  (акт.: {active_s})\n\n"
            f"💰 **Доходы:**\n"
            f"  Сегодня: **{income_d}₽**\n"
            f"  Неделя: **{income_w}₽**\n"
            f"  Месяц: **{income_m}₽**\n"
            f"  Всего: **{income_a}₽**\n\n"
            f"⏳ Ожидают: {pending} заявок\n"
            f"⭐ Отзывов: {reviews_}  |  Рейтинг: {float(avg_stars):.1f}\n"
            f"🔑 Ключей: {keys_a}  |  🎟 Промокодов: {promos_a}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("🔄 Обновить",   callback_data="adm_stats"),
               types.InlineKeyboardButton("📈 Аналитика",  callback_data="adm_analytics"))
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_analytics":
        conn = get_conn()
        # Доход по дням (последние 7)
        days_labels, days_vals = [], []
        for i in range(6, -1, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            v = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed' AND confirmed_at LIKE ?",
                             (d+"%",)).fetchone()[0] or 0
            days_labels.append(d[5:])   # MM-DD
            days_vals.append(int(v))
        # Регистрации по дням
        reg_vals = []
        for i in range(6, -1, -1):
            d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            v = conn.execute("SELECT COUNT(*) FROM users WHERE registered_at LIKE ?", (d+"%",)).fetchone()[0] or 0
            reg_vals.append(int(v))
        conn.close()
        chart_inc = ascii_chart(days_vals, days_labels, 15)
        chart_reg = ascii_chart(reg_vals, days_labels, 15)
        text = (
            "📈 **Аналитика (7 дней)**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💰 **Доход (₽):**\n```\n" + chart_inc + "\n```\n\n"
            "👥 **Регистрации:**\n```\n" + chart_reg + "\n```"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_payments":
        payments = get_pending_payments()
        if not payments:
            text = "⏳ **Ожидающих заявок нет**"
        else:
            text = f"⏳ **Заявки ({len(payments)})**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for p in payments[:15]:
                u = get_user(p["tg_id"])
                un = f"@{esc(u['username'])}" if u and u.get("username") else str(p["tg_id"])
                text += (f"🆔 `#{p['id']}`  💰 **{p['amount']}₽**  {un}\n"
                         f"   🕐 {p['created_at'][:16]}\n"
                         f"   ✅ `/pay {p['id']}`   ❌ `/reject {p['id']}`\n\n")
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="adm_payments"))
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_users":
        conn = get_conn()
        users = conn.execute("SELECT tg_id,username,first_name,registered_at,balance,sub_status,banned "
                             "FROM users ORDER BY registered_at DESC LIMIT 20").fetchall()
        conn.close()
        text = "👥 **Последние 20 пользователей**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for u in users:
            u = dict(u)
            icon = "🚫" if u["banned"] else ("🟢" if "Активна" in (u["sub_status"] or "") else "⚪")
            un   = f"@{esc(u['username'])}" if u.get("username") else "—"
            text += f"{icon} `{u['tg_id']}` {esc(u.get('first_name') or '—')} ({un})\n   💰 {u['balance']}₽  📅 {fmt_dt(u['registered_at'])}\n\n"
        text += "_/userinfo <id> · /ban <id> · /unban <id>_"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_promos":
        conn  = get_conn()
        codes = conn.execute("SELECT * FROM promo_codes ORDER BY id DESC LIMIT 15").fetchall()
        conn.close()
        text = "🎟 **Промокоды**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not codes:
            text += "Промокодов нет.\n"
        for p in codes:
            p    = dict(p)
            exp  = fmt_dt(p.get("expires_at")) if p.get("expires_at") else "∞"
            icon = "✅" if p["uses_left"] > 0 else "❌"
            text += f"{icon} `{p['code']}`  {p['type']} +{p['value']}\n   {p['uses_left']}/{p['uses_left']+p['used_count']}  до {exp}\n\n"
        text += "_/newpromo · /genpromo_"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_keys":
        keys = get_all_keys()
        text = "🔑 **VPN-ключи**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for k in keys:
            icon = "🟢" if k["active"] else "🔴"
            short = k["key_url"][:55] + ("..." if len(k["key_url"]) > 55 else "")
            text += f"{icon} `#{k['id']}` **{k['label']}**  нагр.: {k.get('load_pct',0)}%\n`{short}`\n\n"
        text += "_/addkey · /disablekey · /enablekey · /setload_"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_log":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM action_log ORDER BY id DESC LIMIT 25").fetchall()
        conn.close()
        text = "📋 **Лог действий (25)**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for r in rows:
            r = dict(r)
            text += f"`{r['created_at'][11:16]}` `{r['tg_id']}` **{r['action']}** {r.get('detail','')}\n"
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="adm_log"))
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_reviews":
        revs = get_reviews(10)
        _, avg, total = get_rating_stats()
        text = f"⭐ **Отзывы** ({total}шт.  avg {avg:.1f})\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for r in revs:
            text += f"{'⭐'*r['stars']} `{r['tg_id']}`  {fmt_dt(r['created_at'])}\n_{r['text'][:120]}_\n\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_banners":
        conn  = get_conn()
        bans  = conn.execute("SELECT * FROM banners ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        text  = "🎯 **Рекламные баннеры**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not bans: text += "Баннеров нет.\n"
        for b in bans:
            b    = dict(b)
            icon = "✅" if b["active"] else "❌"
            text += (f"{icon} `#{b['id']}` **{b['title']}**\n"
                     f"   👁 {b['views']} просм.  |  🖱 {b['clicks']} кликов\n"
                     f"   _{b['text'][:80]}_\n\n")
        text += "_/addbanner <название> | <текст> | <url>_"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, text, kb)

    elif a == "adm_export":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("👥 Юзеры CSV",   callback_data="adm_export_users"),
               types.InlineKeyboardButton("💰 Платежи CSV", callback_data="adm_export_pays"))
        kb.add(types.InlineKeyboardButton("⬅️ В панель", callback_data="adm_back"))
        safe_edit(call, "📦 **Экспорт данных**\n\nВыберите что экспортировать:", kb)

    elif a == "adm_export_users":
        safe_ans(call, "⏳ Генерирую...")
        data = export_users_csv()
        f    = io.BytesIO(data.encode("utf-8-sig")); f.name = "users.csv"
        try: bot.send_document(call.message.chat.id, f, caption="👥 Экспорт пользователей")
        except Exception as e: bot.send_message(call.message.chat.id, f"❌ Ошибка: {e}")

    elif a == "adm_export_pays":
        safe_ans(call, "⏳ Генерирую...")
        data = export_payments_csv()
        f    = io.BytesIO(data.encode("utf-8-sig")); f.name = "payments.csv"
        try: bot.send_document(call.message.chat.id, f, caption="💰 Экспорт платежей")
        except Exception as e: bot.send_message(call.message.chat.id, f"❌ Ошибка: {e}")

    elif a == "adm_broadcast":
        user_states[call.from_user.id] = "admin_broadcast"
        safe_edit(call, "📢 **Рассылка**\n\nВведите текст:",
                  types.InlineKeyboardMarkup().add(
                      types.InlineKeyboardButton("❌ Отмена", callback_data="adm_back")))

    elif a == "adm_schedcast":
        user_states[call.from_user.id]  = "admin_schedcast"
        user_context[call.from_user.id] = {}
        safe_edit(call, "📅 **Отложенная рассылка**\n\n"
                  "Шаг 1: введите текст сообщения:",
                  types.InlineKeyboardMarkup().add(
                      types.InlineKeyboardButton("❌ Отмена", callback_data="adm_back")))

    elif a == "adm_back":
        user_states.pop(call.from_user.id, None)
        safe_edit(call,
                  "🔐 **Панель администратора**\n━━━━━━━━━━━━━━━━━━━━━━━\n\nВыберите раздел:",
                  admin_kb())

    elif a == "adm_close":
        user_states.pop(call.from_user.id, None)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

    safe_ans(call)


# ============================================================
#            ADMIN TEXT COMMANDS
# ============================================================
def admin_only(func):
    @functools.wraps(func)
    def wrapper(message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            try: bot.reply_to(message, "🚫 Нет доступа")
            except: pass
            return None
        return func(message, *args, **kwargs)
    return wrapper


@bot.message_handler(commands=['admin'])
@admin_only
def cmd_admin(message):
    bot.send_message(message.chat.id,
                     "🔐 **Панель администратора v3.0**\n"
                     "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     "Выберите раздел:", reply_markup=admin_kb())


@bot.message_handler(commands=['help_admin', 'admhelp'])
@admin_only
def cmd_admhelp(message):
    bot.reply_to(message,
                 "🔐 **Команды администратора**\n"
                 "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 "**Панель:**\n"
                 "`/admin` · `/stats`\n\n"
                 "**Платежи:**\n"
                 "`/pay <id>` · `/reject <id>`\n\n"
                 "**Пользователи:**\n"
                 "`/userinfo <id>` · `/addbal <id> <₽>`\n"
                 "`/subgive <id> <дней>` · `/resetstreak <id>`\n"
                 "`/ban <id>` · `/unban <id>`\n\n"
                 "**Промокоды:**\n"
                 "`/newpromo <код> <тип> <знач> <кол-во> [дней]`\n"
                 "`/genpromo <тип> <знач> <кол-во>`\n"
                 "Типы: `balance|days|discount`\n\n"
                 "**VPN-ключи:**\n"
                 "`/addkey <название> <url>`\n"
                 "`/disablekey <id>` · `/enablekey <id>`\n"
                 "`/setload <id> <0-100>`\n\n"
                 "**Рассылка:**\n"
                 "`/broadcast <текст>` · `/schedcast`\n\n"
                 "**Баннеры:**\n"
                 "`/addbanner <название> | <текст> | <url>`\n"
                 "`/bannertoggle <id>`\n\n"
                 "**TOTP для 2FA:**\n"
                 "`/settotp <secret>`")


@bot.message_handler(commands=['stats'])
@admin_only
def cmd_stats(message):
    conn = get_conn(); c = conn.cursor()
    q = lambda sql, p=(): (c.execute(sql, p).fetchone()[0] or 0)
    sql_active  = "SELECT COUNT(*) FROM users WHERE sub_status LIKE 'Активна%'"
    sql_income  = "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed'"
    sql_pending = "SELECT COUNT(*) FROM payments WHERE status IN ('pending','review')"
    text = (
        "📊 **Статистика**\n\n"
        f"👥 Всего: **{q('SELECT COUNT(*) FROM users')}**\n"
        f"🟢 Активных: **{q(sql_active)}**\n"
        f"💰 Доход всего: **{q(sql_income)}₽**\n"
        f"⏳ Ожидают: **{q(sql_pending)}**\n"
        f"⭐ Отзывов: **{q('SELECT COUNT(*) FROM reviews')}**"
    )
    conn.close()
    bot.reply_to(message, text)


@bot.message_handler(commands=['pay'])
@admin_only
def admin_pay(message):
    try: pid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /pay <id>")
    p = get_payment(pid)
    if not p: return bot.reply_to(message, "❌ Не найдена")
    # Атомарно: статус + зачисление в одной транзакции. Двойной /pay (или два админа) не зачислят дважды.
    if not confirm_payment(pid): return bot.reply_to(message, f"⚠️ Статус: {p['status']}")
    if CASHBACK_ON_TOPUP: give_cashback(p["tg_id"], p["amount"])
    log_action(p["tg_id"], "payment_confirmed", f"pid={pid}")
    new_achs = check_achievements(p["tg_id"])
    threading.Thread(target=notify_achievements, args=(p["tg_id"], new_achs), daemon=True).start()
    bot.reply_to(message, f"✅ Заявка #{pid} подтверждена. +{p['amount']}₽")
    try:
        bot.send_message(p["tg_id"],
                         f"✅ **Оплата подтверждена!**\n\n"
                         f"💰 Зачислено: **+{p['amount']}₽**\n"
                         f"🆔 Заявка `#{pid}`",
                         reply_markup=types.InlineKeyboardMarkup().add(
                             types.InlineKeyboardButton("⚡ Купить подписку", callback_data="buy")))
    except: pass


@bot.message_handler(commands=['reject'])
@admin_only
def admin_reject(message):
    try: pid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /reject <id>")
    p = get_payment(pid)
    if not p: return bot.reply_to(message, "❌ Не найдена")
    if not claim_payment(pid, ("pending", "review"), "rejected"):
        return bot.reply_to(message, f"⚠️ {p['status']}")
    bot.reply_to(message, f"❌ Заявка #{pid} отклонена")
    try: bot.send_message(p["tg_id"],
                          f"❌ Оплата не подтверждена\n🆔 `#{pid}`  💰 {p['amount']}₽\n\nСоздайте новую заявку.")
    except: pass


@bot.message_handler(commands=['addbal'])
@admin_only
def admin_addbal(message):
    try: _, uid, amount = message.text.split(); uid, amount = int(uid), int(amount)
    except: return bot.reply_to(message, "Формат: /addbal <id> <₽>")
    if not get_user(uid): return bot.reply_to(message, "❌ Не найден")
    add_balance(uid, amount)
    log_action(uid, "manual_topup", f"+{amount}")
    bot.reply_to(message, f"✅ `{uid}` +{amount}₽")
    try: bot.send_message(uid, f"💰 Баланс пополнен: **+{amount}₽**!")
    except: pass


@bot.message_handler(commands=['subgive'])
@admin_only
def admin_subgive(message):
    try: _, uid, days = message.text.split(); uid, days = int(uid), int(days)
    except: return bot.reply_to(message, "Формат: /subgive <id> <дней>")
    if not get_user(uid): return bot.reply_to(message, "❌ Не найден")
    key = get_best_key()
    exp = activate_subscription(uid, days)
    add_subscription_record(uid, f"Выдано ({days}дн.)", days, 0, key, exp)
    log_action(uid, "manual_sub", f"+{days}дн")
    bot.reply_to(message, f"✅ `{uid}` +{days} дней подписки")
    try: bot.send_message(uid, f"🎁 Вам выдана подписка **{days} дней**!\n📆 До: **{fmt_dt(exp)}**\n🔑 `{key}`")
    except: pass


@bot.message_handler(commands=['userinfo'])
@admin_only
def admin_userinfo(message):
    try: uid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /userinfo <id>")
    user = get_user(uid)
    if not user: return bot.reply_to(message, "❌ Не найден")
    subs  = get_user_subscriptions(uid)
    done  = get_user_achievements(uid)
    conn  = get_conn()
    pays  = dict(conn.execute("SELECT COUNT(*) as c, COALESCE(SUM(amount),0) as s FROM payments WHERE tg_id=? AND status='confirmed'", (uid,)).fetchone())
    conn.close()
    text = (
        f"👤 **Пользователь** `{uid}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Имя: **{user.get('first_name','—')}**  @{user.get('username','—')}\n"
        f"Статус: {user.get('sub_status','—')}  до {fmt_dt(user.get('sub_until'))}\n\n"
        f"💰 Баланс: {user.get('balance',0)}₽  |  Потрачено: {user.get('total_spent',0)}₽\n"
        f"💵 Кэшбэк: {user.get('cashback_total',0)}₽\n"
        f"📥 Пополнений: {pays['c']} на {pays['s']}₽\n"
        f"📦 Подписок: {len(subs)}\n"
        f"👥 Рефералов: {user.get('ref_count',0)}\n"
        f"🔥 Серия чекинов: {user.get('checkin_streak',0)}  всего: {user.get('total_checkins',0)}\n"
        f"🏅 Достижений: {len(done)}/{len(ACHIEVEMENTS)}\n"
        f"🌍 Язык: {user.get('lang','ru')}\n"
        f"🎁 Проба: {'✅' if user.get('trial_used') else '❌'}  "
        f"🚫 Бан: {'ДА' if user.get('banned') else 'нет'}\n"
        f"📅 Рег: {fmt_dt(user.get('registered_at'))}  "
        f"🕐 Онлайн: {fmt_dt(user.get('last_active'), '%d.%m %H:%M')}"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    if user.get("banned"):
        kb.add(types.InlineKeyboardButton("✅ Разбанить", callback_data=f"adm_unban_{uid}"))
    else:
        kb.add(types.InlineKeyboardButton("🚫 Забанить", callback_data=f"adm_ban_{uid}"))
    kb.add(types.InlineKeyboardButton("💰 Пополнить", callback_data=f"adm_addbal_{uid}"))
    bot.reply_to(message, text, reply_markup=kb)


@bot.message_handler(commands=['ban'])
@admin_only
def admin_ban_cmd(message):
    try: uid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /ban <id>")
    if is_admin(uid): return bot.reply_to(message, "❌ Нельзя забанить администратора")
    ban_user(uid, True)
    log_action(uid, "admin_ban", f"by {message.from_user.id}")
    bot.reply_to(message, f"🚫 `{uid}` заблокирован")
    try: bot.send_message(uid, "🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
    except: pass


@bot.message_handler(commands=['unban'])
@admin_only
def admin_unban_cmd(message):
    try: uid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /unban <id>")
    ban_user(uid, False)
    log_action(uid, "admin_unban", f"by {message.from_user.id}")
    bot.reply_to(message, f"✅ `{uid}` разбанен")
    try: bot.send_message(uid, "✅ Ваш аккаунт разблокирован!")
    except: pass


@bot.message_handler(commands=['resetstreak'])
@admin_only
def admin_resetstreak(message):
    try: uid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /resetstreak <id>")
    conn = get_conn()
    conn.execute("UPDATE users SET checkin_streak=0, checkin_last=NULL WHERE tg_id=?", (uid,))
    conn.commit(); conn.close()
    bot.reply_to(message, f"✅ Серия чекинов `{uid}` сброшена")


@bot.message_handler(commands=['newpromo'])
@admin_only
def admin_newpromo(message):
    parts = message.text.split()
    if len(parts) < 5:
        return bot.reply_to(message,
                            "Формат: `/newpromo <код> <тип> <знач> <кол-во> [дней]`\n"
                            "Типы: `balance|days|discount`")
    try:
        code, ptype, value, uses = parts[1].upper(), parts[2].lower(), int(parts[3]), int(parts[4])
        days_v = int(parts[5]) if len(parts) > 5 else None
        if ptype not in ("balance","days","discount") or value<=0 or uses<=0: raise ValueError
    except: return bot.reply_to(message, "❌ Неверный формат")
    exp = (datetime.datetime.now()+datetime.timedelta(days=days_v)).isoformat() if days_v else None
    if create_promo(code, ptype, value, uses, exp, message.from_user.id):
        bot.reply_to(message, f"✅ `{code}` {ptype} +{value}  x{uses}  до {fmt_dt(exp) if exp else '∞'}")
    else:
        bot.reply_to(message, "❌ Такой код уже существует")


@bot.message_handler(commands=['genpromo'])
@admin_only
def admin_genpromo(message):
    parts = message.text.split()
    if len(parts) < 4: return bot.reply_to(message, "Формат: /genpromo <тип> <знач> <кол-во>")
    try:
        ptype, value, uses = parts[1].lower(), int(parts[2]), int(parts[3])
        if ptype not in ("balance","days","discount"): raise ValueError
    except: return bot.reply_to(message, "❌ Типы: balance|days|discount")
    code = gen_code(8)
    create_promo(code, ptype, value, uses, None, message.from_user.id)
    bot.reply_to(message, f"✅ Промокод: `{code}`\n{ptype} +{value}  x{uses}")


@bot.message_handler(commands=['addkey'])
@admin_only
def admin_addkey(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3: return bot.reply_to(message, "Формат: /addkey <название> <url>")
    if add_vpn_key(parts[2].strip(), parts[1].strip()):
        bot.reply_to(message, f"✅ Ключ добавлен: {parts[1]}")
    else: bot.reply_to(message, "❌ Уже существует")


@bot.message_handler(commands=['disablekey'])
@admin_only
def admin_disablekey(message):
    try: kid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /disablekey <id>")
    toggle_vpn_key(kid, 0); bot.reply_to(message, f"🔴 Ключ #{kid} отключён")


@bot.message_handler(commands=['enablekey'])
@admin_only
def admin_enablekey(message):
    try: kid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /enablekey <id>")
    toggle_vpn_key(kid, 1); bot.reply_to(message, f"🟢 Ключ #{kid} включён")


@bot.message_handler(commands=['setload'])
@admin_only
def admin_setload(message):
    try: _, kid, pct = message.text.split(); set_key_load(int(kid), int(pct))
    except: return bot.reply_to(message, "Формат: /setload <id> <0-100>")
    bot.reply_to(message, f"✅ Нагрузка ключа #{kid} = {pct}%")


@bot.message_handler(commands=['addbanner'])
@admin_only
def admin_addbanner(message):
    text = message.text.replace("/addbanner", "", 1).strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2: return bot.reply_to(message, "Формат: /addbanner <название> | <текст> | <url>")
    title = parts[0]; body = parts[1]; url = parts[2] if len(parts) > 2 else ""
    add_banner(title, body, url, message.from_user.id)
    bot.reply_to(message, f"✅ Баннер добавлен: **{title}**")


@bot.message_handler(commands=['bannertoggle'])
@admin_only
def admin_bannertoggle(message):
    try: bid = int(message.text.split()[1])
    except: return bot.reply_to(message, "Формат: /bannertoggle <id>")
    conn = get_conn()
    row  = conn.execute("SELECT active FROM banners WHERE id=?", (bid,)).fetchone()
    if not row: conn.close(); return bot.reply_to(message, "❌ Не найден")
    new  = 1 - (row["active"] or 0)
    conn.execute("UPDATE banners SET active=? WHERE id=?", (new, bid))
    conn.commit(); conn.close()
    bot.reply_to(message, f"{'✅ Включён' if new else '❌ Выключен'} баннер #{bid}")


@bot.message_handler(commands=['settotp'])
@admin_only
def admin_settotp(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "Формат: /settotp <secret>")
    set_totp_secret(message.from_user.id, parts[1].strip())
    bot.reply_to(message, "✅ TOTP-секрет сохранён.\n"
                          "Теперь при открытии /admin нужно подтверждение кодом.")


@bot.message_handler(commands=['broadcast'])
@admin_only
def admin_broadcast(message):
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text: return bot.reply_to(message, "Формат: /broadcast <текст>")
    _do_broadcast(message.chat.id, text)


@bot.message_handler(commands=['schedcast'])
@admin_only
def admin_schedcast_cmd(message):
    uid = message.from_user.id
    user_states[uid]  = "admin_schedcast"
    user_context[uid] = {}
    bot.reply_to(message, "📅 **Отложенная рассылка**\n\nШаг 1: введите текст сообщения:",
                 reply_markup=back_kb_plain())


def _do_broadcast(chat_id, text):
    users = get_all_users()
    if not users: return bot.send_message(chat_id, "❌ Нет пользователей")
    bot.send_message(chat_id, f"📢 Рассылка запущена: {len(users)} получателей...")
    sent = [0]; failed = [0]
    def run():
        for uid in users:
            try:    bot.send_message(uid, text); sent[0] += 1
            except:
                try:    bot.send_message(uid, text, parse_mode=None); sent[0] += 1
                except: failed[0] += 1
            time.sleep(0.04)
        try: bot.send_message(chat_id, f"✅ Отправлено: {sent[0]}  |  ❌ Ошибок: {failed[0]}")
        except: pass
    threading.Thread(target=run, daemon=True).start()


# ============================================================
#       CATCH-ALL — регистрируется ПОСЛЕДНИМ
# ============================================================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_any_text(message):
    uid = message.from_user.id
    if is_banned(uid): return
    if user_states.get(uid): return
    if (message.text or "").startswith("/"):
        return bot.reply_to(message, "❓ Неизвестная команда.\n/start — главное меню")
    touch_user(uid)
    user = get_user(uid)
    if not user: return cmd_start(message)
    bot.send_message(message.chat.id, main_menu_text(user),
                     reply_markup=main_kb(uid), disable_web_page_preview=True)


# ============================================================
#                     RUN
# ============================================================
# ============================================================
#     ЗАЩИТА ОТ ДВОЙНОГО ЗАПУСКА И ОШИБКИ 409
# ============================================================
LOCK_FILE = os.path.join(BASE_DIR, "bot.lock")
_lock_fh  = None

def acquire_single_instance_lock() -> bool:
    """Не даёт запустить вторую копию бота на этом же сервере."""
    global _lock_fh
    if fcntl is None: return True          # Windows — блокировка недоступна
    try:
        _lock_fh = open(LOCK_FILE, "a+")
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fh.seek(0); _lock_fh.truncate()
        _lock_fh.write(str(os.getpid())); _lock_fh.flush()
        return True
    except BlockingIOError:
        return False
    except OSError as e:                   # файловая система без flock — просто продолжаем
        print(f"[!] Блокировка недоступна ({e}) — продолжаю без неё")
        return True

class _ConflictFilter(logging.Filter):
    """Telegram отвечает 409, если тот же токен опрашивает ещё кто-то.
    Вместо спама одинаковыми трейсами показываем понятную подсказку раз в 10 минут."""
    _last = 0.0
    def filter(self, record):
        if "Error code: 409" in record.getMessage():
            now = time.time()
            if now - _ConflictFilter._last > 600:
                _ConflictFilter._last = now
                print("[!] 409 Conflict: этот токен уже используется другим запущенным ботом.\n"
                      "    Остановите ВСЕ другие копии (ПК, другой хостинг, Replit/Colab)\n"
                      "    или выпустите новый токен: @BotFather → /revoke.")
            return False
        return True

telebot.logger.addFilter(_ConflictFilter())


# ============================================================
#                     RUN
# ============================================================
if __name__ == "__main__":
    if not acquire_single_instance_lock():
        print("[✗] Бот уже запущен на этом сервере (см. PID в bot.lock). Остановите старый\n"
              "    процесс (pkill -f vpn.py) или кнопкой «Остановить» в панели и запустите снова.")
        sys.exit(1)

    init_db()
    os.makedirs(IMAGE_DIR, exist_ok=True)

    # Проверяем токен и снимаем возможный вебхук (он тоже вызывает конфликт с polling)
    try:
        me = bot.get_me()
        print(f"[✓] Бот: @{me.username}")
    except Exception as e:
        print(f"[✗] Не удалось авторизоваться в Telegram: {e}\n    Проверьте BOT_TOKEN.")
        sys.exit(1)
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"[!] remove_webhook: {e}")

    threading.Thread(target=background_worker, daemon=True).start()

    print("╔══════════════════════════════════════════╗")
    print("║    BORSH VPN BOT  v3.1  FIXED EDITION   ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  👨‍💻 Разработчик : {DEV}")
    print(f"  👤 Админы      : {ADMIN_IDS}")
    print(f"  💳 Карта       : **** {CARD_NUMBER[-4:]}")
    print(f"  ⏰ Таймаут     : {PAYMENT_TIMEOUT_MIN} мин")
    print(f"  💵 Кэшбэк      : {CASHBACK_PERCENT}%")
    print(f"  📅 Чекин       : +{CHECKIN_REWARD}₽/день")
    print(f"  👥 Рефералы    : +{REFERRAL_BONUS}₽ / +{REFERRAL_BONUS_NEW}₽")
    print(f"  🏆 Достижений  : {len(ACHIEVEMENTS)}")
    print(f"  🎰 Призов      : {len(WHEEL_PRIZES)}")
    print(f"  ❓ FAQ          : {len(FAQ)} вопросов")
    print(f"  🌍 Серверов    : {len(SERVERS)}")
    print("═" * 44)

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30, skip_pending=True)
        except KeyboardInterrupt:
            print("\n[!] Остановлено"); break
        except Exception as e:
            print(f"[!] Сбой polling: {e}. Перезапуск через 10 сек...")
            time.sleep(10)
