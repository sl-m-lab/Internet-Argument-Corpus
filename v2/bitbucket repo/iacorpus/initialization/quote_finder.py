# -*- coding: utf-8 -*-

from collections import Counter
from pprint import pprint
import string

from suffix_trees.STree import STree
import sys
sys.setrecursionlimit(10000)  # Long repeating posts lead to recursion fail (ie aaaaaaaaaaaaaaaaa...aaaaa)

markers = {'\n',
           '"', '“', '”', "'", '`', '‘', '’', '”', '”',
           '«', '»', '「', '」', '„', '“', '‹', '›',
           '*',
           '…',
           '/', '|', '\\'}
reasonably_long = 10


def find_quotes_from_posts(posts, lowercase=True, verbose=False):
    """posts should be a list of posts as provided by iac_html_parser
    posts should already be sorted. Any further sorting of posts will conflict with quote[source_index]!!!
    """
    # TODO: add feature whitelist_strs=None ... or do it at a later stage
    texts = list()
    parents = list()
    hints = list()
    authors = list()
    timestamps = list()
    posts_by_native_id = {post.get('native_post_id'): post for post in posts}
    if None in posts_by_native_id:
        del posts_by_native_id[None]
    for post in posts:
        if lowercase:
            texts.append(post['text'].lower())
        else:
            texts.append(post['text'])
        authors.append(post['username'])
        timestamps.append(post['timestamp'])

        parent = post.get('parent')
        if parent is None:
            parent = posts_by_native_id.get(post.get('native_parent_post_id'))

        if parent is not None:
            parents.append(posts.index(parent))
        else:
            parents.append(None)

        post_hints = list()
        for markup in post['markup']:
            post_hints.append(markup)
        hints.append(post_hints)

    return find_quotes(texts, parents, hints, authors, timestamps, verbose=verbose)


def find_quotes(texts: [''], parents: [0], hints: [], authors: [''], timestamps: [], verbose=False):
    """Each of the params is a list with consistent indices"""
    quotes = [[] for _ in texts]
    s_tree = STree(texts)
    _full_exact(quotes, s_tree, texts, parents, hints, authors, timestamps)
    _hinted(quotes, s_tree, texts, parents, hints, authors, timestamps)
    _lines(quotes, s_tree, texts, parents, hints, authors, timestamps)
    _combine_quotes(quotes, texts, parents)
    _expand_quotes(quotes, texts)
    _fix_markered_overlap(quotes, texts)
    _combine_quotes(quotes, texts, parents)  # also before _expand_quotes() to reduce work there.
    if verbose:
        _diagnostic(quotes, s_tree, texts, parents, hints, authors, timestamps)
    _kill_bad_quotes(quotes, texts, verbose=verbose)
    return quotes


def _full_exact(quotes, s_tree, texts, parents, hints, authors, timestamps):
    for index, text in enumerate(texts):
        matches = _viable_matches(s_tree, text, index, texts, parents, hints, authors, timestamps, preceding=False)
        for match_index, start in matches:
            match_evidence = [1 for evidence in [
                parents[match_index] == index,
                len(text) >= reasonably_long,
                (start == 0 or texts[match_index][start - 1] in markers) and
                (start + len(text) == len(texts[match_index]) or texts[match_index][start + len(text)] in markers)
                ] if evidence]
            if len(match_evidence) > 1:
                quote = {'start': start,
                         'end': start + len(text),
                         'source_index': index,
                         'source_start': 0,
                         'source_end': len(text),
                         'altered': False,
                         'truncated': False}
                quotes[match_index].append(quote)


