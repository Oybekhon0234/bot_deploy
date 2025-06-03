
import asyncio
import re
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram import Bot, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# 🔑 Bot tokeni
BOT_TOKEN = "8154078356:AAFoT6TFKoRegA1Kx-0Rw-UgXf2hSoY_HeE"

# 🤖 Bot va Dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 📌 Ma’lumotlar bazasini yaratish
def create_database():
    conn = sqlite3.connect("parkins.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mashinalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mashina_raqami TEXT NOT NULL UNIQUE,
            ism_familiya TEXT NOT NULL,
            telefon_raqami TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
 

def save_data(mashina_raqami, ism_familiya, telefon_raqami):
    mashina_raqami = mashina_raqami.upper()
    telefon_raqami = re.sub(r'[^\d+]', '', telefon_raqami)

    if not re.fullmatch(r'\+998\d{9}', telefon_raqami):
        return "❌ Noto‘g‘ri telefon raqami. Format: +998991234567"
    if not (re.fullmatch(r'\d{2}[A-Z]\d{3}[A-Z]{2}', mashina_raqami) or re.fullmatch(r'[A-Z]{5}\d{3}', mashina_raqami) or re.fullmatch(r'\d{5}[A-Z]{3}', mashina_raqami)):
        return "❌ Noto‘g‘ri mashina raqami. Format: 30W111WW yoki VAA80202"

    conn = sqlite3.connect("parkins.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO mashinalar (mashina_raqami, ism_familiya, telefon_raqami)
        VALUES (?, ?, ?)
    """, (mashina_raqami, ism_familiya, telefon_raqami))
    conn.commit()
    conn.close()
    return "✅ Ma’lumotlar saqlandi."
def search_data(mashina_raqami):
    conn = sqlite3.connect("parkins.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ism_familiya, telefon_raqami FROM mashinalar WHERE mashina_raqami = ?
    """, (mashina_raqami.upper(),))
    result = cursor.fetchone()
    conn.close()
    return result

# 🚗 **Shtatlar guruhi (FSM)**
class RegisterCar(StatesGroup):
    waiting_for_car_number = State()
    waiting_for_owner_name = State()
    waiting_for_phone_number = State()
    waiting_for_search_query = State()

# 🔘 **Bosh menyu**
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()  # **Holatni tozalaymiz**
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚗 Mashina raqamini kiritish")],
            [KeyboardButton(text="🔍 Mashina raqami bo‘yicha qidiruv")]
        ],
        resize_keyboard=True
    )
    await message.answer("Quyidagilardan birini tanlang:", reply_markup=keyboard)

# 📌 **Mashina raqamini qo‘shish**
@dp.message(lambda message: message.text == "🚗 Mashina raqamini kiritish")
async def add_car_handler(message: types.Message, state: FSMContext):
    await message.answer("🚗 Mashina raqamini kiriting (Masalan: 30W111WW; 30202VAA):")
    await state.set_state(RegisterCar.waiting_for_car_number)

@dp.message(RegisterCar.waiting_for_car_number)
async def add_car_number(message: types.Message, state: FSMContext):
    formatted_plate = message.text.upper()
    if not (re.fullmatch(r'\d{2}[A-Z]\d{3}[A-Z]{2}', formatted_plate) or re.fullmatch(r'[A-Z]{5}\d{3}', formatted_plate) or re.fullmatch(r'\d{5}[A-Z]{3}', formatted_plate)):
        await message.answer("❌ Noto‘g‘ri format! To‘g‘ri format: 30W111WW yoki 30202VAA")
        return
    await state.update_data(mashina_raqami=formatted_plate)
    await message.answer("👤 Mashina egasining Ism va Familiyasini kiriting:")
    await state.set_state(RegisterCar.waiting_for_owner_name)

@dp.message(RegisterCar.waiting_for_owner_name)
async def add_owner_name(message: types.Message, state: FSMContext):
    await state.update_data(ism_familiya=message.text)
    await message.answer("📞 Telefon raqamini kiriting (+998991234567 yoki +998 99 123 45 67):")
    await state.set_state(RegisterCar.waiting_for_phone_number)

@dp.message(RegisterCar.waiting_for_phone_number)
async def add_phone_number(message: types.Message, state: FSMContext):
    telefon_raqami = re.sub(r'[^\d+]', '', message.text)  # Faqat raqam va + belgisi qolsin
    if not re.fullmatch(r'\+998\d{9}', telefon_raqami):
        await message.answer("❌ Noto‘g‘ri telefon raqami. Format: +998991234567")
        return
    
    data = await state.get_data()
    save_result = save_data(data["mashina_raqami"], data["ism_familiya"], telefon_raqami)
    await message.answer(save_result)
    await state.clear()

# 🔍 **Mashina raqami bo‘yicha qidiruv**
@dp.message(lambda message: message.text == "🔍 Mashina raqami bo‘yicha qidiruv")
async def search_data_callback(message: types.Message, state: FSMContext):
    await message.answer("🔎 Qidirish uchun mashina raqamini kiriting:")
    await state.set_state(RegisterCar.waiting_for_search_query)

@dp.message(RegisterCar.waiting_for_search_query)
async def search_car_handler(message: types.Message, state: FSMContext):
    result = search_data(message.text.upper())
    if result:
        await message.answer(f"✅ Topildi:\n👤 Ism: {result[0]}\n📞 Telefon: {result[1]}")
    else:
        await message.answer("❌ Bunday mashina raqami topilmadi.")
    await state.clear()

# 🚀 **Botni ishga tushirish**
async def main():
    create_database()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
