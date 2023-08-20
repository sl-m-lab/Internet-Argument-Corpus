# -*- coding: utf-8 -*-

import re
import string

#import nltk.tokenize

newline_replacements = (re.compile(r'[\x0A\x0C\x0D]'), '\x0A')
punctuation = re.compile('^['+re.escape(string.punctuation)+']+$')

spaces_re = re.compile(r'\s+', re.UNICODE | re.DOTALL)
legal_tokens = [spaces_re, #whitespace
                re.compile(r"[a-zA-Z]+$", re.UNICODE), #words
                re.compile(r"[a-zA-Z]+([´ʼ’ʻ`'\-]\w+)*$", re.UNICODE), #words and word-like things
                re.compile(r"\$?\d+((\.|,)\d+)*$", re.UNICODE), #basic numbers, ipv4 addresses, etc
                re.compile(r'\d{1,2}:\d\d$', re.UNICODE), #time
                re.compile(r'\d{1,2}/\d{1,2}(/\d{2,4})?$', re.UNICODE), #date
                re.compile(r'\d+(\.\d+)?[%°]$', re.UNICODE), #80% or 80°
                re.compile(r'\d+\'s$', re.UNICODE), #80's 
                re.compile(r'\d*(1st|2nd|3rd|[04-9]th)$', re.UNICODE | re.IGNORECASE), #80th, 1st, 81st, etc
                re.compile(r'(#|0x|\\x)?[a-fA-F0-9]+$'), #hex
                re.compile(r'[!?]+$'), #!?!
                re.compile('(['+re.escape(string.punctuation)+'])\\1+$'), #same punctuation character repeated ....... && *******
                re.compile(r'[}>\]<]?[:;=8BxX][\'`]?[oc\-]?[*XxO03DPpb)[\]}|/\\(]$'), #Western emoticons - see: http://en.wikipedia.org/wiki/List_of_emoticons
                re.compile(r'[(=]?[\-~^T0oOxX\'<>.,\'][_\-.][\-~^T0oOxX\'<>.,\'][)=]?$'), #Eastern emoticons
                re.compile(r'<[/\\]?3+$'), #heart <3
                re.compile(r'\(( ?[.oO] ?)(\)\(|Y)\1\)$'), #boobs
                re.compile(r"[a-zA-Z]+\*+[a-zA-Z]*$", re.UNICODE), #w***s
                re.compile(r'[@#$%^&*]+$', re.UNICODE), # @$%# symbols
                re.compile(r'&[a-zA-Z]+;$', re.UNICODE), #html escapes
                re.compile(r'&#\d+;$', re.UNICODE), #html escapes
                re.compile(r'(https?://|www\.).*$', re.UNICODE | re.IGNORECASE), # urls
                re.compile(r'.*\.(edu|com|org|gov)/?$', re.UNICODE | re.IGNORECASE), # more urls and emails
                re.compile(r'([A-Z])\.$', re.UNICODE), # abrevs.
                re.compile(r'(jr|sr|vs|mr|mrs|ms|prof|dr|st|co|ltd|ph\.d|[a-z]\.[a-z]|etc)\.$', re.UNICODE | re.IGNORECASE), # more abrevs. 
                re.compile(r'\x00+$', re.UNICODE) # null characters
                ]
def tokenize(text, break_into_sentences = False, leave_whitespace=False):
    """This tokenizer is not as efficient as most, but it does a pretty good job
    given english text, returns a list of tokens or a  list of lists of tokens if told to break_into_sentences
    
    """
    token_spans = list()
    previous_end = 0
    for iter in spaces_re.finditer(text):
        if iter.start()!=0:
            token_spans.append((previous_end, iter.start()))
        token_spans.append((iter.start(),iter.end()))
        previous_end = iter.end()
    if previous_end != len(text):
        token_spans.append((previous_end, len(text)))
    
    tokens = [text[start:end] for (start,end) in token_spans]
    tokens = reduce(lambda x, y: x+y, map(tokenize_word, tokens), [])
    if break_into_sentences:
        tokens = tokens_to_sentences(tokens)
    if not leave_whitespace:
        tokens = remove_whitespace_tokens(tokens, break_into_sentences)
    return tokens

def tokenize_word(word):
    """greedily splits into largest possible tokens"""
    if is_legal_token(word):
        return [word]
    tokens = list()
    for i in range(len(word),0,-1):
        if is_legal_token(word[:i]):
            tokens.append(word[:i])
            tokens.extend(tokenize_word(word[i:]))
            break
        if is_legal_token(word[len(word)-i:]):
            tokens.extend(tokenize_word(word[:len(word)-i]))
            tokens.append(word[len(word)-i:])
            break
    return tokens
        
def is_legal_token(token):
    if len(token) == 1:
        return True
    for regex in legal_tokens:
        if regex.match(token):
            return True
    return False
    
#def sentences(text):
#    return nltk.tokenize.sent_tokenize(text) #if trained nltk's is actually pretty good, albeit unpredictable

def tokens_to_sentences(tokens):
#TODO - once people upgrade nltk, use nltk's span option for sent tokenizing...
    sentences = list()
    sentence_buffer = list()
    for token in tokens:
        if len(token) == 0 or '\n' in token or token[-1] in ['.','?',':','!',';'] or '\0' in token:
            sentence_buffer.append(token)
            sentences.append(sentence_buffer)
            sentence_buffer = list()
        else:
            sentence_buffer.append(token)
    if len(sentence_buffer) > 0:
        sentences.append(sentence_buffer)
    return sentences

def remove_whitespace_tokens(tokens, sentences = False):
    """@note: catches all that start with whitespace"""
    if sentences:
        for i in range(len(tokens)):
            tokens[i] = remove_whitespace_tokens(tokens[i]) # tokens[i] is a sentence
        return tokens

    return [token for token in tokens if not spaces_re.match(token)]

def is_text_initial(term, text, start_within=5, ignore_case=True):
    """one or both of text and term can also be lists of tokens, this speeds things up immensely"""
    if type(term) != type(list()):
        if ignore_case: term = term.lower()
        term_tokens = tokenize(term)
    else:
        term_tokens = [token.lower() for token in term] if ignore_case else term
    if type(text) != type(list()):
        if ignore_case: text = text.lower()
        text_tokens = tokenize(text)
    else:
        text_tokens = [token.lower() for token in text] if ignore_case else text
    spacey_text = ' '+(' '.join(text_tokens[:start_within-1+len(term_tokens)]))+' '
    spacey_term = ' '+(' '.join(term_tokens))+' '
    return spacey_term in spacey_text
