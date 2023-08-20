insert into topic select * from iac.topics;

insert into discussion_topic
select discussion.discussion_id, foo.topic_id from
(select discussion_id, topic_id, discussion_url 
from iac.discussions
where topic_id is not null and topic_id != 1 and topic_id != 2
and dataset_id=3) as foo
join discussion on foo.discussion_url=discussion.url;
