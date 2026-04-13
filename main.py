import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
import threading

TOKEN = "8632745463:AAFnXVv-TdZjfvctgiOGC-MUS4A7FRJ7BZw"
ADMIN_ID = 8626918981
GROUP_ID = --1003549378995  # নিজের group id বসা

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
lock = threading.Lock()

# -----------------------------
# GENERIC INVENTORY DATA
# -----------------------------
inventory = {
    "Telegram": {
        "Nepal": {"flag": "🇳🇵", "count": 12},
        "Bangladesh": {"flag": "🇧🇩", "count": 8},
        "USA": {"flag": "🇺🇸", "count": 5}
    },
    "WhatsApp": {
        "Nepal": {"flag": "🇳🇵", "count": 7},
        "Pakistan": {"flag": "🇵🇰", "count": 9}
    }
}

user_state = {}


# -----------------------------
# HELPERS
# -----------------------------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def state_of(user_id: int):
    if user_id not in user_state:
        user_state[user_id] = {"service": None, "country": None}
    return user_state[user_id]


def main_admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("👁 User Panel", "🧩 Services")
    kb.row("🌍 Countries", "📦 Stock")
    kb.row("📢 Group Consume Panel")
    return kb


def user_services_kb():
    kb = InlineKeyboardMarkup()
    with lock:
        for service in inventory.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📱 {service}",
                    callback_data=f"user_service|{service}"
                )
            )
    return kb


def user_countries_kb(service):
    kb = InlineKeyboardMarkup()
    with lock:
        countries = inventory.get(service, {})
        for country, info in countries.items():
            kb.row(
                InlineKeyboardButton(
                    f"{info['flag']} {country} ({info['count']} items)",
                    callback_data=f"user_country|{service}|{country}"
                )
            )
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="user_back_services"))
    return kb


def admin_services_kb():
    kb = InlineKeyboardMarkup()
    with lock:
        for service in inventory.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📱 {service}",
                    callback_data=f"admin_service|{service}"
                )
            )
    kb.row(InlineKeyboardButton("➕ Add Service", callback_data="admin_add_service"))
    return kb


def admin_countries_service_kb():
    kb = InlineKeyboardMarkup()
    with lock:
        for service in inventory.keys():
            kb.row(
                InlineKeyboardButton(
                    f"📱 {service}",
                    callback_data=f"admin_countries_of|{service}"
                )
            )
    return kb


def admin_country_list_kb(service):
    kb = InlineKeyboardMarkup()
    with lock:
        for country, info in inventory.get(service, {}).items():
            kb.row(
                InlineKeyboardButton(
                    f"{info['flag']} {country} ({info['count']})",
                    callback_data=f"admin_country|{service}|{country}"
                )
            )
    kb.row(InlineKeyboardButton("➕ Add Country", callback_data=f"admin_add_country|{service}"))
    kb.row(InlineKeyboardButton("⬅ Back", callback_data="admin_country_services_back"))
    return kb


def admin_stock_country_kb():
    kb = InlineKeyboardMarkup()
    with lock:
        for service, countries in inventory.items():
            for country, info in countries.items():
                kb.row(
                    InlineKeyboardButton(
                        f"{info['flag']} {service} → {country} ({info['count']})",
                        callback_data=f"admin_stock|{service}|{country}"
                    )
                )
    return kb


def admin_group_consume_kb():
    kb = InlineKeyboardMarkup()
    with lock:
        for service, countries in inventory.items():
            for country, info in countries.items():
                kb.row(
                    InlineKeyboardButton(
                        f"➖ {info['flag']} {service} → {country} ({info['count']})",
                        callback_data=f"consume_one|{service}|{country}"
                    )
                )
    return kb


# -----------------------------
# START
# -----------------------------
@bot.message_handler(commands=["start"])
def start(message):
    if is_admin(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "🤖 Admin Panel Ready",
            reply_markup=main_admin_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            "📱 <b>Select a service:</b>",
            reply_markup=user_services_kb()
        )


# -----------------------------
# ADMIN TEXT MENU
# -----------------------------
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in [
    "👁 User Panel", "🧩 Services", "🌍 Countries", "📦 Stock", "📢 Group Consume Panel"
])
def admin_text_menu(message):
    text = message.text

    if text == "👁 User Panel":
        bot.send_message(
            message.chat.id,
            "📱 <b>Select a service:</b>",
            reply_markup=user_services_kb()
        )

    elif text == "🧩 Services":
        bot.send_message(
            message.chat.id,
            "🧩 Manage Services",
            reply_markup=admin_services_kb()
        )

    elif text == "🌍 Countries":
        bot.send_message(
            message.chat.id,
            "🌍 Select Service To Manage Countries",
            reply_markup=admin_countries_service_kb()
        )

    elif text == "📦 Stock":
        bot.send_message(
            message.chat.id,
            "📦 Select Country To Set Stock",
            reply_markup=admin_stock_country_kb()
        )

    elif text == "📢 Group Consume Panel":
        bot.send_message(
            message.chat.id,
            "📢 Consume 1 item from stock",
            reply_markup=admin_group_consume_kb()
        )


