# Bu bot yordamida maktabdagi o'quvchilar uchun dars jadvali,
# uy vazifalari, e'lonlar va sun'iy intellekt yordamida mavzularni tushuntirish mumkin.
# Qo'shimcha ravishda BSB va ChSB imtihonlari haqida ma'lumot beradi.

# --- Kerakli kutubxonalarni import qilish ---
import os
import json
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import re
import logging
import requests
import asyncio

# --- Global konfiguratsiya ---
# Bot tokeni va API kaliti muhit o'zgaruvchilari orqali olinadi.
# Botni ishga tushirishdan oldin, ularni o'rnatganingizga ishonch hosil qiling.
# Masalan: export BOT_TOKEN="your_token_here"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7395359797:AAE7ITSLYzwcgFGOqhaheOyzUNVd2Icv5D4")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBS_4Qp_TQTMMiOUL3YoUpgaWPVnpA1yqI")
DATA_FILE = "bot_data.json"
LOG_FILE = "bot_log.log"

# Loglarni sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- ConversationHandler uchun holatlar (states) ---
CHOOSING_CLASS = 1
CHOOSING_CLASS_PARALLEL = 2
CHOOSING_DAY = 3
AI_CHAT_STATE = 4

# --- Bot ma'lumotlari: Adminlar, Dars jadvallari, Uy vazifalar ---
# Adminlar lug'ati: Har bir sinfga bir yoki bir nechta admin user_id si beriladi
# DIQQAT: Bu ID raqamlarini o'zingizning haqiqiy Telegram ID raqamlaringizga o'zgartiring.
ADMINS = {
    "1a": [123456789], "1b": [987654321], "1d": [123456789], "1e": [123456789],
    "2a": [123456789], "2b": [123456789], "2d": [123456789], "2e": [123456789],
    "3a": [123456789], "3b": [123456789], "3d": [123456789], "3e": [123456789],
    "4a": [123456789], "4b": [123456789], "4d": [123456789], "4e": [123456789],
    "5a": [123456789], "5b": [987654321], "5d": [123456789], "5e": [123456789],
    "6a": [123456789], "6b": [123456789], "6d": [123456789], "6e": [123456789],
    "7a": [123456789], "7b": [123456789], "7d": [123456789], "7e": [123456789],
    "8a": [5220843231], "8b": [123456789], "8d": [123456789], "8e": [123456789],
    "9a": [123456789], "9b": [987654321], "9d": [123456789], "9e": [123456789],
    "10a": [123456789], "10b": [123456789], "10d": [123456789], "10e": [123456789],
    "11a": [123456789], "11b": [123456789], "11d": [123456789], "11e": [123456789],
}
# Super adminlar (hamma sinf uchun ishlaydi)
SUPER_ADMINS = [5220843231, 888888888]


# Foydalanuvchi tekshiruvi
def is_admin(user_id, sinf):
    if user_id in SUPER_ADMINS:
        return True
    return user_id in ADMINS.get(sinf, [])


# --- Dars jadvali, Uy vazifa, BSB va ChSB ma'lumotlarini saqlash uchun lug'atlar ---
# Dastur qayta ishga tushganda ma'lumotlar yo'qolmasligi uchun dastlab bo'sh qoldiriladi.
# Ular "load_data" funksiyasi orqali fayldan yuklab olinadi.
homeworks = {}
dars_jadvallari = {}
user_ids_by_class = {}
bsb_info = {}
chsb_info = {}


