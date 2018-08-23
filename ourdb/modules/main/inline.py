import logging

from telegram import InlineQueryResultCachedSticker, InlineQueryResultCachedGif
from telegram.error import BadRequest
from telegram.ext import InlineQueryHandler

from botutils import is_valid_deeplink
from modules.main.common import MAX_PACK_NAME_LENGTH, get_pack_entries, CREATE_PACK_CHAR
from storage import EntryType

MAX_INLINE_RESULTS = 50


def _inline_query_result_from_entry(entry_type, entry):
    if entry_type == EntryType.STICKER:
        return InlineQueryResultCachedSticker(id=entry, sticker_file_id=entry)
    elif entry_type == EntryType.GIF:
        return InlineQueryResultCachedGif(id=entry, gif_file_id=entry)


def on_inline_query(bot, update):
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

        logging.debug("Entries: %s, offset: %s %s, res_offset: %s" % (len(entries), more, offset, res_offset))

        try:
            bot.answer_inline_query(
                update.inline_query.id,
                [_inline_query_result_from_entry(entry_type, entry) for (entry_type, entry) in entries],
                is_personal=True,
                cache_time=5,
                next_offset=res_offset
            )
        except BadRequest as req:
            if req.message != "Document_invalid":
                raise
            # Thanks to telegram api every file_id is unique from bot to bot
            bot.send_message(
                update.effective_user.id,
                "Error with file_id, please contact the /author"
            )
            logging.exception("Error during inline query")
            return

    else:
        update.inline_query.answer(
            results=[],
            is_personal=True,
            switch_pm_text="Create pack " + query,
            switch_pm_parameter=CREATE_PACK_CHAR + (query if is_valid_deeplink(query) else ''),
            cache_time=5,
        )


__handlers__ = [
    InlineQueryHandler(on_inline_query)
]

__states__ = {
}
