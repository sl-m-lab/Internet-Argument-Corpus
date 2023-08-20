#drop database convote;

SET GLOBAL innodb_file_format=Barracuda;
CREATE SCHEMA convote DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;

use convote;

create table dataset_metadata(
  `row_id` mediumint unsigned not null auto_increment primary key,
  `metadata_field` text not null,
  `metadata_value` mediumtext null
) row_format=Compressed KEY_BLOCK_SIZE=4;
insert into dataset_metadata (metadata_field, metadata_value) values
  ('title', 'ConVote'),
  ('full official name', 'ConVote'),
  ('simple name', 'convote'),
  ('author', 'Matt Thomas, Bo Pang, and Lillian Lee'),
  ('contact', null),
  ('cite', 'Matt Thomas, Bo Pang, and Lillian Lee, "Get out the vote: Determining support or opposition from Congressional floor-debate transcripts", Proceedings of EMNLP (2006).'),
  ('url', 'http://www.cs.cornell.edu/home/llee/data/convote.html'),
  ('version', '1.1'),
  ('original publication date', '2006'),
  ('current version date', '2008'),
  ('language tag', 'eng'),
  ('license', null),
  ('synopsis', ''),
  ('description', null),
  ('notes', ''),
  ('changelog', null),
  ('schema format', 'iac-2.0'),
  ('dependencies', null),
  ('source url', 'https://www.govtrack.us/'),
  ('tools used', null)
  ;

create table author(
  `author_id` mediumint unsigned,
  `username` text not null,
  `full_name` text null,
  `party` enum('D','R','I','X'), # X is unknown
  primary key (author_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table text(
  `text_id` mediumint unsigned,
  `text` longtext not null, #Would be fine with mediumtext
  primary key (text_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table discussion(
  `discussion_id` mediumint unsigned, #avoiding autoincrement on purpose
  `url` text null, #URLs can be longer, if ever an issue should fix
  `title` text null,
  `set_name` enum('training', 'test', 'development'),
  primary key (discussion_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table post(
  `discussion_id` mediumint unsigned,
  `post_id` mediumint unsigned,
  `author_id` mediumint unsigned not null,
  `creation_date` datetime null, #using datetime mostly to force no local timezone adjustments
  `parent_post_id` mediumint unsigned null,
  `parent_missing` boolean not null, #typically parent post was deleted or ambiguous.
  `text_id` mediumint unsigned not null,
  `stage_two` boolean not null,
  `stage_three` boolean not null,
  `yield_start` int unsigned null,
  `bill_mentioned` boolean not null,
  `filename` char(26) not null,
  `source_page` smallint unsigned not null,
  `source_index` smallint unsigned not null,
  `raw_score` float null, # derived from edges_individual_document
  `normalized_score` float null,
  `link_strength` smallint unsigned null,
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
 discussion.title as discussion_title
from post
  join text using(text_id)
  join author using(author_id)
  join discussion using(discussion_id);



create table convote_mention(
  `discussion_id` mediumint unsigned not null,
  `post_id` mediumint unsigned not null,
  `text_id` mediumint unsigned not null,
  `text_index` int unsigned not null,
  `mention_author_id` mediumint unsigned not null,
  `useless_digit` tinyint unsigned not null,
  `mention_name` char(26) not null,
  `raw_score` float null, # derived from edges_reference_set_*
  `normalized_score` float null,
  `link_strength` smallint unsigned null,
  `high_precision_normalized_score` float null,
  `high_precision_link_strength` smallint unsigned null,
  primary key (discussion_id, post_id, text_index),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (discussion_id, post_id) references post(discussion_id, post_id),
  foreign key (mention_author_id) references author(author_id)
);
create table convote_concatenated_edge(
  `discussion_id` mediumint unsigned not null,
  `author_id` mediumint unsigned not null,
  `raw_score` float null, # derived from edges_concatenated_document
  `normalized_score` float null,
  `link_strength` smallint unsigned null,
  primary key (discussion_id, author_id),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (author_id) references author(author_id)
);
create table convote_vote(
  `discussion_id` mediumint unsigned not null,
  `author_id` mediumint unsigned not null,
  `vote` boolean not null, # True is for, False against
  primary key (discussion_id, author_id),
  foreign key (discussion_id) references discussion(discussion_id),
  foreign key (author_id) references author(author_id)
);
