# -*- coding: utf-8 -*-
import telebot
import random
import time
import threading
import json
import os
import logging
from telebot.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN", "8632745463:AAFnXVv-TdZjfvctgiOGC-MUS4A7FRJ7BZw")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003549378995"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "8626918981"))

CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/YOUR_CHANNEL")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/numberfast12_bot")

DATA_FILE = "otp_bot_data.json"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================
# DEFAULT DATA
# delay = seconds for each country
# last_sent = timestamp
# =========================
default_services = [
    "Facebook",
    "Telegram",
    "Google",
    "WhatsApp",
    "TikTok",
    "Apple",
    "1xBet"
]

default_countries = [
    {"name": "Bangladesh", "flag": "🇧🇩", "code": "#BD", "prefix": "+88019", "active": True, "service": "Telegram", "delay": 180, "last_sent": 0},
    {"name": "Italy", "flag": "🇮🇹", "code": "#IT", "prefix": "+39347", "active": True, "service": "Telegram", "delay": 180, "last_sent": 0},
    {"name": "USA", "flag": "🇺🇸", "code": "#US", "prefix": "+1201", "active": True, "service": "Google", "delay": 180, "last_sent": 0},
    {"name": "Pakistan", "flag": "🇵🇰", "code": "#PK", "prefix": "+923", "active": True, "service": "WhatsApp", "delay": 180, "last_sent": 0},
    {"name": "Vietnam", "flag": "🇻🇳", "code": "#VN", "prefix": "+849", "active": True, "service": "TikTok", "delay": 180, "last_sent": 0}
]

data_lock = threading.Lock()

running = False
otp_count = 0
services = default_services[:]
countries = [c.copy() for c in default_countries]

FORCE_STOP = False
AUTO_DELETE_ENABLED = True
AUTO_DELETE_DELAY = 300  # 5 minutes

# for next-step custom country delay
pending_country_delay_index = {}

# =========================
# SAVE / LOAD
# =========================
def save_data():
    global running, otp_count, services, countries
    global FORCE_STOP, AUTO_DELETE_ENABLED, AUTO_DELETE_DELAY
    global CHANNEL_LINK, BOT_LINK

    with data_lock:
        data = {
            "running": running,
            "otp_count": otp_count,
            "services": services,
            "countries": countries,
            "force_stop": FORCE_STOP,
            "auto_delete_enabled": AUTO_DELETE_ENABLED,
            "auto_delete_delay": AUTO_DELETE_DELAY,
            "channel_link": CHANNEL_LINK,
            "bot_link": BOT_LINK
        }

    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info("Data saved.")
    except Exception as e:
        logging.error(f"Save failed: {e}")

def load_data():
    global running, otp_count, services, countries
    global FORCE_STOP, AUTO_DELETE_ENABLED, AUTO_DELETE_DELAY
    global CHANNEL_LINK, BOT_LINK

    if not os.path.exists(DATA_FILE):
        save_data()
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        with data_lock:
            running = data.get("running", False)
            otp_count = data.get("otp_count", 0)
            services = data.get("services", default_services[:])
            countries = data.get("countries", [c.copy() for c in default_countries])
            FORCE_STOP = data.get("force_stop", False)
            AUTO_DELETE_ENABLED = data.get("auto_delete_enabled", True)
            AUTO_DELETE_DELAY = data.get("auto_delete_delay", 300)
            CHANNEL_LINK = data.get("channel_link", CHANNEL_LINK)
            BOT_LINK = data.get("bot_link", BOT_LINK)

            # old data compatibility
            for c in countries:
                c.setdefault("delay", 180)
                c.setdefault("last_sent", 0)

        logging.info("Data loaded.")
    except Exception as e:
        logging.error(f"Load failed: {e}")

# =========================
# HELPERS
# =========================
def is_admin(user_id):
    return user_id == ADMIN_ID

def mask_number(prefix):
    last = random.randint(100, 999)
    return f"{prefix}***{last}"

