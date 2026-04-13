nity_polling()
import telebot
import random
import time
import threading
from telebot.types import *

TOKEN = "8632745463:AAFnXVv-TdZjfvctgiOGC-MUS4A7FRJ7BZw"

GROUP_ID = -1003549378995
ADMIN_ID = 8626918981

CHANNEL_LINK = "https://t.me/YOUR_CHANNEL"
BOT_LINK = "https://t.me/numberfast12_bot"

bot = telebot.TeleBot(TOKEN)

running = False
speed = 3
otp_count = 0

services = [
"Facebook",
"Telegram",
"Google",
"WhatsApp",
"TikTok",
"Apple",
"1xBet"
]

countries = [

{"name":"Bangladesh","flag":"🇧🇩","code":"#BD","prefix":"+88019","active":True,"service":"Telegram"},
{"name":"Italy","flag":"🇮🇹","code":"#IT","prefix":"+39347","active":True,"service":"Telegram"},
{"name":"USA","flag":"🇺🇸","code":"#US","prefix":"+1201","active":True,"service":"Google"},
{"name":"Pakistan","flag":"🇵🇰","code":"#PK","prefix":"+923","active":True,"service":"WhatsApp"},
{"name":"Vietnam","flag":"🇻🇳","code":"#VN","prefix":"+849","active":True,"service":"TikTok"}

]

def mask_number(prefix):

    last = random.randint(100,999)
    return f"{prefix}***{last}"

def generate_otp(service):

    if service == "Telegram":
        return random.randint(10000,99999)

    return random.randint(100000,999999)

def generator():

    global otp_count

    while True:

        if running:

            active = [c for c in countries if c["active"]]

            if not active:
                time.sleep(2)
                continue

            c = random.choice(active)

            number = mask_number(c["prefix"])
            otp = generate_otp(c["service"])

            text = f"""
{c['flag']} {c['name']} {c['code']} 📱 {c['service']}

{number}

🔑 {otp}
"""

            kb = InlineKeyboardMarkup()

            kb.row(
            InlineKeyboardButton("📢 Main Channel",url=CHANNEL_LINK),
            InlineKeyboardButton("🤖 Number Bot",url=BOT_LINK)
            )

            try:
                bot.send_message(GROUP_ID,text,reply_markup=kb)
                otp_count += 1
            except:
                pass

        time.sleep(speed)

threading.Thread(target=generator).start()

def main_menu():

    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("⚡ Speed","📊 OTP Stats")
    kb.row("🌍 Countries","🔧 Service Edit")
    kb.row("▶ Start Generator","⏹ Stop Generator")

    return kb

@bot.message_handler(commands=['start'])
def start(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(msg.chat.id,"🤖 OTP BOT READY",reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def panel(message):

    global running,speed,otp_count

    if message.from_user.id != ADMIN_ID:
        return

    if "OTP Stats" in message.text:

        bot.send_message(
        message.chat.id,
        f"📊 OTP Generated : {otp_count}"
        )

    elif "Countries" in message.text:

        keyboard = InlineKeyboardMarkup()

        for i,c in enumerate(countries):

            status = "✅" if c["active"] else "❌"

            keyboard.row(
            InlineKeyboardButton(
            f"{c['flag']} {c['name']} {status}",
            callback_data=f"country_{i}"
            )
            )

        keyboard.row(
        InlineKeyboardButton("➕ Add Country",callback_data="add_country"),
        InlineKeyboardButton("🗑 Delete Country",callback_data="delete_country")
        )

        keyboard.row(
        InlineKeyboardButton("⬅ Back",callback_data="back")
        )

        bot.send_message(message.chat.id,"🌍 Country Manager",reply_markup=keyboard)

    elif "Service Edit" in message.text:

        keyboard = InlineKeyboardMarkup()

        for i,c in enumerate(countries):

            keyboard.row(
            InlineKeyboardButton(
            f"{c['flag']} {c['name']}",
            callback_data=f"service_{i}"
            )
            )

        keyboard.row(
        InlineKeyboardButton("⬅ Back",callback_data="back")
        )

        bot.send_message(message.chat.id,"🔧 Select Country",reply_markup=keyboard)

    elif "Speed" in message.text:

        kb = ReplyKeyboardMarkup(resize_keyboard=True)

        kb.row("1s","2s","3s")
        kb.row("5s","10s","50s")
        kb.row("1m","2m")
        kb.row("⬅ Back")

        bot.send_message(message.chat.id,"⚡ Select Speed",reply_markup=kb)

    elif message.text.endswith("s"):

        speed = int(message.text.replace("s",""))
        bot.send_message(message.chat.id,f"⚡ Speed Set : {speed} sec")

    elif message.text.endswith("m"):

        speed = int(message.text.replace("m",""))*60
        bot.send_message(message.chat.id,f"⚡ Speed Set : {speed} sec")

    elif "Start Generator" in message.text:

        running = True
        bot.send_message(message.chat.id,"✅ Generator Started")

    elif "Stop Generator" in message.text:

        running = False
        bot.send_message(message.chat.id,"🛑 Generator Stopped")

    elif "Back" in message.text:

        bot.send_message(message.chat.id,"🔙 Back",reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call:True)
def callbacks(call):

    if call.from_user.id != ADMIN_ID:
        return

    if call.data.startswith("country_"):

        i = int(call.data.split("_")[1])

        countries[i]["active"] = not countries[i]["active"]

        status = "ON" if countries[i]["active"] else "OFF"

        bot.answer_callback_query(call.id,f"{countries[i]['name']} {status}")

    elif call.data == "add_country":

        msg = bot.send_message(
        call.message.chat.id,
        "Send country like:\n\n🇯🇵 Japan #JP +819 Telegram"
        )

        bot.register_next_step_handler(msg, add_country_process)

    elif call.data == "delete_country":

        kb = InlineKeyboardMarkup()

        for i,c in enumerate(countries):

            kb.row(
            InlineKeyboardButton(
            f"❌ {c['flag']} {c['name']}",
            callback_data=f"delcountry_{i}"
            )
            )

        bot.edit_message_text(
        "🗑 Select country to delete",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
        )

    elif call.data.startswith("delcountry_"):

        i = int(call.data.split("_")[1])

        name = countries[i]["name"]

        countries.pop(i)

        bot.answer_callback_query(call.id,f"{name} Deleted")

    elif call.data.startswith("service_"):

        i = int(call.data.split("_")[1])

        kb = InlineKeyboardMarkup()

        for s in services:

            kb.row(
            InlineKeyboardButton(
            s,
            callback_data=f"setservice_{i}_{s}"
            )
            )

        bot.edit_message_text(
        "Select Service",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
        )

    elif call.data.startswith("setservice_"):

        data = call.data.split("_")

        i = int(data[1])
        service = data[2]

        countries[i]["service"] = service

        bot.answer_callback_query(call.id,f"{countries[i]['name']} → {service}")

    elif call.data == "back":

        bot.delete_message(call.message.chat.id,call.message.message_id)

def add_country_process(message):

    try:

        data = message.text.split()

        flag = data[0]
        name = data[1]
        code = data[2]
        prefix = data[3]
        service = data[4]

        countries.append({
        "name":name,
        "flag":flag,
        "code":code,
        "prefix":prefix,
        "active":True,
        "service":service
        })

        bot.send_message(message.chat.id,"✅ Country Added")

    except:

        bot.send_message(message.chat.id,"❌ Wrong Format")

print("BOT RUNNING...")

bot.infinity_polling()
