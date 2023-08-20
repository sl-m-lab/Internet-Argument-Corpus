from pprint import pprint
import sys
import os
import subprocess
import tempfile
import datetime
import re

try:
    # lxml seems to be faster - 20%?
    from lxml import etree as ET
except ImportError:
    print('lxml package not found, using Python\'s xml (a bit slower)')
    import xml.etree.ElementTree as ET


_LEMMA_BUG_RE = re.compile(r'(-[lr][rcs]b-)_[A-Z$]+$')


def call_corenlp(file: str, xml_output_dir=None, filelist=None, corenlp_path=None, properties_path=None, memory='16g',
                 verbose=True, noClobber=False, replaceExtension=False, threads=None, extension=None) -> str:
    """Constructs a command and runs it. This yields xml files which can be sent to consume_xml_dir()
    Returns path to outputDirectory

    if corenlp_path is None, it will attempt to use the environment variable "CORENLP"
    if outputDirectory is unspecified, one will be created in your temp location (OS specific).

    Some corenlp commandline parameters are passed through to coreNLP. You may want to set a few of these...
      For reference here is what 3.3.1 says:
        Command line properties:
            "file" - run the pipeline on the content of this file, or on the content of the files in this directory
                     XML output is generated for every input file "file" as file.xml
            "extension" - if -file used with a directory, process only the files with this extension
            "filelist" - run the pipeline on the list of files given in this file
                         output is generated for every input file as file.outputExtension
            "outputDirectory" - where to put output (defaults to the current directory)
            "outputExtension" - extension to use for the output file (defaults to ".xml" for XML, ".ser.gz" for serialized).  Don't forget the dot!
            "outputFormat" - "xml" to output XML (default), "serialized" to output serialized Java objects, "text" to output text
            "serializer" - Class of annotation serializer to use when outputFormat is "serialized".  By default, uses Java serialization.
            "replaceExtension" - flag to chop off the last extension before adding outputExtension to file
            "noClobber" - don't automatically override (clobber) output files that already exist
            "threads" - multithread on this number of threads
    """
    if not os.path.exists(file):
        raise Exception('Input File/Dir not found <'+str(file)+'>')
    if corenlp_path is None:
        corenlp_path = _find_corenlp_path()
    if corenlp_path is None or not os.path.exists(corenlp_path):
        raise Exception('corenlp_path not found <'+str(corenlp_path)+'>, specify or set the CORENLP environment variable')
    if properties_path is None:
        properties_path = os.path.join(os.path.dirname(__file__), 'corenlp.properties')
    if not os.path.exists(properties_path):
        raise Exception('coreNLP properties path not found <'+str(properties_path)+'>')
    if xml_output_dir is None:
        xml_output_dir = tempfile.mkdtemp()
    if not os.path.exists(xml_output_dir):
        raise Exception('Output Dir not found <'+str(xml_output_dir)+'>')

    args = ['java',
            '-mx'+memory,
            '-cp', corenlp_path+'/*',
            'edu.stanford.nlp.pipeline.StanfordCoreNLP',
            '-file', file,
            '-outputDirectory', xml_output_dir,
            '-outputExtension', '.xml',
            '-outputFormat', 'xml',
            '-props', properties_path]
    if filelist is not None:
        raise Exception('corenlp filelist option  not implemented yet')  # TODO, create, append, delete in finally
    if noClobber:
        args.append('-noClobber')
    if replaceExtension:
        args.append('-replaceExtension')
    if extension:
        args.append('-extension')
        args.append(extension)
    if threads is not None:
        args.extend(['-threads', str(threads)])

    if verbose:
        print('Calling CoreNLP...', args, datetime.datetime.now(), sep='\n')

    try:
        subprocess.check_call(args, stderr=subprocess.STDOUT)  # TODO: stderr=stdout, corenlp verbosity options?
    finally:
        if verbose:
            print('XML output in:', xml_output_dir, datetime.datetime.now(), 'Finished parsing!', sep='\n')

    return xml_output_dir


