class TextMixin:
    __tablename__ = 'text'


class ParseMixin:
    pass  # might add methods


def build_class(Base, engine):
    supers = [Base, TextMixin]
    if engine.has_table("token"):
        supers.append(ParseMixin)

    class Text(*supers):
        pass
    return Text
