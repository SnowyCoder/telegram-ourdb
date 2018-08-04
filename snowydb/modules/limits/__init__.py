import os

import math
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler

from bot import storage
from callback import CallbackCommandHandler

MAX_ENTRIES = int(os.environ.get('ENTRY_LIMIT'))

if MAX_ENTRIES < 0:
    MAX_ENTRIES = math.inf

LIMITS_UPGRADE_CHAR = '^'
LIMITS_REPORT_CHAR = '|'


def get_max_entries(user_id):
    # TODO: add special plan or something
    return MAX_ENTRIES


change_plan_markup = InlineKeyboardMarkup([[
    InlineKeyboardButton('Upgrade', callback_data=LIMITS_UPGRADE_CHAR)
]])

limits_report_markup = InlineKeyboardMarkup([[
    InlineKeyboardButton('Check limits', callback_data=LIMITS_REPORT_CHAR)
]])


def check_insertion(user_id, inserted_count=1):
    with storage.session_scope() as session:
        current_entries = storage.count_total_entries(session, user_id)

    return current_entries + inserted_count <= MAX_ENTRIES


def limits_report(bot, update):
    user_id = update.effective_user.id

    with storage.session_scope() as session:
        current_entries = storage.count_total_entries(session, user_id)

    max_entries = get_max_entries(user_id)

    text = "Current entries:\n" \
           "%d/%d (%d%%)\n" \
           "Remaining: %d entries" % (current_entries, max_entries,
                                      (current_entries * 100) // max_entries, max_entries - current_entries)

    # TODO: enable real plans or whatever
    bot.send_message(chat_id=user_id, text=text, reply_markup=change_plan_markup)


def limits_upgrade(bot, update):
    bot.send_message(update.effective_user.id, "Sorry this function isn't available yet, if you want more space clone"
                                               " the bot from /source and host it somewhere :3")


__handlers__ = (
    CommandHandler('limits', limits_report),
    CommandHandler('upgradelimits', limits_upgrade),
    CallbackCommandHandler(LIMITS_REPORT_CHAR, limits_report),
    CallbackCommandHandler(LIMITS_UPGRADE_CHAR, limits_upgrade),
)
