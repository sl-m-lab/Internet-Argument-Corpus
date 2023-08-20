import re
import operator
from collections import namedtuple

from iacorpus.utilities.misc import lazy_property

PostFullID = namedtuple('PostFullID', ['discussion_id', 'post_id'])


class PostMixin:
    __tablename__ = 'post'

    @lazy_property
    def text(self):
        return self.text_obj.text

    @lazy_property
    def username(self):
        return self.author_obj.username

    @lazy_property
    def full_id(self):
        return PostFullID(self.discussion_id, self.post_id)

    @lazy_property
    def parent(self):
        return self.discussion.posts.get(self.parent_post_id)

    @lazy_property
    def quotes(self):
        if hasattr(self, 'all_quotes'):
            return sorted([quote for quote in self.all_quotes.values() if quote.parent_quote_index is None],
                          key=operator.attrgetter('text_offset', 'quote_index'))
        return []

    def load_parse_data(self):
        """deprecated"""
        pass


class TextPrinting:
    def text_with_quotes(self, merge_newlines=True, quote_marker_start='[Quote]\n', quote_marker_end='\n[/Quote]'):
        """Adds the post's quotes to the text.
        Use for human consumable text.
        """
        text_list = list()
        curr_index = 0
        last_char_index = len(self.text.rstrip()) - 1
        for quote in self.quotes:
            quote_text = quote.text_with_quotes(quote_marker_start=quote_marker_start,
                                                quote_marker_end=quote_marker_end)
            quote_text = quote_marker_start + quote_text.strip() + quote_marker_end
            if quote.text_offset < last_char_index:
                quote_text += '\n'
            if quote.text_offset > 0:
                quote_text = '\n' + quote_text
            preceding_text = self.text[curr_index:quote.text_offset]
            if merge_newlines:
                preceding_text = preceding_text.replace('\n', '\n\n')
                preceding_text = re.sub(r'\n\s+\n', '\n\n', preceding_text)
            text_list.append(preceding_text)
            text_list.append(quote_text)
            curr_index = quote.text_offset

        following_text = self.text[curr_index:]
        if merge_newlines:
            following_text = following_text.replace('\n', '\n\n')
            following_text = re.sub(r'\n\s+\n', '\n\n', following_text)
        text_list.append(following_text)

        return ('\n\n'.join([entry.strip() for entry in text_list if entry is not ''])).strip()


def build_class(Base, engine):
    class Post(PostMixin, TextPrinting, Base):
        pass
    return Post
