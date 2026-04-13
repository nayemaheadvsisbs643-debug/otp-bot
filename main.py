import telebot
import random
import time
import threading
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8632745463:AAFnXVv-TdZjfvctgiOGC-MUS4A7FRJ7BZw"
ADMIN_ID = 8626918981
GROUP_ID = --1003549378995  # নিজের group id বসা

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

lock = threading.Lock()

# -------------------------
# GLOBAL STATE
# -------------------------
bot_running = False
event_count = 0
user_state = {}

# folders -> services -> countries
data_store = {
    "Main": {
        "Telegram": {
            "Bangladesh": {
                "flag": "🇧🇩",
                "count": 7,
                "active": True,
                "interval": 5,
                "last_sent": 0
            },
            "USA": {
                "flag": "🇺🇸",
                "count": 5,
                "active": True,
                "interval": 8,
                "last_sent": 0
            }
        },
        "WhatsApp": {
            "Nepal": {
                "flag": "🇳🇵",
                "count": 7,
                "active": True,
                "interval": 10,
                "last_sent": 0
            },
            "Pakistan": {
                "flag": "🇵🇰",
                "count": 9,
                "active": True,
                "interval": 12,
                "last_sent": 0
            }
        }
    }
}


# -------------------------
# HELPERS
# -------------------------
def is_admin(user_id):
    return user_id == ADMIN_ID


def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {
            "folder": None,
            "service": None,
            "country": None,
            "token_index": None
        }
    return user_state[user_id]


def make_fake_token(service, country, idx):
    service_code = service[:2].upper()
    country_code = country[:2].upper()
    return f"{service_code}-{country_code}-{idx:03d}"


def get_country_info(folder, service, country):
    return data_store.get(folder, {}).get(service, {}).get(country)


def all_services():
    result = []
    seen = set()
    for folder, services in data_store.items():
        for service in services.keys():
            if service not in seen:
                result.append(service)
                seen.add(service)
    return result


def folders_keyboard():
    kb = InlineKeyboardMarkup()
    with lock:
        for folder in data_store.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📂 {folder}",
                    callback_data=f"user_folder|{folder}"
                )
            )
    return kb


def services_keyboard(folder):
    kb = InlineKeyboardMarkup()
    with lock:
        services = data_store.get(folder, {})
        for service in services.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📱 {service}",
                    callback_data=f"user_service|{folder}|{service}"
                )
            )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="user_back_folders"))
    return kb


def countries_keyboard(folder, service):
    kb = InlineKeyboardMarkup()
    with lock:
        countries = data_store.get(folder, {}).get(service, {})
        for country, info in countries.items():
            kb.row(
                InlineKeyboardButton(
                    f"{info['flag']} {country} ({info['count']} items)",
                    callback_data=f"user_country|{folder}|{service}|{country}"
                )
            )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data=f"user_back_services|{folder}"))
    return kb


def selected_item_keyboard(folder, service, country):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(
            "🔄 Change Item",
            callback_data=f"user_change_item|{folder}|{service}|{country}"
        )
    )
    kb.row(
        InlineKeyboardButton(
            "🌍 Change Country",
            callback_data=f"user_service|{folder}|{service}"
        ),
        InlineKeyboardButton(
            "📱 Change Service",
            callback_data=f"user_back_services|{folder}"
        )
    )
    kb.row(
        InlineKeyboardButton("📂 Main Folders", callback_data="user_back_folders")
    )
    return kb


def admin_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Stats", "🤖 Bot Control")
    kb.row("📂 Folders", "📱 Services")
    kb.row("🌍 Countries", "⏱ Intervals")
    kb.row("👁 User Panel")
    return kb


def admin_folder_keyboard():
    kb = InlineKeyboardMarkup()
    with lock:
        for folder in data_store.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📂 {folder}",
                    callback_data=f"admin_folder|{folder}"
                )
            )
    kb.row(InlineKeyboardButton("➕ Add Folder", callback_data="admin_add_folder"))
    return kb


def admin_folder_manage_keyboard(folder):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🗑 Delete Folder", callback_data=f"admin_delete_folder|{folder}"))
    kb.row(InlineKeyboardButton("📱 Manage Services", callback_data=f"admin_services_of_folder|{folder}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="admin_back_folders"))
    return kb


def admin_services_folder_keyboard():
    kb = InlineKeyboardMarkup()
    with lock:
        for folder in data_store.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📂 {folder}",
                    callback_data=f"admin_services_folder|{folder}"
                )
            )
    return kb


