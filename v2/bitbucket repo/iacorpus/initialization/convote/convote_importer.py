import re
import os
import csv
import sys
from collections import defaultdict, Counter
from operator import itemgetter

from iacorpus.initialization.dataset_importer import DatasetImporter
from iacorpus.initialization.raw_data_loader import RawDataLoader


def import_data(loader, parser, importer):
    everything = list(loader.run())
    import_authors(loader.all_names, everything, importer)
    import_discussions(everything, parser, importer)
    import_votes(everything, importer)
    import_mentions(loader.edges_data['reference_set'], everything, importer)
    import_convote_concatenated(loader.edges_data['concatenated'], importer)


def import_authors(all_names, everything, importer):
    for identifier, entries in all_names.items():
        name = sorted(entries.items(), key=lambda x: (x[1], len(str(x[0]))), reverse=True)[0][0]
        parties = Counter()
        for _, _, descriptors in everything:
            for descriptor in descriptors:
                if descriptor['speaker'] == identifier:
                    parties[descriptor['party']] += 1
        assert len(parties) < 2
        if len(parties) > 0:
            party = parties.most_common()[0][0]
        else:
            party = 'X'
        author_details = {'username': str(identifier),
                          'full_name': name,
                          'party': party}
        importer.insert('author', author_details)
    importer.flush()


def import_discussions(everything, parser, importer):
    # Discussions
    for category, identifier, entries in everything:
        parsed_result = parser.parse_entry(category, identifier, entries)
        if parsed_result is not None:
            importer.insert(category, parsed_result)
    importer.flush()


def import_votes(everything, importer):
    votes = dict()
    for _, _, descriptors in everything:
        for descriptor in descriptors:
            key = (descriptor['bill'], descriptor['speaker'])
            assert descriptor['vote'] in {'Y', 'N'}
            vote = descriptor['vote'] == 'Y'
            assert key not in votes or votes[key] == vote
            votes[key] = vote
    for (discussion_id, author_id), vote in votes.items():
        importer.insert('vote', {'discussion_id': discussion_id, 'author_id': author_id, 'vote': vote})
    importer.flush()


def import_convote_concatenated(concatenated, importer):
    for (discussion_id, author_id), edge in concatenated.items():
        entry = {'discussion_id': discussion_id, 'author_id': author_id}
        for field in ['raw_score', 'normalized_score', 'link_strength']:
            entry[field] = edge[field]
        importer.insert('concatenated', entry)
    importer.flush()


def import_mentions(reference_set, everything, importer):
    indexed_edges = defaultdict(list)
    for edge in reference_set:
        indexed_edges[(edge['bill'], edge['speakerA'], edge['speakerB'])].append(edge)
    speakers_by_bill = defaultdict(set)
    for _, discussion_id, descriptors in everything:
        for descriptor in descriptors:
            speakers_by_bill[discussion_id].add(descriptor['speaker'])
    indexed_mentions = defaultdict(list)
    for _, discussion_id, descriptors in everything:
        for descriptor in descriptors:
            if len(descriptor['mentions']) > 0 and 'two' in descriptor['stages']:
                for mention in descriptor['mentions']:
                    key = (discussion_id, descriptor['speaker'], mention['mention_author_id'])
                    indexed_mentions[key].append(mention)

    for key, edges in indexed_edges.items():
        mentions = indexed_mentions[key]
        assert len(edges) == len(mentions)
        # I assume they're in order..?
        for edge, mention in zip(edges, mentions):
            mention.update(edge)
    for _, discussion_id, descriptors in everything:
        for descriptor in descriptors:
            for mention in descriptor['mentions']:
                mention_entry = {'discussion_id': discussion_id,
                                 'post_id': descriptor['post']['post_id'],
                                 'text_id': descriptor['post']['text_id'],
                                 'text_index': mention['text_index'],
                                 'mention_author_id': mention['mention_author_id'],
                                 'useless_digit': mention['useless_digit'],
                                 'mention_name': mention['mention_name'],
                                 'raw_score': mention.get('raw_score'),
                                 'normalized_score': mention.get('normalized_score'),
                                 'link_strength': mention.get('link_strength'),
                                 'high_precision_normalized_score': mention.get('high_precision_normalized_score'),
                                 'high_precision_link_strength': mention.get('high_precision_link_strength')}
                importer.insert('mention', mention_entry)
    importer.flush()


