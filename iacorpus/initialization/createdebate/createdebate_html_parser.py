import re

from iacorpus.initialization.dataset_importer import DatasetImporter, import_data
from iacorpus.initialization.raw_data_loader import RawDataLoader
from iacorpus.initialization.iac_html_parser import IAC_HTML_Parser
from iacorpus.initialization import quote_finder


class Createdebate_HTML_Parser(IAC_HTML_Parser):
    def should_skip(self, category, identifier, html_objs):
        if html_objs[0].title.text == 'CreateDebate':
            return True
        if category == 'discussion' and len(list(self.get_post_html_objs(html_objs[0]))) < 2:
            return True
        if category == 'author' and html_objs[0].find('div', id='tabs-3') is None:
            return True
        if identifier in {'http://www.createdebate.com/debate/show/What_s_the_smallest_measurement_of_movement_or_is_it_infinitely_small'}:
            return True
        return False

    def get_post_html_objs(self, html_obj):
        for post_html_obj in html_obj.find_all('div', class_='argBox argument'):
            if not any([parent.get('id') == 'description' for parent in post_html_obj.parents]) and \
                            post_html_obj['id'] not in {'arg388835', 'arg309557', 'arg232417'}:
                # Fixes bad sanitizing in the description and very annoying posts
                yield post_html_obj

    def create_discussion(self, identifier, html_objs):
        discussion = super().create_discussion(identifier, html_objs)
        description_obj = html_objs[0].find('div', class_='centered debatelongDesc')
        if description_obj is not None:
            text, markup, quotes = self.build_text(description_obj)
            text, markup, quotes = self.cleanup_text(text, markup, quotes)
            if 'googletag.cmd.push(function()' not in text:  # avoids some unclosed tables
                discussion['text'] = text
                discussion['markup'] = markup
                # discussion['quotes'] = quotes  # no quotes
        return discussion

    def get_discussion_annotations(self, identifier, html_objs):
        annotations = dict()
        annotations['top level sides'] = [entry.text.strip() for entry in html_objs[0].find_all('h2', class_='sideTitle')]
        return annotations

    def get_canonical_title(self, identifier, html_objs, canonical_url):
        title_obj = html_objs[0].find('h1', class_='debateTitle')
        title = title_obj.text.strip()
        return title

    def get_native_discussion_id(self, identifier, html_objs):
        data = html_objs[0].find('div', id='moreDebates')['data-cat']
        native_discussion_id = int(data[data.find('/')+1:])
        return native_discussion_id

    def get_initiating_author(self, identifier, html_objs):
        containing_element = html_objs[0].find('h3', string='Debate Creator').next_sibling.next_sibling
        initiating_author = self.get_post_author(containing_element)
        return initiating_author

    def create_post(self, post_html_obj, html_obj, discussion):
        post = super().create_post(post_html_obj, html_obj, discussion)
        # Because 'Supported' is simply absent as are top level posts' response types
        if post['native_parent_post_id'] is None:
            del post['annotations']['response_type']
        post['points'] = post['annotations']['points']
        post['response_type'] = post['annotations'].get('response_type')
        return post

    def get_post_author(self, post_html_obj):
        tag = post_html_obj.find('a', href=re.compile(r'//www\.createdebate\.com/user/viewprofile/.*'), title=re.compile('.+'))
        author = tag.string.strip()
        return author

    def get_native_post_id(self, post_html_obj):
        raw_id = post_html_obj['id']
        assert raw_id.startswith('arg')
        native_post_id = int(raw_id[3:])
        return native_post_id

    def get_native_parent_post_id(self, post_html_obj):
        native_parent_post_id = None
        if 'arg-threaded' in post_html_obj.parent['class']:
            for sibling in post_html_obj.parent.previous_siblings:
                if hasattr(sibling, 'contents') and 'argBox' in sibling['class'] and 'argument' in sibling['class']:
                    native_parent_post_id = self.get_native_post_id(sibling)
                    break
        return native_parent_post_id

    def get_text_containing_element(self, post_html_obj):
        text_obj = post_html_obj.find('div', class_='argBody')
        return text_obj

    def get_post_annotations(self, post_html_obj):
        annotations = dict()
        # TODO: side can have script in it
        # e.g  for obfusicating email as in: http://www.createdebate.com/debate/show/Cohabitation_4
        side_text = post_html_obj.find('div', class_='subtext when').text
        side_start = side_text.find('Side: ')
        if side_start >= 0:
            annotations['side'] = side_text[side_start+len('Side: '):].strip()
        annotations['response_type'] = self.get_response_type(post_html_obj)
        annotations['points'] = int(post_html_obj.find('div', class_='argPoints').find('span').string.strip())
        annotations['supporting_evidence'] = self.get_supporting_evidence(post_html_obj)
        return annotations

    def get_response_type(self, post_html_obj):
        element = post_html_obj.find('span', style='color:#FF7711', string='Disputed')
        if element is None:
            element = post_html_obj.find('span', style='color:#777777', string='Clarified')
        if element is not None:
            return element.string.lower()
        else:
            return 'supported'  # Note that this needs to be removed from top level posts later

    def get_supporting_evidence(self, post_html_obj):
        supporting_envidence = post_html_obj.find('div', class_='supportingEvidence')
        # TODO: return the link or embedded object?
        return supporting_envidence is not None

    def create_posts(self, identifier, html_objs, discussion):
        posts = super().create_posts(identifier, html_objs, discussion)
        likely_quotes = quote_finder.find_quotes_from_posts(posts, verbose=False)
        self.remove_non_quotes(discussion, posts, likely_quotes)
        self.realize_quotes(likely_quotes, posts, identifier, discussion)
        return posts

    def remove_non_quotes(self, discussion, posts, likely_quotes):
        not_quotes = self.get_not_quotes(discussion, posts)
        for index, post_quotes in enumerate(likely_quotes):
            for quote in post_quotes:
                quote_text = posts[quote['source_index']]['text'][quote['source_start']:quote['source_end']].strip()
                if quote_text.lower() in not_quotes:
                    quote['delete_me'] = True
            likely_quotes[index] = [quote for quote in post_quotes if quote.get('delete_me') is not True]

    def get_not_quotes(self, discussion, posts):
        not_quotes = set()
        if 'text' in discussion:
            not_quotes.add(discussion['text'].lower())
        if 'top level sides' in discussion['annotations']:
            for side in discussion['annotations']['top level sides']:
                not_quotes.add(side.lower())
        for post in posts:
            if 'side' in post['annotations']:
                not_quotes.add(post['annotations']['side'].lower())
        return not_quotes

    def get_author_details_username(self, html_obj):
        title = html_obj.find('title').text
        username = title[:title.find("'")]
        return username

    def add_bio(self, author_details, html_obj):
        bio_obj = html_obj.find('div', id='tabs-3')
        bio_table = bio_obj.find('table', style='width:225px;border:0')
        if bio_table is not None:
            for row in bio_table.find_all('tr'):
                data = [cell.text.strip() for cell in row.find_all('td')]
                if len(data) == 2 and data[0] != 'Name:':  # Ignored for privacy reasons
                    assert data[0].lower()[-1] == ':'
                    author_details[data[0].lower().replace(' ', '_')[:-1]] = data[1]
            if 'age' in author_details:
                author_details['age'] = int(author_details['age'])
                if author_details['age'] < 0 or author_details['age'] > 127:
                    del author_details['age']