def generate_otp(service):
    if service == "Telegram":
        return random.randint(10000, 99999)
    return random.randint(100000, 999999)

def seconds_to_text(sec):
    if sec < 60:
        return f"{sec}s"
    mins = sec // 60
    rem = sec % 60
    if rem == 0:
        return f"{mins}m"
    return f"{mins}m {rem}s"

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 OTP Stats", "🌍 Countries")
    kb.row("🔧 Service Edit", "⏱ Country Delay")
    kb.row("▶ Start Generator", "⏹ Stop Generator")
    kb.row("🗑 Auto Delete ON", "🗑 Auto Delete OFF")
    kb.row("⏱ Set Delete Time")
    kb.row("🔗 Update Channel Link", "🤖 Update Bot Link")
    return kb

def delete_time_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("1 min", "2 min", "5 min")
    kb.row("Custom Time")
    kb.row("⬅ Back")
    return kb

def countries_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current_countries = countries[:]

    for i, c in enumerate(current_countries):
        status = "✅ ON" if c["active"] else "❌ OFF"
        kb.row(
            InlineKeyboardButton(
                f"{c['flag']} {c['name']} {status}",
                callback_data=f"country_{i}"
            )
        )

    kb.row(
        InlineKeyboardButton("➕ Add Country", callback_data="add_country"),
        InlineKeyboardButton("🗑 Delete Country", callback_data="delete_country")
    )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    return kb

def services_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current_countries = countries[:]

    for i, c in enumerate(current_countries):
        kb.row(
            InlineKeyboardButton(
                f"{c['flag']} {c['name']} → {c['service']}",
                callback_data=f"service_{i}"
            )
        )

    kb.row(InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    return kb

def country_delay_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current_countries = countries[:]

    for i, c in enumerate(current_countries):
        kb.row(
            InlineKeyboardButton(
                f"{c['flag']} {c['name']} ⏱ {seconds_to_text(c.get('delay', 180))}",
                callback_data=f"countrydelay_{i}"
            )
        )

    kb.row(InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    return kb

def country_delay_options_keyboard(index):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("1 min", callback_data=f"setcdelay|{index}|60"),
        InlineKeyboardButton("2 min", callback_data=f"setcdelay|{index}|120")
    )
    kb.row(
        InlineKeyboardButton("5 min", callback_data=f"setcdelay|{index}|300"),
        InlineKeyboardButton("Custom", callback_data=f"customcdelay_{index}")
    )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_country_delay"))
    return kb

def delete_country_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current_countries = countries[:]

    if not current_countries:
        kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_countries"))
        return kb

    for i, c in enumerate(current_countries):
        kb.row(
            InlineKeyboardButton(
                f"❌ {c['flag']} {c['name']}",
                callback_data=f"delcountry_{i}"
            )
        )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_countries"))
    return kb

def select_service_keyboard(country_index):
    kb = InlineKeyboardMarkup()
    with data_lock:
        current_services = services[:]
        current_countries = countries[:]

    if country_index < 0 or country_index >= len(current_countries):
        return None

    for s in current_services:
        kb.row(
            InlineKeyboardButton(
                s,
                callback_data=f"setservice|{country_index}|{s}"
            )
        )

    kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_services"))
    return kb

def generator_text(country, number, otp):
    return (
        f"{country['flag']} <b>{country['name']}</b> {country['code']} 📱 <b>{country['service']}</b>\n\n"
        f"<code>{number}</code>\n\n"
        f"🔑 <b>{otp}</b>"
    )

def auto_delete_message(chat_id, message_id, delay=300):
    def delete_later():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
            logging.info(f"Deleted message {message_id} from {chat_id}")
        except Exception as e:
            logging.error(f"Auto delete failed for {message_id}: {e}")

    threading.Thread(target=delete_later, daemon=True).start()

def send_generator_message(text):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📢 Main Channel", url=CHANNEL_LINK),
        InlineKeyboardButton("🤖 Number Bot", url=BOT_LINK)
    )

    sent = bot.send_message(GROUP_ID, text, reply_markup=kb)

    with data_lock:
        local_auto_delete = AUTO_DELETE_ENABLED
        local_delay = AUTO_DELETE_DELAY

    if local_auto_delete:
        auto_delete_message(GROUP_ID, sent.message_id, local_delay)

    return sent

