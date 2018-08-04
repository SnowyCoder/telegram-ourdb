from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler

from botutils import build_menu, edit_or_send
from callback import CallbackCommandHandler
from modules.main.common import VIEW_PACK_CHAR, CREATE_PACK_CHAR, REMOVE_PACK_CHAR, VIEW_MENU_CHAR

start_menu_markup = InlineKeyboardMarkup(build_menu([
    InlineKeyboardButton('View',   callback_data=VIEW_PACK_CHAR),
    InlineKeyboardButton('Create', callback_data=CREATE_PACK_CHAR),
    InlineKeyboardButton('Remove', callback_data=REMOVE_PACK_CHAR),
], 1))


def view_menu(bot, update):
    edit_or_send(bot, update, "Select operation", reply_markup=start_menu_markup)


__handlers__ = (
    CommandHandler('start', view_menu),
    CallbackCommandHandler(VIEW_MENU_CHAR, view_menu),
)

__states__ = {
    VIEW_MENU_CHAR: []
}
