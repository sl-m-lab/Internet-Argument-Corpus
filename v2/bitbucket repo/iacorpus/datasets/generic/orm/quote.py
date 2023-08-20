import operator
from collections import namedtuple

from iacorpus.utilities.misc import lazy_property
from iacorpus.datasets.generic.orm.post import TextPrinting

QuoteFullID = namedtuple('QuoteFullID', ['discussion_id', 'post_id', 'quote_index'])


class QuoteMixin:
    __tablename__ = 'quote'

    @lazy_property
    def text(self):
        return self.text_obj.text

    @lazy_property
    def source_post(self):
        if self.post.discussion.discussion_id == self.source_discussion_id:
            return self.post.discussion.posts.get(self.source_post_id)
        return None

    @lazy_property
    def full_id(self):
        return QuoteFullID(self.discussion_id, self.post_id, self.quote_index)

    @lazy_property
    def quotes(self):
        return sorted([quote for quote in self.post.all_quotes.values()
                       if quote.parent_quote_index == self.quote_index],
                      key=operator.attrgetter('text_offset', 'quote_index'))


def build_class(Base, engine):
    class Quote(QuoteMixin, TextPrinting, Base):
        pass
    return Quote
