from bot import storage, CommandHandler
from botutils import edit_or_send, strip_command
from callback import CallbackCommandHandler
from modules.main.common import create_select_sticker_menu, REMOVE_PACK_CHAR
from modules.main.menu import start_menu_markup


def remove_pack(bot, update, name):
    if not name:
        reply_markup = create_select_sticker_menu(update.effective_user.id, REMOVE_PACK_CHAR, send_add_button=False)
        edit_or_send(bot, update, "What pack do you want to remove?", reply_markup)
        return

    with storage.session_scope() as session:
        remove_succeded = storage.remove_pack(session, update.effective_user.id, name.lower())

    if remove_succeded:
        edit_or_send(bot, update, 'Pack removed successfully!', reply_markup=start_menu_markup)
    else:
        edit_or_send(bot, update, 'Pack not found')


def on_remove_command(bot, update):
    return remove_pack(bot, update, strip_command(update.message.text))


__handlers__ = (
    CommandHandler('remove', on_remove_command),
    CallbackCommandHandler(REMOVE_PACK_CHAR, remove_pack, pass_data=True)
)


__states__ = {
    REMOVE_PACK_CHAR: []
}
