use fourforums;

drop tables 
  mturk_2010_dialogue_relation_question,
  mturk_2010_qr_task1_worker_response,
  mturk_2010_qr_task2_worker_response,
  mturk_2010_qr_task1_average_response,
  mturk_2010_qr_task2_average_response,
  mturk_2010_p123_worker_response,
  mturk_2010_p123_average_response,
  mturk_2010_qr_entry,
  mturk_2010_p123_entry,
  mturk_2010_p123_post;
drop table mturk_author_stance;

create table mturk_2010_dialogue_relation_question(
    `question_id` tinyint unsigned primary key,
    `title` tinytext not null,
    `task_id` tinyint not null,#1,2
    `is_scalar` boolean not null, #if so on [-5,5] otherwise binary
    `has_unsure` boolean not null, #if unsure option presented
    `question` tinytext not null,
    `low_value_label` tinytext not null,
    `high_value_label` tinytext not null
) row_format=Compressed KEY_BLOCK_SIZE=4;
insert into mturk_2010_dialogue_relation_question
  (question_id, title, task_id, is_scalar, has_unsure, question, low_value_label, high_value_label)
  values 
    (1, 'disagree_agree', 1, True, True, "Does the respondent agree or disagree with the prior post?", 'disagree', 'agree'),
    (2, 'emotion_fact', 1, True, True, "Is the respondent attempting to make a fact based argument or appealing to feelings and emotions?", 'feelings', 'fact'),
    (3, 'attacking_respectful', 1, True, True, "Is the respondent being supportive/respectful or are they attacking/insulting in their writing?", 'attacking/insulting', 'supportive/respectful'),
    (4, 'sarcasm', 1, False, True, "Is the respondent using sarcasm?", 'Yes', 'No'),
    (5, 'nasty_nice', 1, True, True, "Is the respondent attempting to be nice or is their attitude fairly nasty?", 'nasty', 'nice'),
    (6, 'agree', 2, False, False, "Does the respondent agree or disagree with the previous post?", 'Agree', 'Disagree'),
    (7, 'negotiate_attack', 2, True, True, "Does the respondent seem to have an argument of their own OR is the respondent simply attacking the original poster's argument?", 'Own Argument', 'Attack Only'),
    (8, 'defeater_undercutter', 2, True, True, "Is the argument of the respondent targeted at the entirety of the original poster's argument OR is the argument of the respondent targeted at a more specific idea within the post?", 'Whole Post', 'Specific Idea'),
    (9, 'questioning_asserting', 2, True, True, "Is the respondent questioning the original poster OR is the respondent asserting their own ideas?", 'Questioning', 'Asserting'),
    (10, 'personal_audience', 2, True, True, "Is the respondent's arguments intended more to be interacting directly with the original poster OR with a wider audience?", 'Personal', 'Audience');