# --- Ma'lumotlarni faylga saqlash va fayldan yuklash funksiyalari ---
def save_data():
    """Barcha ma'lumotlarni JSON faylga saqlaydi."""
    data_to_save = {
        "homeworks": homeworks,
        "dars_jadvallari": dars_jadvallari,
        "user_ids_by_class": {k: list(v) for k, v in user_ids_by_class.items()},  # To'plamni ro'yxatga aylantirish
        "bsb_info": bsb_info,
        "chsb_info": chsb_info
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    logging.info("Ma'lumotlar JSON faylga saqlandi.")


def load_data():
    """Ma'lumotlarni JSON fayldan yuklaydi."""
    global homeworks, dars_jadvallari, user_ids_by_class, bsb_info, chsb_info
    # Dastlabki ma'lumotlar (agar fayl topilmasa ishlatiladi)
    initial_dars_jadvallari = {
        "1a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "1b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "1d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "1e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "2a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "2b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "2d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "2e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "3a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "3b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "3d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "3e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "4a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "4b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "4d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "4e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "5a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "5b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "5d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "5e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "6a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "6b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "6d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "6e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "7a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "7b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "7d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "7e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "8a": {"dushanba": "- Kelajak soati\n- Texnologiya\n- Biologiya\n- Adabiyot\n- Rus tili\n- Kimyo",
               "seshanba": "- Tarbiya\n- Matematika\n- Kimyo\n- Biologiya\n- Informatika\n- Ingliz tili",
               "chorshanba": "- Huquq\n- Ingliz tili\n- Matematika\n- O'zbekiston tarixi\n- Ona tili",
               "payshanba": "❌ Jadval qo‘shilmagan",
               "juma": "- O'zbekiston tarixi\n- Adabiyot\n- Matematika\n- Jismoniy tarbiya\n- Geometriya\n- Ona tili",
               "shanba": "- IBA/Geogra\n- Fizika\n- Ona tili\n- Jahon tarixi\n- Matematika\n- Ingliz tili", },
        "8b": {"dushanba": "- Kelajak soati\n- Fizika\n- Rus tili\n- Texnologiya\n- Metematika\n- Ingliz tili",
               "seshanba": "- Ingliz tili\n- Tarix\n- Matematika\n- O'zbekiston tarixi\n- Ingliz tili\n- Jismoniy tarbiya",
               "chorshanba": "❌ Jadval qo‘shilmagan",
               "payshanba": "❌ Jadval qo‘shilmagan",
               "juma": "❌ Jadval qo‘shilmagan",
               "shanba": "❌ Jadval qo‘shilmagan", },
        "8d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "8e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "9a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "9b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "9d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "9e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
               "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "10a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "10b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "10d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "10e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "11a": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "11b": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "11d": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", },
        "11e": {"dushanba": "- Boshqa fanlar...", "seshanba": "- Boshqa fanlar...", "chorshanba": "- Boshqa fanlar...",
                "payshanba": "- Boshqa fanlar...", "juma": "- Boshqa fanlar...", "shanba": "- Boshqa fanlar...", }}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            homeworks = data.get("homeworks", {})
            dars_jadvallari = data.get("dars_jadvallari", initial_dars_jadvallari)
            user_ids_by_class = {k: set(v) for k, v in
                                 data.get("user_ids_by_class", {}).items()}  # Ro'yxatni to'plamga aylantirish
            bsb_info = data.get("bsb_info", {})
            chsb_info = data.get("chsb_info", {})
        logging.info("Ma'lumotlar JSON fayldan muvaffaqiyatli yuklandi.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Ma'lumotlar faylini yuklashda xato: {e}. Bo'sh ma'lumotlar yaratilmoqda.")
        homeworks.clear()
        dars_jadvallari.update(initial_dars_jadvallari)
        user_ids_by_class.clear()
        bsb_info.clear()
        chsb_info.clear()
        # Dastlabki bo'sh lug'atlarni yaratish
        for key in ADMINS.keys():
            homeworks[key] = {}
            user_ids_by_class[key] = set()


# --- Bosh menyu tugmalari ---
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["📅 Dars jadvali", "📘 Uy vazifa"], ["📝 BSB", "📘 ChSB"], ["🧠 Sun'iy intellekt"]],
        resize_keyboard=True
    )


# --- Sinf tanlash menyusi ---
def class_selection_keyboard():
    return ReplyKeyboardMarkup(
        [[str(i)] for i in range(1, 12)],
        resize_keyboard=True
    )


