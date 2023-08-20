import json
import os
import inspect
import re
from collections import namedtuple

import inflect
import sqlalchemy
from sqlalchemy.ext.automap import automap_base, generate_relationship, name_for_scalar_relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.collections import attribute_mapped_collection

from iacorpus.utilities.misc import ProgressReporter, tablerepr, lazy_property

from iacorpus.datasets.generic import orm

SQLConnection = namedtuple('SQLConnection', ['engine', 'metadata', 'Base', 'session'])


class Dataset:
    """A base class for datasets.

    This class connects to a database and builds the ORM.
    It supports iterating over Discussions or accessing them individually.
    """
    def __init__(self, name: str, **kwargs):
        self.name = name  # type: str
        self.database_name = kwargs['database_name'] if 'database_name' in kwargs else self.name  # type: str

        # _class_table_map provides a mapping between class name and table name.
        # it's used for relationship names because _camelize_classname is not reversible
        # This is populated as classes are defined
        self._class_table_map = dict()  # type: dict[str, str]

        self.connection = self._load_connection(**kwargs)  # type: SQLConnection

    def __iter__(self):
        """Yields Discussion objects."""
        iterator = self.get_discussions()
        return iterator

    def get_discussions(self, discussion_list=None, max_discussions=None, tablename='discussion', report_progress=True, lock=None):
        """Yields Discussion objects.

        Args:
            discussion_list: A list of discussion_ids (useful if you only want specific discussions)
            max_discussions: the number of discussions to yield (useful for testing)
            tablename: the table to look for discussion_ids
                (if you only want discussions which have an entry in a specific table)
            report_progress: whether to print progress
                'On 1 of 42. Time remaining: 0:20:00. Time taken: 0:00:01'
            lock: a mutex for printing progress
        """
        class DiscussionIterator:
            def __init__(self, id_list, should_report_progress, parent):
                self.id_list = list(id_list)
                self.progress = ProgressReporter(len(self.id_list), text='On ', lock=lock) if should_report_progress else None
                self.curr = 0
                self.parent = parent

            def __iter__(self):
                return self

            def __next__(self):
                if self.progress is not None:
                    self.progress.report()
                if self.curr >= len(self.id_list):
                    raise StopIteration
                else:
                    discussion_id = self.id_list[self.curr]
                    self.curr += 1
                    discussion = self.parent.load_discussion(discussion_id)
                    return discussion

        if discussion_list is None:
            discussion_list = self.get_discussion_ids(tablename=tablename, max_discussions=max_discussions)
        elif max_discussions is not None:
            discussion_list = list(discussion_list)[:max_discussions]

        iterator = DiscussionIterator(discussion_list, report_progress, self)
        return iterator

    def get_discussion_ids(self, tablename='discussion', max_discussions=None) -> [int]:
        """Returns a list of discussion_ids from tablename."""
        table = sqlalchemy.Table(tablename, self.connection.metadata, autoload=True)
        query = sqlalchemy.select([table.c.discussion_id], table.c.discussion_id != None).distinct().order_by(table.c.discussion_id).limit(max_discussions)
        result = query.execute()
        discussion_ids = sorted({entry[0] for entry in result})
        return discussion_ids

    def load_discussion(self, discussion_id: int):
        """Loads an individual discussion."""
        cls = self.connection.Base.classes.Discussion
        query = self.connection.session.query(cls).filter_by(discussion_id=discussion_id)
        discussion = query.scalar()
        return discussion

    def has_table(self, tablename: str) -> bool:
        """Indicates whether the database includes a particular table."""
        return self.connection.metadata.bind.has_table(tablename)

    def get_table(self, tablename: str):
        """Returns a sqlalchemy table."""
        table = sqlalchemy.Table(tablename, self.connection.metadata, autoload=True)
        return table

    def query(self, query_str: str, to_dicts=False):
        """Executes a SQL query.

        If to_dicts is True it returns [{key:value}].
        Otherwise it returns a list of tuples
        (or list of items if there is only one item)
        If this behavior is not desirable,
        call connection.session.execute(query_str) directly
        """
        result = self.connection.session.execute(query_str)
        if to_dicts:
            result = [dict(entry) for entry in result]
        else:
            result = list(result)
            if len(result) > 0 and len(result[0]) == 1:
                result = [x[0] for x in result]
        return result

    @lazy_property
    def dataset_metadata(self) -> dict:
        """Metadata about the dataset (authors, version, source, etc.)
        Named this way to distinguish it from sqlalchemy metadata
        """
        result = self.connection.session.query(self.connection.Base.classes.DatasetMetadata).all()
        metadata = {obj.metadata_field: obj.metadata_value for obj in result}
        return metadata

    def _load_connection(self, connection_details_filename=None,
                         connection_details_configuration_name=None, **kwargs) -> SQLConnection:
        """Connects to the database and sets up the ORM."""
        connection_details = self._load_connection_details(filename=connection_details_filename,
                                                           configuration_name=connection_details_configuration_name)
        connection_details.update(kwargs)
        if 'database_name' in connection_details:
            del connection_details['database_name']

        engine = self._setup_engine(self.database_name, **connection_details)
        metadata = sqlalchemy.MetaData(bind=engine)
        Base = self._setup_base(engine, metadata, self.database_name)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        connection = SQLConnection(engine=engine, metadata=metadata, Base=Base, session=session)
        return connection

    @staticmethod
    def _setup_engine(database_name, dbapi, host, port, username, password):
        connection_string = dbapi + '://' + username
        if password is not None:
            connection_string += ':' + password
        connection_string += '@' + host + ':' + port + '/' + database_name + '?charset=utf8mb4'

        engine = sqlalchemy.create_engine(connection_string)
        return engine

    @staticmethod
    def _load_connection_details(filename=None, configuration_name=None):
        """Returns default connection details (port, username, etc.), possibly loaded from a file."""
        connection_details = {"host": "localhost",
                              "port": "3306",
                              "username": "iacuser",
                              "password": None,
                              "dbapi": "mysql+mysqldb"}
        if filename is None:
            filename = os.environ.get('IAC_CONNECTION_DETAILS')
        if filename is not None and os.path.exists(filename):
            connection_details_file = open(filename)
            connection_details_raw = json.load(connection_details_file)
            if configuration_name is None:
                configuration_name = connection_details_raw['default_configuration']
            connection_details.update(connection_details_raw[configuration_name])
        return connection_details

    def _setup_base(self, engine, metadata, database_name):
        Base = automap_base(metadata=metadata)
        classes = self._build_classes(Base, engine)
        for cls in classes:
            setattr(Base.classes, cls.__name__, cls)
        try:
            Base.prepare(engine, reflect=True,
                         classname_for_table=self._classname_for_table,
                         name_for_scalar_relationship=self._name_for_scalar_relationship,
                         name_for_collection_relationship=self._name_for_collection_relationship,
                         generate_relationship=self._generate_relationship)
        except:
            print('Did you spell the dataset_name correctly?', '"', str(database_name), '"')
            raise
        Base.__repr__ = tablerepr
        return Base

    def _build_classes(self, Base, engine):
        """Constructs ORM classes thereby allowing functions and details not provided by SQLAlchemy's automapping.
        ORM classes should have a module named using their tablename which implements build_class()."""
        classes = list()
        tables_seen = set()
        for dataset_orm in self._get_orms():
            for name, obj in inspect.getmembers(dataset_orm, inspect.ismodule):
                if name not in tables_seen and engine.has_table(name):
                    tables_seen.add(name)
                    cls = obj.build_class(Base, engine)
                    classes.append(cls)
        return classes

    def _get_orms(self):
        """Returns orm modules which are consumed by _build_classes() in order.
         This allows implementing classes to define their own orm in addition to their base classes'
          without having to touch _build_classes()
         Override me! (usually with a call to super())
         """
        return [orm]

    def _classname_for_table(self, base, tablename, table) -> str:
        """Returns an appropriate class name based on the table name"""
        new_name = self._camelize_classname(base, tablename, table)
        self._class_table_map[new_name] = tablename
        return new_name

    @staticmethod
    def _camelize_classname(base, tablename, table) -> str:
        """Produce a 'camelized' class name

        e.g. 'words_and_underscores' -> 'WordsAndUnderscores'
        Code from sqlalchemy documentation.
        """
        return str(tablename[0].upper() + re.sub(r'_([a-z])', lambda m: m.group(1).upper(), tablename[1:]))

    def _name_for_scalar_relationship(self, base, local_cls, referred_cls, constraint) -> str:
        class_name = local_cls.__name__
        referred_class_name = referred_cls.__name__
        if referred_class_name in self._class_table_map:
            referred_class_name = self._class_table_map[referred_class_name]
        if self._should_use_obj_name(class_name, referred_class_name):
            return referred_class_name.lower() + '_obj'
        else:
            return name_for_scalar_relationship(base, local_cls, referred_cls, constraint)

    def _should_use_obj_name(self, class_name: str, referred_class_name: str) -> bool:
        """Indicates whether scalar relationships should end in _obj.

        e.g. post.text or post.text_obj
          this allows post.text = "blah blah"
          while post.text_obj.tokens = [token1, token2]
        Override me! (use super() in case this changes)
        """
        if referred_class_name in {'Discussion', 'Post', 'Quote'}:
            return False
        return True

    _pluralizer = inflect.engine()
    def _name_for_collection_relationship(self, base, local_cls, referred_cls, constraint) -> str:
        class_name = local_cls.__name__
        referred_class_name = referred_cls.__name__
        collection_lookup = {('Post', 'Quote'): 'all_quotes'}
        collection_name = collection_lookup.get((class_name, referred_class_name))
        if collection_name is not None:
            return collection_name
        else:
            if referred_class_name in self._class_table_map:
                referred_class_name = self._class_table_map[referred_class_name]
            else:
                referred_class_name = referred_class_name.lower()
            pluralized = self._pluralizer.plural(referred_class_name)
            return pluralized

    def _generate_relationship(self, base, direction, return_fn, attrname, local_cls, referred_cls, **kw):
        kw['viewonly'] = True
        class_name = local_cls.__name__
        if class_name == 'Discussion' and attrname == 'posts':
            kw['collection_class'] = attribute_mapped_collection('post_id')
        elif class_name == 'Post' and attrname == 'all_quotes':
            kw['collection_class'] = attribute_mapped_collection('quote_index')
        return generate_relationship(base, direction, return_fn, attrname, local_cls, referred_cls, **kw)
