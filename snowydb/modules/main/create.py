import re

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, Filters

from botutils import edit_or_send, strip_command
from callback import CallbackCommandHandler
from modules.main.add_media import add_sticker_reply_markup
from modules.main.common import CANCEL_CHAR, MAX_PACK_NAME_LENGTH, CREATE_PACK_CHAR, ADD_MEDIA_CHAR

create_markup = InlineKeyboardMarkup([[
    InlineKeyboardButton('Cancel',   callback_data=CANCEL_CHAR),
]])

NAME_VALID_REGEX = re.compile(r'^[a-z0-9;:-_\s\'*^$%&]+$')


def check_name(name):
    if len(name) > MAX_PACK_NAME_LENGTH:
        return "Name too long, max: " + str(MAX_PACK_NAME_LENGTH) + " characters"

    if not NAME_VALID_REGEX.fullmatch(name):
        return "Name characters invalid"

    return None  # No complaints here


def create_pack(bot, update, name, user_data):
    if not name:
        edit_or_send(bot, update, "Write the new pack name:", reply_markup=create_markup)
        return CREATE_PACK_CHAR

    name = name.lower()  # Case insensitive as always
    name_error = check_name(name)
    if name_error:
        bot.send_message(chat_id=update.message.chat_id, text=name_error, reply_markup=create_markup)
        return

    user_data['pack'] = name
    bot.send_message(chat_id=update.effective_chat.id, text="Now send me all of your stickers :3", reply_markup=add_sticker_reply_markup)
    return ADD_MEDIA_CHAR


def on_create_command(bot, update, user_data):
    return create_pack(bot, update, strip_command(update.message.text), user_data)


def create_name_response(bot, update, user_data):
    return create_pack(bot, update, update.message.text, user_data)


__handlers__ = [
    CommandHandler('create', on_create_command, pass_user_data=True),
    CallbackCommandHandler(CREATE_PACK_CHAR, create_pack, pass_data=True, pass_user_data=True)
]

__states__ = {
    CREATE_PACK_CHAR: [MessageHandler(Filters.text, create_name_response, pass_user_data=True)]
}
