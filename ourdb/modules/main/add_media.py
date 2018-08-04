import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, Filters

from bot import storage
from botutils import edit_or_send, strip_command
from callback import CallbackCommandHandler
from modules import limits
from modules.main.common import create_select_sticker_menu, ADD_SUBPACK_CHAR, CANCEL_CHAR, ADD_MEDIA_CHAR
from storage import EntryType

add_sticker_reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton('Append Pack', callback_data=ADD_SUBPACK_CHAR)],
    [InlineKeyboardButton('Done', callback_data=CANCEL_CHAR)],
])


def add_stickers(bot, update, pack, user_data):
    chat_id = update.effective_chat.id

    if not pack:
        pack = user_data.get('pack')

    if not pack:
        edit_or_send(bot, update, "Select the pack to expand", create_select_sticker_menu(update.effective_user.id, ADD_MEDIA_CHAR))
        return ADD_SUBPACK_CHAR

    with storage.session_scope() as session:
        has_pack = storage.has_pack(session, update.effective_user.id, pack)

    if not has_pack:
        bot.send_message(chat_id=chat_id, text="Pack not found")
        return

    user_data['pack'] = pack
    edit_or_send(bot, update, text="Send me the media to add", reply_markup=add_sticker_reply_markup)
    return ADD_MEDIA_CHAR


def on_add_sticker_command(bot, update, user_data):
    return add_stickers(bot, update, strip_command(update.message.text), user_data)


def process_entry_from_response(bot, update):
    entry, entry_type, name = None, None, None

    if update.message.sticker:
        entry = update.message.sticker.file_id
        entry_type = EntryType.STICKER
        name = 'Sticker'
    elif update.message.document:
        mime_type = update.message.document.mime_type
        if mime_type == 'video/mp4':
            entry = update.message.document.file_id
            entry_type = EntryType.GIF
            name = "Gif"
    else:
        logging.warning("Unsupported message received", update.message)

    return entry, entry_type, name


def on_add_sticker_response(bot, update, user_data):
    user_id = update.effective_user.id

    entry, entry_type, name = process_entry_from_response(bot, update)

    if not entry:
        bot.send_message(chat_id=user_id, text="type not supported", reply_markup=add_sticker_reply_markup)
        return

    limits_reached = not limits.check_insertion(user_id)

    with storage.session_scope() as session:
        add_result = storage.add_entry(session, user_id, user_data['pack'], entry_type, entry, only_remove=limits_reached)

    if limits_reached and add_result:
        bot.send_message(chat_id=user_id, text="Entry limits exceeded", reply_markup=limits.limits_report_markup)
    elif add_result:
        bot.send_message(chat_id=user_id, text='%s added' % name, reply_markup=add_sticker_reply_markup)
    else:
        bot.send_message(chat_id=user_id, text='%s removed' % name, reply_markup=add_sticker_reply_markup)


__handlers__ = (
    CommandHandler('add', on_add_sticker_command,  pass_user_data=True),
    CallbackCommandHandler(ADD_MEDIA_CHAR, add_stickers, pass_data=True, pass_user_data=True),
)


__states__ = {
    ADD_MEDIA_CHAR: [MessageHandler(Filters.sticker | Filters.document, on_add_sticker_response, pass_user_data=True)]
}
