import logging
import os
from contextlib import contextmanager
from enum import Enum

from sqlalchemy import Column, Integer, String, PrimaryKeyConstraint
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ['DATABASE_URL']

Base = declarative_base()


class EntryType(Enum):
    STICKER = 's'
    # LOCAL_PACK = 'l' # Temporarily remove local sticker pack support
    PACK = 'p'
    GIF = 'g'

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)


# TODO: divide entries and packs
class PackEntry(Base):
    __tablename__ = 'pack_entries'
    __table_args__ = (
        PrimaryKeyConstraint("owner_id", "pack_name", "entry_type", "entry_data"),
    )

    owner_id = Column(Integer, nullable=False)
    pack_name = Column(String(50), nullable=False)
    entry_type = Column(String(1), nullable=False)
    entry_data = Column(String(32), nullable=False)


class DbStorage:
    def __init__(self):
        self.logger = logging.getLogger()
        self.engine = create_engine(DB_URL)
        self.Session = sessionmaker(bind=self.engine)

    def init(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def get_packs(self, session, user_id):
        self.logger.debug("Get Pack: %s" % user_id)

        res = session.query(PackEntry.pack_name).filter(PackEntry.owner_id == user_id).distinct().all()

        self.logger.debug("Get Pack Response: " + str(res))
        return [entry[0] for entry in res]

    def has_pack(self, session, user_id, name):
        return session.query(PackEntry).filter(PackEntry.owner_id == user_id, PackEntry.pack_name == name).count() > 0

    def remove_pack(self, session, user_id, name):
        self.logger.debug("Remove Pack: %s, pack: %s" % (user_id, name))

        return session.query(PackEntry)\
            .filter(PackEntry.owner_id == user_id, PackEntry.pack_name == name)\
            .delete() > 0

    def get_entries(self, session, user_id, pack_name, similar):
        self.logger.info("Get Stickers: %s, pack: %s" % (user_id, pack_name))

        second_filter = PackEntry.pack_name.like(pack_name) if similar else PackEntry.pack_name == pack_name
        res = session.query(PackEntry).filter(PackEntry.owner_id == user_id, second_filter).all()

        self.logger.info('Get Stickers response: ' + str([entry.entry_type + ", " + entry.entry_data for entry in res]))
        if not res: return []
        # Unpack entries
        return [(entry.entry_type, entry.entry_data) for entry in res]

    def has_entry(self, session, user_id, pack_name, entry_type, entry_data):
        return session.query(PackEntry).filter(
            PackEntry.owner_id == user_id,
            PackEntry.pack_name == pack_name,
            PackEntry.entry_type == entry_type.value,
            PackEntry.entry_data == entry_data
        ).count() > 0

    def add_entry(self, session, user_id, pack_name, entry_type, entry_data, only_remove=True):
        self.logger.debug(
            "Add Stickers: %s, pack: %s, type: %s, entry: %s" % (user_id, pack_name, entry_type, entry_data))

        is_entry_present = self.has_entry(session, user_id, pack_name, entry_type, entry_data)

        self.logger.debug('Add stickers result: ' + str(is_entry_present))
        if is_entry_present:
            # Sticker already present, removing
            is_entry_present = session.query(PackEntry).filter(
                PackEntry.owner_id == user_id,
                PackEntry.pack_name == pack_name,
                PackEntry.entry_type == entry_type.value,
                PackEntry.entry_data == entry_data
            ).delete()
        elif not only_remove:
            session.add(PackEntry(owner_id=user_id, pack_name=pack_name, entry_type=entry_type.value, entry_data=entry_data))
            # Sticker not found, adding
        return not is_entry_present

    def remove_every_pack_mention(self, session, user_id, stickerpack_name):
        self.logger.debug("Sticker pack deleted: user: %s, pack: %s" % (user_id, stickerpack_name))

        session.query(PackEntry).filter(
            PackEntry.owner_id == user_id,
            PackEntry.entry_type == EntryType.PACK.value,
            PackEntry.entry_data == stickerpack_name
        ).delete()

    def import_pack(self, session, user_id, pack_name, pack_entries):
        for entry in pack_entries:
            entry_type, entry_data = entry
            if not self.has_entry(session, user_id, pack_name, EntryType(entry_type), entry_data):
                session.add(PackEntry(owner_id=user_id, pack_name=pack_name, entry_type=entry_type, entry_data=entry_data))

    def count_total_entries(self, session, user_id):
        return session.query(PackEntry).filter(PackEntry.owner_id == user_id).count()
