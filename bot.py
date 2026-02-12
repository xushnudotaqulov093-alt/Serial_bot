import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = "BOT_TOKENINGNI_BU_YERGA_QO'Y"
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect("anime.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT UNIQUE,
            description TEXT,
            photo TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_code TEXT,
            part_number INTEGER,
            file_id TEXT
        )
        """)
        await db.commit()

# ================= KEYBOARDS =================
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Anemi izlash")],
        [KeyboardButton(text="⭐ Premium anemilar")],
        [KeyboardButton(text="🆕 Ongion anemilar")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi anemi qo‘shish")],
        [KeyboardButton(text="📌 Qism qo‘shish")]
    ],
    resize_keyboard=True
)

# ================= STATES =================
class AddAnime(StatesGroup):
    name = State()
    code = State()
    desc = State()
    photo = State()

class AddPart(StatesGroup):
    code = State()
    number = State()
    file = State()

class UserSearch(StatesGroup):
    code = State()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Admin panel", reply_markup=admin_kb)
    else:
        await message.answer("👋 Xush kelibsiz!", reply_markup=user_kb)

# ================= USER SEARCH =================
@dp.message(F.text == "🔍 Anemi izlash")
async def search_start(message: Message, state: FSMContext):
    await message.answer("Anemi kodini kiriting:")
    await state.set_state(UserSearch.code)

@dp.message(UserSearch.code)
async def search_code(message: Message, state: FSMContext):
    code = message.text.strip()
    async with aiosqlite.connect("anime.db") as db:
        anime = await db.execute_fetchone(
            "SELECT name, description, photo FROM anime WHERE code=?", (code,)
        )
        parts = await db.execute_fetchall(
            "SELECT part_number FROM parts WHERE anime_code=? ORDER BY part_number", (code,)
        )

    if not anime:
        await message.answer("❌ Anemi topilmadi")
        await state.clear()
        return

    name, desc, photo = anime

    kb = InlineKeyboardMarkup(row_width=5)
    btns = [
        InlineKeyboardButton(
            text=str(p[0]),
            callback_data=f"part:{code}:{p[0]}"
        ) for p in parts
    ]
    kb.add(*btns)

    await message.answer_photo(
        photo=photo,
        caption=f"📌 {name}\n\n{desc}",
        reply_markup=kb
    )
    await state.clear()

# ================= PART CLICK =================
@dp.callback_query(F.data.startswith("part:"))
async def send_part(call: types.CallbackQuery):
    _, code, part = call.data.split(":")
    async with aiosqlite.connect("anime.db") as db:
        row = await db.execute_fetchone(
            "SELECT file_id FROM parts WHERE anime_code=? AND part_number=?",
            (code, part)
        )
    if row:
        await call.message.answer_video(row[0], caption=f"{part}-qism")
    await call.answer()

# ================= PREMIUM =================
@dp.message(F.text == "⭐ Premium anemilar")
async def premium_list(message: Message):
    async with aiosqlite.connect("anime.db") as db:
        rows = await db.execute_fetchall("SELECT name, code FROM anime")

    text = ""
    for name, code in rows:
        if len(code) == 3:
            text += f"🎬 Anemi nomi: {name}\n🔑 Kod: {code}\n\n"

    await message.answer(text or "❌ Premium anemilar yo‘q")

# ================= ONGION =================
@dp.message(F.text == "🆕 Ongion anemilar")
async def ongoing_list(message: Message):
    async with aiosqlite.connect("anime.db") as db:
        rows = await db.execute_fetchall("SELECT name, code FROM anime")

    text = ""
    for name, code in rows:
        if len(code) == 5:
            text += f"🎬 Anemi nomi: {name}\n🔑 Kod: {code}\n\n"

    await message.answer(text or "❌ Ongion anemilar yo‘q")

# ================= ADMIN =================
@dp.message(F.text == "➕ Yangi anemi qo‘shish")
async def add_anime(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Nomi:")
    await state.set_state(AddAnime.name)

@dp.message(AddAnime.name)
async def a1(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Kodi:")
    await state.set_state(AddAnime.code)

@dp.message(AddAnime.code)
async def a2(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Tavsifi:")
    await state.set_state(AddAnime.desc)

@dp.message(AddAnime.desc)
async def a3(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Rasm yubor:")
    await state.set_state(AddAnime.photo)

@dp.message(AddAnime.photo, F.photo)
async def a4(message: Message, state: FSMContext):
    d = await state.get_data()
    async with aiosqlite.connect("anime.db") as db:
        await db.execute(
            "INSERT INTO anime (name, code, description, photo) VALUES (?,?,?,?)",
            (d["name"], d["code"], d["desc"], message.photo[-1].file_id)
        )
        await db.commit()
    await message.answer("✅ Saqlandi", reply_markup=admin_kb)
    await state.clear()

@dp.message(F.text == "📌 Qism qo‘shish")
async def p1(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Anemi kodi:")
    await state.set_state(AddPart.code)

@dp.message(AddPart.code)
async def p2(message: Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Qism raqami:")
    await state.set_state(AddPart.number)

@dp.message(AddPart.number)
async def p3(message: Message, state: FSMContext):
    await state.update_data(number=int(message.text))
    await message.answer("Video yubor:")
    await state.set_state(AddPart.file)

@dp.message(AddPart.file, F.video)
async def p4(message: Message, state: FSMContext):
    d = await state.get_data()
    async with aiosqlite.connect("anime.db") as db:
        await db.execute(
            "INSERT INTO parts (anime_code, part_number, file_id) VALUES (?,?,?)",
            (d["code"], d["number"], message.video.file_id)
        )
        await db.commit()
    await message.answer("✅ Qism qo‘shildi", reply_markup=admin_kb)
    await state.clear()

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())