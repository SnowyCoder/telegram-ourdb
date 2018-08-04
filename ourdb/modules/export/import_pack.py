import json
import logging
from enum import Enum
from io import BytesIO
from typing import List

from telegram import ReplyKeyboardMarkup, Update, Bot
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, RegexHandler, Filters

from bot import storage
from modules import limits
from modules.main.cancel import cancel_markup
from modules.main.menu import start_menu_markup
from storage import EntryType

IMPORT_CHAR = '<'


class ConflictResolutionMethod(Enum):
    OVERRIDE = 0
    MERGE = 1
    SKIP = 2


# Import phases
SELECT_FILE, RESOLVE_CONFLICT, LAST_CONFIRM, IMPORT = range(4)


class ImportEntry:
    def __init__(self, user_id, raw_pack):
        self.user_id = user_id
        self.name = raw_pack['name']
        self.entries = raw_pack['entries']
        self.initialized = False
        self.conflict = False
        self.conflict_resolution = None
        self.added_medias = 0

    def initialize(self, session):
        self.initialized = True
        if storage.has_pack(session, self.user_id, self.name):
            self.conflict = True
            for entry_type, entry_data in self.entries:
                if not storage.has_entry(session, self.user_id, self.name, EntryType(entry_type), entry_data):
                    self.added_medias += 1

        else:
            self.added_medias = len(self.entries)

    def import_pack(self, session):
        if self.conflict:
            if self.conflict_resolution is None:
                raise ValueError("Conflicts not resolved: " + self.name)

            if self.conflict_resolution is ConflictResolutionMethod.SKIP:
                return

        if self.conflict_resolution == ConflictResolutionMethod.OVERRIDE:
            storage.remove_pack(session, self.user_id, self.name)
        storage.import_pack(session, self.user_id, self.name, self.entries)


class ImportSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.imports = None  # type: List[ImportEntry]
        self.current_conflict = None
        self.last_confirm = False

    def on_receive_file(self, raw_content):
        try:
            self.analyze_json_sanity(raw_content)
        except ValueError as e:
            logging.exception("Exception during import")
            return e.args
        except Exception:
            return "Invalid file"

        self.initialize_from_json(raw_content)

    def next_unresolved_conflicts(self):
        for entry in self.imports:
            if entry.conflict and entry.conflict_resolution is None:
                self.current_conflict = entry
                return entry.name
        return None

    def on_conflict_answer(self, method: ConflictResolutionMethod):
        assert self.current_conflict is not None
        self.current_conflict.conflict_resolution = method

    def analyze_json_sanity(self, raw):
        if raw['version'] != '1.0':
            raise ValueError('Version not supported')

        packs = raw['packs']

        for pack in packs:
            assert isinstance(pack['name'], str)
            entries = pack['entries']
            for entry in entries:
                assert isinstance(entry, list)
                assert len(entry) == 2
                entry_type, entry_data = entry
                # check if the entry exists
                assert EntryType.has_value(entry_type)
                # TODO: assert entries[0] in SUPPORTED_CHARS

    def initialize_from_json(self, raw):
        packs = raw['packs']
        self.imports = []

        with storage.session_scope() as session:
            for raw_pack in packs:
                import_entry = ImportEntry(self.user_id, raw_pack)
                self.imports.append(import_entry)
                import_entry.initialize(session)

    def import_json(self):
        if not limits.check_insertion(self.user_id, inserted_count=self.new_media_count):
            return False

        with storage.session_scope() as session:
            for entry in self.imports:
                entry.import_pack(session)
        return True

    def on_last_confirm(self):
        self.last_confirm = True

    def get_phase(self):
        if not self.imports:
            return SELECT_FILE
        if any(entry.conflict and entry.conflict_resolution is None for entry in self.imports):
            return RESOLVE_CONFLICT
        if not self.last_confirm:
            return LAST_CONFIRM
        return IMPORT

    @property
    def new_media_count(self):
        count = 0
        for pack in self.imports:
            if pack.conflict_resolution is not ConflictResolutionMethod.SKIP:
                count += pack.added_medias
        return count

    @property
    def new_packs_count(self):
        return sum(1 for pack in self.imports if pack.conflict_resolution is not ConflictResolutionMethod.SKIP)

    def create_resume(self):
        result = ""
        for pack in self.imports:
            result += pack.name
            if pack.conflict:
                if pack.conflict_resolution == ConflictResolutionMethod.SKIP:
                    resolution_name = "SKIP"
                elif pack.conflict_resolution == ConflictResolutionMethod.MERGE:
                    resolution_name = "MERGE"
                else:
                    resolution_name = "OVERRIDE"
                result += " (" + resolution_name + ")\n"
            result += "\n"
        return result[:-1]


