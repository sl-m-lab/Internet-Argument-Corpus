from grab_data.discussion import Dataset, results_root_dir, data_root_dir

def main():
    dataset = Dataset(name='fourforums', annotation_list=['topic','mechanical_turk'])
    for discussion in dataset.get_discussions(annotation_label='mechanical_turk'):
        print 'Discussion id:', discussion.id
        print 'Discussion metadata:', discussion.metadata
        print 'Discussion title:', discussion.metadata['title']
        print 'Discussion annotations:', discussion.annotations
        print 'Discussion authors:', discussion.authors
        #discussion.posts is a dict of posts
        for post in discussion.get_posts():
            text_without_quotes = post.delete_ranges('quotes')
            print '  Post id:', post.id
            print '  Post author:', post.author
            print '  Post timestamp:', post.timestamp
            print '  Post parent_id:', post.parent_id
            print '  Post annotations:', post.annotations
            print '  Post Text:', text_without_quotes
            print '--------------------------------\n\n\n'
        break

main()