def admin_services_keyboard(folder):
    kb = InlineKeyboardMarkup()
    with lock:
        for service in data_store.get(folder, {}).keys():
            kb.row(
                InlineKeyboardButton(
                    f"📱 {service}",
                    callback_data=f"admin_service|{folder}|{service}"
                )
            )
    kb.row(InlineKeyboardButton("➕ Add Service", callback_data=f"admin_add_service|{folder}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="admin_services_folder_back"))
    return kb


def admin_service_manage_keyboard(folder, service):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🗑 Delete Service", callback_data=f"admin_delete_service|{folder}|{service}"))
    kb.row(InlineKeyboardButton("🌍 Manage Countries", callback_data=f"admin_countries_of|{folder}|{service}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data=f"admin_services_folder|{folder}"))
    return kb


def admin_country_service_picker():
    kb = InlineKeyboardMarkup()
    with lock:
        for folder, services in data_store.items():
            for service in services.keys():
                kb.row(
                    InlineKeyboardButton(
                        f"📂 {folder} → 📱 {service}",
                        callback_data=f"admin_countries_of|{folder}|{service}"
                    )
                )
    return kb


def admin_countries_keyboard(folder, service):
    kb = InlineKeyboardMarkup()
    with lock:
        for country, info in data_store.get(folder, {}).get(service, {}).items():
            status = "✅" if info["active"] else "❌"
            kb.row(
                InlineKeyboardButton(
                    f"{info['flag']} {country} {status} | {info['count']} | {info['interval']}s",
                    callback_data=f"admin_country|{folder}|{service}|{country}"
                )
            )
    kb.row(InlineKeyboardButton("➕ Add Country", callback_data=f"admin_add_country|{folder}|{service}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="admin_back_country_picker"))
    return kb


def admin_country_manage_keyboard(folder, service, country):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🔁 Toggle ON/OFF", callback_data=f"admin_toggle_country|{folder}|{service}|{country}"))
    kb.row(InlineKeyboardButton("🗑 Delete Country", callback_data=f"admin_delete_country|{folder}|{service}|{country}"))
    kb.row(InlineKeyboardButton("⏱ Set Interval", callback_data=f"admin_set_interval|{folder}|{service}|{country}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data=f"admin_countries_of|{folder}|{service}"))
    return kb


def admin_intervals_picker():
    kb = InlineKeyboardMarkup()
    with lock:
        for folder, services in data_store.items():
            for service, countries in services.items():
                for country, info in countries.items():
                    kb.row(
                        InlineKeyboardButton(
                            f"{info['flag']} {folder}/{service}/{country} ({info['interval']}s)",
                            callback_data=f"admin_set_interval|{folder}|{service}|{country}"
                        )
                    )
    return kb


# -------------------------
# SIMULATOR THREAD
# -------------------------
def simulator():
    global event_count, bot_running

    while True:
        try:
            with lock:
                current_running = bot_running
                snapshot = []
                for folder, services in data_store.items():
                    for service, countries in services.items():
                        for country, info in countries.items():
                            snapshot.append((folder, service, country, info.copy()))

            if current_running:
                now = time.time()

                for folder, service, country, info in snapshot:
                    if not info["active"]:
                        continue

                    if now - info["last_sent"] >= info["interval"]:
                        fake_id = random.randint(100, 999)
                        text = (
                            f"📡 <b>Fake Simulator Event</b>\n\n"
                            f"📂 Folder: {folder}\n"
                            f"📱 Service: {service}\n"
                            f"{info['flag']} Country: {country}\n"
                            f"🆔 Event ID: EVT-{fake_id}"
                        )

                        try:
                            bot.send_message(GROUP_ID, text)
                        except Exception:
                            pass

                        with lock:
                            try:
                                data_store[folder][service][country]["last_sent"] = time.time()
                                event_count += 1
                            except KeyError:
                                pass

                        time.sleep(0.4)

            time.sleep(1)

        except Exception:
            time.sleep(2)


threading.Thread(target=simulator, daemon=True).start()


# -------------------------
# START
# -------------------------
@bot.message_handler(commands=["start"])
def start(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🤖 Admin Panel Ready", reply_markup=admin_main_menu())
    else:
        bot.send_message(message.chat.id, "📂 <b>Select a folder:</b>", reply_markup=folders_keyboard())


# -------------------------
# ADMIN TEXT MENU
# -------------------------
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in [
    "📊 Stats", "🤖 Bot Control", "📂 Folders", "📱 Services", "🌍 Countries", "⏱ Intervals", "👁 User Panel"
])
def admin_menu_handler(message):
    global bot_running

    text = message.text

    if text == "📊 Stats":
        with lock:
            folder_count = len(data_store)
            service_count = sum(len(services) for services in data_store.values())
            country_count = sum(len(countries) for services in data_store.values() for countries in services.values())
            total_items = sum(info["count"] for services in data_store.values() for countries in services.values() for info in countries.values())
            status = "ON ✅" if bot_running else "OFF ❌"

        bot.send_message(
            message.chat.id,
            f"📊 <b>Stats</b>\n\n"
            f"🤖 Bot: {status}\n"
            f"📂 Folders: {folder_count}\n"
            f"📱 Services: {service_count}\n"
            f"🌍 Countries: {country_count}\n"
            f"📦 Total Items: {total_items}\n"
            f"📡 Events Sent: {event_count}"
        )

    elif text == "🤖 Bot Control":
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("✅ ON", callback_data="admin_bot_on"),
            InlineKeyboardButton("🛑 OFF", callback_data="admin_bot_off")
        )
        bot.send_message(message.chat.id, "🤖 Bot Control", reply_markup=kb)

    elif text == "📂 Folders":
        bot.send_message(message.chat.id, "📂 Manage Folders", reply_markup=admin_folder_keyboard())

    elif text == "📱 Services":
        bot.send_message(message.chat.id, "📱 Select Folder To Manage Services", reply_markup=admin_services_folder_keyboard())

    elif text == "🌍 Countries":
        bot.send_message(message.chat.id, "🌍 Select Service To Manage Countries", reply_markup=admin_country_service_picker())

    elif text == "⏱ Intervals":
        bot.send_message(message.chat.id, "⏱ Select Country To Set Interval", reply_markup=admin_intervals_picker())

    elif text == "👁 User Panel":
        bot.send_message(message.chat.id, "📂 <b>Select a folder:</b>", reply_markup=folders_keyboard())


# -------------------------
# CALLBACKS
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    global bot_running

    user_id = call.from_user.id
    data = call.data

    # ---------- USER PANEL ----------
    if data == "user_back_folders":
        bot.edit_message_text(
            "📂 <b>Select a folder:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=folders_keyboard()
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("user_folder|"):
        _, folder = data.split("|", 1)
        st = get_state(user_id)
        st["folder"] = folder
        st["service"] = None
        st["country"] = None
        st["token_index"] = None

        bot.edit_message_text(
            f"📱 <b>Select a service in {folder}:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=services_keyboard(folder)
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("user_back_services|"):
        _, folder = data.split("|", 1)
        bot.edit_message_text(
            f"📱 <b>Select a service in {folder}:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=services_keyboard(folder)
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("user_service|"):
        _, folder, service = data.split("|", 2)
        st = get_state(user_id)
        st["folder"] = folder
        st["service"] = service
        st["country"] = None
        st["token_index"] = None

        bot.edit_message_text(
            f"🌍 <b>Select a country for {service}:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=countries_keyboard(folder, service)
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("user_country|"):
        _, folder, service, country = data.split("|", 3)

        with lock:
            info = get_country_info(folder, service, country)

        if not info:
            bot.answer_callback_query(call.id, "Not found")
            return

        token_index = random.randint(1, max(1, info["count"]))
        token = make_fake_token(service, country, token_index)

        st = get_state(user_id)
        st["folder"] = folder
        st["service"] = service
        st["country"] = country
        st["token_index"] = token_index

        text = (
            f"{info['flag']} <b>{country} {service} Items:</b>\n\n"
            f"🎫 Item ID: <code>{token}</code>\n"
            f"📦 Available: <b>{info['count']}</b>\n\n"
            f"ℹ️ Demo item display"
        )

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=selected_item_keyboard(folder, service, country)
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("user_change_item|"):
        _, folder, service, country = data.split("|", 3)

        with lock:
            info = get_country_info(folder, service, country)

        if not info:
            bot.answer_callback_query(call.id, "Not found")
            return

        token_index = random.randint(1, max(1, info["count"]))
        token = make_fake_token(service, country, token_index)

        st = get_state(user_id)
        st["token_index"] = token_index

        text = (
            f"{info['flag']} <b>{country} {service} Items:</b>\n\n"
            f"🎫 Item ID: <code>{token}</code>\n"
            f"📦 Available: <b>{info['count']}</b>\n\n"
            f"ℹ️ Demo item display"
        )

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=selected_item_keyboard(folder, service, country)
        )
        bot.answer_callback_query(call.id, "Changed")

    # ---------- ADMIN BOT CONTROL ----------
    elif is_admin(user_id) and data == "admin_bot_on":
        with lock:
            bot_running = True
        bot.answer_callback_query(call.id, "Bot ON")
        bot.edit_message_text("🤖 Bot Status: ON ✅", call.message.chat.id, call.message.message_id)

    elif is_admin(user_id) and data == "admin_bot_off":
        with lock:
            bot_running = False
        bot.answer_callback_query(call.id, "Bot OFF")
        bot.edit_message_text("🤖 Bot Status: OFF ❌", call.message.chat.id, call.message.message_id)

    # ---------- ADMIN FOLDERS ----------
    elif is_admin(user_id) and data == "admin_back_folders":
        bot.edit_message_text(
            "📂 Manage Folders",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_folder_keyboard()
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data == "admin_add_folder":
        msg = bot.send_message(call.message.chat.id, "New folder name পাঠাও")
        bot.register_next_step_handler(msg, process_add_folder)
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_folder|"):
        _, folder = data.split("|", 1)
        bot.edit_message_text(
            f"📂 <b>{folder}</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_folder_manage_keyboard(folder)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_delete_folder|"):
        _, folder = data.split("|", 1)
        with lock:
            if folder in data_store and len(data_store) > 1:
                del data_store[folder]
                bot.answer_callback_query(call.id, f"{folder} deleted")
            else:
                bot.answer_callback_query(call.id, "Last folder delete করা যাবে না")

        bot.edit_message_text(
            "📂 Manage Folders",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_folder_keyboard()
        )

    # ---------- ADMIN SERVICES ----------
    elif is_admin(user_id) and data == "admin_services_folder_back":
        bot.edit_message_text(
            "📱 Select Folder To Manage Services",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_services_folder_keyboard()
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_services_folder|"):
        _, folder = data.split("|", 1)
        bot.edit_message_text(
            f"📱 Services in {folder}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_services_keyboard(folder)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_services_of_folder|"):
        _, folder = data.split("|", 1)
        bot.edit_message_text(
            f"📱 Services in {folder}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_services_keyboard(folder)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_add_service|"):
        _, folder = data.split("|", 1)
        msg = bot.send_message(call.message.chat.id, f"{folder} folder-এর জন্য new service name পাঠাও")
        bot.register_next_step_handler(msg, process_add_service, folder)
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_service|"):
        _, folder, service = data.split("|", 2)
        bot.edit_message_text(
            f"📱 <b>{service}</b> in {folder}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_service_manage_keyboard(folder, service)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_delete_service|"):
        _, folder, service = data.split("|", 2)
        with lock:
            if folder in data_store and service in data_store[folder] and len(data_store[folder]) > 1:
                del data_store[folder][service]
                bot.answer_callback_query(call.id, f"{service} deleted")
            else:
                bot.answer_callback_query(call.id, "Last service delete করা যাবে না")

        bot.edit_message_text(
            f"📱 Services in {folder}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_services_keyboard(folder)
        )

    # ---------- ADMIN COUNTRIES ----------
    elif is_admin(user_id) and data == "admin_back_country_picker":
        bot.edit_message_text(
            "🌍 Select Service To Manage Countries",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_country_service_picker()
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_countries_of|"):
        _, folder, service = data.split("|", 2)
        bot.edit_message_text(
            f"🌍 Countries in {folder}/{service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_countries_keyboard(folder, service)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_add_country|"):
        _, folder, service = data.split("|", 2)
        msg = bot.send_message(
            call.message.chat.id,
            "Country format:\n\nBangladesh 🇧🇩 7 5\n\n"
            "Format = Name Flag Count Interval"
        )
        bot.register_next_step_handler(msg, process_add_country, folder, service)
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_country|"):
        _, folder, service, country = data.split("|", 3)
        bot.edit_message_text(
            f"🌍 <b>{country}</b> in {folder}/{service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_country_manage_keyboard(folder, service, country)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_toggle_country|"):
        _, folder, service, country = data.split("|", 3)
        with lock:
            info = get_country_info(folder, service, country)
            if info:
                info["active"] = not info["active"]
                status = "ON ✅" if info["active"] else "OFF ❌"
                bot.answer_callback_query(call.id, f"{country} {status}")
            else:
                bot.answer_callback_query(call.id, "Not found")

        bot.edit_message_text(
            f"🌍 Countries in {folder}/{service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_countries_keyboard(folder, service)
        )

    elif is_admin(user_id) and data.startswith("admin_delete_country|"):
        _, folder, service, country = data.split("|", 3)
        with lock:
            if country in data_store.get(folder, {}).get(service, {}):
                del data_store[folder][service][country]
                bot.answer_callback_query(call.id, f"{country} deleted")
            else:
                bot.answer_callback_query(call.id, "Not found")

        bot.edit_message_text(
            f"🌍 Countries in {folder}/{service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_countries_keyboard(folder, service)
        )

    # ---------- ADMIN INTERVALS ----------
    elif is_admin(user_id) and data.startswith("admin_set_interval|"):
        _, folder, service, country = data.split("|", 3)
        current = 0
        with lock:
            info = get_country_info(folder, service, country)
            if info:
                current = info["interval"]

        msg = bot.send_message(
            call.message.chat.id,
            f"{folder}/{service}/{country}\nCurrent interval: {current}s\n\nNew seconds পাঠাও"
        )
        bot.register_next_step_handler(msg, process_set_interval, folder, service, country)
        bot.answer_callback_query(call.id)


# -------------------------
# NEXT STEP HANDLERS
# -------------------------
def process_add_folder(message):
    if not is_admin(message.from_user.id):
        return

    folder = (message.text or "").strip()
    if not folder:
        bot.send_message(message.chat.id, "❌ Empty folder name")
        return

    with lock:
        if folder not in data_store:
            data_store[folder] = {}

    bot.send_message(message.chat.id, f"✅ Folder added: {folder}")


def process_add_service(message, folder):
    if not is_admin(message.from_user.id):
        return

    service = (message.text or "").strip()
    if not service:
        bot.send_message(message.chat.id, "❌ Empty service name")
        return

    with lock:
        if folder not in data_store:
            data_store[folder] = {}
        if service not in data_store[folder]:
            data_store[folder][service] = {}

    bot.send_message(message.chat.id, f"✅ Service added: {folder} → {service}")


def process_add_country(message, folder, service):
    if not is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip().split()

    if len(raw) < 4:
        bot.send_message(message.chat.id, "❌ Format:\nBangladesh 🇧🇩 7 5")
        return

    try:
        name = " ".join(raw[:-3])
        flag = raw[-3]
        count = int(raw[-2])
        interval = int(raw[-1])
    except Exception:
        bot.send_message(message.chat.id, "❌ Wrong format")
        return

    with lock:
        if folder not in data_store:
            data_store[folder] = {}
        if service not in data_store[folder]:
            data_store[folder][service] = {}

        data_store[folder][service][name] = {
            "flag": flag,
            "count": count,
            "active": True,
            "interval": interval,
            "last_sent": 0
        }

    bot.send_message(
        message.chat.id,
        f"✅ Country added\n📂 {folder}\n📱 {service}\n🌍 {flag} {name}\n📦 {count}\n⏱ {interval}s"
    )


def process_set_interval(message, folder, service, country):
    if not is_admin(message.from_user.id):
        return

    try:
        sec = int((message.text or "").strip())
        if sec < 1:
            bot.send_message(message.chat.id, "❌ Minimum 1 second")
            return
    except Exception:
        bot.send_message(message.chat.id, "❌ শুধু number দে")
        return

    with lock:
        info = get_country_info(folder, service, country)
        if info:
            info["interval"] = sec

    bot.send_message(message.chat.id, f"✅ Interval updated: {folder}/{service}/{country} = {sec}s")


print("BOT RUNNING...")
bot.infinity_polling()
