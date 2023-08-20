import re
import json
from itertools import combinations
from collections import defaultdict
import datetime
import dateutil.parser

from bs4 import BeautifulSoup

MARKUP_TAGS = {'font': 'font',
               'code': 'code',
               'pre': 'preformatted',
               'span': 'span',
               'div': 'div',
               'b': 'bold',
               'u': 'underline',
               'i': 'italic',
               'a': 'link',
               'center': 'center',
               'sup': 'superscript',
               'sub': 'subscript',
               's': 'incorrect',
               'del': 'deleted',
               'ins': 'inserted',
               'em': 'emphasized',
               'strong': 'strong',
               'small': 'small'}
BR_RE = re.compile(r'\s*(<br\s*/?>\s*)+', re.IGNORECASE)


class IAC_HTML_Parser():
    def __init__(self):
        self.timestamp_format = None
        self.tz_offset_formatted = None

    def parse_entry(self, category, identifier, html_texts):
        html_objs = self._get_html_objs(html_texts)
        if self.should_skip(category, identifier, html_objs):
            return None
        if category == 'discussion':
            discussion = self.create_discussion(identifier, html_objs)
            posts = self.create_posts(identifier, html_objs, discussion)
            discussion['posts'] = posts
            return discussion
        elif category == 'author':
            author_details = self.create_author_details(identifier, html_objs)
            return author_details
        else:
            return None  # TODO: raise

    def should_skip(self, category, identifier, html_objs):
        """Override me!"""
        return False

    def _get_html_objs(self, html_texts):
        html_objs = [self._get_html_obj(html) for html in html_texts]
        return html_objs

    def _get_html_obj(self, html_str, html_parser='html5lib'):
        # 'lxml' would be faster but some sites are sloppy about closing tags and 'html5lib' handles those sites better
        html_str = self._preprocess_html(html_str)
        html_obj = BeautifulSoup(html_str, html_parser)
        return html_obj

    def _preprocess_html(self, html_str):
        html_str = html_str.replace('\r\n', '\n')
        html_str = BR_RE.sub('<br/>', html_str)
        return html_str

    def create_discussion(self, identifier, html_objs):
        discussion = dict()
        discussion['url'] = self.get_canonical_url(identifier, html_objs)
        discussion['title'] = self.get_canonical_title(identifier, html_objs, discussion['url'])
        discussion['native_discussion_id'] = self.get_native_discussion_id(identifier, html_objs)
        discussion['initiating_author'] = self.get_initiating_author(identifier, html_objs)
        discussion['annotations'] = self.get_discussion_annotations(identifier, html_objs)
        return discussion

    def get_canonical_url(self, identifier, html_objs):
        """By default it assumes the identifier is the canonical url
        Another option would be something like:
          min_url = min(html_objs, key=lambda x: len(x.find('link', rel='canonical')['href']))['href']
        """
        return identifier

    def get_canonical_title(self, identifier, html_objs, canonical_url):
        title = html_objs[0].title.text
        return title

    def get_native_discussion_id(self, identifier, html_objs):
        """Override me!
        (if not already handled with identifier..)"""
        native_discussion_id = identifier
        return native_discussion_id

    def get_initiating_author(self, identifier, html_objs):
        """Override me!
        If initiating_author = None is returned, it will be determined by first post later"""
        initiating_author = None
        return initiating_author

    def get_discussion_annotations(self, identifier, html_objs):
        """Override me!"""
        annotations = dict()
        return annotations

    def create_posts(self, identifier, html_objs, discussion):
        posts = list()
        for html_obj in html_objs:
            for post_html_obj in self.get_post_html_objs(html_obj):
                try:
                    post = self.create_post(post_html_obj, html_obj, discussion)
                except:
                    print('Failed while trying to create the following post:')
                    print(discussion.get('discussion_url'))
                    print(post_html_obj)
                    raise
                posts.append(post)
        self.assign_post_parents(identifier, html_objs, discussion, posts)
        posts = self.fix_double_posts(identifier, html_objs, discussion, posts)
        return posts

    def get_post_html_objs(self, html_obj):
        """Override me!"""
        for post_html_obj in html_obj.find_all('div', class_='post'):  # For example...
            yield post_html_obj

    def assign_post_parents(self, identifier, html_objs, discussion, posts):
        """Override me!"""

    def create_post(self, post_html_obj, html_obj, discussion):
        post = dict()
        post['username'] = self.get_post_author(post_html_obj)
        post['creation_date'] = self.get_timestamp(post_html_obj)
        post['native_post_id'] = self.get_native_post_id(post_html_obj)
        post['native_parent_post_id'] = self.get_native_parent_post_id(post_html_obj)
        post['annotations'] = self.get_post_annotations(post_html_obj)
        text, markup, quotes = self.get_text(post_html_obj)
        post['text'] = text
        post['markup'] = markup
        post['quotes'] = quotes
        return post

    def get_post_author(self, post_html_obj):
        """Override me!"""
        return None

    def get_timestamp(self, post_html_obj):
        """Override me!
        If exactly one <time datetime='1999-12-31T23:59:59+00:00'> tag exists the following should work.
        May desire first, last, or something else entirely."""
        time_elements = post_html_obj.find_all('time')
        assert len(time_elements) == 1
        timestamp_str = list(time_elements)[0]['datetime']
        timestamp = self.str_to_timestamp(timestamp_str)
        return timestamp

    def get_native_post_id(self, post_html_obj):
        """Override me!"""
        return None

    def get_native_parent_post_id(self, post_html_obj):
        """Override me!"""
        return None

    def get_post_annotations(self, post_html_obj):
        """Override me!"""
        return None

    def get_text(self, post_html_obj):
        """Consider overriding element_to_text() first"""
        text_obj = self.get_text_containing_element(post_html_obj)
        text, markup, quotes = self.build_text(text_obj)
        text, markup, quotes = self.cleanup_text(text, markup, quotes)
        return text, markup, quotes

    def get_text_containing_element(self, post_html_obj):
        """Override me!"""
        text_obj = post_html_obj.find('div', class_='post body')  # for example
        return text_obj

    def build_text(self, curr, preceding_character='\n', is_pre=False):
        """Recursive function
        Whitespace generally collapsed
        (preceding_character='\n' means newlines generally shouldn't appear at the start)
        """
        text = ''
        markup = list()
        quotes = list()

        for child in curr.children:
            if hasattr(child, 'contents'):
                internal_text, internal_markup, internal_quotes = self.element_to_text(child, preceding_character, is_pre)
                self._update_offsets(len(text), internal_markup, internal_quotes)
                text += internal_text
                if len(text) > 0:
                    preceding_character = text[-1]
                markup.extend(internal_markup)
                quotes.extend(internal_quotes)
            else:
                internal_text = child.string
                if not is_pre:
                    # This removes extra whitespace.
                    # Would do it on the html directly but that would affect attributes and pre tags badly
                    leading_space = ' ' if not preceding_character.isspace() and len(internal_text) > 0 and internal_text[0].isspace() else ''
                    trailing_space = ' ' if len(internal_text) > 1 and internal_text[-1].isspace() else ''
                    internal_text = leading_space + ' '.join(internal_text.split()) + trailing_space
                    if preceding_character.isspace():
                        internal_text = internal_text.lstrip()
                text += internal_text
                if len(text) > 0:
                    preceding_character = text[-1]

        return text, markup, quotes

    def element_to_text(self, element, preceding_character, is_pre):
        """Override me!

        Example:
        if element is of special interest:
          text, markup, quotes = whatever...
        else:
          text, markup, quotes = super().element_to_text(element, preceding_character, is_pre)
        return text, markup, quotes
        """
        text = ''
        markup = list()
        quotes = list()
        if element.name == 'br':
            if preceding_character != '\n':
                text = '\n'

        elif element.name in {'wbr'}:
            # Ignored tags
            internal_text, internal_markup, internal_quotes = self.build_text(element, preceding_character, is_pre)
            text = internal_text
            markup.extend(internal_markup)
            quotes.extend(internal_quotes)

        elif element.name in {'img', 'iframe', 'video'}:
            text = element.get('alt')
            if text is None or text.strip() == '':
                text = element.get('title')
            if text is None or text.strip() == '':
                text = element.get('src')
            if text is None:
                text = ''
            text = ' ' + text.strip() + ' '
            markup_attribute = dict(element.attrs)
            markup_entry = {'start': 0, 'type': element.name, 'attributes': json.dumps(markup_attribute), 'end': len(text)}
            markup.append(markup_entry)

        elif element.name in {'p', 'div',
                              'blockquote',
                              'ul', 'ol', 'li',
                              'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:  # TODO: better lists, etc
            # Paragraph/block tags
            if preceding_character != '\n':
                text = '\n'
                preceding_character = text[-1]
            internal_text, internal_markup, internal_quotes = self.build_text(element, preceding_character, is_pre)
            internal_text, internal_markup, internal_quotes = self.remove_trailing_whitespace(internal_text, internal_markup, internal_quotes)
            self._update_offsets(len(text), internal_markup, internal_quotes)
            text += internal_text
            if not text.endswith('\n'):
                text += '\n'
            markup.extend(internal_markup)
            quotes.extend(internal_quotes)

        elif element.name in MARKUP_TAGS:
            type_name = MARKUP_TAGS[element.name]
            if element.attrs is not None:
                markup_attribute = dict(element.attrs)
                if type_name == 'link' and 'target' in markup_attribute and markup_attribute['target'].strip() in {'_blank', '_self'}:
                    del markup_attribute['target']
            else:
                markup_attribute = None
            internal_text, internal_markup, internal_quotes = self.build_text(element, preceding_character, is_pre=(element.name == 'pre'))
            markup_entry = {'start': 0, 'type': type_name, 'attributes': json.dumps(markup_attribute)}
            text = internal_text
            markup_entry['end'] = len(text)  # after adding internal text
            markup.append(markup_entry)
            markup.extend(internal_markup)
            quotes.extend(internal_quotes)

        elif element.name == 'script':
            pass

        else:
            print('Unhandled tag:', element)
            if element.text is not None:
                text = element.text.strip()
                text = re.sub(r'\n\s*\n', '\n', text)
                if not preceding_character.isspace():
                    text = '\n' + text
                if len(text) == 0 or text[-1] != '\n':
                    text += '\n'
                print('Using:', text)

        return text, markup, quotes

    def cleanup_text(self, text, markup, quotes):
        """Cleans up extra whitespace, merges markup, removes empty markup"""
        text, markup, quotes = self.cleanup_markup(text, markup, quotes)
        text, markup, quotes = self.remove_trailing_whitespace(text, markup, quotes)
        return text, markup, quotes

    def cleanup_markup(self, text, markup, quotes):
        # Removes empty markup
        markup = [entry for entry in markup if entry['start'] != entry['end']]
        # Merges markup
        grouped = defaultdict(list)
        for entry in markup:
            grouped[(entry['type'], str(entry['attributes']))].append(entry)
        for entries in grouped.values():
            entries.sort(key=lambda x: x['start'])
            for entry, other in combinations(entries, 2):
                if entry.get('delete_me') is True or other.get('delete_me') is True:
                    continue
                if text[entry['end']:other['start']].strip() == '':
                    entry['end'] = max(entry['end'], other['end'])
                    other['delete_me'] = True
        markup = [entry for entry in markup if entry.get('delete_me') is not True]
        return text, markup, quotes

    def remove_trailing_whitespace(self, text, markup, quotes):
        max_end = max(max([entry['end'] for entry in markup], default=0), max([entry['text_offset'] for entry in quotes], default=0))
        loc = max(max_end, len(text.rstrip()))
        if loc < len(text):
            text = text[:loc]
        return text, markup, quotes

    def _update_offsets(self, amount, markup, quotes):
        for entry in markup:
            entry['start'] += amount
            entry['end'] += amount
        for quote in quotes:
            if quote.get('parent_quote_index') is not None:
                quote['text_offset'] += amount

    def str_to_timestamp(self, timestamp_str):
        """separated to deal with relative situations (e.g. 'yesterday')
        Be Sure UTC/local is as intended (also, check sign...).
         current_local_offset = -time.timezone/3600
        """
        if self.timestamp_format is None:
            timestamp = dateutil.parser.parse(timestamp_str)
        else:
            if self.tz_offset_formatted is not None:
                timestamp = datetime.datetime.strptime(timestamp_str + ' ' + self.tz_offset_formatted, self.timestamp_format + ' %z')
            else:
                timestamp = datetime.datetime.strptime(timestamp_str, self.timestamp_format)
        return timestamp

    def fix_double_posts(self, identifier, html_objs, discussion, posts):
        possible_duplicates = defaultdict(set)
        for i, post in zip(range(len(posts)), posts):
            sudo_post = dict()
            for field in ['text', 'username', 'markup', 'quotes']:
                sudo_post[field] = post[field]
            possible_duplicates[str(sudo_post)].add(i)

        for dups in possible_duplicates.values():
            dups = [posts[i] for i in dups]
            if len(dups) > 1:
                if len({dup['native_parent_post_id'] for dup in dups}) == 1:  # TODO: also if one responds to the other
                    kept = min(dups, key=lambda x: (-len(str(x)), x['creation_date'], x['native_post_id']))
                    assert kept.get('delete_me') is not True
                    for dup in dups:
                        if dup is not kept:
                            dup['delete_me'] = True
                            for post in posts:
                                if post['native_parent_post_id'] == dup['native_post_id']:
                                    post['native_parent_post_id'] = kept['native_post_id']
        posts = [post for post in posts if post.get('delete_me') is not True]
        return posts

    def realize_quotes(self, likely_quotes, posts, identifier, discussion):
        source_indexed_quotes = defaultdict(list)
        for likely_post_quotes in likely_quotes:
            for quote in likely_post_quotes:
                source_indexed_quotes[quote['source_index']].append(quote)
        for index, likely_post_quotes, post in zip(range(len(posts)), likely_quotes, posts):
            text = post['text']
            new_text = []
            new_quotes = []
            likely_post_quotes.sort(key=lambda q: q['start'] if q.get('markered_start') is None else q.get('markered_start'))
            curr = 0
            for quote in likely_post_quotes:
                start = quote['start'] if quote.get('markered_start') is None else quote.get('markered_start')
                end = quote['end'] if quote.get('markered_end') is None else quote.get('markered_end')
                if start == 0 and end < len(text) and text[end] == '\n' and all([quote is other or other.get('start') is None or other['start'] > end for other in likely_post_quotes]):
                    end += 1  # chomps off first newline if a post opens with a quote followed by a newline
                new_text.append(text[curr:start])
                quote['text_offset'] = sum([len(segment) for segment in new_text])
                quote['text'] = text[quote['start']:quote['end']]
                del quote['start']
                del quote['end']
                new_quotes.append(quote)  # Should be same object, not a copy

                # update markup within post
                for markup in post['markup']:
                    if markup['start'] > quote['text_offset']:
                        markup['start'] = max(quote['text_offset'], markup['start'] - (end - start))
                    if markup['end'] > quote['text_offset']:
                        markup['end'] = max(quote['text_offset'], markup['end'] - (end - start))
                # update any existing quotes (probably none)
                for other in post['quotes']:
                    if other['text_offset'] > quote['text_offset']:
                        other['text_offset'] = max(quote['text_offset'], other['text_offset'] - (end - start))
                # update all quotes that point to this post
                for other in source_indexed_quotes[index]:
                    if other['source_start'] > quote['text_offset']:
                        other['source_start'] = max(quote['text_offset'], other['source_start'] - (end - start))
                    if other['source_end'] > quote['text_offset']:
                        other['source_end'] = max(quote['text_offset'], other['source_end'] - (end - start))
                curr = end
            new_text.append(text[curr:])
            post['quotes'].extend(new_quotes)

            cleaned_text, cleaned_markup, cleaned_quotes = self.cleanup_text(''.join(new_text), post['markup'], post['quotes'])
            post['text'] = cleaned_text
            post['markup'] = cleaned_markup
            post['quotes'] = cleaned_quotes

    def create_author_details(self, identifier, html_objs):
        html_obj = html_objs[0]
        author_details = dict()
        author_details['username'] = self.get_author_details_username(html_obj)
        self.add_bio(author_details, html_obj)
        return author_details

    def get_author_details_username(self, html_obj):
        """Override me!"""
        return None

    def add_bio(self, author_details, html_obj):
        """Override me!"""
        pass
