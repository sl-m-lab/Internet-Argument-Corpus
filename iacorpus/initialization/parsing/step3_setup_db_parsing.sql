#Add parsing tables to the DB
# copy over any tables which should use the same IDs from other databases


#drop table corenlp_coref, corenlp_named_entity, corenlp_named_entity_tag, dependency, token, corenlp_parse, parse_tag, sentence, word, pos_tag, dependency_relation;

#Stanford deps. see/derived from: http://nlp.stanford.edu/software/dependencies_manual.pdf
create table dependency_relation(
    `dependency_relation_id` smallint unsigned primary key,
    `parent_dependency_relation_id` smallint unsigned null, # e.g. dep -> arg -> subj -> nsubj
    `dependency_relation` tinytext not null,
    `dependency_relation_long` tinytext not null
) row_format=Compressed KEY_BLOCK_SIZE=4;




create table pos_tag(
    `pos_tag_id` tinyint unsigned primary key,
    `pos_tag` tinytext not null,
    `pos_tag_description` tinytext not null #e.g. Proper Noun
) row_format=Compressed KEY_BLOCK_SIZE=4;



#called word for simplicity, alternative would be vocabulary or lexicon
# separated from token mainly to remove the variable length field
create table word(
    `word_id` mediumint unsigned primary key auto_increment,  # adjust size as needed
    `word` text not null # could probably get away with something smaller..
) row_format=Compressed KEY_BLOCK_SIZE=4;


create table sentence(
    `text_id` mediumint unsigned,
    `sentence_index` smallint unsigned, # increase size as needed
    `sentence_start` mediumint unsigned not null,
    `sentence_end` mediumint unsigned not null,
    `sentence_sentiment` enum(
      'very negative',
      'negative',
      'neutral',
      'positive',
      'very positive') not null,
    primary key (text_id, sentence_index),
    foreign key (text_id) references text(text_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;




create table parse_tag(
    `parse_tag_id` tinyint unsigned primary key,
    `parse_tag` tinytext not null,
    `parse_tag_description` tinytext null, #e.g. Proper Noun
    `parse_tag_level` tinytext null
) row_format=Compressed KEY_BLOCK_SIZE=4;

# Note that this is a nested set datastructure, check wikipedia if you have not seen it
create table corenlp_parse(
    `text_id` mediumint unsigned,
    `parse_node_index` mediumint unsigned,
    `sentence_index` smallint unsigned not null, # Note that sentence_index is not in the primary key - this makes things easier
    #`parent_parse_node_index` mediumint unsigned null,
    `descendant_right_index` mediumint unsigned not null,
    `depth` smallint unsigned not null,
    `parse_tag_id` tinyint unsigned not null,
    primary key (text_id, parse_node_index),
    foreign key (text_id) references text(text_id),
    foreign key (text_id, sentence_index) references sentence(text_id, sentence_index),
    foreign key (parse_tag_id) references parse_tag(parse_tag_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table token(
    `text_id` mediumint unsigned,
    `token_index` smallint unsigned, # increase size as needed
    `sentence_index` smallint unsigned not null, #note that sentence_index is not part of the primary key
    `token_start` mediumint unsigned not null,
    `token_end` mediumint unsigned not null,
    `pos_tag_id` tinyint unsigned not null,
    `word_id` mediumint unsigned not null,
    `lemma_word_id` mediumint unsigned not null,
    `parse_node_index` mediumint unsigned not null,
    `token_sentiment` enum(
      'very negative',
      'negative',
      'neutral',
      'positive',
      'very positive') not null,
    primary key (text_id, token_index),
    foreign key (text_id) references text(text_id),
    foreign key (word_id) references word(word_id),
    foreign key (lemma_word_id) references word(word_id),
    foreign key (pos_tag_id) references pos_tag(pos_tag_id),
    foreign key (text_id, parse_node_index) references corenlp_parse(text_id, parse_node_index)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table dependency(
    `text_id` mediumint unsigned,
    `dependency_id` smallint unsigned,
    `sentence_index` smallint unsigned not null,
    `dependency_relation_id` smallint unsigned not null,
    `governor_token_index` smallint unsigned not null, # ROOT gov=dep
    `dependent_token_index` smallint unsigned not null,
    primary key (text_id, dependency_id),
    foreign key (text_id) references text(text_id),
    foreign key (dependency_relation_id) references dependency_relation(dependency_relation_id),
    foreign key (text_id, governor_token_index) references token(text_id, token_index),
    foreign key (text_id, dependent_token_index) references token(text_id, token_index)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table corenlp_named_entity_tag(
    `ner_tag_id` tinyint unsigned primary key,
    `ner_tag` tinytext not null, # e.g. person, location
    `ner_tag_description` tinytext null
) row_format=Compressed KEY_BLOCK_SIZE=4;


create table corenlp_named_entity(
    `text_id` mediumint unsigned,
    `ner_index` smallint unsigned,
    `token_index_first` smallint unsigned not null,
    `token_index_last` smallint unsigned not null,  # inclusive. i.e. this is the last token in this NE, in the case of one token NE, this is equal to token_index_first
    `ner_tag_id` tinyint unsigned not null, # no good reason for separating out to a reference table. Data integrity is nice, enums are awkward, fixed width is nice
    primary key (text_id, ner_index),
    foreign key (ner_tag_id) references corenlp_named_entity_tag(ner_tag_id),
    foreign key (text_id) references text(text_id),
    foreign key (text_id, token_index_first) references token(text_id, token_index),
    foreign key (text_id, token_index_last) references token(text_id, token_index)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table corenlp_coref(
    `text_id` mediumint unsigned,
    `coref_id` smallint unsigned,
    `coref_chain_id` smallint unsigned, # group by this!
    `token_index_first` smallint unsigned not null,
    `token_index_last` smallint unsigned not null,  # inclusive. i.e. this is the last token in this coref
    `token_index_head` smallint unsigned not null,
    `is_representative` boolean not null,
    primary key (text_id, coref_id),
    foreign key (text_id) references text(text_id),
    foreign key (text_id, token_index_first) references token(text_id, token_index),
    foreign key (text_id, token_index_last) references token(text_id, token_index),
    foreign key (text_id, token_index_head) references token(text_id, token_index)
) row_format=Compressed KEY_BLOCK_SIZE=4;




#views
create view token_view as
select
 token.*,
 word.word as word,
 lemma.word as lemma,
 pos_tag
from token
 join pos_tag using(pos_tag_id)
 join word using(word_id)
 join word as lemma on token.lemma_word_id=lemma.word_id;


create view dependency_view as
select
 dependency.*,
 dependency_relation,
 gov_token.word_id as governor_word_id,
 gov_token.word as governor_word,
 gov_token.lemma_word_id as governor_lemma_word_id,
 gov_token.lemma as governor_lemma,
 gov_token.pos_tag as governor_pos_tag,
 dep_token.word_id as dependent_word_id,
 dep_token.word as dependent_word,
 dep_token.lemma_word_id as dependent_lemma_word_id,
 dep_token.lemma as dependent_lemma,
 dep_token.pos_tag as dependent_pos_tag
from dependency
 join dependency_relation
   on dependency.dependency_relation_id = dependency_relation.dependency_relation_id
 join token_view as gov_token
   on (dependency.text_id=gov_token.text_id
       and dependency.governor_token_index=gov_token.token_index)
 join token_view as dep_token
   on (dependency.text_id=dep_token.text_id
       and dependency.dependent_token_index=dep_token.token_index);
