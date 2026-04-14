# -*- coding: utf-8 -*-
import os
import io
import json
import time
import random
import threading
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import telebot
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
PANEL_AUTO_DELETE_DELAY = 60  # panel/user messages delete after 1 min

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================
# DEFAULT DATA
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
    {"name": "Bangladesh", "flag": "🇧🇩", "code": "#BD", "prefix": "+88019", "active": True, "service": "Telegram", "delay": 120, "last_sent": 0},
    {"name": "Italy", "flag": "🇮🇹", "code": "#IT", "prefix": "+39347", "active": True, "service": "Telegram", "delay": 120, "last_sent": 0},
    {"name": "USA", "flag": "🇺🇸", "code": "#US", "prefix": "+1201", "active": True, "service": "Google", "delay": 120, "last_sent": 0},
    {"name": "Pakistan", "flag": "🇵🇰", "code": "#PK", "prefix": "+923", "active": True, "service": "WhatsApp", "delay": 120, "last_sent": 0},
    {"name": "Vietnam", "flag": "🇻🇳", "code": "#VN", "prefix": "+849", "active": True, "service": "TikTok", "delay": 120, "last_sent": 0}
]

data_lock = threading.Lock()

running = False
otp_count = 0
services = default_services[:]
countries = [c.copy() for c in default_countries]

FORCE_STOP = False
AUTO_DELETE_ENABLED = True
AUTO_DELETE_DELAY = 300  # group OTP image auto delete
CUSTOM_SMS_TEXT = "তোর টেলিগ্রাম কোড এসেছে গুরুপ চেক কর"
GROUP_SEND_DELAY = 120  # default delay for all/new countries

pending_country_delay_index = {}

# =========================
# FONTS
# =========================
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def get_font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# =========================
# SAVE / LOAD
# =========================
def save_data():
    global running, otp_count, services, countries
    global FORCE_STOP, AUTO_DELETE_ENABLED, AUTO_DELETE_DELAY
    global CHANNEL_LINK, BOT_LINK, CUSTOM_SMS_TEXT, GROUP_SEND_DELAY

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
            "bot_link": BOT_LINK,
            "custom_sms_text": CUSTOM_SMS_TEXT,
            "group_send_delay": GROUP_SEND_DELAY
        }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    global running, otp_count, services, countries
    global FORCE_STOP, AUTO_DELETE_ENABLED, AUTO_DELETE_DELAY
    global CHANNEL_LINK, BOT_LINK, CUSTOM_SMS_TEXT, GROUP_SEND_DELAY

    if not os.path.exists(DATA_FILE):
        save_data()
        return

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
        CUSTOM_SMS_TEXT = data.get("custom_sms_text", CUSTOM_SMS_TEXT)
        GROUP_SEND_DELAY = data.get("group_send_delay", 120)

        for c in countries:
            c.setdefault("delay", GROUP_SEND_DELAY)
            c.setdefault("last_sent", 0)

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

def auto_delete(chat_id, message_id, delay=60):
    def delete_later():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=delete_later, daemon=True).start()

def delete_user_message_later(chat_id, message_id, delay=60):
    def delete_later():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=delete_later, daemon=True).start()

def send_panel_message(chat_id, text, reply_markup=None, delay=PANEL_AUTO_DELETE_DELAY):
    msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
    auto_delete(chat_id, msg.message_id, delay)
    return msg

def get_service_display(service):
    s = (service or "").strip().lower()
    if s == "whatsapp":
        return "🟢 WhatsApp"
    if s == "telegram":
        return "🔵 Telegram"
    if s == "facebook":
        return "📘 Facebook"
    if s == "google":
        return "🔷 Google"
    if s == "tiktok":
        return "🎵 TikTok"
    if s == "apple":
        return "🍎 Apple"
    if s == "1xbet":
        return "🎰 1xBet"
    return f"📱 {service}"

# =========================
# KEYBOARDS
# =========================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 OTP Stats", "🌍 Countries")
    kb.row("🔧 Service Edit", "⏱ Country Delay")
    kb.row("▶ Start Generator", "⏹ Stop Generator")
    kb.row("🗑 Auto Delete ON", "🗑 Auto Delete OFF")
    kb.row("⏱ Set Delete Time", "⏰ Group Send Time")
    kb.row("🔗 Update Channel Link", "🤖 Update Bot Link")
    kb.row("📝 SMS Text")
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
        current = countries[:]
    for i, c in enumerate(current):
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

