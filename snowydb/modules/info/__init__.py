from telegram.ext import CommandHandler

SOURCE_LOC = "https://github.com/SnowyCoder/telegram-snowydb"


def author(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Author: @SnowyCoder")


def source(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Source: " + SOURCE_LOC)


__handlers__ = (
    CommandHandler('author', author),
    CommandHandler('source', source),
)

