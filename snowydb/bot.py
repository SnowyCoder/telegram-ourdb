import os
import logging
import re

from telegram import *
from telegram.error import BadRequest
from telegram.ext import *
from storage import *
from botutils import *


URL = 'https://snowydb.herokuapp.com/'
TOKEN = os.environ['TOKEN']
PORT = int(os.environ['PORT'])
WEBHOOK = True

MAX_INLINE_RESULTS = 50
MAX_VIEW_RESULTS = 25
MAX_PACK_NAME_LENGTH = 50
SOURCE_LOC = "https://github.com/SnowyCoder/telegram-snowydb"

BETA_TESTERS = list(map(int, os.environ['BETA_TESTERS'].split(",")))
BETA_UNAUTHORIZED_MESSAGE = "Sorry, This bot is for personal use (cause the developer is lazy as hell)\n" \
                             "Contact @SnowyCoder for details"


WAITING_PACK_NAME, RECEIVING_STICKERS, RECEIVING_STICKER_PACK = range(3)
END = -1

logger = logging.getLogger()

storage = DbStorage()
storage.init()


MENU_CHAR     = 'm'
REMOVE_CHAR   = 'r'
VIEW_CHAR     = 'v'
ADD_CHAR      = 'a'
ADD_PACK_CHAR = 'p'
CREATE_CHAR   = 'c'
CANCEL_CHAR   = '/'


back_button = InlineKeyboardButton('Back', callback_data=MENU_CHAR)
start_menu_markup = InlineKeyboardMarkup(build_menu([
    InlineKeyboardButton('View',   callback_data=VIEW_CHAR),
    InlineKeyboardButton('Create', callback_data=CREATE_CHAR),
    InlineKeyboardButton('Remove', callback_data=REMOVE_CHAR),
], 1))

create_markup = InlineKeyboardMarkup([[
    InlineKeyboardButton('Cancel',   callback_data=CANCEL_CHAR),
]])

add_sticker_reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton('Append Pack', callback_data=ADD_PACK_CHAR)],
    [InlineKeyboardButton('Done', callback_data=CANCEL_CHAR)],
])

add_sticker_pack_reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton('Append Sticker', callback_data=ADD_CHAR)],
    [InlineKeyboardButton('Done', callback_data=CANCEL_CHAR)],
])


def restrict_beta(func):
    def on_unauthorized_access(bot, update):
        logger.info("Unauthorized access denied for %s.", update.effective_user)
        if update.effective_chat:
            bot.send_message(update.effective_chat.id, BETA_UNAUTHORIZED_MESSAGE)
        elif update.inline_query:
            update.inline_query.answer(results=[], is_personal=True, switch_pm_text="Unhautorized access",
                                       switch_pm_parameter="beta")

    return restrict_to(BETA_TESTERS, on_unauthorized_access)(func)


def create_select_sticker_menu(user_id, callback_char, send_add_button=True, send_back_button=True):
    sticker_packs = storage.get_packs(user_id)
    buttons = [InlineKeyboardButton(pack, callback_data=callback_char + str(pack)) for pack in sticker_packs]

    footer_buttons = []
    if send_add_button:
        footer_buttons.append(InlineKeyboardButton("Add entry", callback_data=CREATE_CHAR))
    if send_back_button:
        footer_buttons.append(back_button)
    menu = build_menu(buttons, 1, None, footer_buttons)
    return InlineKeyboardMarkup(menu)


@restrict_beta
def start(bot, update, user_data=None,):
    arg = None if not update.message else strip_command(update.message.text)

    if arg:
        cmd = CHAR_TO_COMMAND.get(arg[0])
        if cmd:
            cmd(bot, update, arg[1:], user_data)
            return

    bot.send_message(chat_id=update.message.chat_id, text="Hello, I remember your stickers by name",
                     reply_markup=start_menu_markup)

# ------------------------------- MENU -------------------------------


def view_menu(bot, update, name, user_data=None):
    edit_or_send(bot, update, "Select operation", reply_markup=start_menu_markup)


# ------------------------------- CREATE -------------------------------


def create_pack(bot, update, name, user_data):
    if not name:
        edit_or_send(bot, update, "Write the new pack name:", reply_markup=create_markup)
        user_data['state'] = WAITING_PACK_NAME
        return
    if len(name) >= MAX_PACK_NAME_LENGTH:
        bot.send_message(chat_id=update.message.chat_id, text="Name too long", reply_markup=create_markup)
        return
    name = name.lower()

    user_data['state'] = RECEIVING_STICKERS
    user_data['pack'] = name
    bot.send_message(chat_id=update.effective_chat.id, text="Now send me all of your stickers :3", reply_markup=add_sticker_reply_markup)
    return END


