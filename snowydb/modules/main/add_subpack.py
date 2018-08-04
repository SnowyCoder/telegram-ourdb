import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler

from bot import storage, MessageHandler, Filters
from botutils import edit_or_send, strip_command
from callback import CallbackCommandHandler
from modules import limits
from modules.main.add_media import ADD_MEDIA_CHAR
from modules.main.common import create_select_sticker_menu, CANCEL_CHAR, ADD_SUBPACK_CHAR
from storage import EntryType

add_sticker_pack_reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton('Append Sticker', callback_data=ADD_MEDIA_CHAR)],
    [InlineKeyboardButton('Done', callback_data=CANCEL_CHAR)],
])


def add_sticker_pack(bot, update, pack, user_data):
    chat_id = update.effective_chat.id
    if not pack:
        pack = user_data.get('pack')

    if not pack:
        edit_or_send(bot, update, "Select the pack to expand with the sticker pack", create_select_sticker_menu(update.effective_user.id, ADD_SUBPACK_CHAR))
        return

    with storage.session_scope() as session:
        has_pack = storage.has_pack(session, update.effective_user.id, pack)

    if not has_pack:
        bot.send_message(chat_id=chat_id, text="Pack not found")
        return

    user_data['pack'] = pack
    edit_or_send(bot, update, text="Send me the sticker packs to append", reply_markup=add_sticker_pack_reply_markup)
    # Set state to ADD_PACK so that we receive the next user's messages
    return ADD_SUBPACK_CHAR


def on_add_pack_command(bot, update, user_data):
    return add_sticker_pack(bot, update, strip_command(update.message.text), user_data)


def on_add_pack_response(bot, update, user_data):
    user_id = update.effective_user.id

    if update.message.sticker:
        entry = update.message.sticker.set_name
        entry_type = EntryType.PACK
        name = entry
        # Temporarily remove local sticker pack support
        '''elif update.message.text:
        entry = update.message.text
        if not storage.has_pack(update.effective_user.id, entry):
            bot.send_message(chat_id=chat_id, text="Pack '%s' not found" % entry)
            return
        entry_type = EntryType.LOCAL_PACK
        name = entry'''
    else:
        logging.warning("Unsupported message received '%s'", update.message)
        bot.send_message(chat_id=user_id, text="type not supported", reply_markup=add_sticker_pack_reply_markup)
        return

    limits_reached = not limits.check_insertion(user_id)

    with storage.session_scope() as session:
        add_result = storage.add_entry(session, user_id, user_data['pack'], entry_type, entry, only_remove=limits_reached)

    if limits_reached and add_result:
        bot.send_message(chat_id=user_id, text="Entry limits exceeded", reply_markup=limits.limits_report_markup)
    elif add_result:
        bot.send_message(chat_id=user_id, text='%s appended' % name, reply_markup=add_sticker_pack_reply_markup)
    else:
        bot.send_message(chat_id=user_id, text='%s removed' % name, reply_markup=add_sticker_pack_reply_markup)


__handlers__ = (
    CommandHandler('addsub', on_add_pack_command,  pass_user_data=True),
    CallbackCommandHandler(ADD_SUBPACK_CHAR, add_sticker_pack, pass_data=True, pass_user_data=True),
)


__states__ = {
    ADD_SUBPACK_CHAR: [MessageHandler(Filters.sticker | Filters.document, on_add_pack_response, pass_user_data=True)]
}