class ConvoteLoader(RawDataLoader):
    def __init__(self, convote_path):
        super().__init__(dataset_name='convote')
        self.convote_path = convote_path
        self.filename_re = re.compile(r'(?P<bill>\d{3})_(?P<speaker>\d{6})_(?P<page>\d{4})(?P<index>\d{3})_(?P<party>[RDIX])(?P<bill_mention>[MO])(?P<vote>[YN])\.txt')
        self.mention_re = re.compile(r'(\( (?P<name>mr?s?\. [^()]+) \) )?xz(?P<speaker>\d{6})(?P<useless_digit>\d)')
        self.all_names = defaultdict(Counter)  # for diagnostics
        self.edges_data = self.load_csv_data()

    def load_raw_data(self, descriptor):
        filename = os.path.join(self.convote_path,
                                'data_stage_one',
                                descriptor['set_name'] + '_set',
                                descriptor['filename'])
        text, mentions, yield_start = self.load_file(filename)
        self.all_names[descriptor['speaker']][None] += 0
        descriptor['text'] = text
        descriptor['yield_start'] = yield_start
        descriptor['stages'] = ['one']
        for stage in ['two', 'three']:
            filename = os.path.join(self.convote_path,
                                    'data_stage_' + stage,
                                    descriptor['set_name'] + '_set',
                                    descriptor['filename'])
            if os.path.exists(filename):
                descriptor['stages'].append(stage)
        descriptor['edges_individual'] = self.edges_data['individual'].get(descriptor['filename'])
        descriptor['mentions'] = mentions
        return descriptor

    def load_file(self, filename) -> (str, list, int):
        mentions = list()
        text = ''
        end = 0
        raw_text = open(filename).read().strip()
        for entry in self.mention_re.finditer(raw_text):
            start = entry.start()
            preceding_text = raw_text[end:start]
            name = entry.group('name')
            if name is None:
                name = self.find_mention_name(preceding_text)
            text += preceding_text
            mentions.append({'text_index': len(text), 'mention_author_id': int(entry.group('speaker')),
                             'useless_digit': int(entry.group('useless_digit')), 'mention_name': name})
            end = entry.end()
            if len(preceding_text) > 0 and preceding_text[-1].isspace() and len(raw_text) > end and raw_text[end] == ' ':
                end += 1
            self.all_names[entry.group('speaker')][name] += 1
        text += raw_text[end:]

        yield_start = text.rfind('\n')
        if yield_start is -1 or 'yield' not in text[yield_start:]:
            yield_start = None
        return text, mentions, yield_start

    def find_mention_name(self, preceding_text):
        name = None
        names = list(re.finditer(r'(mr?s?)\.', preceding_text))
        # Also captures m. kennedy and m. slaughter
        # but this seems to be how the original authors did it
        # and those two have more identifiers with mr. and ms. respectively
        if len(names) > 0:
            name = preceding_text[names[-1].start():].strip()
            if name.endswith(' )'):
                name = name[:-len(' )')]
        return name

    def get_group_id(self, descriptor):
        return descriptor['bill']

    def get_descriptors(self):
        descriptors = list()
        stage_one_path = os.path.join(self.convote_path, 'data_stage_one')
        for dirpath, dirnames, filenames in os.walk(stage_one_path):
            for filename in filenames:
                filename_match = self.filename_re.match(os.path.basename(filename))
                assert filename_match is not None
                set_name = os.path.basename(dirpath)[:-len('_set')]
                entry = {'set_name': set_name, 'filename': filename}
                entry.update({key: self.try_int(value) for key, value in filename_match.groupdict().items()})
                descriptors.append(entry)
        return descriptors

    def maybe_sort_descriptors(self, descriptors):
        descriptors.sort(key=itemgetter('filename'))

    def load_csv_data(self):
        csv_dir = os.path.join(self.convote_path, 'graph_edge_data')
        edges_individual, edges_concatenated, edges_reference_set = self.main_csvs(csv_dir)
        edges_data = {'individual': edges_individual,
                      'concatenated': edges_concatenated,
                      'reference_set': edges_reference_set, }
        return edges_data

    def main_csvs(self, csv_dir: str):
        edges_individual_document = os.path.join(csv_dir, 'edges_individual_document.v1.1.csv')
        edges_concatenated_document = os.path.join(csv_dir, 'edges_concatenated_document.v1.1.csv')
        edges_reference_set_full = os.path.join(csv_dir, 'edges_reference_set_full.v1.1.csv')
        edges_reference_set_high_precision = os.path.join(csv_dir, 'edges_reference_set_high_precision.v1.1.csv')

        edges_individual = dict()
        for entry in csv.DictReader(open(edges_individual_document),
                                    fieldnames=['filename',
                                                'raw_score',
                                                'normalized_score',
                                                'link_strength',
                                                'inverse_link_strength']):
            for key in entry.keys():
                entry[key] = self.try_int(entry[key])
            if entry['filename'] == '052_400011_0327014_DON.txt':
                assert entry['raw_score'] == -0.38605469, 'Bad entry - differs from other file'
                print('Fixing data error for: ', entry, ' raw_score should be: <-1.38605469>')
                entry['raw_score'] = -1.38605469
            assert entry['link_strength'] == 10000 - entry['inverse_link_strength'], entry
            assert entry['filename'] not in edges_individual
            edges_individual[entry['filename']] = entry

        edges_concatenated = dict()
        for entry in csv.DictReader(open(edges_concatenated_document),
                                    fieldnames=['filename',
                                                'raw_score',
                                                'normalized_score',
                                                'link_strength',
                                                'inverse_link_strength']):
            for key in entry.keys():
                entry[key] = self.try_int(entry[key])
            assert entry['link_strength'] == 10000 - entry['inverse_link_strength'], entry
            bill = int(entry['filename'][0:3])
            speaker = int(entry['filename'][4:10])
            if (bill, speaker) in edges_concatenated:
                for key, value in entry.items():
                    assert key == 'filename' or edges_concatenated[(bill, speaker)][key] == value, (entry, edges_concatenated[(bill, speaker)])
            else:
                edges_concatenated[(bill, speaker)] = entry

        edges_reference_set = list()
        for entry, hp_entry in zip(csv.DictReader(open(edges_reference_set_full),
                                                  fieldnames=['true_label',
                                                              'bill',
                                                              'speakerA',
                                                              'speakerB',
                                                              'raw_score',
                                                              'normalized_score',
                                                              'link_strength']),
                                   csv.DictReader(open(edges_reference_set_high_precision),
                                                  fieldnames=['true_label',
                                                              'bill',
                                                              'speakerA',
                                                              'speakerB',
                                                              'raw_score',
                                                              'high_precision_normalized_score',
                                                              'high_precision_link_strength'])):
            for key in entry:
                assert key not in hp_entry or entry[key] == hp_entry[key]
            entry.update(hp_entry)
            for key in entry.keys():
                entry[key] = self.try_int(entry[key])
            edges_reference_set.append(entry)

        # edges_individual # filename
        # edges_concatenated # (bill, speaker)
        # edges_reference_set # list
        return edges_individual, edges_concatenated, edges_reference_set

    def try_int(self, s: str):
        try:
            s = int(s)
        except ValueError:
            try:
                s = float(s)
            except ValueError:
                pass
        return s