@restrict_beta
def on_create_command(bot, update, user_data):
    return create_pack(bot, update, strip_command(update.message.text), user_data)


def create_name_response(bot, update, user_data):
    return create_pack(bot, update, user_data, update.message.text)


# ------------------------------- REMOVE -------------------------------

def on_stickerpack_removed(bot, user_id, stickerpack_name):
    """Called whenever a stickerpack of a user gets removed"""
    bot.send_message(user_id, "The sticker pack %s has been removed, sorry for the inconvenience" % stickerpack_name)
    storage.remove_every_pack_mention(user_id, stickerpack_name)


def remove_pack(bot, update, name, user_data=None):
    if not name:
        reply_markup = create_select_sticker_menu(update.effective_user.id, REMOVE_CHAR, send_add_button=False)
        edit_or_send(bot, update, "What pack do you want to remove?", reply_markup)
        return
    if storage.remove_pack(update.effective_user.id, name.lower()):
        edit_or_send(bot, update, 'Pack removed successfully!', reply_markup=start_menu_markup)
    else:
        edit_or_send(bot, update, 'Pack not found')


@restrict_beta
def on_remove_command(bot, update, user_data):
    return remove_pack(bot, update, strip_command(update.message.text), user_data)


def get_pack_entries(bot, user_id, pack_name, offset, limit=1000000, similar=False):
    assert limit > 0
    entries = storage.get_entries(user_id, pack_name, similar)
    discard_remaining = offset
    remaining = limit
    result = []
    more = False
    for entry_type, entry in entries:
        logger.debug("e: %s, discard_remaining: %s, remaining: %s, result: %s", (entry_type, entry), discard_remaining, remaining, len(result))
        if remaining <= 0:
            more = True
            break
        if entry_type == EntryType.PACK:
            try:
                pack = bot.get_sticker_set(entry)
            except BadRequest:
                on_stickerpack_removed(bot, user_id, entry)
                continue
            stickers = pack.stickers
            if len(stickers) <= discard_remaining:
                discard_remaining -= len(stickers)
                continue
            elif discard_remaining > 0:
                stickers = stickers[discard_remaining:]
                discard_remaining = 0
            if len(stickers) > remaining:
                stickers = stickers[:remaining]
                more = True

            remaining -= len(stickers)
            result += ((EntryType.STICKER, sticker.file_id) for sticker in stickers)
            # Temporarily remove local sticker pack support
            '''elif entry_type == EntryType.LOCAL_PACK:
            stickers, pack_more = get_pack_entries(bot, user_id, entry, discard_remaining, limit - len(result))
            remaining -= len(stickers)
            if remaining == 0:
                more = pack_more
            result += stickers'''
        elif discard_remaining:
            discard_remaining -= 1
        else:
            remaining -= 1
            result.append((entry_type, entry))
    logger.debug("DiscardRem: %s, res: %s", discard_remaining, len(result))
    assert discard_remaining == 0
    return result, more


# ------------------------------- VIEW -------------------------------