# =========================
# GENERATOR THREAD
# each country has its own delay
# =========================
def generator():
    global otp_count

    while True:
        try:
            with data_lock:
                local_running = running
                local_force_stop = FORCE_STOP
                now = time.time()

                eligible = []
                for i, c in enumerate(countries):
                    if not c.get("active"):
                        continue
                    delay = int(c.get("delay", 180))
                    last_sent = float(c.get("last_sent", 0))
                    if now - last_sent >= delay:
                        eligible.append((i, c.copy()))

            if local_force_stop:
                time.sleep(1)
                continue

            if local_running:
                if not eligible:
                    time.sleep(1)
                    continue

                idx, c = random.choice(eligible)
                number = mask_number(c["prefix"])
                otp = generate_otp(c["service"])
                text = generator_text(c, number, otp)

                try:
                    with data_lock:
                        if FORCE_STOP or not running:
                            time.sleep(1)
                            continue

                    send_generator_message(text)

                    with data_lock:
                        if not FORCE_STOP and running:
                            otp_count += 1
                            if 0 <= idx < len(countries):
                                countries[idx]["last_sent"] = time.time()

                    save_data()
                    logging.info(
                        f"OTP sent: {c['name']} | {c['service']} | total={otp_count} | delay={c.get('delay',180)}"
                    )

                except Exception as e:
                    logging.error(f"Send failed: {e}")

            time.sleep(1)

        except Exception as e:
            logging.error(f"Generator loop error: {e}")
            time.sleep(2)

# =========================
# COMMANDS
# =========================
@bot.message_handler(commands=['start'])
def start(msg):
    if not is_admin(msg.from_user.id):
        return

    with data_lock:
        current_running = running
        auto_del = "ON" if AUTO_DELETE_ENABLED else "OFF"
        delete_time = seconds_to_text(AUTO_DELETE_DELAY)
        active_count = len([c for c in countries if c["active"]])

    text = (
        "🤖 <b>OTP BOT READY</b>\n\n"
        f"🎯 Status: <b>{'RUNNING' if current_running else 'STOPPED'}</b>\n"
        f"🌍 Active Countries: <b>{active_count}</b>\n"
        f"🗑 Auto Delete: <b>{auto_del}</b>\n"
        f"⏱ Delete Time: <b>{delete_time}</b>\n"
        f"🔗 Channel: <code>{CHANNEL_LINK}</code>\n"
        f"🤖 Bot: <code>{BOT_LINK}</code>"
    )
    bot.send_message(msg.chat.id, text, reply_markup=main_menu())