# -----------------------------
# CALLBACKS
# -----------------------------
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    user_id = call.from_user.id
    data = call.data

    # -------- USER PANEL --------
    if data.startswith("user_service|"):
        service = data.split("|", 1)[1]
        st = state_of(user_id)
        st["service"] = service
        st["country"] = None

        bot.edit_message_text(
            f"🌍 <b>Select a country for {service}:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=user_countries_kb(service)
        )
        bot.answer_callback_query(call.id)

    elif data.startswith("user_country|"):
        _, service, country = data.split("|", 2)

        with lock:
            info = inventory.get(service, {}).get(country)

        if not info:
            bot.answer_callback_query(call.id, "Not found")
            return

        text = (
            f"{info['flag']} <b>{country} {service}</b>\n\n"
            f"📦 Available Items: <b>{info['count']}</b>"
        )

        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("🌍 Change Country", callback_data=f"user_service|{service}"))
        kb.row(InlineKeyboardButton("📱 Main Services", callback_data="user_back_services"))

        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)

    elif data == "user_back_services":
        bot.edit_message_text(
            "📱 <b>Select a service:</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=user_services_kb()
        )
        bot.answer_callback_query(call.id)

    # -------- ADMIN SERVICES --------
    elif is_admin(user_id) and data == "admin_add_service":
        msg = bot.send_message(call.message.chat.id, "New service name পাঠাও")
        bot.register_next_step_handler(msg, process_add_service)
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_service|"):
        _, service = data.split("|", 1)
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("🗑 Delete Service", callback_data=f"admin_delete_service|{service}"))
        kb.row(InlineKeyboardButton("⬅ Back", callback_data="admin_services_back"))

        bot.edit_message_text(
            f"📱 <b>{service}</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data == "admin_services_back":
        bot.edit_message_text(
            "🧩 Manage Services",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_services_kb()
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_delete_service|"):
        _, service = data.split("|", 1)
        with lock:
            if service in inventory:
                del inventory[service]

        bot.edit_message_text(
            "🧩 Manage Services",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_services_kb()
        )
        bot.answer_callback_query(call.id, f"{service} deleted")

    # -------- ADMIN COUNTRIES --------
    elif is_admin(user_id) and data == "admin_country_services_back":
        bot.edit_message_text(
            "🌍 Select Service To Manage Countries",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_countries_service_kb()
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_countries_of|"):
        _, service = data.split("|", 1)
        bot.edit_message_text(
            f"🌍 Countries in {service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_country_list_kb(service)
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_add_country|"):
        _, service = data.split("|", 1)
        msg = bot.send_message(call.message.chat.id, f"{service} এর জন্য country name + flag পাঠাও\nExample:\nNepal 🇳🇵")
        bot.register_next_step_handler(msg, process_add_country, service)
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_country|"):
        _, service, country = data.split("|", 2)
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("🗑 Delete Country", callback_data=f"admin_delete_country|{service}|{country}"))
        kb.row(InlineKeyboardButton("⬅ Back", callback_data=f"admin_countries_of|{service}"))

        bot.edit_message_text(
            f"🌍 <b>{country}</b> in {service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)

    elif is_admin(user_id) and data.startswith("admin_delete_country|"):
        _, service, country = data.split("|", 2)
        with lock:
            if service in inventory and country in inventory[service]:
                del inventory[service][country]

        bot.edit_message_text(
            f"🌍 Countries in {service}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_country_list_kb(service)
        )
        bot.answer_callback_query(call.id, f"{country} deleted")

    # -------- ADMIN STOCK --------
    elif is_admin(user_id) and data.startswith("admin_stock|"):
        _, service, country = data.split("|", 2)

        with lock:
            current = inventory.get(service, {}).get(country, {}).get("count", 0)

        msg = bot.send_message(
            call.message.chat.id,
            f"{service} → {country}\nCurrent stock: {current}\n\nNew stock count পাঠাও"
        )
        bot.register_next_step_handler(msg, process_set_stock, service, country)
        bot.answer_callback_query(call.id)

    # -------- GROUP CONSUME --------
    elif is_admin(user_id) and data.startswith("consume_one|"):
        _, service, country = data.split("|", 2)

        with lock:
            info = inventory.get(service, {}).get(country)
            if not info:
                bot.answer_callback_query(call.id, "Not found")
                return

            if info["count"] > 0:
                info["count"] -= 1
                new_count = info["count"]
                flag = info["flag"]
            else:
                new_count = 0
                flag = info["flag"]

        bot.answer_callback_query(call.id, f"{country} stock now {new_count}")

        bot.edit_message_text(
            "📢 Consume 1 item from stock",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_group_consume_kb()
        )

        try:
            bot.send_message(
                GROUP_ID,
                f"📉 Consumed 1 item\n\n📱 Service: {service}\n{flag} Country: {country}\n📦 Remaining: {new_count}"
            )
        except Exception:
            pass


# -----------------------------
# NEXT STEP
# -----------------------------
def process_add_service(message):
    if not is_admin(message.from_user.id):
        return

    service = (message.text or "").strip()
    if not service:
        bot.send_message(message.chat.id, "❌ Empty name")
        return

    with lock:
        if service not in inventory:
            inventory[service] = {}

    bot.send_message(message.chat.id, f"✅ Service added: {service}")


def process_add_country(message, service):
    if not is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip()
    parts = raw.split()

    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Format:\nNepal 🇳🇵")
        return

    country = " ".join(parts[:-1])
    flag = parts[-1]

    with lock:
        if service not in inventory:
            inventory[service] = {}
        if country not in inventory[service]:
            inventory[service][country] = {
                "flag": flag,
                "count": 0
            }

    bot.send_message(message.chat.id, f"✅ Country added: {flag} {country}")


def process_set_stock(message, service, country):
    if not is_admin(message.from_user.id):
        return

    try:
        count = int((message.text or "").strip())
        if count < 0:
            bot.send_message(message.chat.id, "❌ 0 বা তার বেশি দিতে হবে")
            return
    except Exception:
        bot.send_message(message.chat.id, "❌ শুধু সংখ্যা দে")
        return

    with lock:
        if service in inventory and country in inventory[service]:
            inventory[service][country]["count"] = count

    bot.send_message(message.chat.id, f"✅ Stock set: {service} → {country} = {count}")


print("BOT RUNNING...")
bot.infinity_polling()
