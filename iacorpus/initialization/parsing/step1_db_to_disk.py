"""This dumps the text table to disk in preparation for parsing.
It splits tests table entries by quotes to ensure
coref and parsing don't jump over quotes
('he' after the quote may refer to someone the quote refers to
and not someone from before the quote)"""

from collections import defaultdict
import os

from sqlalchemy import Table, select

from iacorpus import load_dataset


def main(dbname: str, parsing_dir: str):
    text_dir = os.path.join(parsing_dir, 'texts')
    connection = load_dataset(dbname).connection
    breaks = get_segmentation_breaks(connection)
    write_texts_to_disk(text_dir, connection, breaks)
    write_filelist(parsing_dir, text_dir)


def write_texts_to_disk(text_dir: str, connection, breaks: dict):
    # duplicates = defaultdict(list)  # type: dict[str:list[int]]  # TODO: support filtering on duplicates
    text_table = Table('text', connection.metadata, autoload=True)
    query = select([text_table.c.text_id, text_table.c.text])
    # total = 0
    for text_id, text in query.execute():
        # if text in duplicates:
        #     duplicates[text].append(text_id)
        #     continue
        # else:
        #     duplicates[text].append(text_id)
        sub_directory = os.path.join(text_dir, str(int(text_id / 1000)))  # assumes they are relatively contiguous
        os.makedirs(sub_directory, exist_ok=True)

        breaks[text_id].update([0, len(text)])
        boundaries = sorted(breaks[text_id])
        partitions = [text[boundaries[i]:boundaries[i + 1]] for i in range(len(boundaries) - 1)]

        offset = 0
        for text_segment in partitions:
            filename = str(text_id) + '_' + str(offset)
            assert len(filename) < 255, filename
            # total += 1
            file = open(os.path.join(sub_directory, filename), 'w')
            file.write(text_segment)
            file.close()
            offset += len(text_segment)


def write_filelist(top_dir: str, text_dir: str, excluded=None) -> list:
    filelist = []
    for root, dirs, files in os.walk(text_dir):
        for filename in files:
            text_id, offset = filename.split('_')
            if excluded and text_id in excluded:
                continue
            filelist.append(os.path.join(root, filename))
    filelist.sort()
    filelist_file = open(os.path.join(top_dir, 'filelist.txt'), 'w')
    filelist_file.write('\n'.join(filelist))
    filelist_file.close()
    print('total:', len(filelist))
    return filelist


def get_segmentation_breaks(connection) -> dict:
    entries = defaultdict(set)  # type: dict[int, set[int]]
    if not connection.metadata.bind.has_table('quote'):
        return entries
    query_str = """select text.text_id as text_id, text_offset
from quote
 join post using(discussion_id, post_id)
 join text on post.text_id = text.text_id
where parent_quote_index is null;"""
    for row in connection.session.execute(query_str):
        entries[row[0]].add(row[1])

    # For nested quotes
    query_str = """select text.text_id as text_id, nested.text_offset
from quote as nested
 join quote
   on quote.discussion_id=nested.discussion_id
   and quote.post_id=nested.post_id
   and quote.quote_index=nested.parent_quote_index
 join text on quote.text_id = text.text_id;"""
    for row in connection.session.execute(query_str):
        entries[row[0]].add(row[1])
    return entries


if __name__ == '__main__':
    input_parsing_dir = './parsing'
    main('fourforums', input_parsing_dir)

