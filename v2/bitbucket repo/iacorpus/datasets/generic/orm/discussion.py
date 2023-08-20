import operator
from iacorpus.utilities.misc import lazy_property


class DiscussionMixin:
    __tablename__ = 'discussion'

    # TODO: test performance vs @reconstructor+init() ... we typically want this attribute but sometimes not
    @lazy_property
    def post_list(self):
        return sorted(self.posts.values(), key=operator.attrgetter('creation_date', 'post_id'))

    @lazy_property
    def topic(self):
        if hasattr(self, 'topics') and len(self.topics) == 1:
            return self.topics[0].topic
        else:
            return None

    @lazy_property
    def topic_id(self):
        if hasattr(self, 'topics') and len(self.topics) == 1:
            return self.topics[0].topic_id
        else:
            return None

    def __iter__(self):
        iterator = self.get_posts()
        return iterator

    def get_posts(self):
        iterator = iter(self.post_list)
        return iterator


def build_class(Base, engine):
    class Discussion(DiscussionMixin, Base):
        pass
    return Discussion
