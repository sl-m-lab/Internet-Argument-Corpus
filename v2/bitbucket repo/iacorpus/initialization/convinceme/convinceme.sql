#drop database convinceme;

SET GLOBAL innodb_file_format=Barracuda;
CREATE SCHEMA convinceme DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;

use convinceme;

create table dataset_metadata(
  `row_id` mediumint unsigned not null auto_increment primary key,
  `metadata_field` text not null,
  `metadata_value` mediumtext null
) row_format=Compressed KEY_BLOCK_SIZE=4;
insert into dataset_metadata (metadata_field, metadata_value) values
  ('title', 'Internet Argument Corpus: ConvinceMe'),
  ('full official name', 'Internet Argument Corpus: ConvinceMe'),
  ('simple name', 'convinceme'),
  ('author', 'Rob Abbott, Brian Ecker, Pranav Anand, Marilyn A. Walker'),
  ('contact', 'Rob Abbott <abbott@soe.ucsc.edu>'),
  ('cite', 'Abbott, R., Ecker, B., Anand, P., Walker, M. A.(2016). Internet Argument Corpus 2.0: An SQL schema for Dialogic Social Media and the Corpora to go with it. In LREC'),
  ('url', 'https://nlds.soe.ucsc.edu/iac2'),
  ('version', '2.0'),
  ('original publication date', '2016-05-25'),
  ('current version date', '2016-05-25'),
  ('language tag', 'eng'),
  ('license', null),
  ('synopsis', 'The ConvinceMe dataset consists of discussions from a debate oriented website. Discussions are two sided debates with posters declaring their side at time of posting. All replies are intended to be rebuttals. There are roughly 65,000 posts in 5400 discussions by 5500 authors.'),
  ('description', null),
  ('notes', 'Not all posts have identifiable parents, in these instances <post.parent_missing=true> (also <post.parent_post_id=null> but this occurs with top-level posts as well). Because replies are required to be on the side opposite their parent post, people who wish to reply to posts on their own side may sometimes post replies on the side they don\'t support.'),
  ('changelog', null),
  ('schema format', 'iac-2.0'),
  ('dependencies', null),
  ('source url', 'http://www.convinceme.net'),
  ('tools used', 'CoreNLP-3.6.0')
  ;

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

create table discussion_stance(
  `discussion_id` mediumint unsigned,
  `discussion_stance_id` tinyint unsigned,  # probably 0,1  but could go higher if there are many possible stances
  `discussion_stance` tinytext not null,
  `topic_id` mediumint unsigned null, #corresponding topic, hopefully matches the discussion topic...
  `topic_stance_id` tinyint unsigned null, #corresponding (more general) topic_stance
  primary key (discussion_id, discussion_stance_id),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (topic_id, topic_stance_id) references topic_stance(topic_id, topic_stance_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table post(
  `discussion_id` mediumint unsigned,
  `post_id` mediumint unsigned,
  `author_id` mediumint unsigned not null,
  `creation_date` datetime not null, #using datetime mostly to force no local timezone adjustments
  `parent_post_id` mediumint unsigned null,
  `parent_missing` boolean not null, #typically parent post was deleted or ambiguous.
  `text_id` mediumint unsigned not null,
  `points` mediumint signed not null,
  `discussion_stance_id` tinyint unsigned null,
  `is_rebuttal` boolean not null,
  primary key (discussion_id, post_id),
  foreign key (text_id) references text(text_id),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (author_id) references author(author_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;




create view post_view as
select
 post.*,
 text,
 username,
 discussion.title as discussion_title,
 discussion_stance,
 topic,
 stance
from post
  join text using(text_id)
  join author using(author_id)
  join discussion using(discussion_id)
  left join discussion_topic using(discussion_id)
  left join topic on (topic.topic_id=discussion_topic.topic_id)
  left join discussion_stance using(discussion_id, discussion_stance_id)
  left join topic_stance
    on (discussion_stance.topic_id=topic_stance.topic_id
        and discussion_stance.topic_stance_id=topic_stance.topic_stance_id);
