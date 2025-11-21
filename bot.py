import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ChatMember
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from typing import Optional
from pathlib import Path

DOWNLOADS_DIR = "downloads"
BOT_TOKEN = "7924889067:AAHaQLLx9REvxay_Wt9qFbSgSJ3zYm6AHGc"
REQUIRED_CHANNEL = "https://t.me/+c89KSS6hqqA5YmRi"

Path(DOWNLOADS_DIR).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class DownloadStates(StatesGroup):
    waiting_for_link = State()
    choosing_format = State()

async def is_user_subscribed(user_id: int, channel_name: str) -> bool:
    try:
        if channel_name.startswith('@'):
            channel_name = channel_name[1:]
        member = await bot.get_chat_member(chat_id=f"@{channel_name}", user_id=user_id)
        status = member.status
        active_statuses = [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.RESTRICTED]
        return status in active_statuses
    except:
        return False

def detect_source(url: str) -> Optional[str]:
    sources = {
        'youtube': ['youtube.com', 'youtu.be', 'youtube.ru'],
        'instagram': ['instagram.com', 'instagr.am'],
        'tiktok': ['tiktok.com', 'vm.tiktok.com'],
        'vk': ['vk.com', 'vk.ru', 'm.vk.com'],
        'twitter': ['twitter.com', 'x.com'],
        'facebook': ['facebook.com'],
        'twitch': ['twitch.tv'],
        'reddit': ['reddit.com'],
    }
    for source, domains in sources.items():
        if any(domain in url.lower() for domain in domains):
            return source
    return None

async def get_video_info(url: str) -> Optional[dict]:
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Видео'),
                'duration': info.get('duration', 0),
            }
    except:
        return None

