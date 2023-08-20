from collections import Counter, defaultdict
import time
from pprint import pprint
import os

import sqlalchemy

from iacorpus import load_connection
from iacorpus.utilities.misc import ProgressReporter
from iacorpus.utilities.nlp import corenlp_mine as corenlp


class ParseImporter:
    def __init__(self, dataset_name, flush_delay=60, simulated=True):
        self.simulated = simulated
        self.dataset_name = dataset_name
        self.connection = load_connection(self.dataset_name)

        self.lookups = self._get_lookups()
        self.queues = defaultdict(list)

        self.last_flush_time = 0
        self.flush_delay = flush_delay
        self.tables = dict()
        self.next_parse_ids = Counter()
        self.next_lookup_ids = dict()
        self.tables['text'] = sqlalchemy.Table('text', self.connection.metadata, autoload=True)
        self.flush_order = ['word',
                            'pos_tag',
                            'parse_tag',
                            'sentence',
                            'corenlp_parse',
                            'token',
                            'dependency_relation',
                            'dependency',
                            'corenlp_named_entity_tag',
                            'corenlp_named_entity',
                            'corenlp_coref']  # Should we just turn FKs off?
        self.fields = self._setup_fields()

        self.counts = Counter()

    def _setup_fields(self):
        fields = defaultdict(set)
        for tablename in self.flush_order:
            table = sqlalchemy.Table(tablename, self.connection.metadata, autoload=True)
            fields[tablename] = {str(column.key) for column in table.columns}
        return fields

    def import_data(self, parsing_dir, skip_to=None, excluded=None, disable_foreign_key_checks=False, extension='.xml'):
        xml_dir = os.path.join(parsing_dir, self.dataset_name, 'xml')
        file_list = self.load_file_list(xml_dir, skip_to=skip_to, excluded=excluded, extension=extension)
        progress = ProgressReporter(total_number=len(file_list))
        if disable_foreign_key_checks:
            self.connection.session.execute('set foreign_key_checks=0;')
        self.flush()
        for filename in file_list:
            try:
                xml = corenlp.get_xml_from_file(filename)
                parse = corenlp.consume_xml(xml, absolute_token_indices=True, count_from_zero=True)
                base_filename = os.path.basename(filename)[:-len(extension)]
                text_id, character_offset = map(int, base_filename.split('_'))
                self.insert(parse, text_id, character_offset)
            except:
                print('exception on:', filename)
                raise
            if progress.report():
                print('    Most recent:', filename)
                self.maybe_flush()
        self.flush()
        if disable_foreign_key_checks:
            self.connection.session.execute('set foreign_key_checks=1;')

    def load_file_list(self, xml_dir, skip_to, excluded, extension):
        file_list = os.listdir(xml_dir)  # todo: not one giant folder (os.walk()?)
        file_list.sort(key=lambda x: [int(i) for i in x[:-len(extension)].split('_')])
        if skip_to is not None:
            file_list = [filename for filename in file_list
                         if int(filename[:filename.find('_')]) >= skip_to and
                         (excluded is None or int(filename[:filename.find('_')]) not in excluded)]

        file_list = [os.path.join(xml_dir, filename) for filename in file_list]

        curr_text_id, curr_character_offset = None, None
        for filename in file_list:
            next_text_id, next_character_offset = map(int, os.path.basename(filename)[:-len(extension)].split('_'))
            bad = (curr_text_id == next_text_id and curr_character_offset >= next_character_offset) or \
                  (curr_text_id != next_text_id and next_character_offset != 0)
            assert not bad, (filename, curr_text_id, curr_character_offset)
            file_empty = not os.path.exists(filename) or os.stat(filename).st_size == 0
            assert not file_empty, filename
            curr_text_id, curr_character_offset = next_text_id, next_character_offset
        return file_list

    def maybe_flush(self):
        if time.time() - self.last_flush_time >= self.flush_delay:
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

    def insert_entry(self, entry, tablename):
        if entry is not None:
            db_entry = {field: entry.get(field) for field in self.fields[tablename]}
            self.queues[tablename].append(db_entry)

    def insert(self, parse, text_id, character_offset):
        text = sqlalchemy.select([self.tables['text'].c.text]).where(self.tables['text'].c.text_id == text_id).scalar()

        if character_offset != 0:
            # Note that this assumes that previous parses have been seen in order!
            assert self.next_parse_ids['curr_text_id'] == text_id and self.next_parse_ids['curr_character_offset'] < character_offset, str((text_id, character_offset, self.next_parse_ids))
            self.next_parse_ids['curr_character_offset'] = character_offset
            corenlp.update_indices(parse,
                                   character_offset=self.next_parse_ids['curr_character_offset'],
                                   sentence_offset=self.next_parse_ids['sentence'],
                                   parse_node_offset=self.next_parse_ids['corenlp_parse'],
                                   token_offset=self.next_parse_ids['token'],)
        else:
            self.next_parse_ids = Counter()
            self.next_parse_ids['curr_text_id'] = text_id

        for sentence_parse in parse['sentences']:
            # TODO: move stuff to own functions... ie clean up

            # sentences
            sentence_values = {
                'text_id': text_id,
                'sentence_index': sentence_parse['sentence_index'],
                'sentence_start': sentence_parse['tokens'][0]['CharacterOffsetBegin'],
                'sentence_end': sentence_parse['tokens'][-1]['CharacterOffsetEnd'],
                'sentence_sentiment': sentence_parse['sentiment']
            }
            self.next_parse_ids['sentence'] = max(self.next_parse_ids['sentence'], sentence_values['sentence_index'])+1
            self.queues['sentence'].append(sentence_values)

            # constituency parse
            for node in corenlp.traverse_parse_tree(sentence_parse['parse']):
                if node['token'] is not None:
                    node['token']['parse_node_index'] = node['parent_node_index']
                else:
                    values = {
                        'text_id': text_id,
                        'sentence_index': sentence_parse['sentence_index'],
                        'parse_node_index': node['node_index'],
                        'parent_parse_node_index': node['parent_node_index'],
                        'descendant_right_index': node['descendant_right_index'],
                        'depth': node['depth'],
                        'parse_tag_id': self.get_ref_table_id(node['tag'], 'parse_tag')
                    }
                    self.next_parse_ids['corenlp_parse'] = 1 + max(self.next_parse_ids['corenlp_parse'],
                                                                   values['parse_node_index'])
                    self.queues['corenlp_parse'].append(values)

            # tokens
            for token_entry in sentence_parse['tokens']:
                pos_tag_id = self.get_ref_table_id(token_entry['POS'], 'pos_tag')
                token_values = {
                    'text_id': text_id,
                    'token_index': token_entry['token_index'],
                    'sentence_index': sentence_parse['sentence_index'],
                    'token_start': token_entry['CharacterOffsetBegin'],
                    'token_end': token_entry['CharacterOffsetEnd'],
                    'parse_node_index': token_entry['parse_node_index'],
                    'token_sentiment': token_entry['sentiment'],
                    'pos_tag_id': pos_tag_id
                }
                actual_word_text = text[token_values['token_start']:token_values['token_end']]
                token_values['word_id'] = self.get_ref_table_id(actual_word_text, 'word')
                token_values['lemma_word_id'] = self.get_ref_table_id(token_entry['lemma'], 'word')
                self.next_parse_ids['token'] = max(self.next_parse_ids['token'], token_values['token_index'])+1
                self.queues['token'].append(token_values)

            # deps
            for dep in sentence_parse['dependencies']:
                if dep['governor'] is None:
                    # root - this leads to one less edge case
                    governor_token_index = dep['dependent']['token_index']
                else:
                    governor_token_index = dep['governor']['token_index']
                dep_values = {
                    'text_id': text_id,
                    'sentence_index': sentence_parse['sentence_index'],
                    'dependency_id': self.next_parse_ids['dependency'],
                    'dependency_relation_id': self.get_ref_table_id(dep['type'], 'dependency_relation'),
                    'governor_token_index': governor_token_index,
                    'dependent_token_index': dep['dependent']['token_index']
                }
                self.next_parse_ids['dependency'] += 1
                self.queues['dependency'].append(dep_values)

            for ner in sentence_parse['ners']:
                values = {
                    'text_id': text_id,
                    'ner_index': self.next_parse_ids['corenlp_named_entity'],
                    'token_index_first': ner['tokens'][0]['token_index'],
                    'token_index_last': ner['tokens'][-1]['token_index'],
                    'ner_tag_id': self.get_ref_table_id(ner['type'], 'corenlp_named_entity_tag'),
                }
                self.next_parse_ids['corenlp_named_entity'] += 1
                self.queues['corenlp_named_entity'].append(values)

        for coref_chain in parse['corefs']:
            for mention in coref_chain:
                values = {
                    'text_id': text_id,
                    'coref_id': self.next_parse_ids['corenlp_coref'],
                    'coref_chain_id': self.next_parse_ids['corenlp_coref_chain'],
                    'token_index_first': mention['tokens'][0]['token_index'],
                    'token_index_last': mention['tokens'][-1]['token_index'],
                    'token_index_head': mention['head_token']['token_index'],
                    'is_representative': mention['is_representative']
                }
                self.next_parse_ids['corenlp_coref'] += 1
                self.queues['corenlp_coref'].append(values)
            self.next_parse_ids['corenlp_coref_chain'] += 1

    def get_ref_table_id(self, lookup_key, tablename):
        if lookup_key not in self.lookups[tablename]:
            if tablename not in self.next_lookup_ids:
                self.next_lookup_ids[tablename] = max(self.lookups[tablename].values(), default=0)+1
            self.lookups[tablename][lookup_key] = self.next_lookup_ids[tablename]
            self.next_lookup_ids[tablename] += 1

            entry = {tablename+'_id': self.lookups[tablename][lookup_key],
                     tablename: lookup_key}
            if tablename == 'dependency_relation':
                parent_relation_id = None
                if ':' in lookup_key:
                    parent_relation_id = self.get_ref_table_id(lookup_key[:lookup_key.rfind(':')], tablename)
                entry['parent_dependency_relation_id'] = parent_relation_id
                entry['dependency_relation_long'] = lookup_key
            elif tablename == 'pos_tag':
                entry['pos_tag_description'] = lookup_key
            elif tablename == 'parse_tag':
                entry['parse_tag_description'] = None
                entry['parse_tag_level'] = None
            elif tablename == 'corenlp_named_entity_tag':
                entry['ner_tag_id'] = self.lookups[tablename][lookup_key]
                entry['ner_tag'] = lookup_key
                entry['ner_tag_description'] = None
            self.queues[tablename].append(entry)
        return self.lookups[tablename][lookup_key]

    def _get_lookups(self):
        lookups = defaultdict(dict)
        for table, query_str in [('word', 'select word, word_id from word'),
                                 ('dependency_relation', 'select dependency_relation, dependency_relation_id from dependency_relation'),
                                 ('pos_tag', 'select pos_tag, pos_tag_id from pos_tag'),
                                 ('parse_tag', 'select parse_tag, parse_tag_id from parse_tag'),
                                 ('corenlp_named_entity_tag', 'select ner_tag, ner_tag_id from corenlp_named_entity_tag')]:
            lookups[table] = dict(list(self.connection.session.execute(query_str)))
        return lookups

if __name__ == '__main__':
    input_parsing_dir = './parsing'
    importer = ParseImporter('fourforums', flush_delay=60, simulated=False)
    importer.import_data(input_parsing_dir, skip_to=None, excluded=None, disable_foreign_key_checks=True)
