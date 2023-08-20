set @fourforums_dataset_id = (select dataset_id from iac.datasets where name='fourforums' limit 1);

insert into fourforums.author select author_id, username from iac.authors where dataset_id=@fourforums_dataset_id;
insert into fourforums.text select text_id, text from iac.texts where dataset_id=@fourforums_dataset_id;
insert into fourforums.discussion select discussion_id, discussion_url, title, initiating_author_id from iac.discussions where dataset_id=@fourforums_dataset_id;
insert into fourforums.post select discussion_id, post_id, author_id, creation_date, parent_post_id, parent_missing, text_id from iac.posts where dataset_id=@fourforums_dataset_id;
insert into fourforums.quote select discussion_id, post_id, quote_index, parent_quote_index, text_index, text_id, source_discussion_id, source_post_id, source_start, source_end, source_truncated, source_altered from iac.quotes where dataset_id=@fourforums_dataset_id;


create trigger fourforums.temp_trigger
before insert on fourforums.markup
for each row
SET
 NEW.markup_id =
 (select coalesce(max(fourforums.markup.markup_id)+1, 0)
   from fourforums.markup
   where fourforums.markup.text_id=NEW.text_id);

insert into fourforums.markup
(text_id, markup_id, markup_start, markup_end, type, attributes)
select text_id, 0, start, end, type_name, attribute_str
from iac.basic_markup where dataset_id=@fourforums_dataset_id;

drop trigger fourforums.temp_trigger;

insert into fourforums.topic select * from iac.topics;
insert into fourforums.discussion_topic select discussion_id, topic_id from iac.discussions where topic_id is not null and topic_id != 1 and topic_id != 2 and dataset_id=@fourforums_dataset_id;