def delete_country_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current = countries[:]
    if not current:
        kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_countries"))
        return kb
    for i, c in enumerate(current):
        kb.row(
            InlineKeyboardButton(
                f"❌ {c['flag']} {c['name']}",
                callback_data=f"delcountry_{i}"
            )
        )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_countries"))
    return kb

def services_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current = countries[:]
    for i, c in enumerate(current):
        kb.row(
            InlineKeyboardButton(
                f"{c['flag']} {c['name']} → {c['service']}",
                callback_data=f"service_{i}"
            )
        )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    return kb

def select_service_keyboard(country_index):
    kb = InlineKeyboardMarkup()
    with data_lock:
        current_services = services[:]
        current_countries = countries[:]

    if country_index < 0 or country_index >= len(current_countries):
        return None

    for s in current_services:
        kb.row(InlineKeyboardButton(s, callback_data=f"setservice|{country_index}|{s}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="show_services"))
    return kb

def country_delay_keyboard():
    kb = InlineKeyboardMarkup()
    with data_lock:
        current = countries[:]
    for i, c in enumerate(current):
        kb.row(
            InlineKeyboardButton(
                f"{c['flag']} {c['name']} ⏱ {seconds_to_text(c.get('delay', GROUP_SEND_DELAY))}",
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

# =========================
# IMAGE CARD DESIGN
# =========================
def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def draw_glow(base_img: Image.Image, box, color=(55, 126, 255), blur=18, alpha=70, radius=28):
    glow = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    rgba = (*color, alpha)
    gdraw.rounded_rectangle(box, radius=radius, fill=rgba)
    glow = glow.filter(ImageFilter.GaussianBlur(blur))
    base_img.alpha_composite(glow)

def create_otp_card(country, number, otp):
    W, H = 1280, 820
    img = Image.new("RGBA", (W, H), (7, 12, 27, 255))
    draw = ImageDraw.Draw(img)

    # glow bg
    draw_glow(img, (120, 90, W - 120, H - 90), color=(36, 79, 168), blur=30, alpha=55, radius=40)

    # main card
    card = (90, 70, W - 90, 520)
    draw_glow(img, card, color=(58, 118, 255), blur=26, alpha=90, radius=34)

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    rounded_rect(ld, card, radius=34, fill=(25, 42, 88, 230), outline=(92, 149, 255, 110), width=2)
    img.alpha_composite(layer)
    draw = ImageDraw.Draw(img)

    # fonts
    f_title = get_font(FONT_BOLD, 64)
    f_badge = get_font(FONT_BOLD, 38)
    f_service = get_font(FONT_BOLD, 52)
    f_num = get_font(FONT_REG, 54)
    f_otp = get_font(FONT_BOLD, 62)
    f_time = get_font(FONT_REG, 42)
    f_btn = get_font(FONT_BOLD, 48)
    f_msg = get_font(FONT_REG, 30)

    # title
    draw.text((140, 105), "THG Admin", font=f_title, fill=(255, 210, 129))

    # admin badge
    badge_text = "Admin"
    badge_box = (1000, 95, 1180, 160)
    rounded_rect(draw, badge_box, radius=28, fill=(43, 91, 52))
    draw.text((1044, 106), badge_text, font=f_badge, fill=(163, 255, 135))

    # service
    line1 = f"{country['flag']}  {country['code']}  {get_service_display(country.get('service','Unknown'))}"
    draw.text((140, 200), line1, font=f_service, fill=(244, 244, 244))

    # number field
    number_box = (130, 290, W - 130, 390)
    rounded_rect(draw, number_box, radius=24, fill=(56, 94, 170, 110), outline=(130, 170, 255), width=2)
    draw.text((170, 310), number, font=f_num, fill=(255, 255, 255))

    # otp
    draw.text((155, 430), f"🔐 {otp}", font=f_otp, fill=(255, 244, 190))

    # time
    tm = datetime.now().strftime("%H:%M")
    draw.text((W - 250, 425), tm, font=f_time, fill=(177, 190, 214))

    # footer text
    draw.text((155, 500), CUSTOM_SMS_TEXT, font=f_msg, fill=(225, 235, 255))

    # buttons
    b1 = (105, 560, 605, 680)
    b2 = (675, 560, 1175, 680)

    draw_glow(img, b1, color=(180, 66, 66), blur=18, alpha=90, radius=28)
    rounded_rect(draw, b1, radius=28, fill=(151, 52, 52), outline=(210, 121, 121), width=2)
    draw.text((190, 595), "📞 Channel", font=f_btn, fill=(255, 255, 255))
    draw.text((540, 570), "↗", font=f_btn, fill=(223, 223, 223))

    draw_glow(img, b2, color=(66, 165, 78), blur=18, alpha=90, radius=28)
    rounded_rect(draw, b2, radius=28, fill=(56, 132, 46), outline=(130, 214, 119), width=2)
    draw.text((770, 595), "🤖 Panel", font=f_btn, fill=(255, 255, 255))
    draw.text((1110, 570), "↗", font=f_btn, fill=(223, 223, 223))

    output = io.BytesIO()
    output.name = "otp_card.png"
    img.convert("RGB").save(output, format="PNG")
    output.seek(0)
    return output

# =========================
# GROUP SENDER
# =========================
def auto_delete_group_message(chat_id, message_id, delay=300):
    def delete_later():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            logging.error(f"Auto delete failed for {message_id}: {e}")
    threading.Thread(target=delete_later, daemon=True).start()

def send_generator_message(country, number, otp):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📞 Channel", url=CHANNEL_LINK),
        InlineKeyboardButton("🤖 Panel", url=BOT_LINK)
    )

    image_file = create_otp_card(country, number, otp)
    sent = bot.send_photo(GROUP_ID, image_file, reply_markup=kb)

    with data_lock:
        local_auto_delete = AUTO_DELETE_ENABLED
        local_delay = AUTO_DELETE_DELAY

    if local_auto_delete:
        auto_delete_group_message(GROUP_ID, sent.message_id, local_delay)

    return sent

# =========================
# GENERATOR LOOP
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
                    delay = int(c.get("delay", GROUP_SEND_DELAY))
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

                try:
                    with data_lock:
                        if FORCE_STOP or not running:
                            time.sleep(1)
                            continue

                    send_generator_message(c, number, otp)

                    with data_lock:
                        if not FORCE_STOP and running:
                            otp_count += 1
                            if 0 <= idx < len(countries):
                                countries[idx]["last_sent"] = time.time()

                    save_data()

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

    delete_user_message_later(msg.chat.id, msg.message_id, PANEL_AUTO_DELETE_DELAY)

    with data_lock:
        current_running = running
        auto_del = "ON" if AUTO_DELETE_ENABLED else "OFF"
        delete_time = seconds_to_text(AUTO_DELETE_DELAY)
        active_count = len([c for c in countries if c["active"]])
        send_time = seconds_to_text(GROUP_SEND_DELAY)

    bot.send_message(
        msg.chat.id,
        (
            "🤖 <b>OTP BOT READY</b>\n\n"
            f"🎯 Status: <b>{'RUNNING' if current_running else 'STOPPED'}</b>\n"
            f"🌍 Active Countries: <b>{active_count}</b>\n"
            f"🗑 Auto Delete: <b>{auto_del}</b>\n"
            f"⏱ Delete Time: <b>{delete_time}</b>\n"
            f"📨 Default Group Send Time: <b>{send_time}</b>\n"
            f"📝 SMS Text: <code>{CUSTOM_SMS_TEXT}</code>\n"
            f"🔗 Channel: <code>{CHANNEL_LINK}</code>\n"
            f"🤖 Bot: <code>{BOT_LINK}</code>"
        ),
        reply_markup=main_menu()
    )

# =========================
# PANEL HANDLER
# =========================
@bot.message_handler(func=lambda message: True)
def panel(message):
    global running, FORCE_STOP, AUTO_DELETE_ENABLED, AUTO_DELETE_DELAY
    global CHANNEL_LINK, BOT_LINK, CUSTOM_SMS_TEXT, GROUP_SEND_DELAY

    if not is_admin(message.from_user.id):
        return

    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)
    text = (message.text or "").strip()

    if text == "📊 OTP Stats":
        with data_lock:
            count = otp_count
            current_running = running
            active_count = len([c for c in countries if c["active"]])
            auto_del = "ON" if AUTO_DELETE_ENABLED else "OFF"
            delete_time = seconds_to_text(AUTO_DELETE_DELAY)
            send_time = seconds_to_text(GROUP_SEND_DELAY)

        send_panel_message(
            message.chat.id,
            (
                f"📊 <b>OTP Generated:</b> {count}\n"
                f"🎯 <b>Status:</b> {'RUNNING' if current_running else 'STOPPED'}\n"
                f"🌍 <b>Active Countries:</b> {active_count}\n"
                f"🗑 <b>Auto Delete:</b> {auto_del}\n"
                f"⏱ <b>Delete Time:</b> {delete_time}\n"
                f"📨 <b>Default Group Send Time:</b> {send_time}\n"
                f"📝 <b>SMS Text:</b> <code>{CUSTOM_SMS_TEXT}</code>\n"
                f"🔗 <b>Channel:</b> <code>{CHANNEL_LINK}</code>\n"
                f"🤖 <b>Bot:</b> <code>{BOT_LINK}</code>"
            )
        )

    elif text == "🌍 Countries":
        send_panel_message(message.chat.id, "🌍 <b>Country Manager</b>", reply_markup=countries_keyboard())

    elif text == "🔧 Service Edit":
        send_panel_message(message.chat.id, "🔧 <b>Select Country</b>", reply_markup=services_keyboard())

    elif text == "⏱ Country Delay":
        send_panel_message(message.chat.id, "⏱ <b>Select Country For Delay</b>", reply_markup=country_delay_keyboard())

    elif text == "▶ Start Generator":
        with data_lock:
            FORCE_STOP = False
            running = True
        save_data()
        send_panel_message(message.chat.id, "✅ <b>Generator Started</b>")

    elif text == "⏹ Stop Generator":
        with data_lock:
            running = False
            FORCE_STOP = True
        save_data()
        send_panel_message(message.chat.id, "🛑 <b>Generator Stopped</b>")

    elif text == "🗑 Auto Delete ON":
        with data_lock:
            AUTO_DELETE_ENABLED = True
        save_data()
        send_panel_message(message.chat.id, f"🗑 <b>Auto Delete Enabled</b>\n⏱ Delay: {seconds_to_text(AUTO_DELETE_DELAY)}")

    elif text == "🗑 Auto Delete OFF":
        with data_lock:
            AUTO_DELETE_ENABLED = False
        save_data()
        send_panel_message(message.chat.id, "🗑 <b>Auto Delete Disabled</b>")

    elif text == "⏱ Set Delete Time":
        send_panel_message(message.chat.id, "⏱ <b>Select Auto Delete Time</b>", reply_markup=delete_time_menu())

    elif text in {"1 min", "2 min", "5 min"}:
        mins = int(text.split()[0])
        with data_lock:
            AUTO_DELETE_DELAY = mins * 60
        save_data()
        send_panel_message(message.chat.id, f"⏱ <b>Delete Time Set:</b> {mins} minutes")

    elif text == "Custom Time":
        msg = send_panel_message(
            message.chat.id,
            "Send auto delete time in seconds\n\nExample: <code>1</code> / <code>5</code> / <code>60</code>",
            delay=PANEL_AUTO_DELETE_DELAY
        )
        bot.register_next_step_handler(msg, set_custom_time)

    elif text == "🔗 Update Channel Link":
        msg = send_panel_message(
            message.chat.id,
            "Send new channel link\n\nExample:\n<code>https://t.me/your_channel</code>",
            delay=PANEL_AUTO_DELETE_DELAY
        )
        bot.register_next_step_handler(msg, update_channel_link_process)

    elif text == "🤖 Update Bot Link":
        msg = send_panel_message(
            message.chat.id,
            "Send new bot link\n\nExample:\n<code>https://t.me/your_bot</code>",
            delay=PANEL_AUTO_DELETE_DELAY
        )
        bot.register_next_step_handler(msg, update_bot_link_process)

    elif text == "📝 SMS Text":
        msg = send_panel_message(
            message.chat.id,
            f"Current SMS Text:\n\n<code>{CUSTOM_SMS_TEXT}</code>\n\nSend new SMS text now:",
            delay=PANEL_AUTO_DELETE_DELAY
        )
        bot.register_next_step_handler(msg, update_sms_text_process)

    elif text == "⏰ Group Send Time":
        msg = send_panel_message(
            message.chat.id,
            f"Current Default Group Send Time: <b>{GROUP_SEND_DELAY} sec</b>\n\nSend new time in seconds\nExample: <code>120</code>\n\nএটা সব দেশের delay একসাথে set করবে.",
            delay=PANEL_AUTO_DELETE_DELAY
        )
        bot.register_next_step_handler(msg, update_group_send_time_process)

    elif text == "⬅ Back":
        send_panel_message(message.chat.id, "⬅ <b>Back To Main Menu</b>")

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

            try:
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=countries_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass

        elif call.data == "add_country":
            msg = send_panel_message(
                call.message.chat.id,
                "Send format like:\n\n<code>🇯🇵 Japan #JP +819 Telegram</code>",
                delay=PANEL_AUTO_DELETE_DELAY
            )
            bot.register_next_step_handler(msg, add_country_process)
            bot.answer_callback_query(call.id)

        elif call.data == "delete_country":
            try:
                bot.edit_message_text(
                    "🗑 <b>Select country to delete</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=delete_country_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass
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
            try:
                bot.edit_message_text(
                    "🗑 <b>Select country to delete</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=delete_country_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass

        elif call.data == "show_countries":
            try:
                bot.edit_message_text(
                    "🌍 <b>Country Manager</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=countries_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass
            bot.answer_callback_query(call.id)

        elif call.data.startswith("service_"):
            i = int(call.data.split("_")[1])
            kb = select_service_keyboard(i)
            if kb is None:
                bot.answer_callback_query(call.id, "Invalid country")
                return
            try:
                bot.edit_message_text(
                    "🔧 <b>Select Service</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass
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
            try:
                bot.edit_message_text(
                    "🔧 <b>Select Country</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=services_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass

        elif call.data == "show_services":
            try:
                bot.edit_message_text(
                    "🔧 <b>Select Country</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=services_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass
            bot.answer_callback_query(call.id)

        elif call.data == "show_country_delay":
            try:
                bot.edit_message_text(
                    "⏱ <b>Select Country For Delay</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=country_delay_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass
            bot.answer_callback_query(call.id)

        elif call.data.startswith("countrydelay_"):
            i = int(call.data.split("_")[1])
            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                cname = countries[i]["name"]
            try:
                bot.edit_message_text(
                    f"⏱ <b>Set Delay For {cname}</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=country_delay_options_keyboard(i)
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass
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
            try:
                bot.edit_message_text(
                    "⏱ <b>Select Country For Delay</b>",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=country_delay_keyboard()
                )
                auto_delete(call.message.chat.id, call.message.message_id, PANEL_AUTO_DELETE_DELAY)
            except Exception:
                pass

        elif call.data.startswith("customcdelay_"):
            i = int(call.data.split("_")[1])
            with data_lock:
                if i < 0 or i >= len(countries):
                    bot.answer_callback_query(call.id, "Invalid country")
                    return
                cname = countries[i]["name"]
            pending_country_delay_index[call.message.chat.id] = i
            msg = send_panel_message(
                call.message.chat.id,
                f"Send custom delay in seconds for <b>{cname}</b>\n\nExample: <code>1</code> / <code>5</code> / <code>60</code>",
                delay=PANEL_AUTO_DELETE_DELAY
            )
            bot.register_next_step_handler(msg, set_custom_country_delay)
            bot.answer_callback_query(call.id)

        elif call.data == "back_main":
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            send_panel_message(call.message.chat.id, "⬅ <b>Back To Main Menu</b>")
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
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

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
                "delay": GROUP_SEND_DELAY,
                "last_sent": 0
            })

        save_data()
        send_panel_message(message.chat.id, f"✅ <b>Country Added</b>\n\n{flag} {name} {code} {prefix} {service}")

    except Exception:
        send_panel_message(
            message.chat.id,
            "❌ <b>Wrong Format</b>\n\nUse:\n<code>🇯🇵 Japan #JP +819 Telegram</code>"
        )

def set_custom_time(message):
    global AUTO_DELETE_DELAY
    if not is_admin(message.from_user.id):
        return
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

    try:
        sec = int((message.text or "").strip())
        if sec < 1:
            send_panel_message(message.chat.id, "❌ Minimum 1 sec")
            return
        with data_lock:
            AUTO_DELETE_DELAY = sec
        save_data()
        send_panel_message(message.chat.id, f"⏱ <b>Auto Delete Time Set:</b> {sec} sec")
    except Exception:
        send_panel_message(message.chat.id, "❌ Invalid number")

def update_channel_link_process(message):
    global CHANNEL_LINK
    if not is_admin(message.from_user.id):
        return
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

    text = (message.text or "").strip()
    if not text.startswith("https://t.me/"):
        send_panel_message(message.chat.id, "❌ Invalid channel link")
        return
    CHANNEL_LINK = text
    save_data()
    send_panel_message(message.chat.id, f"✅ <b>Channel Link Updated</b>\n\n{CHANNEL_LINK}")

def update_bot_link_process(message):
    global BOT_LINK
    if not is_admin(message.from_user.id):
        return
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

    text = (message.text or "").strip()
    if not text.startswith("https://t.me/"):
        send_panel_message(message.chat.id, "❌ Invalid bot link")
        return
    BOT_LINK = text
    save_data()
    send_panel_message(message.chat.id, f"✅ <b>Bot Link Updated</b>\n\n{BOT_LINK}")

def update_sms_text_process(message):
    global CUSTOM_SMS_TEXT
    if not is_admin(message.from_user.id):
        return
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

    text = (message.text or "").strip()
    if not text:
        send_panel_message(message.chat.id, "❌ SMS text empty হতে পারবে না")
        return
    CUSTOM_SMS_TEXT = text
    save_data()
    send_panel_message(message.chat.id, f"✅ <b>SMS Text Updated</b>\n\n<code>{CUSTOM_SMS_TEXT}</code>")

def update_group_send_time_process(message):
    global GROUP_SEND_DELAY
    if not is_admin(message.from_user.id):
        return
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

    try:
        sec = int((message.text or "").strip())
        if sec < 1:
            send_panel_message(message.chat.id, "❌ Minimum 1 sec")
            return

        GROUP_SEND_DELAY = sec
        with data_lock:
            for i in range(len(countries)):
                countries[i]["delay"] = sec

        save_data()
        send_panel_message(
            message.chat.id,
            f"✅ <b>Default Group Send Time Updated:</b> {GROUP_SEND_DELAY} sec\nসব দেশের delay update হয়েছে।"
        )
    except Exception:
        send_panel_message(message.chat.id, "❌ Invalid number")

def set_custom_country_delay(message):
    if not is_admin(message.from_user.id):
        return
    delete_user_message_later(message.chat.id, message.message_id, PANEL_AUTO_DELETE_DELAY)

    chat_id = message.chat.id
    if chat_id not in pending_country_delay_index:
        send_panel_message(chat_id, "❌ No country selected")
        return

    try:
        sec = int((message.text or "").strip())
        if sec < 1:
            send_panel_message(chat_id, "❌ Minimum 1 sec")
            return

        idx = pending_country_delay_index[chat_id]
        with data_lock:
            if idx < 0 or idx >= len(countries):
                send_panel_message(chat_id, "❌ Invalid country")
                return
            countries[idx]["delay"] = sec
            cname = countries[idx]["name"]

        save_data()
        pending_country_delay_index.pop(chat_id, None)
        send_panel_message(chat_id, f"⏱ <b>{cname} Delay Set:</b> {sec} sec")

    except Exception:
        send_panel_message(chat_id, "❌ Invalid number")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    if TOKEN == "PASTE_NEW_BOT_TOKEN_HERE":
        raise ValueError("Please set BOT_TOKEN first.")

    load_data()
    threading.Thread(target=generator, daemon=True).start()

    print("BOT RUNNING...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            logging.error(f"Polling error: {e}")
            time.sleep(5)