def consume_xml_dir(xml_output_dir: str, file_list=None, absolute_token_indices=True,
                    count_from_zero=True, dependencies_type="collapsed-ccprocessed-dependencies") -> dict:
    for filename in os.listdir(xml_output_dir):
        if (filename.endswith('.xml') or filename.endswith('.out')) and (file_list is None or filename in file_list):
            xml = get_xml_from_file(os.path.join(xml_output_dir, filename))
            parse = consume_xml(xml, absolute_token_indices, count_from_zero, dependencies_type)
            parse['xml_filename'] = filename
            parse['filename'] = filename[:-len('.xml')] if filename.endswith('.xml') else filename
            yield parse


def get_xml_from_file(xml_filename: str) -> ET.ElementTree:
    try:
        parse = ET.parse(xml_filename)
    except:
        print('Error on ', xml_filename)
        raise
    return parse


def get_xml_from_str(xml_str: str) -> ET.ElementTree:
    parse = ET.fromstring(xml_str)
    return parse


def consume_xml(xml: ET.ElementTree, absolute_token_indices=True,
                count_from_zero=True, dependencies_type="collapsed-ccprocessed-dependencies")->dict:
    root = xml.getroot()
    doc_xml = root.find('document')
    sentences = _extract_sentences(doc_xml, count_from_zero, absolute_token_indices, dependencies_type)
    corefs = _extract_coreferences(doc_xml, sentences)

    parse = {'sentences': sentences, 'corefs': corefs}
    return parse


def _extract_coreferences(doc_xml: ET.ElementTree, sentences: list,) -> [[dict]]:
    """ returns a list of lists of mentions (where mentions are dicts)"""
    corefs = list()
    coref_root_xml = doc_xml.find('coreference')
    if coref_root_xml is None:
        return corefs
    for coref_mentions_xml in coref_root_xml:
        mentions = list()
        for mention_xml in coref_mentions_xml:
            indices = {child.tag: int(child.text) - 1 for child in mention_xml if child.tag != 'text'}
            assert indices['start'] <= indices['head'] < indices['end']
            sentence = sentences[indices['sentence']]
            mention = {'sentence': sentence,
                       'tokens': sentence['tokens'][indices['start']:indices['end']],
                       'head_token': sentence['tokens'][indices['head']],
                       'is_representative': (mention_xml.get('representative') == 'true'),
                       'text': mention_xml.find('text').text}
            mentions.append(mention)
        corefs.append(mentions)
    return corefs


def _extract_sentences(doc_xml: ET.ElementTree, count_from_zero: bool,
                       absolute_indices: bool, dependencies_type: str) -> [dict]:
    sentences = list()
    sentence_first_token_index = 0 if count_from_zero else 1
    sentence_first_parse_node_index = 0 if count_from_zero else 1
    zero_start_correction = -1 if count_from_zero else 0
    if doc_xml.find('sentences') is None:
        return sentences
    for sentence_xml in doc_xml.find('sentences'):
        sentence_index = int(sentence_xml.get('id')) + zero_start_correction
        sentiment = _standardize_sentiment(sentence_xml.get('sentiment'))
        # sentimentValue = sentence_xml.get('sentimentValue') seems to be an enumeration index and tied 1 to 1 with sentiment?
        tokens = _extract_tokens(sentence_xml, sentence_first_token_index, zero_start_correction)
        dependencies = _extract_dependencies(sentence_xml, tokens, dependencies_type)
        parse, parse_str = _extract_parse(sentence_xml, tokens, sentence_first_parse_node_index)
        ners = _merge_ners(tokens)
        sentences.append({'sentence_index': sentence_index,
                          'tokens': tokens,
                          'dependencies': dependencies,
                          'parse': parse,
                          'parse_str': parse_str,
                          'ners': ners,
                          'sentiment': sentiment})
        if absolute_indices:
            sentence_first_token_index += len(tokens)
            sentence_first_parse_node_index = parse['descendant_right_index'] + 1 if parse is not None else 1
    return sentences