class ConvoteParser:
    def parse_entry(self, category, identifier, entries):
        if category == 'discussion':
            discussion = self.create_discussion(identifier, entries)
            posts = self.create_posts(identifier, entries, discussion)
            discussion['posts'] = posts
            return discussion
        return None

    def create_discussion(self, identifier, descriptors):
        discussion = dict()
        discussion['native_discussion_id'] = identifier
        discussion['url'] = None
        discussion['title'] = None
        discussion['set_name'] = descriptors[0]['set_name']
        assert all([entry['set_name'] == discussion['set_name'] for entry in descriptors])
        return discussion

    def create_posts(self, identifier, descriptors, discussion):
        posts = list()
        for descriptor in descriptors:
            post = self.create_post(descriptor, discussion)  # self.create_post(post_html_obj, html_obj, discussion)
            posts.append(post)
        return posts

    def create_post(self, descriptor, discussion):
        post = dict()
        descriptor['post'] = post
        post['username'] = str(descriptor['speaker'])
        post['creation_date'] = None
        post['text'] = descriptor['text']
        post['stage_two'] = 'two' in descriptor['stages']
        post['stage_three'] = 'three' in descriptor['stages']
        post['yield_start'] = descriptor['yield_start']
        post['filename'] = descriptor['filename']
        for field in ['raw_score', 'normalized_score', 'link_strength']:
            post[field] = descriptor['edges_individual'][field] if descriptor['edges_individual'] is not None else None
        post['bill_mentioned'] = descriptor['bill_mention'] == 'M'
        post['source_page'] = int(descriptor['page'])
        post['source_index'] = int(descriptor['index'])
        post['mentions'] = descriptor['mentions']
        return post


class ConvoteImporter(DatasetImporter):
    def __init__(self, flush_delay=60, simulated=True):
        super().__init__('convote',
                         use_native_discussion_ids=True,
                         use_native_post_ids=False,
                         flush_delay=flush_delay,
                         simulated=simulated)
        self.flush_order = ['author',
                            'text',
                            'discussion',
                            'post',
                            'convote_mention',
                            'convote_concatenated_edge',
                            'convote_vote']

    def insert(self, category, entry):
        super().insert(category, entry)
        if category == 'vote':
            self.insert_vote(entry)
        elif category == 'concatenated':
            self.insert_concatenated(entry)
        elif category == 'mention':
            self.insert_mention(entry)

    def get_author_id(self, username):
        if username not in self.author_id_lookup:
            self.author_id_lookup[username] = int(username)
        return self.author_id_lookup[username]

    def should_skip_discussion(self, discussion):
        return False

    def insert_vote(self, vote):
        self.queues['convote_vote'].append(vote)

    def insert_concatenated(self, concatenated):
        self.queues['convote_concatenated_edge'].append(concatenated)

    def insert_mention(self, mention):
        self.queues['convote_mention'].append(mention)


if __name__ == '__main__':
    path = sys.argv[1]  # '/path/to/convote_v1.1/'
    convote_loader = ConvoteLoader(path)
    convote_parser = ConvoteParser()
    convote_importer = ConvoteImporter(flush_delay=30, simulated=True)
    import_data(convote_loader, convote_parser, convote_importer)
