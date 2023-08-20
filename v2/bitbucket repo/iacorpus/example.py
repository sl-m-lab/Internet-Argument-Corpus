from pprint import pprint

import sqlalchemy

from iacorpus import load_dataset


def iterate_example():
    print('\nLoading a dataset:')
    dataset = load_dataset('fourforums')
    print(dataset.dataset_metadata)
    print('\nIterating over discussions:')
    for discussion in dataset:
        print(discussion)
        for post in discussion:
            print(post)
            return


def load_orm_object():
    print('\nLoading an ORM object directly:')
    dataset = load_dataset('fourforums')
    cls = dataset.connection.Base.classes.Post
    query = dataset.connection.session.query(cls).filter_by(discussion_id=1, post_id=1)
    post = query.scalar()
    print(post)


def query_table():
    print('\nQuerying a table directly:')
    dataset = load_dataset('fourforums')
    table = dataset.get_table('text')
    # alternatively: sqlalchemy.Table(tablename, dataset.connection.metadata, autoload=True)
    query = sqlalchemy.select([table.c.text_id, table.c.text]).limit(4)
    raw_result = query.execute()
    dict_result = [dict(entry) for entry in raw_result]
    pprint(dict_result)


def straight_sql():
    print('\nSQL Query (calculating post count, may take a moment):')
    dataset = load_dataset('fourforums')
    query_str = """select
     title as discussion_title,
     count(*) as post_count
    from post
     natural join discussion
    group by discussion_id
    order by count(*) desc
    limit 4;
    """
    result = dataset.query(query_str, to_dicts=True)
    # alternatively: dataset.connection.session.execute(query_str)
    pprint(result)


def parses():
    dataset = load_dataset('fourforums')
    for discussion in dataset:
        print(discussion)
        for post in discussion:
            print(post.text_obj.dependencies[0])
            print(post.text_obj.dependencies[0].dependency_relation_obj.dependency_relation)
            print(post.text_obj.dependencies[0])
            return


if __name__ == '__main__':
    iterate_example()
    load_orm_object()
    query_table()
    straight_sql()
