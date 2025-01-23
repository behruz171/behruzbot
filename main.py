from aiogram import Bot, Dispatcher, executor, types
import sqlite3
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = "6538736550:AAGUxaYjBWdwbERkVkyYA9FbaxjcD-oMVSc"  # Bot tokeningizni kiriting
MY_TELEGRAM_ID = 6550264522  # O'zingizning Telegram IDingizni kiriting

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

class Form(StatesGroup):
    reply_to_message = State()
# SQLite bilan ishlash uchun bazani yaratish
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS group_chat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_chat_id INTEGER)''')
    conn.commit()
    conn.close()

def save_group_chat_id(group_chat_id):
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute("INSERT INTO group_chat (group_chat_id) VALUES (?)", (group_chat_id,))
    conn.commit()
    conn.close()

def get_group_chat_id():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute("SELECT group_chat_id FROM group_chat ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

init_db()  # SQLite bazasini yaratish

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if message.chat.type in ['group', 'supergroup']:
        group_chat_id = message.chat.id
        save_group_chat_id(group_chat_id)  # Guruh chat ID saqlanadi
        await message.reply("Guruh chat ID saqlandi!")
    elif message.chat.id == MY_TELEGRAM_ID:
        await message.reply("Salom! Men yordamga tayyorman.")
    else:
        await message.reply("Bu bot faqat guruhlarda ishlaydi.")

# Guruhdagi xabarlarni qabul qilish va botga yuborish
@dp.message_handler(lambda message: message.chat.id != MY_TELEGRAM_ID and message.chat.type in ['group', 'supergroup'],  content_types=types.ContentTypes.ANY)
async def handle_group_messages(message: types.Message):
    group_chat_id = get_group_chat_id()  # Guruh chat ID olish
    print(message)
    if group_chat_id:
        sender_name = message.from_user.full_name
        reply_button = InlineKeyboardButton(text=f"Javob berish {sender_name}",
                                            callback_data=f"reply_{message.message_id}")
        keyboard = InlineKeyboardMarkup(row_width=1).add(reply_button)

        if message.text:
            await bot.send_message(MY_TELEGRAM_ID, f"Kimdan: {sender_name}\nXabar: {message.text}",
                                   reply_markup=keyboard)
        elif message.photo:
            await bot.send_photo(MY_TELEGRAM_ID, message.photo[-1].file_id, caption=f"Kimdan: {sender_name}",
                                 reply_markup=keyboard)
        elif message.sticker:
            await bot.send_sticker(MY_TELEGRAM_ID, message.sticker.file_id, reply_markup=keyboard)
        elif message.animation:  # GIF uchun
            await bot.send_animation(MY_TELEGRAM_ID, message.animation.file_id, reply_markup=keyboard)

# Faqat sizdan kelgan xabarlarni guruhga yuborish
@dp.message_handler(lambda message: message.chat.id == MY_TELEGRAM_ID,  content_types=types.ContentTypes.ANY)
async def handle_personal_messages(message: types.Message):
    group_chat_id = get_group_chat_id()  # Guruh ID olish
    if group_chat_id:
        if message.text:
            await bot.send_message(group_chat_id, message.text)
        elif message.photo:
            await bot.send_photo(group_chat_id, message.photo[-1].file_id)
        elif message.sticker:
            await bot.send_sticker(group_chat_id, message.sticker.file_id)
        elif message.animation:  # GIF uchun
            await bot.send_animation(group_chat_id, message.animation.file_id)
        elif message.document:  # Fayl uchun
            await bot.send_document(group_chat_id, message.document.file_id)
        else:
            await message.reply("Guruh chat ID hali aniqlanmagan.")


# Inline buttonni bosganida ishlaydigan callback handler@dp.callback_query_handler(lambda c: c.data.startswith('reply_'))
@dp.callback_query_handler(lambda c: c.data.startswith('reply_'))
async def handle_inline_button(callback_query: types.CallbackQuery, state: FSMContext):
    message_id = int(callback_query.data.split('_')[1])
    # Foydalanuvchidan habar yuborishini so'raymiz
    await bot.send_message(
        callback_query.from_user.id,
        "Iltimos, javob xabarini yuboring:",
    )

    # Javob yozish uchun state'ni sozlash
    await state.update_data(message_id=message_id)
    await Form.reply_to_message.set()  # Form.reply_to_message - bu holatni saqlash
    # Callbackni yopish
    await callback_query.answer()


@dp.message_handler(state=Form.reply_to_message)
async def process_reply_message(message: types.Message, state: FSMContext):
    # O'zgartirishlarni amalga oshiramiz
    # group_chat_id = get_group_chat_id()  # Guruh chat ID olish
    user_data = await state.get_data()
    message_id = user_data.get("message_id")
    if message_id:
        # Guruhga yoki admin chatga xabarni yuboramiz
        group_chat_id = get_group_chat_id()  # Guruh chat ID olish
        if group_chat_id:
            # Javob xabarni yuborish
            await bot.send_message(
                group_chat_id,
                message.text,  # Foydalanuvchidan olingan xabar matni
                reply_to_message_id=message_id  # Oldingi xabarga javob sifatida
            )
            await message.reply("Javob yuborildi!")
        else:
            await message.reply("Guruh chat ID aniqlanmagan.")
    else:
        await message.reply("Javob beriladigan xabar topilmadi.")

        # Xabar yuborilgandan so'ng, holatni tozalash
    await state.finish()
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
