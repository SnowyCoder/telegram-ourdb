
# Conversation states

from telegram.ext import ConversationHandler

from modules.main import add_media, add_subpack, cancel, create, menu, remove, view, inline

conversation_parts = [
    add_media,
    add_subpack,
    cancel,
    create,
    menu,
    remove,
    view,
    inline,
]

conversation_handlers = [entrypoint for part in conversation_parts for entrypoint in part.__handlers__]
conversation_states = {k: v for d in conversation_parts for k, v in d.__states__.items()}


conversation_handler = ConversationHandler(
    entry_points=conversation_handlers,
    states=conversation_states,
    fallbacks=[],
    allow_reentry=True,
    per_chat=False
)

__handlers__ = (
    conversation_handler,
)