def get_parallel_keyboard(sinf_number):
    buttons = [[f"{sinf_number}a", f"{sinf_number}b"], [f"{sinf_number}d", f"{sinf_number}e"], ["Orqaga"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# --- AI chat menyusi ---
def ai_chat_keyboard():
    return ReplyKeyboardMarkup([["Orqaga"]], resize_keyboard=True)


# --- /start buyrug'ini qabul qilish va sinfni tanlashni taklif qilish ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Sinfni tanlang:", reply_markup=class_selection_keyboard())
    return CHOOSING_CLASS


async def handle_class_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.isdigit() and 1 <= int(text) <= 11:
        keyboard = get_parallel_keyboard(text)
        await update.message.reply_text(f"✏️ {text}-sinf parallelni tanlang:", reply_markup=keyboard)
        context.user_data["sinf_number"] = text
        return CHOOSING_CLASS_PARALLEL

    await update.message.reply_text("❌ Iltimos, sinf raqamini kiriting.")
    return CHOOSING_CLASS


async def handle_parallel_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    if text == "orqaga":
        await update.message.reply_text("📚 Sinfni tanlang:", reply_markup=class_selection_keyboard())
        return CHOOSING_CLASS

    valid_classes = [f"{context.user_data['sinf_number']}{p}" for p in ["a", "b", "d", "e"]]
    if text in valid_classes:
        sinf = text
        context.user_data["sinf"] = sinf
        user_ids_by_class.setdefault(sinf, set()).add(user_id)
        save_data()  # Ma'lumotni saqlash
        await update.message.reply_text(
            f"✅ {sinf.upper()} sinfi tanlandi.\nQuyidagilardan birini tanlang:",
            reply_markup=main_menu_keyboard()
        )
        return CHOOSING_DAY

    await update.message.reply_text("❌ Bunday parallel sinf mavjud emas.")
    return CHOOSING_CLASS_PARALLEL


async def handle_main_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    sinf = context.user_data.get("sinf")
    user_id = update.message.from_user.id

    # --- Dars jadvali tugmasi bosilsa ---
    if text == "📅 Dars jadvali":
        if not sinf:
            await update.message.reply_text("❌ Avval sinfni tanlang!")
            return ConversationHandler.END
        days = [["Dushanba", "Seshanba"], ["Chorshanba", "Payshanba"], ["Juma", "Shanba"], ["Orqaga"]]
        keyboard = ReplyKeyboardMarkup(days, resize_keyboard=True)
        await update.message.reply_text("📅 Qaysi kunni ko‘rishni xohlaysiz?", reply_markup=keyboard)
        return CHOOSING_DAY

    if text.lower() in ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba"]:
        if not sinf:
            await update.message.reply_text("❌ Avval sinfni tanlang!")
            return ConversationHandler.END
        kun_nomi = text.lower()
        jadval_matni = dars_jadvallari.get(sinf, {}).get(kun_nomi, "😔 Bu kun uchun dars jadvali topilmadi.")
        vazifa = homeworks.get(sinf, {}).get(kun_nomi, "❌ Vazifa kiritilmagan.")

        matn = f"📅 **{sinf.upper()} sinfi uchun {kun_nomi.capitalize()} dars jadvali:**\n\n{jadval_matni}\n\n📘 *Uy vazifa*:\n{vazifa}"
        await update.message.reply_text(matn, parse_mode="Markdown")
        return CHOOSING_DAY

    if text == "Orqaga":
        await update.message.reply_text(f"✏️ {context.user_data['sinf_number']}-sinf parallelni tanlang:",
                                        reply_markup=get_parallel_keyboard(context.user_data['sinf_number']))
        return CHOOSING_CLASS_PARALLEL

    # --- Uy vazifa tugmasi bosilsa ---
    if text == "📘 Uy vazifa":
        if not sinf:
            await update.message.reply_text("❌ Avval sinfni tanlang!")
            return ConversationHandler.END
        vazifa = homeworks.get(sinf, {})
        if not vazifa:
            await update.message.reply_text("❌ Uy vazifa kiritilmagan.")
            return CHOOSING_DAY

        matn = f"📘 {sinf.upper()} uy vazifalar:\n\n"
        for kun, vaz in vazifa.items():
            matn += f"➡️ {kun.capitalize()}: {vaz}\n"
        await update.message.reply_text(matn)
        return CHOOSING_DAY

    # --- BSB tugmasi bosilganda ---
    if text == "📝 BSB":
        if not sinf:
            await update.message.reply_text("❌ Avval sinfni tanlang!")
            return ConversationHandler.END
        info = bsb_info.get(sinf)
        if info:
            caption = f"📅 **Sana:** {info['sana']}\n⏰ **Vaqti:** {info['vaqt']}\n📍 **Joy:** {info['joy']}"
            await update.message.reply_document(
                document=info['fayl_id'],
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("😔 Bu sinf uchun BSB haqida ma'lumot hali kiritilmagan.")
        return CHOOSING_DAY

    # --- ChSB tugmasi bosilganda ---
    if text == "📘 ChSB":
        if not sinf:
            await update.message.reply_text("❌ Avval sinfni tanlang!")
            return ConversationHandler.END
        info = chsb_info.get(sinf)
        if info:
            caption = f"📅 **Sana:** {info['sana']}\n⏰ **Vaqti:** {info['vaqt']}\n📍 **Joy:** {info['joy']}"
            await update.message.reply_document(
                document=info['fayl_id'],
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("😔 Bu sinf uchun ChSB haqida ma'lumot hali kiritilmagan.")
        return CHOOSING_DAY

    # --- Sun'iy intellekt tugmasi bosilganda ---
    if text == "🧠 Sun'iy intellekt":
        await update.message.reply_text(
            "🧠 AI chat rejimiga o'tdingiz. Istalgan mavzuda savol bering yoki tushuntirish so'rang. Tugatish uchun 'Orqaga' tugmasini bosing.",
            reply_markup=ai_chat_keyboard()
        )
        return AI_CHAT_STATE  # ConversationHandler ga holatni o'zgartirish

    await update.message.reply_text("❌ Iltimos, tugmalardan foydalaning.", reply_markup=main_menu_keyboard())
    return CHOOSING_DAY


# --- AI bilan suhbatlashish funksiyasi ---
async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if user_text.strip() == "Orqaga":
        await update.message.reply_text(
            "✅ AI chat rejimidan chiqdingiz. Asosiy menyu:",
            reply_markup=main_menu_keyboard()
        )
        return CHOOSING_DAY

    if not GEMINI_API_KEY:
        await update.message.reply_text("❌ Sun'iy intellekt funksiyasi sozlanmagan.")
        return AI_CHAT_STATE

    sent_message = await update.message.reply_text("⏳ Javob tayyorlanmoqda...")

    try:
        # Gemini API URL
        GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
        payload = {
            "contents": [{"parts": [{"text": user_text}]}],
            "tools": [{"google_search": {}}],
            "systemInstruction": {
                "parts": [{
                    "text": "Siz maktab o‘quvchilari uchun mavzularni oddiy va tushunarli tilda tushuntiradigan yordamchisiz. Javoblaringizni o'zbek tilida, qisqa va aniq qilib bering. Matematik formulalar uchun LaTeX formatidan foydalaning (masalan, $x^2 + y^2 = r^2$)."}]
            }
        }

        # API so'rovini yuborish
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload
        )
        response.raise_for_status()

        result = response.json()
        candidate = result.get("candidates", [{}])[0]
        generated_text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "❌ Javob topilmadi.")

        await sent_message.edit_text(generated_text)

    except requests.exceptions.RequestException as e:
        logging.error(f"API so'rovida xato: {e}")
        await sent_message.edit_text(
            "❌ Sun'iy intellekt bilan bog'lanishda xato yuz berdi. Iltimos, keyinroq urinib ko'ring.")
    except Exception as e:
        logging.error(f"Noma'lum xato: {e}")
        await sent_message.edit_text("❌ Kutilmagan xato yuz berdi.")

    return AI_CHAT_STATE


# --- Super adminlar uchun fayl yuklash funksiyasi ---
async def handle_admin_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in SUPER_ADMINS:
        return

    caption = update.message.caption if update.message.caption else ""
    match = re.search(r"/(bsb|chsb)\s+(\w+)(.*)", caption, re.IGNORECASE | re.DOTALL)

    if match:
        exam_type = match.group(1).lower()
        sinf = match.group(2).lower()
        details_text = match.group(3).strip()

        sana = re.search(r"Sana:\s*(.*)", details_text, re.IGNORECASE)
        vaqt = re.search(r"Vaqti:\s*(.*)", details_text, re.IGNORECASE)
        joy = re.search(r"Joy:\s*(.*)", details_text, re.IGNORECASE)

        sana = sana.group(1).strip() if sana else "Kiritilmagan"
        vaqt = vaqt.group(1).strip() if vaqt else "Kiritilmagan"
        joy = joy.group(1).strip() if joy else "Kiritilmagan"

        file_id = update.message.document.file_id

        info = {
            "sana": sana,
            "vaqt": vaqt,
            "joy": joy,
            "fayl_id": file_id
        }

        if exam_type == "bsb":
            bsb_info[sinf] = info
        else:  # chsb
            chsb_info[sinf] = info

        save_data()  # Ma'lumotni saqlash

        await update.message.reply_text(
            f"✅ {sinf.upper()} sinfi uchun **{exam_type.upper()}** ma'lumotlari va fayli muvaffaqiyatli saqlandi!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Faylni yuklashda xato. Iltimos, izohga quyidagi formatda yozing:\n\n"
            "**/bsb sinf_nomi\nSana:...\nVaqti:...\nJoy:...**"
        )


# --- Vazifa qo‘shish (/add) ---
async def add_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "ℹ️ Foydalanish: /add sinf kun vazifa\n\n"
            "Masalan: /add 10e dushanba Matematika: 25-masala",
            parse_mode="Markdown"
        )
        return

    sinf = context.args[0].lower()
    user_id = update.message.from_user.id

    if not is_admin(user_id, sinf):
        await update.message.reply_text("❌ Siz bu sinfning admini emassiz!")
        return

    day = context.args[1].lower()
    vazifa = " ".join(context.args[2:])

    if sinf not in homeworks:
        homeworks[sinf] = {}

    homeworks[sinf][day] = vazifa
    save_data()  # Ma'lumotni saqlash

    await update.message.reply_text(
        f"✅ {sinf.upper()} uchun {day.capitalize()} vazifa qo‘shildi:\n{vazifa}"
    )


# --- Vazifa o‘chirish (/del) ---
async def del_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ Foydalanish: /del sinf kun\n\nMasalan: /del 10e dushanba"
        )
        return

    sinf = context.args[0].lower()
    user_id = update.message.from_user.id

    if not is_admin(user_id, sinf):
        await update.message.reply_text("❌ Siz bu sinfning admini emassiz!")
        return

    day = context.args[1].lower()
    if sinf in homeworks and day in homeworks[sinf]:
        removed = homeworks[sinf].pop(day)
        save_data()  # Ma'lumotni saqlash
        await update.message.reply_text(
            f"🗑 {sinf.upper()} uchun {day.capitalize()} vazifa o‘chirildi:\n{removed}"
        )
    else:
        await update.message.reply_text("❌ Bu kun uchun vazifa topilmadi.")


