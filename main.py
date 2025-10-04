import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from PIL import Image
import imagehash
import sqlite3
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("hashes.db")
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS images (chat_id INT, msg_id INT, hash TEXT)")
conn.commit()

async def download_file(file_id, filename):
    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.read()
            with open(filename, "wb") as f:
                f.write(data)

def get_hash(path):
    return str(imagehash.phash(Image.open(path)))

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Ответь на сообщение с картинкой и тегни меня, я проверю, была ли она в чате")

@dp.message(F.photo)
async def save_photo(msg: types.Message):
    photo = msg.photo[-1]
    filename = f"temp_{msg.message_id}.jpg"
    await download_file(photo.file_id, filename)

    hash_val = get_hash(filename)

    cur.execute("INSERT INTO images VALUES (?, ?, ?)", (msg.chat.id, msg.message_id, hash_val))
    conn.commit()

    os.remove(filename)

@dp.message()
async def check_repost(msg: types.Message):
    if not msg.reply_to_message.photo:
        return
    
    photo = msg.reply_to_message.photo[-1]
    filename = f"temp_check_{msg.reply_to_message.message_id}.jpg"
    await download_file(photo.file_id, filename)

    hash_val = get_hash(filename)
    os.remove(filename)

    cur.execute("SELECT msg_id, hash FROM images WHERE chat_id = ?", (msg.chat.id,))
    rows = cur.fetchall()

    for msg_id, h in rows:
        if imagehash.hex_to_hash(h) - imagehash.hex_to_hash(hash_val) <= 5:
            await msg.answer(f"Эта картинка уже постилась, [сообщение](https://t.me/c/{str(msg.chat.id)[4:]}/{msg_id})", parse_mode="Markdown")
            return
    
    await msg.answer("Эта картинка ещё не постилась ✅")

    

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