class CreateDebateLoader(RawDataLoader):
    def __init__(self):
        super().__init__(dataset_name='createdebate', ordered_categories=['discussion'])

    def get_category(self, descriptor):
        if descriptor['url'].startswith('http://www.createdebate.com/debate/show/'):
            return 'discussion'
        elif descriptor['url'].startswith('http://www.createdebate.com/user/viewprofile/'):
            return 'author'
        else:
            return None


class CreateDebateImporter(DatasetImporter):
    def __init__(self, flush_delay=60, simulated=True):
        super().__init__('createdebate', use_native_discussion_ids=True, use_native_post_ids=True, flush_delay=flush_delay, simulated=simulated)
        self.flush_order = ['author',
                            'text',
                            'markup',
                            'discussion',
                            'discussion_stance',
                            'post',
                            'quote',
                           ]

    def insert_discussion_details(self, discussion):
        super().insert_discussion_details(discussion)
        self.insert_discussion_stances(discussion)

    def insert_discussion_stances(self, discussion):
        sides = []
        side_lookup = {}
        if 'top level sides' in discussion['annotations']:
            for side in discussion['annotations']['top level sides']:
                side = side.replace('\n', ' ').strip()
                if side.lower() not in side_lookup:
                    side_index = len(sides)
                    sides.append(side)
                    side_lookup[side] = side_index
                    side_lookup[side.lower()] = side_index
                    side_lookup[side.lower().rstrip('.')] = side_index
        for post in discussion['posts']:
            side = post['annotations'].get('side')
            side_index = None
            if side is not None:
                side = side.replace('\n', ' ').strip()
                side_index = side_lookup.get(side)
                if side_index is None:
                    side_index = side_lookup.get(side.lower().rstrip('.'))
                if side_index is None:
                    side_index = len(sides)
                    sides.append(side)
                    side_lookup[side] = side_index
                    side_lookup[side.lower()] = side_index
            post['discussion_stance_id'] = side_index
        entries = [{'discussion_id': discussion['discussion_id'],
                    'discussion_stance_id': index,
                    'discussion_stance': side,
                    'topic_id':None,
                    'topic_stance_id': None} for index, side in enumerate(sides)]
        self.queues['discussion_stance'].extend(entries)


if __name__ == '__main__':
    skip_to = None
    loader = CreateDebateLoader()
    parser = Createdebate_HTML_Parser()
    importer = CreateDebateImporter(flush_delay=30, simulated=False)
    import_data(loader, parser, importer, skip_to=skip_to)
