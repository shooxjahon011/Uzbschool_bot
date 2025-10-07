# TELEGRAM_BOT_TOKEN = "8183349980:AAFVCWlnygfU2YMDAFpBXNKO9QcwKzC5n-o"
# GEMINI_API_KEY = "AIzaSyB5eTQe2D0gU98Sd_BCmOnG9aABv1Li5UM"
import asyncio
import json
import datetime
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import google.generativeai as genai

# -------- LOG xabarlarni tozalash --------
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["GRPC_LOG_LEVEL"] = "ERROR"
logging.getLogger("google").setLevel(logging.ERROR)

# -------- Sozlamalar --------
TELEGRAM_BOT_TOKEN = "8183349980:AAFVCWlnygfU2YMDAFpBXNKO9QcwKzC5n-o"
GEMINI_API_KEY = "AIzaSyB5eTQe2D0gU98Sd_BCmOnG9aABv1Li5UM"
ADMIN_ID = 123456789  # Admin Telegram ID

DATA_FILE = "students.json"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# -------- JSON bilan ishlash --------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# -------- Asosiy menyu --------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Savol yuborish")],
        [KeyboardButton(text="📜 Dars tarixi"), KeyboardButton(text="❌ Chiqish")]
    ],
    resize_keyboard=True
)

# -------- /start komandasi --------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    uid = str(message.from_user.id)
    if uid not in data:
        data[uid] = {}
        save_data(data)
        await message.answer("Salom! 👋 Ismingizni kiriting:")
        return
    await message.answer("Xush kelibsiz! Endi savolingizni yozing yoki 'Savol yuborish'ni tanlang.", reply_markup=main_kb)

# -------- Ism, familiya, sinf so‘rash --------
@dp.message()
async def handle_message(message: types.Message):
    uid = str(message.from_user.id)
    text = message.text.strip()

    # Ism kiritilmagan
    if "ism" not in data.get(uid, {}):
        data[uid]["ism"] = text
        save_data(data)
        await message.answer("Familiyangizni kiriting:")
        return

    # Familiya kiritilmagan
    if "familiya" not in data.get(uid, {}):
        data[uid]["familiya"] = text
        save_data(data)
        await message.answer("Sinfingizni kiriting:")
        return

    # Sinf kiritilmagan
    if "sinf" not in data.get(uid, {}):
        data[uid]["sinf"] = text.upper()
        save_data(data)
        await message.answer("✅ Rahmat! Endi savolingizni yozing.", reply_markup=main_kb)
        return

    # Chiqish tugmasi
    if text == "❌ Chiqish":
        await message.answer("Xayr! 👋", reply_markup=types.ReplyKeyboardRemove())
        return

    # Dars tarixi
    if text == "📜 Dars tarixi":
        lessons = data[uid].get("savollar", [])
        if not lessons:
            await message.answer("Siz hali hech narsa yozmagansiz.", reply_markup=main_kb)
        else:
            msg = "\n\n".join(
                [f"📅 {s['vaqt']}\n💬 {s['savol']}" for s in lessons[-10:]]
            )
            await message.answer("🧾 Oxirgi dars:\n\n" + msg, reply_markup=main_kb)
        return

    # Savol yuborish tugmasi
    if text == "Savol yuborish":
        await message.answer("Iltimos, savolingizni yozing 👇", reply_markup=main_kb)
        return

    # Asosiy savol — AI ga yuborish
    ism = data[uid].get("ism", "Noma’lum")
    familiya = data[uid].get("familiya", "Noma’lum")
    sinf = data[uid].get("sinf", "Noma’lum")
    vaqt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Savolni tarixga yozish
    data[uid].setdefault("savollar", []).append({
        "savol": text,
        "vaqt": vaqt
    })
    save_data(data)

    # Admin(ga) yuborish
    admin_msg = (
        f"📩 Yangi dars so‘rovi!\n"
        f"👤 Ism: {ism}\n"
        f"👥 Familiya: {familiya}\n"
        f"🏫 Sinf: {sinf}\n"
        f"💬 Savol: {text}\n"
        f"🕒 Sana: {vaqt}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_msg)
    except Exception as e:
        print(f"Admin ga yuborilmadi: {e}")

    # AI javobi
    try:
        response = model.generate_content(text)
        javob = response.text.strip() if hasattr(response, "text") else "Javobni olishda xato yuz berdi."
    except Exception:
        javob = "AI bilan bog‘lanishda xato yuz berdi."

    await message.answer(javob, reply_markup=main_kb)

# -------- Dastur ishga tushirish --------
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
