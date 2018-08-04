from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ConversationHandler

from botutils import build_menu
from callback import CallbackCommandHandler
from modules.main.common import CANCEL_CHAR
from modules.main.menu import view_menu

cancel_markup = InlineKeyboardMarkup(build_menu([
    InlineKeyboardButton('Cancel',   callback_data=CANCEL_CHAR),
], 1))


def cancel_current_operation(bot, update):
    view_menu(bot, update)
    return ConversationHandler.END


__handlers__ = [
    CommandHandler('cancel', cancel_current_operation),
    CallbackCommandHandler(CANCEL_CHAR, cancel_current_operation),
]


__states__ = {
    CANCEL_CHAR: []
}
