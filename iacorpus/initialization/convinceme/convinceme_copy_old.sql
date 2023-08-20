set @convinceme_dataset_id = (select dataset_id from iac.datasets where name='convinceme' limit 1);

insert into convinceme.author select author_id, username from iac.authors where dataset_id=@convinceme_dataset_id;
insert into convinceme.text select text_id, text from iac.texts where dataset_id=@convinceme_dataset_id;
insert into convinceme.discussion select discussion_id, discussion_url, title, initiating_author_id from iac.discussions where dataset_id=@convinceme_dataset_id;
insert into convinceme.discussion_stance select discussion_id, discussion_stance_id, discussion_stance, null, null from iac.discussion_stances where dataset_id=@convinceme_dataset_id;
insert into convinceme.post
  select
    discussion_id,
    post_id,
    author_id,
    timestamp as creation_date,
    parent_post_id,
    parent_missing,
    text_id,
    votes,
    discussion_stance_id,
    (parent_missing or parent_post_id is not null) # is_rebuttal
  from iac.posts
    natural join iac.post_stances
  where dataset_id=@convinceme_dataset_id;
insert into convinceme.topic select * from iac.topics;
insert into convinceme.discussion_topic select discussion_id, topic_id from iac.discussions where topic_id is not null and topic_id != 1 and topic_id != 2 and dataset_id=@convinceme_dataset_id;

  