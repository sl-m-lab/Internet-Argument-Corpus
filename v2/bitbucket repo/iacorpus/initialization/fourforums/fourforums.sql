#drop database fourforums;

SET GLOBAL innodb_file_format=Barracuda;
CREATE SCHEMA fourforums DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;

use fourforums;

create table dataset_metadata(
  `row_id` mediumint unsigned not null auto_increment primary key,
  `metadata_field` text not null,
  `metadata_value` mediumtext null
) row_format=Compressed KEY_BLOCK_SIZE=4;
insert into dataset_metadata (metadata_field, metadata_value) values
  ('title', 'Internet Argument Corpus: 4forums'),
  ('full official name', 'Internet Argument Corpus: 4forums'),
  ('simple name', 'fourforums'),
  ('author', 'Rob Abbott, Brian Ecker, Pranav Anand, Marilyn A. Walker, Jean E. Fox Tree, Joseph King'),
  ('contact', 'Rob Abbott <abbott@soe.ucsc.edu>'),
  ('cite', '["Abbott, R., Ecker, B., Anand, P., Walker, M. A.(2016). Internet Argument Corpus 2.0: An SQL schema for Dialogic Social Media and the Corpora to go with it. In LREC", "Walker, M. A., Tree, J. E. F., Anand, P., Abbott, R., & King, J. (2012). A Corpus for Research on Deliberation and Debate. In LREC"]'),
  ('url', 'https://nlds.soe.ucsc.edu/iac2'),
  ('version', '2.0'),
  ('original publication date', '2012-05-23'),
  ('current version date', '2016-05-25'),
  ('language tag', 'eng'),
  ('license', null),
  ('synopsis', 'The 4forums dataset consists of discussions from a debate oriented website.'),
  ('description', null),
  ('notes', 'Not all debates are two sided and not all two sided debates feature sides (either or both) that correspond to opposing topic stances.'),
  ('changelog', null),
  ('schema format', 'iac-2.0'),
  ('dependencies', null),
  ('source url', 'http://www.4forums.com/political/'),
  ('tools used', 'CoreNLP-3.6.0')
  ;


#SET foreign_key_checks = 1;
#drop table author, text, discussion, topic, topic_stance, discussion_stance, post, markup, quote;

create table author(
  `author_id` mediumint unsigned,
  `username` text not null,
  primary key (author_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table text(
  `text_id` mediumint unsigned,
  `text` longtext not null, #Would be fine with mediumtext
  primary key (text_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table discussion(
  `discussion_id` mediumint unsigned, #avoiding autoincrement on purpose
  `url` text not null, #URLs can be longer, if ever an issue should fix
  `title` text not null,
  `initiating_author_id` mediumint unsigned null,
  primary key (discussion_id),
  foreign key (initiating_author_id) references author(author_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table topic(
  `topic_id` mediumint unsigned primary key,
  `topic` tinytext not null
) row_format=Compressed KEY_BLOCK_SIZE=4;
create table discussion_topic(
  `discussion_id` mediumint unsigned,
  `topic_id` mediumint unsigned not null,
  primary key (discussion_id),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (topic_id) references topic(topic_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table topic_stance(
  `topic_id` mediumint unsigned,
  `topic_stance_id` tinyint unsigned,
  `stance` tinytext not null,
  primary key (topic_id, topic_stance_id),
  foreign key (topic_id) references topic(topic_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;
create table post(
  `discussion_id` mediumint unsigned,
  `post_id` mediumint unsigned,
  `author_id` mediumint unsigned not null,
  `creation_date` datetime not null, #using datetime mostly to force no local timezone adjustments
  `parent_post_id` mediumint unsigned null,
  `parent_missing` boolean not null, #typically parent post was deleted or ambiguous.
  `text_id` mediumint unsigned not null,
  primary key (discussion_id, post_id),
  foreign key (text_id) references text(text_id),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (author_id) references author(author_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;


create table markup(
  `text_id` mediumint unsigned,
  `markup_id` mediumint unsigned,
  `markup_start` mediumint unsigned not null,
  `markup_end` mediumint unsigned not null,
  `type` tinytext not null, #bold, italic, link, etc.
  `attributes` text null, #html markup stored as a json encoded dict. red, 12pt, url, etc. Unfortunately urls can be long...
  primary key (text_id, markup_id), # TODO: GET SQLAlchemy ORM to not require a primary key, or just let it be
  foreign key (text_id) references text(text_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table quote(
  `discussion_id` mediumint unsigned,
  `post_id` mediumint unsigned, #the containing post
  `quote_index` smallint unsigned,  #Should be the correct order, but use text_index for order
  `parent_quote_index` smallint unsigned null, #for nested quotes, otherwise null
  `text_offset` mediumint unsigned not null, #the quote directly _precedes_ this character (index) in the quoting post/quote, frequently 0
  `text_id` mediumint unsigned not null, #The quote`s text
  `source_discussion_id` mediumint unsigned null, #Likely same as discussion_id, sometimes different, sometimes unknown (null)
  `source_post_id` mediumint unsigned null, #doubles as source_found...

  #The following source_* fields are only valid if source_post_id is not null!!
  #see source_quotes.py

    #If came from a prior post, where in the prior post did it start?
    #null if unknown, 0 if the start
    #note that the quotes text may not precisely match the sources text - see source_altered column
  `source_start` mediumint unsigned null,
  `source_end` mediumint unsigned null, #and end? null if unknown, length(post.text) if the end

  `truncated` boolean null, #if the source is truncated, null if no source identified
  `altered` boolean null, #Could you go to the source and get the same text using start/end?, null if no source identified
  primary key (discussion_id, post_id, quote_index),
  foreign key (discussion_id, post_id) references post(discussion_id, post_id),
  foreign key (text_id) references text(text_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;




create view post_view as
select
 post.*,
 text,
 username,
 discussion.title as discussion_title,
 topic
from post
  join text using(text_id)
  join author using(author_id)
  join discussion using(discussion_id)
  left join discussion_topic using(discussion_id)
  left join topic on (topic.topic_id=discussion_topic.topic_id);