# =========================
# MESSAGE HANDLER
# =========================
@bot.message_handler(func=lambda message: True)
def panel(message):
    global running, FORCE_STOP, AUTO_DELETE_ENABLED, AUTO_DELETE_DELAY
    global CHANNEL_LINK, BOT_LINK

    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    if text == "📊 OTP Stats":
        with data_lock:
            count = otp_count
            current_running = running
            active_count = len([c for c in countries if c["active"]])
            auto_del = "ON" if AUTO_DELETE_ENABLED else "OFF"
            delete_time = seconds_to_text(AUTO_DELETE_DELAY)

        bot.send_message(
            message.chat.id,
            f"📊 <b>OTP Generated:</b> {count}\n"
            f"🎯 <b>Status:</b> {'RUNNING' if current_running else 'STOPPED'}\n"
            f"🌍 <b>Active Countries:</b> {active_count}\n"
            f"🗑 <b>Auto Delete:</b> {auto_del}\n"
            f"⏱ <b>Delete Time:</b> {delete_time}\n"
            f"🔗 <b>Channel:</b> <code>{CHANNEL_LINK}</code>\n"
            f"🤖 <b>Bot:</b> <code>{BOT_LINK}</code>",
            reply_markup=main_menu()
        )

    elif text == "🌍 Countries":
        bot.send_message(
            message.chat.id,
            "🌍 <b>Country Manager</b>",
            reply_markup=countries_keyboard()
        )

    elif text == "🔧 Service Edit":
        bot.send_message(
            message.chat.id,
            "🔧 <b>Select Country</b>",
            reply_markup=services_keyboard()
        )

    elif text == "⏱ Country Delay":
        bot.send_message(
            message.chat.id,
            "⏱ <b>Select Country For Delay</b>",
            reply_markup=country_delay_keyboard()
        )

    elif text == "▶ Start Generator":
        with data_lock:
            FORCE_STOP = False
            running = True
        save_data()
        bot.send_message(message.chat.id, "✅ <b>Generator Started</b>", reply_markup=main_menu())

    elif text == "⏹ Stop Generator":
        with data_lock:
            running = False
            FORCE_STOP = True
        save_data()
        bot.send_message(message.chat.id, "🛑 <b>Generator Stopped</b>", reply_markup=main_menu())

    elif text == "🗑 Auto Delete ON":
        with data_lock:
            AUTO_DELETE_ENABLED = True
        save_data()
        bot.send_message(
            message.chat.id,
            f"🗑 <b>Auto Delete Enabled</b>\n⏱ Delay: {seconds_to_text(AUTO_DELETE_DELAY)}",
            reply_markup=main_menu()
        )

    elif text == "🗑 Auto Delete OFF":
        with data_lock:
            AUTO_DELETE_ENABLED = False
        save_data()
        bot.send_message(
            message.chat.id,
            "🗑 <b>Auto Delete Disabled</b>",
            reply_markup=main_menu()
        )

    elif text == "⏱ Set Delete Time":
        bot.send_message(
            message.chat.id,
            "⏱ <b>Select Auto Delete Time</b>",
            reply_markup=delete_time_menu()
        )

    elif text in {"1 min", "2 min", "5 min"}:
        mins = int(text.split()[0])

        with data_lock:
            AUTO_DELETE_DELAY = mins * 60
        save_data()

        bot.send_message(
            message.chat.id,
            f"⏱ <b>Delete Time Set:</b> {mins} minutes",
            reply_markup=main_menu()
        )

    elif text == "Custom Time":
        msg = bot.send_message(
            message.chat.id,
            "Send auto delete time in seconds\n\nExample: <code>60</code> / <code>120</code> / <code>300</code>"
        )
        bot.register_next_step_handler(msg, set_custom_time)

    elif text == "🔗 Update Channel Link":
        msg = bot.send_message(
            message.chat.id,
            "Send new channel link\n\nExample:\n<code>https://t.me/your_channel</code>"
        )
        bot.register_next_step_handler(msg, update_channel_link_process)

    elif text == "🤖 Update Bot Link":
        msg = bot.send_message(
            message.chat.id,
            "Send new bot link\n\nExample:\n<code>https://t.me/your_bot</code>"
        )
        bot.register_next_step_handler(msg, update_bot_link_process)

    elif text == "⬅ Back":
        bot.send_message(message.chat.id, "🔙 <b>Back To Main Menu</b>", reply_markup=main_menu())