def view_pack(bot, update, arg, user_data=None):
    if not arg:
        edit_or_send(bot, update, "Select the pack to view", create_select_sticker_menu(update.effective_user.id, VIEW_CHAR))
        return

    chat_id = update.effective_chat.id

    args = arg.rsplit(' ', 1)
    name = args[0].lower()
    if len(args) < 2:
        offset = 0
    else:
        try:
            offset = int(args[1])
        except ValueError:
            offset = 0
            name  += ' ' + args[1].lower() # It's part of the name

    entries, more = get_pack_entries(bot, update.effective_user.id, name, offset * MAX_VIEW_RESULTS, MAX_VIEW_RESULTS)

    logger.debug("Entries for %s: %s", name, str(entries))

    if entries is None:
        edit_or_send(bot, update, "Cannot find pack")
        return

    buttons = []

    navigate_buttons = []
    if offset != 0:
        navigate_buttons.append(InlineKeyboardButton('Back', callback_data=VIEW_CHAR + name + ' ' + str(offset - 1)))
    if more:
        navigate_buttons.append(InlineKeyboardButton('Next', callback_data=VIEW_CHAR + name + ' ' + str(offset + 1)))

    if navigate_buttons:
        buttons.append(navigate_buttons)
    buttons += [
        [InlineKeyboardButton('Add', callback_data=ADD_CHAR + name)],
        [InlineKeyboardButton('Append Pack', callback_data=ADD_PACK_CHAR + name)],
        [InlineKeyboardButton('Remove Pack', callback_data=REMOVE_CHAR + name)],
        [InlineKeyboardButton('Menu', callback_data=MENU_CHAR)],
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
            if entry_type == EntryType.STICKER:
                message = bot.send_sticker(chat_id=chat_id, sticker=content, timeout=3000, reply_markup=None if has_more else more_markup)
            elif entry_type == EntryType.GIF:
                message = bot.send_document(chat_id=chat_id, document=content, reply_markup=None if has_more else more_markup)
            else:
                logger.warning('Unsupported type: ', entry_type)
                continue
            message_ids.append(message.message_id)
        user_data['last_messages'] = message_ids
    else:
        edit_or_send(bot, update, text="No sticker found", reply_markup=more_markup)


@restrict_beta
def on_view_command(bot, update, user_data=None):
    return view_pack(bot, update, strip_command(update.message.text), user_data)


# ------------------------------- ADD -------------------------------


def add_stickers(bot, update, pack, user_data):
    chat_id = update.effective_chat.id

    if not pack:
        edit_or_send(bot, update, "Select the pack to expand", create_select_sticker_menu(update.effective_user.id, ADD_CHAR))
        return

    if not storage.has_pack(update.effective_user.id, pack):
        bot.send_message(chat_id=chat_id, text="Pack not found")
        return

    user_data['pack'] = pack
    user_data['state'] = RECEIVING_STICKERS
    bot.send_message(chat_id=chat_id, text="Send me the stickers to add", reply_markup=add_sticker_reply_markup)


@restrict_beta
def on_add_command(bot, update, user_data):
    return add_stickers(bot, update, strip_command(update.message.text), user_data)


def on_add_sticker(bot, update, user_data):
    chat_id=update.effective_user.id
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
        entry = None
        logger.warning("Unsupported message received", update.message)

    if not entry:
        bot.send_message(chat_id=chat_id, text="type not supported", reply_markup=add_sticker_reply_markup)
    elif not storage.add_entry(update.effective_user.id, user_data['pack'], entry_type, entry):
        bot.send_message(chat_id=chat_id, text='%s removed' % name, reply_markup=add_sticker_reply_markup)
    else:
        bot.send_message(chat_id=chat_id, text='%s added' % name, reply_markup=add_sticker_reply_markup)


# ------------------------------- ADD_PACK -------------------------------


def add_sticker_pack(bot, update, pack, user_data):
    chat_id = update.effective_chat.id
    if not pack:
        pack = user_data.get('pack')

    if not pack and user_data.get('state') != RECEIVING_STICKERS:
        edit_or_send(bot, update, "Select the pack to expand with the sticker pack", create_select_sticker_menu(update.effective_user.id, ADD_PACK_CHAR))
        return

    if not storage.has_pack(update.effective_user.id, pack):
        bot.send_message(chat_id=chat_id, text="Pack not found")
        return

    user_data['state'] = RECEIVING_STICKER_PACK
    user_data['pack'] = pack
    bot.send_message(chat_id=chat_id, text="Send me the sticker packs to append", reply_markup=add_sticker_pack_reply_markup)


@restrict_beta
def on_add_pack_command(bot, update, user_data):
    return add_sticker_pack(bot, update, strip_command(update.message.text), user_data)


def on_add_pack(bot, update, user_data):
    chat_id = update.effective_user.id
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
        logger.warning("Unsupported message received", update.message)
        bot.send_message(chat_id=chat_id, text="type not supported", reply_markup=add_sticker_pack_reply_markup)
        return

    if not storage.add_entry(update.effective_user.id, user_data['pack'], entry_type, entry):
        bot.send_message(chat_id=chat_id, text='%s removed' % name, reply_markup=add_sticker_pack_reply_markup)
    else:
        bot.send_message(chat_id=chat_id, text='%s appended' % name, reply_markup=add_sticker_pack_reply_markup)


def on_cancel(bot, update, text, user_data):
    state = user_data.get('state')

    if state == RECEIVING_STICKERS:
        del user_data['state']
        edit_or_send(bot, update, "Stickers saved", start_menu_markup)
    elif state:
        del user_data['state']
        view_menu(bot, update, text, user_data)


@restrict_beta
def on_cancel_command(bot, update, user_data):
    return on_cancel(bot, update, None, user_data)


# ------------------------------- INLINE -------------------------------


def _inline_query_result_from_entry(entry_type, entry):
    if entry_type == EntryType.STICKER:
        return InlineQueryResultCachedSticker(id=entry, sticker_file_id=entry)
    elif entry_type == EntryType.GIF:
        return InlineQueryResultCachedGif(id=entry, gif_file_id=entry)


@restrict_beta
def inline(bot, update):
    query = update.inline_query.query
    if not query:
        return
    if len(query) >= MAX_PACK_NAME_LENGTH:
        update.inline_query.answer(
            results=[],
            is_personal=False,
            switch_pm_text="Pack name too long",
            switch_pm_parameter="z",
            cache_time=60*60*12
        )
        return
    query = query.lower()
    offset = 0 if not update.inline_query.offset else int(update.inline_query.offset)
    real_offset = offset * MAX_INLINE_RESULTS
    entries, more = get_pack_entries(bot, update.effective_user.id, query, real_offset, MAX_INLINE_RESULTS, similar=True)
    if entries:
        res_offset = offset + 1 if more else None

        logger.debug("Entries: %s, offset: %s %s, res_offset: %s" % (len(entries), more, offset, res_offset))

        bot.answer_inline_query(
            update.inline_query.id,
            [_inline_query_result_from_entry(entry_type, entry) for (entry_type, entry) in entries],
            is_personal=True,
            cache_time=5,
            next_offset=res_offset
        )
    else:
        update.inline_query.answer(
            results=[],
            is_personal=True,
            switch_pm_text="Create pack " + query,
            switch_pm_parameter=CREATE_CHAR + (query if is_valid_deeplink(query) else ''),
            cache_time=5,
        )


# ------------------------------- MISC -------------------------------


def on_text(bot, update, user_data):
    state = user_data.get('state')
    if state == WAITING_PACK_NAME:
        del user_data['state']
        create_pack(bot, update, update.message.text, user_data)
    # Temporarily remove local sticker pack support
    #elif state== RECEIVING_STICKER_PACK:
    #   on_add_pack(bot, update, user_data)


def on_sticker(bot, update, user_data):
    state = user_data.get('state')
    if state == RECEIVING_STICKERS:
        on_add_sticker(bot, update, user_data)
    elif state == RECEIVING_STICKER_PACK:
        on_add_pack(bot, update, user_data)


def on_callback_query(bot, update, user_data):
    query = update.callback_query
    query.answer()
    cmd_char = query.data[0]
    command = CHAR_TO_COMMAND.get(cmd_char)
    if not command:
        logger.debug("Invalid callback query data: ", query.data)
        return
    return command(bot, update, query.data[1:], user_data)


def on_error(bot, update, error):
    logger.exception("Telegram error %s, %s", update, error)


def on_author_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Author: @SnowyCoder")


def on_sourcecode_command(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Source: " + SOURCE_LOC)


CHAR_TO_COMMAND = {
    REMOVE_CHAR: remove_pack,
    VIEW_CHAR: view_pack,
    ADD_CHAR: add_stickers,
    ADD_PACK_CHAR: add_sticker_pack,
    CREATE_CHAR: create_pack,
    MENU_CHAR: view_menu,
    CANCEL_CHAR: on_cancel,
}


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    updater = Updater(TOKEN)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start, pass_user_data=True))
    dp.add_handler(CommandHandler('view', on_view_command, pass_user_data=True))
    dp.add_handler(CommandHandler('create', on_create_command, pass_user_data=True))
    dp.add_handler(CommandHandler('remove', on_remove_command, pass_user_data=True))
    dp.add_handler(CommandHandler('add', on_add_command, pass_user_data=True))
    dp.add_handler(CommandHandler('addpack', on_add_pack_command, pass_user_data=True))
    dp.add_handler(CommandHandler('done', on_cancel_command, pass_user_data=True))
    dp.add_handler(CommandHandler('cancel', on_cancel_command, pass_user_data=True))
    dp.add_handler(CallbackQueryHandler(on_callback_query, pass_user_data=True))
    dp.add_handler(MessageHandler(Filters.text, on_text, pass_user_data=True))
    dp.add_handler(MessageHandler(Filters.sticker | Filters.document, on_sticker, pass_user_data=True))

    dp.add_handler(CommandHandler('author', on_author_command))
    dp.add_handler(CommandHandler('source', on_sourcecode_command))

    dp.add_handler(InlineQueryHandler(inline))

    dp.add_error_handler(callback=on_error)

    if WEBHOOK:
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN
        )

        updater.bot.set_webhook(URL + TOKEN)
    else:
        updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
