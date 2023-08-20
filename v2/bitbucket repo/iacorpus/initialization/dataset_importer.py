from collections import Counter, defaultdict
import time
from pprint import pprint

import sqlalchemy

from iacorpus import load_connection


def import_data(loader, parser, importer, skip_to=None):
    for category, identifier, entries in loader.run(skip_to=skip_to):
        parsed_result = parser.parse_entry(category, identifier, entries)
        if parsed_result is not None:
            importer.insert(category, parsed_result)
    importer.flush()


class DatasetImporter:
    def __init__(self, dataset_name, use_native_discussion_ids, use_native_post_ids, flush_delay=60, simulated=True):
        self.simulated = simulated
        self.dataset_name = dataset_name
        self.use_native_discussion_ids = use_native_discussion_ids
        self.use_native_post_ids = use_native_post_ids

        self.connection = load_connection(self.dataset_name)

        self.author_id_lookup = self._get_author_id_mapping()
        self.next_author_id = max(self.author_id_lookup.values(), default=0) + 1
        self.next_text_id = self._get_initial_text_id()
        self.next_discussion_id = self._get_initial_discussion_id()

        self.queues = defaultdict(list)
        self.fields = defaultdict(set)
        self.setup_fields()

        self.last_flush_time = 0
        self.last_category = None
        self.flush_delay = flush_delay
        self.tables = dict()
        self.flush_order = ['author',
                            'text',
                            'markup',
                            'discussion',
                            'post',
                            'quote']  # Should we just turn FKs off?

        self.counts = Counter()

    def setup_fields(self):
        for tablename in self.connection.metadata.tables.keys():
            table = sqlalchemy.Table(tablename, self.connection.metadata, autoload=True)
            self.fields[tablename] = {str(column.key) for column in table.columns}

    def insert(self, category, entry):
        self.maybe_flush(category)
        if category == 'discussion':
            self.insert_discussion(entry)
        elif category == 'author':
            self.insert_author(entry)

    def maybe_flush(self, category):
        should_flush = False
        if category != self.last_category:
            self.last_category = category
            should_flush = True
        if should_flush is False and time.time() - self.last_flush_time > self.flush_delay:
            should_flush = True
        if should_flush:
            self.flush()

    def flush(self):
        print('flushing queues (don\'t interrupt)')
        flush_order = self.flush_order.copy()
        for key in self.queues.keys():
            if key not in flush_order:
                flush_order.append(key)
        for key in flush_order:
            if key not in self.queues:
                continue
            self.counts[key] += len(self.queues[key])
            if not self.simulated:
                self.load_tables(flush_order)
                self.connection.engine.execute(self.tables[key].insert(), self.queues[key])
        if not self.simulated:
            self.connection.session.commit()
            self.connection.session.flush()
        pprint(self.counts)
        self.queues.clear()
        self.last_flush_time = time.time()

    def load_tables(self, table_names):
        for table in table_names:
            if table not in self.tables:
                self.tables[table] = sqlalchemy.Table(table, self.connection.metadata, autoload=True)

    def insert_discussion(self, discussion):
        if self.should_skip_discussion(discussion):
            return
        self.insert_authors(discussion)
        self.insert_all_discussion_text(discussion)
        self.insert_discussion_details(discussion)
        self.insert_posts(discussion)
        self.insert_dataset_specific(discussion)

    def insert_authors(self, discussion):
        for post in discussion['posts']:
            author_details = {'username': post['username']}
            self.insert_author(author_details)
            post['author_id'] = self.get_author_id(author_details['username'])
        if 'initiating_author' in discussion:
            author_details = {'username': discussion['initiating_author']}
            self.insert_author(author_details)
            discussion['initiating_author_id'] = self.get_author_id(author_details['username'])

    def insert_author(self, author_details):
        if author_details is not None and author_details['username'] is not None and author_details['username'] not in self.author_id_lookup:
            author_details['author_id'] = self.get_author_id(author_details['username'])
            entry = {field: author_details.get(field) for field in self.fields['author']}
            self.queues['author'].append(entry)

    def get_author_id(self, username):
        if username not in self.author_id_lookup:
            self.author_id_lookup[username] = self.next_author_id
            self.next_author_id += 1
        return self.author_id_lookup[username]

    def insert_discussion_details(self, discussion):
        """This assigns a discussion_id and updates the sql discussion table
        (don't update the post table here)
        """
        discussion['discussion_id'] = self.assign_discussion_id(discussion)
        entry = {field: discussion.get(field) for field in self.fields['discussion']}
        self.queues['discussion'].append(entry)

    def assign_discussion_id(self, discussion)->int:
        if self.use_native_discussion_ids:
            return discussion['native_discussion_id']
        else:
            discussion_id = self.next_discussion_id
            self.next_discussion_id += 1
            return discussion_id

    def insert_posts(self, discussion):
        self.assign_post_ids(discussion)
        self.assign_quote_ids(discussion)
        for post in discussion['posts']:
            entry = {field: post[field] for field in self.fields['post']}
            self.queues['post'].append(entry)
            if 'quotes' in post:
                for quote in post['quotes']:
                    entry = {field: quote.get(field) for field in self.fields['quote']}
                    self.queues['quote'].append(entry)

    def assign_post_ids(self, discussion):
        # Assumed to be sorted
        for index, post in enumerate(discussion['posts']):
            post['discussion_id'] = discussion['discussion_id']
            if self.use_native_post_ids:
                post['post_id'] = post['native_post_id']
            else:
                post['post_id'] = index+1
        if any(['native_post_id' in post for post in discussion['posts']]):
            native_to_actual = {post['native_post_id']: post['post_id'] for post in discussion['posts']}
        else:
            native_to_actual = dict()
        for post in discussion['posts']:
            post['parent_post_id'] = native_to_actual.get(post.get('native_parent_post_id'))
            post['parent_missing'] = (post['parent_post_id'] is None and post.get('native_parent_post_id') is not None)

    def get_all_quotes(self, post):
        all_quotes = list()
        if 'quotes' in post:
            for quote in post['quotes']:
                all_quotes.append(quote)
                all_quotes.extend(self.get_all_quotes(quote))
        return all_quotes

    def assign_quote_ids(self, discussion):
        # assumes that post_ids have already been set
        for post in discussion['posts']:
            self.assign_quote_indices(post)
            for quote in self.get_all_quotes(post):
                quote['discussion_id'] = discussion['discussion_id']
                quote['post_id'] = post['post_id']
                quote['source_discussion_id'] = discussion['discussion_id']
                quote['source_post_id'] = discussion['posts'][quote['source_index']]['post_id']

    def assign_quote_indices(self, post, curr_quote=None, next_index=0):
        # breadth first index assignment
        obj = curr_quote if curr_quote else post
        if 'quotes' not in obj:
            return
        parent_quote_index = curr_quote['quote_index'] if curr_quote else None
        for quote in obj['quotes']:  # Not all_quotes! - ensures parent assigned first
            quote['quote_index'] = next_index
            next_index += 1
            quote['parent_quote_index'] = parent_quote_index
        for quote in obj['quotes']:
            self.assign_quote_indices(post, quote, next_index)

    def insert_all_discussion_text(self, discussion):
        # assign ids
        # assumes post_list is sorted (not terribly important)
        if 'text' in discussion:
            self.insert_single_text(discussion)
            discussion['description_text_id'] = discussion['text_id']
        for post in discussion['posts']:
            self.insert_single_text(post)
        for post in discussion['posts']:
            for quote in self.get_all_quotes(post):
                self.insert_single_text(quote)

    def insert_single_text(self, obj):
        obj['text_id'] = self.next_text_id
        self.next_text_id += 1
        if 'markup' in obj:
            for markup_index, markup in enumerate(obj['markup']):
                markup['text_id'] = obj['text_id']
                markup['markup_id'] = markup_index
                entry = {field: markup.get(field) for field in self.fields['markup']}
                self.queues['markup'].append(entry)
        entry = {field: obj[field] for field in self.fields['text']}
        self.queues['text'].append(entry)

    def insert_dataset_specific(self, discussion):
        """Override me!"""
        if not self.simulated:
            pass
        else:
            pass

    def should_skip_discussion(self, discussion):
        if discussion is None:
            self.counts['Discussion skipped (other reason)'] += 1
            return True
        if len(discussion['posts']) <= 1:
            self.counts['Discussion skipped: <= 1 Posts'] += 1
            return True
        if len({post['username'] for post in discussion['posts']}) <= 1:
            self.counts['Discussion skipped: <= 1 Authors'] += 1
            return True
        return False

    def _get_author_id_mapping(self):
        mapping = dict(list(self.connection.session.execute('select username, author_id from author')))
        return mapping

    def _get_initial_discussion_id(self):
        max_id = self.connection.session.execute('select max(discussion_id) from discussion').scalar()
        if max_id is None:
            max_id = 0
        return max_id + 1

    def _get_initial_text_id(self):
        max_id = self.connection.session.execute('select max(text_id) from text').scalar()
        if max_id is None:
            max_id = 0
        return max_id + 1