# =========================
# CALLBACKS
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if not is_admin(call.from_user.id):
        return

    try:
        if call.data.startswith("country_"):
            i = int(call.data.split("_")[1])

            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                countries[i]["active"] = not countries[i]["active"]
                status = "ON" if countries[i]["active"] else "OFF"
                country_name = countries[i]["name"]

            save_data()
            bot.answer_callback_query(call.id, f"{country_name} {status}")
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=countries_keyboard()
            )

        elif call.data == "add_country":
            msg = bot.send_message(
                call.message.chat.id,
                "Send format like:\n\n<code>🇯🇵 Japan #JP +819 Telegram</code>"
            )
            bot.register_next_step_handler(msg, add_country_process)
            bot.answer_callback_query(call.id)

        elif call.data == "delete_country":
            bot.edit_message_text(
                "🗑 <b>Select country to delete</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=delete_country_keyboard()
            )
            bot.answer_callback_query(call.id)

        elif call.data.startswith("delcountry_"):
            i = int(call.data.split("_")[1])

            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                name = countries[i]["name"]
                countries.pop(i)

            save_data()
            bot.answer_callback_query(call.id, f"{name} Deleted")
            bot.edit_message_text(
                "🗑 <b>Select country to delete</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=delete_country_keyboard()
            )

        elif call.data == "show_countries":
            bot.edit_message_text(
                "🌍 <b>Country Manager</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=countries_keyboard()
            )
            bot.answer_callback_query(call.id)

        elif call.data.startswith("service_"):
            i = int(call.data.split("_")[1])
            kb = select_service_keyboard(i)

            if kb is None:
                bot.answer_callback_query(call.id, "Invalid country")
                return

            bot.edit_message_text(
                "🔧 <b>Select Service</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb
            )
            bot.answer_callback_query(call.id)

        elif call.data.startswith("setservice|"):
            parts = call.data.split("|", 2)
            if len(parts) != 3:
                bot.answer_callback_query(call.id, "Invalid service data")
                return

            i = int(parts[1])
            service = parts[2]

            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                countries[i]["service"] = service
                country_name = countries[i]["name"]

            save_data()
            bot.answer_callback_query(call.id, f"{country_name} → {service}")
            bot.edit_message_text(
                "🔧 <b>Select Country</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=services_keyboard()
            )

        elif call.data == "show_services":
            bot.edit_message_text(
                "🔧 <b>Select Country</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=services_keyboard()
            )
            bot.answer_callback_query(call.id)

        elif call.data == "show_country_delay":
            bot.edit_message_text(
                "⏱ <b>Select Country For Delay</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=country_delay_keyboard()
            )
            bot.answer_callback_query(call.id)

        elif call.data.startswith("countrydelay_"):
            i = int(call.data.split("_")[1])

            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                cname = countries[i]["name"]

            bot.edit_message_text(
                f"⏱ <b>Set Delay For {cname}</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=country_delay_options_keyboard(i)
            )
            bot.answer_callback_query(call.id)

        elif call.data.startswith("setcdelay|"):
            parts = call.data.split("|")
            if len(parts) != 3:
                bot.answer_callback_query(call.id, "Invalid delay data")
                return

            i = int(parts[1])
            sec = int(parts[2])

            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                countries[i]["delay"] = sec
                cname = countries[i]["name"]

            save_data()
            bot.answer_callback_query(call.id, f"{cname} delay {seconds_to_text(sec)}")
            bot.edit_message_text(
                "⏱ <b>Select Country For Delay</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=country_delay_keyboard()
            )

        elif call.data.startswith("customcdelay_"):
            i = int(call.data.split("_")[1])

            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                cname = countries[i]["name"]

            pending_country_delay_index[call.message.chat.id] = i
            msg = bot.send_message(
                call.message.chat.id,
                f"Send custom delay in seconds for <b>{cname}</b>\n\nExample: <code>60</code> / <code>120</code> / <code>300</code>"
            )
            bot.register_next_step_handler(msg, set_custom_country_delay)
            bot.answer_callback_query(call.id)

        elif call.data == "back_main":
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, "🔙 <b>Back To Main Menu</b>", reply_markup=main_menu())
            bot.answer_callback_query(call.id)

    except Exception as e:
        logging.error(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "Error occurred")
        except Exception:
            pass

