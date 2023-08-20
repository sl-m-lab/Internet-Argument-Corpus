CREATE SCHEMA createdebate_released DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;

use createdebate_released;

# do standard create table statements first


insert into word select * from createdebate.word;
insert into dependency_relation select * from createdebate.dependency_relation;
insert into pos_tag select * from createdebate.pos_tag;
insert into parse_tag select * from createdebate.parse_tag;
insert into corenlp_named_entity_tag select * from createdebate.corenlp_named_entity_tag;
insert into topic select * from createdebate.topic;
insert into topic_stance select * from createdebate.topic_stance;

insert into author select createdebate.author.*
from createdebate.author natural join(
  (select initiating_author_id as author_id
  from createdebate.discussion_released
  natural join createdebate.discussion
  union
  select author_id
  from createdebate.discussion_released
  natural join createdebate.post
  )
  ) as used_author order by author_id;

insert into text select createdebate.text.*
from createdebate.text natural join(
  (select description_text_id as text_id
  from createdebate.discussion_released
  natural join createdebate.discussion
  union
  select text_id
  from createdebate.discussion_released
  natural join createdebate.post
  union
  select text_id
  from createdebate.discussion_released
  natural join createdebate.quote
  )
  ) as used_text order by text_id;

insert into discussion select createdebate.discussion.*
from createdebate.discussion_released
natural join createdebate.discussion order by discussion_id;

insert into discussion_topic select createdebate.discussion_topic.*
from createdebate.discussion_released
natural join createdebate.discussion_topic order by discussion_id;

insert into discussion_stance select createdebate.discussion_stance.*
from createdebate.discussion_released
natural join createdebate.discussion_stance order by discussion_id, discussion_stance_id;

insert into post select createdebate.post.*
from createdebate.discussion_released
natural join createdebate.post order by discussion_id, post_id;

insert into quote select createdebate.quote.*
from createdebate.discussion_released
natural join createdebate.quote order by discussion_id, post_id, quote_index;

insert into markup select createdebate.markup.*
from createdebate_released.text
natural join createdebate.markup order by text_id, markup_id;

insert into sentence select createdebate.sentence.*
from createdebate_released.text
natural join createdebate.sentence order by text_id, sentence_index;

insert into corenlp_parse select createdebate.corenlp_parse.*
from createdebate_released.text
natural join createdebate.corenlp_parse order by text_id, parse_node_index;

insert into token select createdebate.token.*
from createdebate_released.text
natural join createdebate.token order by text_id, token_index;

insert into dependency select createdebate.dependency.*
from createdebate_released.text
natural join createdebate.dependency order by text_id, dependency_id;

insert into corenlp_named_entity select createdebate.corenlp_named_entity.*
from createdebate_released.text
natural join createdebate.corenlp_named_entity order by text_id, ner_index;

insert into corenlp_coref select createdebate.corenlp_coref.*
from createdebate_released.text
natural join createdebate.corenlp_coref order by text_id, coref_id;