def _hinted(quotes, s_tree, texts, parents, hints, authors, timestamps):
    for index, text in enumerate(texts):
        if text.strip() == '':
            continue
        for hint in hints[index]:
            if hint['end'] - hint['start'] >= reasonably_long and \
                    (hint['start'] == 0 or text[hint['start'] - 1] in markers) and \
                    (hint['end'] == len(text) or text[hint['end']] in markers):
                hint_text = text[hint['start']:hint['end']]
                matches = _viable_matches(s_tree, hint_text, index, texts, parents, hints, authors, timestamps)
                for match_index, start in matches:
                    if parents[index] == match_index:
                        quote = {'start': hint['start'],
                                 'end': hint['end'],
                                 'source_index': match_index,
                                 'source_start': start,
                                 'source_end': start + len(hint_text),
                                 'altered': False,
                                 'truncated': not (start == 0 and len(hint_text) == len(texts[match_index]))}
                        quotes[index].append(quote)

                hint_text = text[hint['start']:hint['end']].strip(''.join(markers)+' '+string.punctuation).strip()
                if reasonably_long <= len(hint_text) < hint['end'] - hint['start']:
                    real_start = text.find(hint_text, hint['start'], hint['end'])
                    assert real_start >= hint['start'] >= 0
                    real_end = real_start + len(hint_text)
                    matches = _viable_matches(s_tree, hint_text, index, texts, parents, hints, authors, timestamps)
                    for match_index, start in matches:
                        if parents[index] == match_index:
                            quote = {'start': real_start,
                                     'end': real_end,
                                     'source_index': match_index,
                                     'source_start': start,
                                     'source_end': start + len(hint_text),
                                     'altered': False,
                                     'truncated': not (start == 0 and len(hint_text) == len(texts[match_index])),
                                     'markered_start': hint['start'],
                                     'markered_end': hint['end']}
                            quotes[index].append(quote)


def _lines(quotes, s_tree, texts, parents, hints, authors, timestamps):
    line_hints = [[] for _ in texts]
    for index, text in enumerate(texts):
        post_line_hints = []
        lines = text.split('\n')
        curr = 0
        for line in lines:
            hint = {'start': curr, 'end': curr + len(line), 'type': 'line'}
            if hint['end'] - hint['start'] < len(text) and \
                    not any([hint['start'] == existing['start'] and
                             hint['end'] == existing['end']
                             for existing in hints[index]]):
                # Ignore existing hints to avoid repeat work
                post_line_hints.append(hint)
            curr += len(line) + 1  # +1 for '\n'
        line_hints[index] = post_line_hints

    _hinted(quotes, s_tree, texts, parents, line_hints, authors, timestamps)


def _combine_quotes(quotes, texts, parents):
    for index, post_quotes in enumerate(quotes):
        for other in post_quotes:
            if other.get('delete_me') is True:
                continue
            for quote in post_quotes:
                if quote is other or quote.get('delete_me') is True:
                    continue
                if quote['end'] - quote['start'] > other['end'] - other['start'] and \
                        quote['start'] <= other['start'] <= other['end'] <= quote['end']:
                    # contained - (don't care the source)
                    other['delete_me'] = True
                elif all([quote[field] == other[field] for field in ['start', 'end', 'source_index']]):
                    # equal - prefer not altered, earlier source_start
                    if (quote['altered'] and not other['altered']) or other['source_start'] < quote['source_start']:
                        quote['delete_me'] = True
                    else:
                        other['delete_me'] = True
                elif all([quote[field] == other[field] for field in ['start', 'end']]):
                    # equal - different source - prefer parent , not altered, not truncated
                    if other['source_index'] == parents[index] or \
                            (quote['source_index'] != parents[index] and
                             (quote['altered'] and not other['altered']) and
                             (quote['truncated'] and not other['truncated'])):
                        quote['delete_me'] = True
                    else:
                        other['delete_me'] = True
                elif quote['end'] <= other['start'] and \
                        texts[index][quote['end']:other['start']].strip(''.join(markers)+'. ').strip() == '' and \
                        quote['source_index'] == other['source_index'] and \
                        quote['source_end'] <= other['source_start'] and \
                        texts[quote['source_index']][quote['source_end']:other['source_start']].strip() == '':
                    # abutting
                    quote['end'] = max(quote['end'], other['end'])
                    quote['source_end'] = max(quote['source_end'], other['source_end'])
                    quote['altered'] = quote['altered'] or other['altered']
                    quote['truncated'] = not (quote['source_start'] == 0 and
                                              quote['source_end'] == len(texts[quote['source_index']]))
                    if other.get('markered_end') is not None:
                        quote['markered_end'] = other['markered_end']
                    other['delete_me'] = True
                if other.get('delete_me') is True:
                    break

        new_post_quotes = []
        for quote in post_quotes:
            if quote.get('delete_me') is not True:
                quote['truncated'] = not (quote['source_start'] == 0 and
                                          quote['source_end'] == len(texts[quote['source_index']]))
                if quote.get('markered_start') is not None and quote.get('markered_start') >= quote['start']:
                    del quote['markered_start']
                if quote.get('markered_end')is not None and quote.get('markered_end') <= quote['end']:
                    del quote['markered_end']
                new_post_quotes.append(quote)
        quotes[index] = new_post_quotes


