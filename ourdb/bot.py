import logging
import os

LOG_LEVEL = os.environ.get('LOG_LEVEL', default=logging.INFO)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=LOG_LEVEL)

import telegram
from telegram.ext import *

import modules
from storage import *


WEBHOOK = os.environ['WEBHOOK'] == 'True'

if WEBHOOK:
    URL = os.environ['URL']
    PORT = int(os.environ['PORT'])

TOKEN = os.environ['TOKEN']

storage = DbStorage()
storage.init()


def error_callback(bot, update, error):
    logging.exception("Error %s", error)


def main():
    updater = Updater(TOKEN)

    dp = updater.dispatcher

    handlers = modules.__handlers__

    for handler in handlers:
        dp.add_handler(handler)

    dp.add_error_handler(error_callback)

    if WEBHOOK:
        logging.info("Starting webhook at %s port %d", URL, PORT)
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN
        )

        updater.bot.set_webhook(URL + TOKEN)
    else:
        logging.info("Starting polling")
        updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