# --- E'lon yuborish (/send) ---
async def send_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ Foydalanish: /send sinf_nomi xabar\n\n"
            "Masalan: /send 10a Bugun maktabda tadbir bor.\n"
            "Barcha sinflar uchun: /send all Barcha darslar bekor qilindi.",
            parse_mode="Markdown"
        )
        return

    target = context.args[0].lower()
    message_text = " ".join(context.args[1:])
    user_id = update.message.from_user.id

    if not is_admin(user_id, target) and target != "all" and not user_id in SUPER_ADMINS:
        await update.message.reply_text("❌ Sizda bu e'lonni yuborishga ruxsat yo‘q.")
        return

    sent_count = 0
    if target == "all":
        # Barcha foydalanuvchilarga xabar yuborish
        for sinf in user_ids_by_class:
            for user_id_to_send in user_ids_by_class[sinf]:
                try:
                    await context.bot.send_message(
                        chat_id=user_id_to_send,
                        text=f"📢 **E'lon:**\n{message_text}",
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                except Exception as e:
                    logging.error(f"Xabar yuborishda xato yuz berdi {user_id_to_send}: {e}")
        await update.message.reply_text(f"✅ E'lon barcha sinflardagi {sent_count} foydalanuvchiga yuborildi.")
    else:
        if target in user_ids_by_class:
            for user_id_to_send in user_ids_by_class[target]:
                try:
                    await context.bot.send_message(
                        chat_id=user_id_to_send,
                        text=f"📢 **E'lon ({target.upper()} sinfi):**\n{message_text}",
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                except Exception as e:
                    logging.error(f"Xabar yuborishda xato yuz berdi {user_id_to_send}: {e}")
            await update.message.reply_text(
                f"✅ E'lon {target.upper()} sinfining {sent_count} foydalanuvchisiga yuborildi.")
        else:
            await update.message.reply_text("❌ Bunday sinf topilmadi. Yoki bu sinfdan hali hech kim botga kirmagan.")


# --- Botni ishga tushirish ---
def main():
    """Botni ishga tushiruvchi asosiy funksiya."""
    # Ma'lumotlarni fayldan yuklash
    load_data()

    # Botni qurish
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_class_selection)],
            CHOOSING_CLASS_PARALLEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_parallel_selection)],
            CHOOSING_DAY: [
                MessageHandler(
                    filters.Regex(
                        "^(📅 Dars jadvali|📘 Uy vazifa|📝 BSB|📘 ChSB|🧠 Sun'iy intellekt|Dushanba|Seshanba|Chorshanba|Payshanba|Juma|Shanba|Orqaga)$"
                    ), handle_main_menu_message
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_message)
            ],
            AI_CHAT_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat)
            ]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("add", add_homework))
    app.add_handler(CommandHandler("del", del_homework))
    app.add_handler(CommandHandler("send", send_announcement))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.Caption(), handle_admin_file_upload))

    print("🤖 Bot ishlayapti...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

