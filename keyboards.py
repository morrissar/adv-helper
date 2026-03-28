from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Новая реклама')],
        [KeyboardButton(text='Добавить канал')],
        [KeyboardButton(text='Профиль')],
        [KeyboardButton(text='Поддержка')]
    ],
    resize_keyboard=True,
    input_field_placeholder='Выберите действие...'
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text='Отмена')]],
    resize_keyboard=True
)

def get_duration_keyboard():
    buttons = [
        [InlineKeyboardButton(text='24 часа', callback_data='duration_24')],
        [InlineKeyboardButton(text='48 часов', callback_data='duration_48')],
        [InlineKeyboardButton(text='72 часа', callback_data='duration_72')],
        [InlineKeyboardButton(text='Другое (введи число)', callback_data='duration_custom')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_channels_keyboard(channels):
    keyboard = []
    for ch in channels:
        db_id, _, username, title = ch
        text = f"@{username}" if username else title or str(db_id)
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"channel_{db_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subscribe_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='📢 Подписаться на канал', url='https://t.me/advhelper')],
            [InlineKeyboardButton(text='✅ Проверить подписку', callback_data='check_sub')]
        ]
    )