def _expand_quotes(quotes, texts):
    for index, post_quotes in enumerate(quotes):
        text = texts[index]
        for quote in post_quotes:
            source_text = texts[quote['source_index']]
            while quote['source_start'] > 0 and quote['start'] > 0 and \
                    source_text[quote['source_start'] - 1] == text[quote['start'] - 1] and \
                    text[quote['start'] - 1] != '\n':
                quote['source_start'] -= 1
                quote['start'] -= 1
                if 'markered_start' in quote and quote['markered_start'] >= quote['start']:
                    del quote['markered_start']
            while quote['source_end'] < len(source_text) and quote['end'] < len(text) and \
                    source_text[quote['source_end']] == text[quote['end']] and \
                    text[quote['end']] != '\n':
                quote['source_end'] += 1
                quote['end'] += 1
                if 'markered_end' in quote and quote['markered_end'] <= quote['end']:
                    del quote['markered_end']


def _fix_markered_overlap(quotes, texts):
    for index, post_quotes in enumerate(quotes):
        for other in post_quotes:
            if 'markered_start' in other or 'markered_end' in other:
                for quote in post_quotes:
                    if quote is other:
                        continue
                    if 'markered_start' in other and other['markered_start'] < quote['end'] <= other['start']:
                        other['markered_start'] = quote['end']
                    if 'markered_end' in other and other['end'] <= quote['start'] < other['markered_end']:
                        other['markered_end'] = quote['start']
                    if 'markered_end' in other and 'markered_start' in quote \
                            and quote['markered_start'] < other['markered_end'] <= quote['start']:
                        other['markered_end'] = max(quote['markered_start'], other['end'])
                        quote['markered_start'] = min(other['markered_end'], quote['start'])


def _viable_matches(s_tree, search_text, index, texts, parents, hints, authors, timestamps, preceding=True):
    if search_text.strip() == '':
        return []
    matches = s_tree.find_all(search_text)
    indexed_matches = [_suffix_tree_index_to_real_index(stree_index, texts) for stree_index in matches]
    indexed_matches = [(match_index, start)
                       for match_index, start in indexed_matches
                       if index != match_index and
                       authors[index] != authors[match_index] and
                       ((preceding and timestamps[match_index] <= timestamps[index]) or
                        (not preceding and timestamps[index] <= timestamps[match_index]))]
    return indexed_matches


def _suffix_tree_index_to_real_index(stree_index, texts):
    # TODO: currently O(n), should be O(log(n)) or less. profile before optimizing
    curr = stree_index
    for index, text in enumerate(texts):
        text_len = len(text)
        if curr < text_len:
            return index, curr
        else:
            curr -= text_len + 1
    assert False


def _kill_bad_quotes(quotes, texts, verbose=True):
    for index, post_quotes in enumerate(quotes):
        for quote in post_quotes:
            if quote['end'] - quote['start'] == len(texts[index]):
                quote['delete_me'] = True
        for quote in post_quotes:
            if quote.get('delete_me') is True:
                continue
            for other in post_quotes:
                if quote is other or other.get('delete_me') is True:
                    continue
                if quote['start'] <= other['start'] < quote['end']:
                    if quote['end'] - quote['start'] > other['end'] - other['start']:
                        other['delete_me'] = True
                    else:
                        quote['delete_me'] = True
                if quote.get('delete_me') is True:
                    break

        new_post_quotes = [quote for quote in post_quotes if quote.get('delete_me') is not True]
        quotes[index] = new_post_quotes


def _diagnostic(quotes, s_tree, texts, parents, hints, authors, timestamps):
    counts = Counter()
    for index, post_quotes in enumerate(quotes):
        if len(post_quotes) > 0:
            counts['Posts with'] += 1
        for quote in post_quotes:
            counts['total'] += 1
            pprint(quote)
            print(texts[index][quote['start']:quote['end']])
            print('-----------------')
            print(texts[quote['source_index']])
            print('\n------------\n')
            print(texts[index])
            print('\n\n')
            for other in post_quotes:
                if quote is other:
                    continue
                if quote['start'] < other['start'] < quote['end']:
                    counts['overlapping'] += 1
                if quote['start'] == other['start']:
                    counts['identical starts (doubled)'] += 1

    pprint(counts)
