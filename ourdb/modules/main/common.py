import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from bot import storage
from botutils import build_menu
from storage import EntryType

MAX_PACK_NAME_LENGTH = 50

ADD_MEDIA_CHAR = 'a'
ADD_SUBPACK_CHAR = 'p'
CREATE_PACK_CHAR = 'c'
CANCEL_CHAR = '/'
VIEW_MENU_CHAR = 'm'
REMOVE_PACK_CHAR = 'r'
VIEW_PACK_CHAR = 'v'


back_button = InlineKeyboardButton('Back', callback_data=VIEW_MENU_CHAR)


def create_select_sticker_menu(user_id, callback_char, send_add_button=True, send_back_button=True):
    with storage.session_scope() as session:
        sticker_packs = storage.get_packs(session, user_id)
    buttons = [InlineKeyboardButton(pack, callback_data=callback_char + str(pack)) for pack in sticker_packs]

    footer_buttons = []
    if send_add_button:
        footer_buttons.append(InlineKeyboardButton("Add entry", callback_data=CREATE_PACK_CHAR))
    if send_back_button:
        footer_buttons.append(back_button)
    menu = build_menu(buttons, 1, None, footer_buttons)
    return InlineKeyboardMarkup(menu)


def get_pack_entries(bot, user_id, pack_name, offset, limit=1000000, similar=False):
    assert limit > 0
    with storage.session_scope() as session:
        entries = storage.get_entries(session, user_id, pack_name, similar)
    discard_remaining = offset
    remaining = limit
    result = []
    more = False
    for entry_type, entry in entries:
        logging.debug("e: %s, discard_remaining: %s, remaining: %s, result: %s", (entry_type, entry), discard_remaining, remaining, len(result))
        if remaining <= 0:
            more = True
            break

        entry_type = EntryType(entry_type)
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
        logging.debug("DiscardRem: %s, res: %s", discard_remaining, len(result))
    assert discard_remaining == 0
    return result, more


def on_stickerpack_removed(bot, user_id, stickerpack_name):
    """Called whenever a stickerpack of a user gets removed"""
    bot.send_message(user_id, "The sticker pack %s has been removed, sorry for the inconvenience" % stickerpack_name)
    with storage.session_scope() as session:
        storage.remove_every_pack_mention(session, user_id, stickerpack_name)