@dp.message_handler(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = """
🎬 <b>Video Downloader Bot</b>

Скачивай видео с популярных платформ!

<b>📊 СИСТЕМА ДОСТУПА:</b>

✅ <b>ОТКРЫТО (без подписки):</b>
  • 360p - Низкое качество
  • 480p - Среднее качество
  • MP3 - Аудиолог

🔒 <b>ТРЕБУЕТ ПОДПИСКУ:</b>
  • 720p (HD) - Хорошее качество
  • 1080p (Full HD) - Отличное
  • 1440p (2K) - Premium
  • 2160p (4K) - Максимум

Я скачиваю видео с YouTube, Instagram, TikTok, ВКонтакте и еще 1800+ сайтов!

<b>Как использовать:</b>
1. Отправьте ссылку на видео
2. Выберите качество
3. Получите файл
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить ссылку", callback_data="send_link")],
        [InlineKeyboardButton(text="❓ Справка", callback_data="help")],
    ])
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message_handler(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
<b>📖 Справка</b>

<b>✅ ОТКРЫТО (все могут скачивать):</b>
  360p - ~30MB за 10 минут видео
  480p - ~50MB за 10 минут видео
  MP3 - ~8MB за 10 минут видео

<b>🔒 ТРЕБУЕТ ПОДПИСКУ на канал:</b>
  720p (HD) - ~100MB за 10 минут видео
  1080p (Full HD) - ~200MB за 10 минут видео
  1440p (2K) - ~300MB за 10 минут видео
  2160p (4K) - ~500MB за 10 минут видео

<b>Примеры ссылок:</b>
https://youtu.be/dQw4w9WgXcQ
https://www.instagram.com/p/ABC...
https://www.tiktok.com/@user/video/123...
    """
    await message.answer(help_text, parse_mode="HTML")

@dp.message_handler(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено. /start")

@dp.callback_query_handler(lambda c: c.data == "send_link")
async def process_callback_send_link(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("📎 Отправьте ссылку на видео:")
    await state.set_state(DownloadStates.waiting_for_link)

@dp.callback_query_handler(lambda c: c.data == "help")
async def help_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("Справка отправлена через /help")

@dp.message_handler(DownloadStates.waiting_for_link)
async def process_link(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ Неверная ссылка")
        return
    source = detect_source(url)
    if not source:
        await message.answer("❌ Сайт не поддерживается")
        await state.clear()
        return
    await message.answer(f"✅ Источник: <b>{source.upper()}</b>\n⏳ Получаю информацию...", parse_mode="HTML")
    await state.update_data(url=url, source=source)
    try:
        info = await get_video_info(url)
        if not info:
            await message.answer("❌ Ошибка при получении информации")
            await state.clear()
            return
        await state.update_data(video_info=info)
        is_subscribed = await is_user_subscribed(message.from_user.id, REQUIRED_CHANNEL)
        info_text = f"""
<b>📹 {info.get('title', 'Видео')[:80]}</b>

⏱️ Длительность: {format_duration(info.get('duration', 0))}

<b>Выберите качество:</b>
        """
        buttons = [
            [InlineKeyboardButton(text="🎥 360p (открыто)", callback_data="q_360")],
            [InlineKeyboardButton(text="🎥 480p (открыто)", callback_data="q_480")],
        ]
        if is_subscribed:
            buttons.extend([
                [InlineKeyboardButton(text="🎥 720p (HD) ✅", callback_data="q_720")],
                [InlineKeyboardButton(text="🎥 1080p (Full HD) ✅", callback_data="q_1080")],
                [InlineKeyboardButton(text="🎥 1440p (2K) ✅", callback_data="q_1440")],
                [InlineKeyboardButton(text="🎥 2160p (4K) ✅", callback_data="q_2160")],
            ])
        else:
            buttons.append([InlineKeyboardButton(text="🔒 720p+ (требует подписку)", callback_data="q_locked")])
        buttons.extend([
            [InlineKeyboardButton(text="🎵 MP3 (открыто)", callback_data="q_mp3")],
            [InlineKeyboardButton(text="❌", callback_data="q_cancel")],
        ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(info_text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(DownloadStates.choosing_format)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:80]}")
        await state.clear()

@dp.callback_query_handler(lambda c: c.data.startswith('q_'))
async def process_download(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    quality = callback_query.data
    if quality == 'q_locked':
        channel_link = REQUIRED_CHANNEL.replace('@', '')
        await callback_query.message.answer(f"🔒 <b>720p+ требует подписку!</b>\n\n<a href=\"https://t.me/{channel_link}\">Подпишитесь на канал</a>\n\nПосле подписки попробуйте снова.", parse_mode="HTML")
        return
    if quality == 'q_cancel':
        await callback_query.message.edit_text("❌ Отменено. /start")
        await state.clear()
        return
    if quality in ['q_720', 'q_1080', 'q_1440', 'q_2160']:
        is_subscribed = await is_user_subscribed(callback_query.from_user.id, REQUIRED_CHANNEL)
        if not is_subscribed:
            channel_link = REQUIRED_CHANNEL.replace('@', '')
            await callback_query.message.answer(f"🔒 <b>720p+ требует подписку!</b>\n\n<a href=\"https://t.me/{channel_link}\">Подпишитесь</a>\n\nПосле подписки попробуйте снова.", parse_mode="HTML")
            return
    await callback_query.message.edit_text("⏳ Скачиваю видео...\nПожалуйста подождите")
    data = await state.get_data()
    url = data.get('url')
    try:
        if quality == 'q_360':
            fmt = 'best[height<=360]/best'
        elif quality == 'q_480':
            fmt = 'best[height<=480]/best'
        elif quality == 'q_720':
            fmt = 'best[height<=720]/best'
        elif quality == 'q_1080':
            fmt = 'best[height<=1080]/best[height<=720]'
        elif quality == 'q_1440':
            fmt = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]'
        elif quality == 'q_2160':
            fmt = 'bestvideo[height<=2160]+bestaudio/best[height<=2160]'
        elif quality == 'q_mp3':
            fmt = 'bestaudio'
        ydl_opts = {
            'format': fmt,
            'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
            'quiet': False,
        }
        if quality == 'q_mp3':
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        if quality in ['q_1440', 'q_2160']:
            if 'postprocessors' not in ydl_opts:
                ydl_opts['postprocessors'] = []
            ydl_opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'})
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            if file_size > 2 * 1024 * 1024 * 1024:
                await callback_query.message.answer("❌ Файл слишком большой (>2GB)")
                os.remove(filepath)
            else:
                try:
                    file = FSInputFile(filepath)
                    filename = os.path.basename(filepath)
                    if filename.endswith(('.mp3', '.wav', '.m4a')):
                        await callback_query.message.answer_audio(file, title=filename)
                    else:
                        await callback_query.message.answer_video(file, caption=filename)
                    await callback_query.message.answer("✅ Готово!\n\n/start для новой загрузки")
                except Exception as e:
                    await callback_query.message.answer(f"❌ Ошибка: {str(e)[:80]}")
                finally:
                    if os.path.exists(filepath):
                        os.remove(filepath)
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"❌ Ошибка: {str(e)[:120]}")
        await state.clear()

@dp.message_handler(F.text.regexp(r'https?://'))
async def handle_direct_link(message: types.Message, state: FSMContext):
    url = message.text.strip()
    source = detect_source(url)
    if not source:
        await message.answer("❌ Не поддерживается")
        return
    await message.answer(f"✅ Источник: {source.upper()}\n⏳ Получаю инфо...")
    await state.update_data(url=url)
    try:
        info = await get_video_info(url)
        if not info:
            await message.answer("❌ Ошибка")
            return
        is_subscribed = await is_user_subscribed(message.from_user.id, REQUIRED_CHANNEL)
        buttons = [
            [InlineKeyboardButton(text="🎥 360p", callback_data="q_360")],
            [InlineKeyboardButton(text="🎥 480p", callback_data="q_480")],
        ]
        if is_subscribed:
            buttons.extend([
                [InlineKeyboardButton(text="🎥 720p ✅", callback_data="q_720")],
                [InlineKeyboardButton(text="🎥 1080p ✅", callback_data="q_1080")],
                [InlineKeyboardButton(text="🎥 1440p ✅", callback_data="q_1440")],
                [InlineKeyboardButton(text="🎥 2160p ✅", callback_data="q_2160")],
            ])
        else:
            buttons.append([InlineKeyboardButton(text="🔒 720p+", callback_data="q_locked")])
        buttons.extend([
            [InlineKeyboardButton(text="🎵 MP3", callback_data="q_mp3")],
            [InlineKeyboardButton(text="❌", callback_data="q_cancel")],
        ])
        await message.answer("Выберите качество:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await state.set_state(DownloadStates.choosing_format)
    except:
        await message.answer("❌ Ошибка")

def format_duration(seconds: int) -> str:
    if seconds == 0:
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

async def main():
    print("🤖 Бот запущен")
    print(f"📢 Канал подписки: {REQUIRED_CHANNEL}")
    print("\n📋 СИСТЕМА ДОСТУПА:")
    print("✅ 360p, 480p, MP3 - ОТКРЫТО ДЛЯ ВСЕХ")
    print("🔒 720p, 1080p, 1440p, 2K - ТРЕБУЕТ ПОДПИСКУ")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Остановлен")
