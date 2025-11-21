import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp

BOT_TOKEN = os.environ.get('BOT_TOKEN')
REQUIRED_CHANNEL = os.getenv('REQUIRED_CHANNEL')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOADS_DIR = 'downloads'
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

class DownloadState(StatesGroup):
    waiting_for_url = State()
    waiting_for_quality = State()

@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        is_subscriber = member.status in ['member', 'administrator', 'creator']
    except:
        is_subscriber = False
    
    if not is_subscriber:
        await message.answer(
            f"❌ Подпишитесь на канал: {REQUIRED_CHANNEL}\n\n"
            "Затем нажмите /start"
        )
        return
    
    await message.answer(
        "🎬 Добро пожаловать!\n\n"
        "Я помогу вам скачать видео с YouTube, Instagram, TikTok, VK и других платформ в нужном вам качестве. "
        "Просто отправьте ссылку на видео и выберите желаемое качество (360p, 480p, 720p, 1080p или MP3)!\n\n"
        "Отправьте ссылку чтобы начать 👇"
    )
    await state.set_state(DownloadState.waiting_for_url)

@dp.message(DownloadState.waiting_for_url)
async def process_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ Введите корректную ссылку!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="360p", callback_data="quality_360")],
        [InlineKeyboardButton(text="480p", callback_data="quality_480")],
        [InlineKeyboardButton(text="720p", callback_data="quality_720")],
        [InlineKeyboardButton(text="1080p", callback_data="quality_1080")],
        [InlineKeyboardButton(text="MP3", callback_data="quality_mp3")],
    ])
    
    await state.update_data(url=url)
    await message.answer("Выберите качество:", reply_markup=keyboard)

@dp.callback_query(DownloadState.waiting_for_url)
async def process_quality(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url = data.get('url')
    quality = callback.data.split('_')[1]
    
    await callback.message.edit_text("⏳ Скачиваю...")
    
    try:
        if quality == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
                'quiet': True,
            }
        else:
            quality_map = {'360': '18', '480': '135', '720': '22', '1080': '137'}
            fmt = quality_map.get(quality, '22')
            ydl_opts = {
                'format': fmt,
                'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
                'quiet': True,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            
            if file_size > 2 * 1024 * 1024 * 1024:
                await callback.message.edit_text("❌ Файл слишком большой (>2GB)")
                os.remove(filepath)
            else:
                try:
                    file = FSInputFile(filepath)
                    filename = os.path.basename(filepath)
                    await callback.message.answer_document(file, caption=f"✅ {filename}")
                    await callback.message.edit_text("✅ Готово!")
                except Exception as e:
                    await callback.message.edit_text(f"❌ Ошибка отправки: {str(e)[:100]}")
                finally:
                    if os.path.exists(filepath):
                        os.remove(filepath)
    
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)[:100]}")
    
    await state.set_state(DownloadState.waiting_for_url)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