def _extract_parse(sentence_xml: ET.ElementTree, tokens: list, first_parse_node_index: int) -> (dict, str):
    parse_stack = [{'children': [], 'node_index':None}]  # dummy entry just to simplify the code a tad
    node_index = first_parse_node_index
    token_index = 0
    parse_xml = sentence_xml.find('parse')
    if parse_xml is None:
        return None, None
    parse_str = parse_xml.text.strip()
    depth = 0
    for parse_token in parse_str.split(' '):
        # Note that this needs to be split on space because occasional other whitespace are used in tokens
        if parse_token[0] == '(':
            parse_node = {'tag': parse_token[1:],
                          'node_index': node_index,
                          'parent_node_index': parse_stack[-1]['node_index'],
                          'descendant_right_index': None,  # enables nested set, ie for a relational DB, updated when traveling back up the stack
                          'depth': depth,
                          'children': [],
                          'token': None}
            parse_stack[-1]['children'].append(parse_node)
            parse_stack.append(parse_node)
            node_index += 1
            depth += 1
        elif parse_token[-1] == ')':
            # token is a leaf node
            parse_stack[-1]['token'] = tokens[token_index]
            token_index += 1

            n_closed = len(parse_token) - len(parse_token.rstrip(')'))
            # n_closed=how far back up the tree we should go. Note that very rare tokens include parens
            for _ in range(n_closed):  # back up the stack setting descendant_right_index as we go
                depth -= 1
                node_index += 1
                parse_stack.pop()['descendant_right_index'] = node_index - 1
        else:
            # I'm not sure if this still occurs?
            # part of token with spaces, i.e. the "4 1/2" in (CD 4 1/2)
            #  ignored because index and order are used to lookup the token
            pass

    assert len(parse_stack) == 1 and len(parse_stack[0]['children']) == 1, 'Should be exactly one root node per sentence parse and should have closed all nodes : ' + parse_str
    root_node = parse_stack[0]['children'][0]
    return root_node, parse_str


def _extract_tokens(sentence_xml: ET.ElementTree, sentence_first_token_index: int,
                    zero_start_correction: int) -> [dict]:
    """token consists of fields:
        'id', 'word', 'lemma', 'POS', 'NER', 'NormalizedNER', 'Speaker', 'CharacterOffsetBegin', 'CharacterOffsetEnd'
    """
    tokens = list()
    tokens_xml = sentence_xml.find('tokens')
    if tokens_xml is None:
        return tokens
    for token_xml in tokens_xml:
        token = dict()
        token['token_index'] = int(token_xml.get('id')) + sentence_first_token_index + zero_start_correction
        for field in token_xml:
            token[field.tag] = field.text

        # make a few fields more friendly:
        token['CharacterOffsetBegin'] = int(token['CharacterOffsetBegin'])
        token['CharacterOffsetEnd'] = int(token['CharacterOffsetEnd'])
        if token.get('NER') == 'O':  # Why even bother giving null entries a tag?
            token['NER'] = None
        if 'lemma' in token:
            token['lemma'] = _LEMMA_BUG_RE.sub(r'\1', token['lemma'])
            # fixes bug where lemmas get the POS tag appended
            # eg "don't usually have ;) )?"   yields <lemma>;-rrb-_NN</lemma>
            token['lemma'] = _unescape_token(token['lemma'])
        if 'word' in token:
            token['word'] = _unescape_token(token['word'])
        if 'sentiment' in token:
            token['sentiment'] = _standardize_sentiment(token['sentiment'])
        tokens.append(token)

    return tokens


def _merge_ners(tokens: list) -> [dict]:
    ners = list()
    curr_ner = None
    for token in tokens:
        token_ner = token.get('NER')
        if curr_ner is not None and curr_ner['type'] != token_ner:
            # old NE ended, gets appended to list, new NE _possibly_ starting
            ners.append(curr_ner)
            curr_ner = None

        if token_ner is not None:  # this token belongs to a NE
            if curr_ner is None:  # NE is new
                curr_ner = {'type': token_ner, 'tokens': []}
            curr_ner['tokens'].append(token)
    if curr_ner is not None:
        ners.append(curr_ner)

    return ners


def _standardize_sentiment(sentiment):
    """Because the token and sentence sentiment values don't match (3.6.0)..."""
    sentiment = sentiment.lower()
    if sentiment == 'verypositive':
        sentiment = 'very positive'
    elif sentiment == 'verynegative':
        sentiment = 'very negative'
    return sentiment


