import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.exceptions import TelegramForbiddenError

from config import REQUIRED_CHANNEL
from database import (
    add_user, get_user, add_channel, get_user_channels,
    get_channel_by_id, add_post, get_pending_posts, get_sent_posts_to_delete,
    update_post_sent, delete_post, get_user_stats
)
from keyboards import main, cancel_keyboard, get_duration_keyboard, get_channels_keyboard, get_subscribe_keyboard
from states import CreateAdStates, AddChannelStates
from utils import parse_datetime, format_datetime, MOSCOW_TZ

router = Router()

async def is_subscribed(bot, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
    return member.status in ('member', 'administrator', 'creator')

@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    await add_user(user_id, username)

    if await is_subscribed(message.bot, user_id):
        await state.clear()
        await message.answer(
            '👋 Привет! Я - бот "Реклама в каналах - Легко!".\n'
            '💯 Благодаря мне ты сможешь с легкостью управлять рекламой в своих каналах.\n'
            '📆 С чего начнем?',
            reply_markup=main
        )
    else:
        await message.answer(
            '❗ Чтобы пользоваться ботом, подпишитесь на наш канал.',
            reply_markup=get_subscribe_keyboard()
        )

@router.callback_query(lambda c: c.data == 'check_sub')
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await is_subscribed(callback.bot, user_id):
        await callback.message.edit_text(
            'Спасибо за подписку! Теперь вы можете пользоваться ботом.',
            reply_markup=None
        )
        await state.clear()
        await callback.message.answer(
            '👋 Привет! Я - бот "Реклама в каналах - Легко!".\n'
            '💯 Благодаря мне ты сможешь с легкостью управлять рекламой в своих каналах.\n'
            '📆 С чего начнем?',
            reply_markup=main
        )
        await callback.answer('Подписка подтверждена!')
    else:
        await callback.answer('Вы ещё не подписались на канал!', show_alert=True)

@router.message(F.text == 'Добавить канал')
async def add_channel_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_subscribed(message.bot, user_id):
        await message.answer('Сначала подпишитесь на канал!', reply_markup=get_subscribe_keyboard())
        return
    await state.set_state(AddChannelStates.waiting_for_channel)
    await message.answer(
        '📢 Отправьте мне username канала (например, @my_channel) или его ID (число).\n'
        'Для отмены нажмите /cancel',
        reply_markup=cancel_keyboard
    )

@router.message(AddChannelStates.waiting_for_channel, F.text)
async def add_channel_process(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    input_text = message.text.strip()
    if input_text == 'Отмена':
        await state.clear()
        await message.answer('Добавление канала отменено.', reply_markup=main)
        return

    if input_text.startswith('@'):
        channel_username = input_text[1:]
        chat = await bot.get_chat(input_text)
        channel_id = str(chat.id)
        title = chat.title
    else:
        channel_id = str(int(input_text))
        chat = await bot.get_chat(channel_id)
        channel_username = chat.username
        title = chat.title

    me = await bot.get_me()
    member = await bot.get_chat_member(chat_id=channel_id, user_id=me.id)
    if member.status not in ('administrator', 'creator'):
        await message.answer('❌ Бот не является администратором этого канала. Добавьте его и повторите попытку.')
        return

    await add_channel(user_id, channel_id, channel_username, title)
    await message.answer(f'✅ Канал "{title or channel_username or channel_id}" успешно добавлен!', reply_markup=main)
    await state.clear()

@router.message(Command('cancel'))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('Нет активных действий для отмены.')
        return
    await state.clear()
    await message.answer('Действие отменено.', reply_markup=main)

@router.message(F.text == 'Новая реклама')
async def new_ad_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_subscribed(message.bot, user_id):
        await message.answer('Сначала подпишитесь на канал!', reply_markup=get_subscribe_keyboard())
        return

    channels = await get_user_channels(user_id)
    if not channels:
        await message.answer('❌ У вас пока нет добавленных каналов. Сначала добавьте канал через кнопку "Добавить канал".')
        return

    if len(channels) == 1:
        await state.update_data(channel_db_id=channels[0][0])
        await state.set_state(CreateAdStates.content)
        await message.answer(
            '📝 Отправьте текст рекламного сообщения. Если хотите добавить фото/видео, отправьте его с подписью (текст будет подписью).',
            reply_markup=cancel_keyboard
        )
    else:
        await state.set_state(CreateAdStates.selecting_channel)
        await message.answer(
            '📢 Выберите канал для публикации:',
            reply_markup=get_channels_keyboard(channels)
        )

@router.callback_query(CreateAdStates.selecting_channel, F.data.startswith('channel_'))
async def process_channel_selection(callback: CallbackQuery, state: FSMContext):
    channel_db_id = int(callback.data.split('_')[1])
    await state.update_data(channel_db_id=channel_db_id)
    await state.set_state(CreateAdStates.content)
    await callback.message.delete()
    await callback.message.answer(
        '📝 Отправьте текст рекламного сообщения. Если хотите добавить фото/видео, отправьте его с подписью (текст будет подписью).',
        reply_markup=cancel_keyboard
    )
    await callback.answer()

@router.message(CreateAdStates.content, F.text | F.photo | F.video | F.document)
async def process_content(message: Message, state: FSMContext):
    data = {}
    if message.text:
        data['text_content'] = message.text
    elif message.photo:
        data['media_type'] = 'photo'
        data['media_file_id'] = message.photo[-1].file_id
        data['caption'] = message.caption or ''
    elif message.video:
        data['media_type'] = 'video'
        data['media_file_id'] = message.video.file_id
        data['caption'] = message.caption or ''
    elif message.document:
        data['media_type'] = 'document'
        data['media_file_id'] = message.document.file_id
        data['caption'] = message.caption or ''
    else:
        await message.answer('Пожалуйста, отправьте текст, фото, видео или документ.')
        return

    await state.update_data(content=data)
    await state.set_state(CreateAdStates.scheduled_time)
    await message.answer(
        '🕒 Укажите дату и время публикации в формате:\n'
        'ДД.ММ.ГГГГ ЧЧ:ММ (по московскому времени)\n'
        'Пример: 01.01.2025 15:30',
        reply_markup=cancel_keyboard
    )

@router.message(CreateAdStates.scheduled_time, F.text)
async def process_scheduled_time(message: Message, state: FSMContext):
    dt = parse_datetime(message.text)
    if not dt:
        await message.answer('❌ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ (например, 01.01.2025 15:30)')
        return

    if dt < datetime.now(MOSCOW_TZ):
        await message.answer('❌ Время публикации не может быть в прошлом. Пожалуйста, укажите будущее время.')
        return

    await state.update_data(scheduled_at=dt)
    await state.set_state(CreateAdStates.duration)
    await message.answer(
        '⏱️ На сколько часов закрепить пост в канале?\n'
        'Выберите один из вариантов или введите своё число (только цифры).',
        reply_markup=get_duration_keyboard()
    )

@router.callback_query(CreateAdStates.duration, F.data.startswith('duration_'))
async def process_duration_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == 'duration_custom':
        await callback.message.answer('Введите количество часов (только число):')
        await callback.answer()
        return
    else:
        hours = int(data.split('_')[1])
        await finish_ad_creation(callback.message, state, hours)
        await callback.answer()

@router.message(CreateAdStates.duration, F.text)
async def process_duration_text(message: Message, state: FSMContext):
    if message.text == 'Отмена':
        await state.clear()
        await message.answer('Создание рекламы отменено.', reply_markup=main)
        return
    try:
        hours = int(message.text.strip())
        if hours <= 0:
            raise ValueError
        await finish_ad_creation(message, state, hours)
    except ValueError:
        await message.answer('❌ Пожалуйста, введите целое положительное число часов (например, 12).')

async def finish_ad_creation(message: Message, state: FSMContext, duration_hours: int):
    data = await state.get_data()
    channel_db_id = data['channel_db_id']
    content = data['content']
    scheduled_at = data['scheduled_at']

    await add_post(
        channel_db_id=channel_db_id,
        text_content=content.get('text_content'),
        media_type=content.get('media_type'),
        media_file_id=content.get('media_file_id'),
        caption=content.get('caption'),
        scheduled_at=scheduled_at,
        duration_hours=duration_hours
    )

    await state.clear()
    await message.answer(
        f'✅ Реклама запланирована!\n'
        f'🕒 Дата публикации: {format_datetime(scheduled_at)}\n'
        f'⏱️ Длительность показа: {duration_hours} часов',
        reply_markup=main
    )

@router.message(F.text == 'Профиль')
async def profile_handler(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer('Пользователь не найден. Начните с /start')
        return

    created_at = user[2]
    posts_count, channels = await get_user_stats(user_id)

    profile_text = f"📊 **Ваш профиль**\n\n"
    profile_text += f"🆔 ID: {user_id}\n"
    profile_text += f"📅 Дата регистрации: {created_at}\n"
    profile_text += f"📝 Всего рекламных постов: {posts_count}\n\n"
    profile_text += f"📢 **Подключенные каналы:**\n"
    if channels:
        for ch in channels:
            _, channel_id, username, title = ch
            name = f"@{username}" if username else title or channel_id
            profile_text += f"- {name}\n"
    else:
        profile_text += "Нет добавленных каналов.\n"
    await message.answer(profile_text, parse_mode='Markdown')

@router.message(F.text == 'Поддержка')
async def support_handler(message: Message):
    await message.answer(
        '👨‍💻 По всем вопросам обращайтесь к разработчику: @developer_username\n'
        'Или пишите на почту: support@example.com'
    )

async def scheduler(bot: Bot):
    while True:
        await asyncio.sleep(60)

        pending = await get_pending_posts()
        for post in pending:
            post_id, channel_db_id, text_content, media_type, media_file_id, caption, _ = post
            channel = await get_channel_by_id(channel_db_id)
            if not channel:
                await delete_post(post_id)
                continue
            real_channel_id = channel[1]

            sent_message = None
            if media_type == 'photo':
                sent_message = await bot.send_photo(
                    chat_id=real_channel_id,
                    photo=media_file_id,
                    caption=caption or text_content
                )
            elif media_type == 'video':
                sent_message = await bot.send_video(
                    chat_id=real_channel_id,
                    video=media_file_id,
                    caption=caption or text_content
                )
            elif media_type == 'document':
                sent_message = await bot.send_document(
                    chat_id=real_channel_id,
                    document=media_file_id,
                    caption=caption or text_content
                )
            else:
                sent_message = await bot.send_message(
                    chat_id=real_channel_id,
                    text=text_content
                )
            await update_post_sent(post_id, sent_message.message_id, datetime.now(MOSCOW_TZ))

        to_delete = await get_sent_posts_to_delete()
        for post in to_delete:
            post_id, channel_db_id, sent_message_id, _, _ = post
            channel = await get_channel_by_id(channel_db_id)
            if not channel:
                await delete_post(post_id)
                continue
            real_channel_id = channel[1]
            await bot.delete_message(chat_id=real_channel_id, message_id=sent_message_id)
            await delete_post(post_id)
