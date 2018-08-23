import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CommandHandler

from botutils import edit_or_send, lookahead, strip_command
from callback import CallbackCommandHandler
from modules.main.common import create_select_sticker_menu, get_pack_entries, VIEW_PACK_CHAR, ADD_MEDIA_CHAR, \
    ADD_SUBPACK_CHAR, REMOVE_PACK_CHAR, VIEW_MENU_CHAR
from storage import EntryType

MAX_VIEW_RESULTS = 25
OFFSET_DIVIDER = '|'


def view_pack(bot, update, arg: str=None, user_data=None):
    if not arg:
        edit_or_send(bot, update, "Select the pack to view", create_select_sticker_menu(update.effective_user.id, VIEW_PACK_CHAR))
        return

    chat_id = update.effective_chat.id

    # Split sticker and offset
    # In theory the divider should not be part of the name so there's no
    # confusion when splitting the command
    # As a matter of fact the character selected is filtered out of the possible names
    args = arg.rsplit(OFFSET_DIVIDER, 1)
    name = args[0].lower()
    if len(args) < 2:
        offset = 0
    else:
        try:
            offset = int(args[1])
        except ValueError:
            offset = 0

    entries, more = get_pack_entries(bot, update.effective_user.id, name, offset * MAX_VIEW_RESULTS, MAX_VIEW_RESULTS)

    logging.debug("Entries for %s: %s", name, entries)

    if entries is None:
        edit_or_send(bot, update, "Cannot find pack")
        return

    buttons = []

    navigate_buttons = []
    if offset != 0:
        navigate_buttons.append(InlineKeyboardButton('Back', callback_data=VIEW_PACK_CHAR + name + OFFSET_DIVIDER + str(offset - 1)))
    if more:
        navigate_buttons.append(InlineKeyboardButton('Next', callback_data=VIEW_PACK_CHAR + name + OFFSET_DIVIDER + str(offset + 1)))

    if navigate_buttons:
        buttons.append(navigate_buttons)
    buttons += [
        [InlineKeyboardButton('Add', callback_data=ADD_MEDIA_CHAR + name)],
        [InlineKeyboardButton('Append Pack', callback_data=ADD_SUBPACK_CHAR + name)],
        [InlineKeyboardButton('Remove Pack', callback_data=REMOVE_PACK_CHAR + name)],
        [InlineKeyboardButton('Menu', callback_data=VIEW_MENU_CHAR)],
    ]

    more_markup = InlineKeyboardMarkup(buttons)

    if 'last_messages' in user_data:
        message_ids = user_data.pop('last_messages')
        for id in message_ids:
            bot.delete_message(chat_id=chat_id, message_id=id)

    if entries:
        message_ids = []
        for entry, has_more in lookahead(entries):
            entry_type, content = entry
            try:
                if entry_type == EntryType.STICKER:
                    message = bot.send_sticker(chat_id=chat_id, sticker=content, timeout=3000, reply_markup=None if has_more else more_markup)
                elif entry_type == EntryType.GIF:
                    message = bot.send_document(chat_id=chat_id, document=content, reply_markup=None if has_more else more_markup)
                else:
                    logging.warning('Unsupported type: %s', entry_type)
                    continue
            except BadRequest as req:
                if req.message != "Document_invalid":
                    raise
                # Thanks to telegram api every file_id is unique from bot to bot
                bot.send_message(
                    update.effective_user.id,
                    "Error with file_id, please contact the /author"
                )
                logging.exception("Error during view operation")
                return

            message_ids.append(message.message_id)
        user_data['last_messages'] = message_ids
    else:
        edit_or_send(bot, update, text="No sticker found", reply_markup=more_markup)


def on_view_command(bot, update, user_data=None):
    return view_pack(bot, update, strip_command(update.message.text), user_data)


__handlers__ = (
    CommandHandler('view', on_view_command,  pass_user_data=True),
    CallbackCommandHandler(VIEW_PACK_CHAR, view_pack, pass_data=True, pass_user_data=True),
)


__states__ = {
    VIEW_PACK_CHAR: []
}
