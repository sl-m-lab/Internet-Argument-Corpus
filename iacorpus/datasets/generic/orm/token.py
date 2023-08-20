from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from iacorpus.utilities.misc import lazy_property


class TokenMixin:
    __tablename__ = 'token'

    @declared_attr
    def word_obj(self):
        return relationship("Word", lazy=True, foreign_keys="[Token.word_id]")

    @declared_attr
    def lemma_word_obj(self):
        return relationship("Word", lazy=True, foreign_keys="[Token.lemma_word_id]")

    @lazy_property
    def word(self):
        return self.word_obj.word

    @lazy_property
    def lemma(self):
        return self.lemma_word_obj.word


def build_class(Base, engine):
    class Token(TokenMixin, Base):
        pass
    return Token
