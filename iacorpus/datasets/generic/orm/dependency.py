from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr


class DependencyMixin:
    __tablename__ = 'dependency'

    @declared_attr
    def governor_token(self):
        return relationship("Token", lazy=True, foreign_keys="[Dependency.text_id, Dependency.governor_token_index]")

    @declared_attr
    def dependent_token(self):
        return relationship("Token", lazy=True, foreign_keys="[Dependency.text_id, Dependency.dependent_token_index]")


def build_class(Base, engine):
    class Dependency(DependencyMixin, Base):
        pass
    return Dependency