def _unescape_token(word):
    for escaped, replacement in [('-rrb-', ')'), ('-rsb-', ']'), ('-rcb-', '}'),
                                 ('-lrb-', '('), ('-lsb-', '['), ('-lcb-', '{'),
                                 (chr(160), ' ')]:
        word = word.replace(escaped, replacement).replace(escaped.upper(), replacement)
    return word


def _extract_dependencies(sentence_xml: ET.ElementTree, tokens: list, dependencies_type: str) -> [dict]:
    deps = dict()
    for dep_list_xml in sentence_xml.findall('dependencies'):
        if dep_list_xml.get('type') != dependencies_type:
            continue
        for dep_xml in dep_list_xml:
            dep = {'type': dep_xml.get('type')}
            for child in dep_xml:  # i.e. dependent, governor
                token_index = int(child.get('idx')) - 1
                if token_index >= 0:
                    dep[child.tag] = tokens[token_index]
                else:
                    dep[child.tag] = None  # root governor index is -1

            # This prevents duplicates as can sometimes occur in the collapsed dependencies.
            gov_index = dep['governor']['token_index'] if dep['governor'] is not None else None
            key = (dep['type'], dep['dependent']['token_index'], gov_index)
            if key not in deps:
                deps[key] = dep

    return list(deps.values())


def _find_corenlp_path(directory_to_search=None):
    # environment variable
    corenlp_path = os.environ.get('CORENLP')
    if corenlp_path is not None:
        return corenlp_path

    # look in this file's directory, then the current directory
    # choose newest
    # hope filename format never changes...
    import glob
    for directory in [directory_to_search, os.path.dirname(__file__), '.']:
        if directory is None:
            continue
        # don't simplify the following path with wildcard (*) as that will hit zip files
        paths = glob.glob(os.path.join(directory, 'stanford-corenlp-full-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'))
        paths.sort(key=lambda filename: int(filename[-len('2014-01-01'):].replace('-', '')), reverse=True)
        if paths:
            return paths[0]

    # couldn't find any path to coreNLP dir, we tried
    return None


def traverse_parse_tree(parse_node: dict) -> dict:
    # recurrence probably isn't too bad.. I hope
    yield parse_node
    for child in parse_node['children']:
        for yielded in traverse_parse_tree(child):
            yield yielded


def update_indices(parse, character_offset=0, sentence_offset=0, token_offset=0, parse_node_offset=0):
    if character_offset != 0 or sentence_offset != 0 or token_offset != 0 or parse_node_offset != 0:
        for sentence in parse['sentences']:
            sentence['sentence_index'] += sentence_offset
            if character_offset != 0 or token_offset != 0:
                for token in sentence['tokens']:
                    token['CharacterOffsetBegin'] += character_offset
                    token['CharacterOffsetEnd'] += character_offset
                    token['token_index'] += token_offset
            if parse_node_offset != 0:
                for node in traverse_parse_tree(sentence['parse']):
                    node['node_index'] += parse_node_offset
                    node['descendant_right_index'] += parse_node_offset
                    if node['parent_node_index'] is not None:
                        node['parent_node_index'] += parse_node_offset


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("This is intended to be invoked in code, but here's a simple commandline option...", file=sys.stderr)
        print("  corenlp.py /path/to/text(s/) [/path/to/output/ [/path/to/corenlp_dir] ]", file=sys.stderr)
    else:
        input_filename = sys.argv[1]
        input_outputs = sys.argv[2] if len(sys.argv) > 2 else None
        input_corenlp_path = sys.argv[3] if len(sys.argv) > 3 else None
        input_no_clobber = True

        # ****************
        # ****************
        call_corenlp(file=input_filename, xml_output_dir=input_outputs,
                     corenlp_path=input_corenlp_path, noClobber=input_no_clobber)

        for parse_data in consume_xml_dir(xml_output_dir=input_outputs):
            pprint(parse_data['xml_filename'])
            pprint(parse_data)
            print()
            break
        # ****************
        # ****************

        print('Output in <', input_outputs, '>')