def cleanup_import(user_data):
    user_data.pop('import_data', None)


def next_import_step(bot, update, user_data):
    import_data = user_data.get('import_data')  # type: ImportSession
    user_id = update.effective_user.id

    if import_data is None:
        import_data = ImportSession(user_id)
        user_data['import_data'] = import_data

    next_phase = import_data.get_phase()
    if next_phase == SELECT_FILE:
        bot.send_message(user_id, "Send Import file", reply_markup=cancel_markup)
        return SELECT_FILE

    if next_phase == RESOLVE_CONFLICT:
        conflict_name = import_data.next_unresolved_conflicts()
        reply_keyboard = [['Override', 'Merge'], ['Skip', 'Cancel']]
        bot.send_message(
            user_id,
            text="You already have packet '%s'" % conflict_name,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return RESOLVE_CONFLICT

    if next_phase == LAST_CONFIRM:
        reply_keyboard = [['Confirm'], ['Cancel']]

        resume = import_data.create_resume()
        bot.send_message(
            user_id,
            text="Confirm importing the packs?\n" + resume,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return LAST_CONFIRM

    if next_phase == IMPORT:
        result = import_data.import_json()
        if result:
            bot.send_message(user_id, "Packs imported", reply_markup=start_menu_markup)
        else:
            bot.send_message(chat_id=user_id, text="Entry limits exceeded",
                             reply_markup=limits.limits_report_markup)
        cleanup_import(user_data)
        return ConversationHandler.END

    return ConversationHandler.END


def on_import_command(bot, update, user_data):
    return next_import_step(bot, update, user_data)


def on_file_selected(bot: Bot, update: Update, user_data):
    importer = user_data['import_data']  # type: ImportSession
    file = bot.get_file(update.message.document.file_id)
    with BytesIO() as file_data:
        file.download(out=file_data)
        file_str = str(file_data.getbuffer(), 'utf-8')
    json_data = json.loads(file_str)
    error = importer.on_receive_file(json_data)
    if error is not None:
        bot.send_message(update.effective_user.id, error)
    return next_import_step(bot, update, user_data)


def on_resolve_answer(bot, update, user_data):
    answer = update.message.text
    if answer == 'Cancel':
        return on_cancel(bot, update, user_data)
    import_data = user_data['import_data']  # type: ImportSession

    if answer == 'Override':
        method = ConflictResolutionMethod.OVERRIDE
    elif answer == 'Merge':
        method = ConflictResolutionMethod.MERGE
    elif answer == 'Skip':
        method = ConflictResolutionMethod.SKIP
    else:
        raise AssertionError("Unknown method '%s'" % answer)

    import_data.on_conflict_answer(method)
    return next_import_step(bot, update, user_data)


def on_last_confirm(bot, update, user_data):
    response = update.message.text
    if response == "Confirm":
        import_data = user_data['import_data']  # type: ImportSession
        import_data.on_last_confirm()
        next_import_step(bot, update, user_data)
    else:
        return on_cancel(bot, update, user_data)


def on_cancel(bot, update, user_data):
    cleanup_import(user_data)
    user_id = update.effective_user.id
    bot.send_message(user_id, text="Import operation cancelled", reply_markup=start_menu_markup)
    return ConversationHandler.END


__handlers__ = (
    ConversationHandler(
        entry_points=[
            CommandHandler('import', on_import_command, pass_user_data=True)
        ],
        states={
            SELECT_FILE: {
                MessageHandler(Filters.document, on_file_selected, pass_user_data=True)
            },
            RESOLVE_CONFLICT: [
                RegexHandler('^(Override|Merge|Skip|Cancel)$', on_resolve_answer, pass_user_data=True)
            ],
            LAST_CONFIRM: [
                RegexHandler('^(Confirm|Cancel)$', on_last_confirm, pass_user_data=True)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', on_cancel, pass_user_data=True)
        ]
    ),
)