# =========================
# NEXT STEP HANDLERS
# =========================
def add_country_process(message):
    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    try:
        data = text.split()

        if len(data) != 5:
            raise ValueError("Need exactly 5 parts")

        flag = data[0]
        name = data[1]
        code = data[2]
        prefix = data[3]
        service = data[4]

        if not code.startswith("#"):
            raise ValueError("Country code must start with #")

        if not prefix.startswith("+"):
            raise ValueError("Prefix must start with +")

        with data_lock:
            countries.append({
                "name": name,
                "flag": flag,
                "code": code,
                "prefix": prefix,
                "active": True,
                "service": service,
                "delay": 180,
                "last_sent": 0
            })

        save_data()
        bot.send_message(
            message.chat.id,
            f"✅ <b>Country Added</b>\n\n{flag} {name} {code} {prefix} {service}",
            reply_markup=main_menu()
        )

    except Exception as e:
        logging.error(f"Add country failed: {e}")
        bot.send_message(
            message.chat.id,
            "❌ <b>Wrong Format</b>\n\nUse:\n<code>🇯🇵 Japan #JP +819 Telegram</code>",
            reply_markup=main_menu()
        )

def set_custom_time(message):
    global AUTO_DELETE_DELAY

    if not is_admin(message.from_user.id):
        return

    try:
        sec = int((message.text or "").strip())

        if sec < 10:
            bot.send_message(message.chat.id, "❌ Minimum 10 sec", reply_markup=main_menu())
            return

        with data_lock:
            AUTO_DELETE_DELAY = sec
        save_data()

        bot.send_message(
            message.chat.id,
            f"⏱ <b>Auto Delete Time Set:</b> {sec} sec",
            reply_markup=main_menu()
        )

    except Exception:
        bot.send_message(message.chat.id, "❌ Invalid number", reply_markup=main_menu())

def set_custom_country_delay(message):
    if not is_admin(message.from_user.id):
        return

    chat_id = message.chat.id
    if chat_id not in pending_country_delay_index:
        bot.send_message(chat_id, "❌ No country selected", reply_markup=main_menu())
        return

    try:
        sec = int((message.text or "").strip())

        if sec < 10:
            bot.send_message(chat_id, "❌ Minimum 10 sec", reply_markup=main_menu())
            return

        idx = pending_country_delay_index[chat_id]

        with data_lock:
            if idx < 0 or idx >= len(countries):
                bot.send_message(chat_id, "❌ Invalid country", reply_markup=main_menu())
                return
            countries[idx]["delay"] = sec
            cname = countries[idx]["name"]

        save_data()
        pending_country_delay_index.pop(chat_id, None)

        bot.send_message(
            chat_id,
            f"⏱ <b>{cname} Delay Set:</b> {sec} sec",
            reply_markup=main_menu()
        )

    except Exception:
        bot.send_message(chat_id, "❌ Invalid number", reply_markup=main_menu())

def update_channel_link_process(message):
    global CHANNEL_LINK

    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    if not text.startswith("https://t.me/"):
        bot.send_message(message.chat.id, "❌ Invalid channel link", reply_markup=main_menu())
        return

    CHANNEL_LINK = text
    save_data()

    bot.send_message(
        message.chat.id,
        f"✅ <b>Channel Link Updated</b>\n\n{CHANNEL_LINK}",
        reply_markup=main_menu()
    )

def update_bot_link_process(message):
    global BOT_LINK

    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    if not text.startswith("https://t.me/"):
        bot.send_message(message.chat.id, "❌ Invalid bot link", reply_markup=main_menu())
        return

    BOT_LINK = text
    save_data()

    bot.send_message(
        message.chat.id,
        f"✅ <b>Bot Link Updated</b>\n\n{BOT_LINK}",
        reply_markup=main_menu()
    )

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    if TOKEN == "PASTE_NEW_BOT_TOKEN_HERE":
        raise ValueError("Please set BOT_TOKEN in Railway Variables or replace TOKEN in code.")

    load_data()
    threading.Thread(target=generator, daemon=True).start()

    logging.info("Bot started.")
    print("BOT RUNNING...")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(5)
