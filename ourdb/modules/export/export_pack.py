import json
from io import BytesIO

from telegram import Bot

from bot import storage, CommandHandler
from botutils import edit_or_send, strip_command
from callback import CallbackCommandHandler
from modules.main.common import create_select_sticker_menu

EXPORT_CHAR = '>'


def export_json(packs):
    processed = {
        'version': '1.0',
        'packs': [
            {
                'name': pack[0],
                'entries': pack[1]
            } for pack in packs
        ]
    }
    raw_out = bytes(json.dumps(processed, check_circular=False, separators=(',', ':')), 'utf-8')
    return BytesIO(raw_out)


def export_pack(bot: Bot, update, pack):
    user_id = update.effective_user.id

    if not pack:
        markup = create_select_sticker_menu(user_id, EXPORT_CHAR, send_add_button=False)
        edit_or_send(bot, update, "Select the pack to export", reply_markup=markup)
        return

    with storage.session_scope() as session:
        pack_entries = storage.get_entries(session, user_id, pack, False)

    if not pack:
        bot.send_message(user_id, "Pack not found")
        return

    packs = [(pack, pack_entries)]

    out_buf = export_json(packs)
    filename = pack.replace(" ", "_") + ".json"

    bot.send_document(chat_id=user_id, document=out_buf, filename=filename)


def on_export_command(bot, update):
    pack = strip_command(update.message.text)

    return export_pack(bot, update, pack)


__handlers__ = (
    CommandHandler('export', on_export_command),
    CallbackCommandHandler(EXPORT_CHAR, export_pack, pass_data=True),
)