create table mturk_2010_qr_entry(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `discussion_id` mediumint unsigned null,
    `post_id` mediumint unsigned null,
    `quote_index` smallint unsigned null,
    `response_text_end` mediumint unsigned null, #for convenience only, response start and quote start/end should be derived directly from the quote table
    `presented_quote` text not null, #exactly as presented, there may be inferior parsing vs the current text
    `presented_response` text not null,
    `term` tinytext,
    `topic` tinytext not null,
    primary key (page_id, tab_number),
    foreign key (discussion_id, post_id) references post(discussion_id, post_id),
    foreign key (discussion_id, post_id, quote_index) references quote(discussion_id, post_id, quote_index)
) row_format=Compressed KEY_BLOCK_SIZE=4;
create table mturk_2010_qr_task1_worker_response(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `workerid` char(64) BINARY,
    `response_number` tinyint unsigned, #Usually 0... but some data was reuploaded at higher $ with poor care and so some workers did the same task multiple times...
    `disagree_agree` tinyint not null,
    `disagree_agree_unsure` boolean not null,
    `attacking_respectful` tinyint not null,
    `attacking_respectful_unsure` boolean not null,
    `emotion_fact` tinyint not null,
    `emotion_fact_unsure` boolean not null,
    `nasty_nice` tinyint not null,
    `nasty_nice_unsure` boolean not null,
    `sarcasm` enum('Yes', 'No', 'Unsure') not null,
    primary key (page_id, tab_number, workerid, response_number),
    foreign key (page_id, tab_number) references mturk_2010_qr_entry(page_id, tab_number)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table mturk_2010_qr_task2_worker_response(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `workerid` char(64) BINARY,
    `response_number` tinyint unsigned, #Usually 0... but some data was reuploaded at higher $ with poor care and so some workers did the same task multiple times...
    `agree` boolean not null,
    `defeater_undercutter` tinyint null,
    `defeater_undercutter_unsure` boolean null,
    `negotiate_attack` tinyint null,
    `negotiate_attack_unsure` boolean null,
    `personal_audience` tinyint null,
    `personal_audience_unsure` boolean null,
    `questioning_asserting` tinyint null,
    `questioning_asserting_unsure` boolean null,
    primary key (page_id, tab_number, workerid, response_number),
    foreign key (page_id, tab_number) references mturk_2010_qr_entry(page_id, tab_number)
) row_format=Compressed KEY_BLOCK_SIZE=4;



create table mturk_2010_qr_task1_average_response(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `num_annots` tinyint unsigned not null,
    `disagree_agree` float not null,
    `disagree_agree_unsure` float not null,
    `attacking_respectful` float not null,
    `attacking_respectful_unsure` float not null,
    `emotion_fact` float not null,
    `emotion_fact_unsure` float not null,
    `nasty_nice` float not null,
    `nasty_nice_unsure` float not null,
    `sarcasm_yes` float not null, #percent of annotators who say it is sarcastic
    `sarcasm_no` float not null,
    `sarcasm_unsure` float not null,
    primary key (page_id, tab_number),
    foreign key (page_id, tab_number) references mturk_2010_qr_entry(page_id, tab_number)
) row_format=Compressed KEY_BLOCK_SIZE=4;

create table mturk_2010_qr_task2_average_response(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `num_disagree` tinyint unsigned not null,
    `num_annots` tinyint unsigned not null, # note that num_disagree is more important for this task!
    `agree` float not null, #percent 'Agree'
# of those who disagree...
    `defeater_undercutter` float null, # of those who disagree, mean defeater_undercutter
    `defeater_undercutter_unsure` float null,
    `negotiate_attack` float null,
    `negotiate_attack_unsure` float null,
    `personal_audience` float null,
    `personal_audience_unsure` float null,
    `questioning_asserting` float null,
    `questioning_asserting_unsure` float null,
    primary key (page_id, tab_number),
    foreign key (page_id, tab_number) references mturk_2010_qr_entry(page_id, tab_number)
) row_format=Compressed KEY_BLOCK_SIZE=4;








#p123 data consists of 2 tables, the first references a single post, the second references a pair of entries in the former
create table mturk_2010_p123_post(
    `p123_triple_id` smallint unsigned,
    `triple_index` tinyint unsigned, #0, 1, 2
    `discussion_id` mediumint unsigned null,
    `post_id` mediumint unsigned null,
    `presented_text` text,
    `presented_text_term_removed` text null,
    `term` tinytext null,
    `topic` tinytext not null,
    primary key (p123_triple_id, triple_index),
    foreign key (discussion_id, post_id) references post(discussion_id, post_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;
create table mturk_2010_p123_entry(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `p123_triple_id` smallint unsigned not null,
    `context_triple_index` tinyint unsigned not null, #0,1
    `response_triple_index` tinyint unsigned not null, #1,2
    primary key (page_id, tab_number),
    foreign key (p123_triple_id, context_triple_index) references mturk_2010_p123_post(p123_triple_id, triple_index),
    foreign key (p123_triple_id, response_triple_index) references mturk_2010_p123_post(p123_triple_id, triple_index)
) row_format=Compressed KEY_BLOCK_SIZE=4;



create table mturk_2010_p123_worker_response(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `workerid` char(64) BINARY not null,
    `response_number` tinyint unsigned not null, #Usually 0... but some data was reuploaded at higher $ with poor care and so some workers did the same task multiple times...
    `disagree_agree` tinyint not null,
    `disagree_agree_unsure` boolean not null,
    `attacking_respectful` tinyint not null,
    `attacking_respectful_unsure` boolean not null,
    `emotion_fact` tinyint not null,
    `emotion_fact_unsure` boolean not null,
    `nasty_nice` tinyint not null,
    `nasty_nice_unsure` boolean not null,
    `sarcasm` enum('Yes', 'No', 'Unsure') not null,
    primary key (page_id, tab_number, workerid, response_number),
    foreign key (page_id, tab_number) references mturk_2010_p123_entry(page_id, tab_number)
) row_format=Compressed KEY_BLOCK_SIZE=4;



create table mturk_2010_p123_average_response(
    `page_id` smallint unsigned,
    `tab_number` tinyint unsigned, #0-6
    `num_annots` tinyint unsigned not null,
    `disagree_agree` float not null,
    `disagree_agree_unsure` float not null,
    `attacking_respectful` float not null,
    `attacking_respectful_unsure` float not null,
    `emotion_fact` float not null,
    `emotion_fact_unsure` float not null,
    `nasty_nice` float not null,
    `nasty_nice_unsure` float not null,
    `sarcasm_yes` float not null, #percent of annotators who say it is sarcastic
    `sarcasm_no` float not null,
    `sarcasm_unsure` float not null,
    primary key (page_id, tab_number),
    foreign key (page_id, tab_number) references mturk_2010_p123_entry(page_id, tab_number)
) row_format=Compressed KEY_BLOCK_SIZE=4;


insert into mturk_2010_qr_entry
select page_id,  tab_number, discussion_id, post_id, quote_index, response_text_end, presented_quote, presented_response, term, topic
from iac.mturk_2010_qr_entries;

insert into mturk_2010_qr_task1_worker_response
select page_id, tab_number, SHA2(workerid, 256), response_number, disagree_agree, disagree_agree_unsure, attacking_respectful, attacking_respectful_unsure, emotion_fact, emotion_fact_unsure, nasty_nice, nasty_nice_unsure, sarcasm
from iac.mturk_2010_qr_task1_worker_responses;

insert into mturk_2010_qr_task2_worker_response
select page_id, tab_number, SHA2(workerid, 256), response_number, agree, defeater_undercutter, defeater_undercutter_unsure, negotiate_attack, negotiate_attack_unsure, personal_audience, personal_audience_unsure, questioning_asserting, questioning_asserting_unsure
from iac.mturk_2010_qr_task2_worker_responses;

insert into mturk_2010_qr_task1_average_response
select * from iac.mturk_2010_qr_task1_average_responses;

insert into mturk_2010_qr_task2_average_response
select * from iac.mturk_2010_qr_task2_average_responses;

insert into mturk_2010_p123_post
select p123_triple_id,  triple_index, discussion_id, post_id, presented_text, presented_text_term_removed, term, topic
from iac.mturk_2010_p123_posts;

insert into mturk_2010_p123_entry
select * from iac.mturk_2010_p123_entries;

insert into mturk_2010_p123_worker_response
select page_id, tab_number, SHA2(workerid, 256), response_number, disagree_agree, disagree_agree_unsure, attacking_respectful, attacking_respectful_unsure, emotion_fact, emotion_fact_unsure, nasty_nice, nasty_nice_unsure, sarcasm
from iac.mturk_2010_p123_worker_responses;

insert into mturk_2010_p123_average_response
select * from iac.mturk_2010_p123_average_responses;

create table mturk_author_stance(
  `discussion_id` mediumint unsigned not null,
  `author_id` mediumint unsigned not null,
  `topic_id` mediumint unsigned not null,
  `topic_stance_id_1` tinyint unsigned not null,
  `topic_stance_votes_1` tinyint unsigned not null,
  `topic_stance_id_2` tinyint unsigned not null,
  `topic_stance_votes_2` tinyint unsigned not null,
  `topic_stance_votes_other` tinyint unsigned not null,
  primary key (discussion_id, author_id),
  foreign key (author_id) references author(author_id),
  foreign key (topic_id, topic_stance_id_1) references topic_stance(topic_id, topic_stance_id),
  foreign key (topic_id, topic_stance_id_2) references topic_stance(topic_id, topic_stance_id)
) row_format=Compressed KEY_BLOCK_SIZE=4;

insert into mturk_author_stance 
select
discussion_id, author_id, topic_id, 
if(topic_stance_id_1< topic_stance_id_2, topic_stance_id_1, topic_stance_id_2),
if(topic_stance_id_1< topic_stance_id_2, topic_stance_votes_1, topic_stance_votes_2),
if(topic_stance_id_1< topic_stance_id_2, topic_stance_id_2, topic_stance_id_1),
if(topic_stance_id_1< topic_stance_id_2, topic_stance_votes_2, topic_stance_votes_1),
topic_stance_votes_other
from iac.mturk_author_stance;
