from collections import defaultdict, Counter

from grab_data.discussion import Dataset, results_root_dir, data_root_dir

from utilities.file_formatting import latex_writer, csv_wrapper
from utilities.parsing import tokenizer

def main():
    dataset = Dataset('fourforums',annotation_list=['topic','mechanical_turk'])
    
    gen_numbers1(dataset)
    gen_table1(dataset)
    gen_table2(dataset)
    
def gen_numbers1(dataset):
    print 'generating numbers 1...'
    
    counts = Counter()
    for discussion in dataset.get_discussions():
        for post in discussion.get_posts():
            counts['Posts']+=1
            counts['Posts with quotes']+=1 if len(post.get_ranges('quotes')) >=1 else 0
    for key, count in counts.most_common():
        print key, count
    print counts['Posts with quotes']/float(counts['Posts']), 'percent of posts contain quotes'
    print '\n\n\n'
    
def gen_table1(dataset):
    print 'generating table 1...'
    counts = defaultdict(Counter)
    authors = defaultdict(Counter)
    text_lengths = defaultdict(list)
    annots = defaultdict(Counter)
    
    for discussion in dataset.get_discussions():#annotation_label='mechanical_turk'):
        for topic in ['All',str(discussion.annotations.get('topic'))]:
            counts[topic]['Discs']+=1
            counts[topic]['Posts']+=len(discussion.get_posts())
            for post in discussion.get_posts():
                authors[topic][post.author]+=1
                text_lengths[topic].append(len(post.delete_ranges('quotes')))
            
            if 'mechanical_turk' in discussion.annotations and 'qr_averages' in discussion.annotations['mechanical_turk']:
                for key, entry in discussion.annotations['mechanical_turk']['qr_averages'].items():
                    if discussion.annotations['mechanical_turk']['qr_resample'][key]['resampled']==True:
                        annots[topic]['total']+=1
                        if entry['agreement'] >= 1.0:
                            annots[topic]['Agree']+=1
                        if entry['attack'] <= -1.0:
                            annots[topic]['Attack']+=1
                        if entry['nicenasty'] <= -1.0:
                            annots[topic]['Nasty']+=1
                        if entry['fact-feeling'] <= -1.0:
                            annots[topic]['Emote']+=1
                        if entry['sarcasm'] >= 0.5:
                            annots[topic]['Sarcasm']+=1
            
    for topic in counts:
        counts[topic]['NumA']=len(authors[topic])
        counts[topic]['A>1P']=len([author for author, count in authors[topic].items() if count > 1])/float(counts[topic]['NumA'])*100.0
        counts[topic]['P/A']=counts[topic]['Posts']/float(counts[topic]['NumA'])
        counts[topic]['PL']=sorted(text_lengths[topic])[len(text_lengths[topic])/2]
        counts[topic]['Samp']=annots[topic]['total']
        for field in annots['All']:
            if field =='total': continue
            counts[topic][field]=annots[topic][field]/float(annots[topic]['total'])*100.0 if annots[topic]['total']>0 else None
        counts[topic]['Topic']=str(topic).capitalize()
        
    final_table = sorted([entry for entry in counts.values() if entry['Topic'] not in ['All','None']], key=lambda x:-x['Posts'])
    final_table.extend([counts['None'],counts['All']])
    
    print '\n\n\n'
    latex_writer.write_table(final_table,fieldnames=['Topic','|','Discs','Posts','NumA','P/A','A>1P','PL','Samp','Agree','Sarcasm','Emote','Attack','Nasty'], decimal_places=0, include_sorted_remaining_fields=False, fields_with_percents=['Agree','Sarcasm','Emote','Attack','Nasty','A>1P'])
    print '\n\n\n'

def gen_table2(dataset):
    print 'generating table 2...'
    original_dist = {None:10836, "and":767,"because":179,"just":131,"yea":19,"yeah":171,"see":76,"yes":561,"really":112,"i think":280,"no":885,"i see":54,"actually":343,"you":958,"i know":72,"i believe":81,"you know":55,"but":350,"you mean":55,"know":3,"No terms in first 10":11969,"you think":7,"oh":256,"i":2543,"well":667,"i dunno":10,"so":802}
    
    qr_counts = Counter()
    post_counts = Counter()
    for discussion in dataset.get_discussions(annotation_label='topic'):
        for post in discussion.get_posts():
            for quote, response in post.get_quote_response_pairs():
                tokens = tokenizer.tokenize(response.lower()[:300]) #For speedup, only look at 300 characters.... in fact changes 3 (of >60,000 each) from none to no terms in first 10. 
                if len(tokens)==0: continue
                term = _get_initial_term(tokens)
                qr_counts[term]+=1
            tokens = tokenizer.tokenize(post.delete_ranges('quotes').lower()[:300])#For speedup, only look at 300 characters.... in fact changes 3 (of >60,000 each) from none to no terms in first 10. 
            if len(tokens)==0: continue
            term = _get_initial_term(tokens)
            post_counts[term]+=1
    
    #todo: get use in raw mech turk...
    raw_qr = csv_wrapper.read_csv(data_root_dir+'MechanicalTurk/raw/database/qr_pages.csv')
    raw_qr_counts = Counter()
    for entry in raw_qr:
        for i in range(7):
            term = entry[str(i)+'_term']
            if term=='None': term = None 
            raw_qr_counts[term]+=1
    
    #todo: get use in raw mech turk...
    num_wo = 0
    total = 0
    raw_123= csv_wrapper.read_csv(data_root_dir+'MechanicalTurk/raw/database/123_triples.csv')
    raw_123_counts = defaultdict(Counter)
    for entry in raw_123:
        total+=1
        wo = True
        for i in range(3):
            term = entry['post_'+str(i)+'_term']
            if term=='no_terms': 
                text = entry['post_'+str(i)]
                tokens = tokenizer.tokenize(text.lower()[:300]) #For speedup, only look at 300 characters.... in fact changes 3 (of >60,000 each) from none to no terms in first 10. 
                if len(tokens)==0: continue
                term = _get_initial_term(tokens)
            else:
                wo = False
            raw_123_counts[i][term]+=1
        if wo:
            num_wo+=1
            
    print 'p123:', num_wo, 'of', total, 'have no terms in any of the 3 posts'
    
    #todo: get use in resampled...
    print '\t'.join(['term', 'qr_count', 'post_count',  'original_dist', 'raw_qr_counts', 'raw_123_counts_[1]', 'raw_123_counts[2]', 'raw_123_counts[3]'])
    for term, qr_count in qr_counts.most_common():
        print '\t'.join([str(term).capitalize(), str(qr_count), str(post_counts[term]),  str(original_dist[term]), str(raw_qr_counts[term]), str(raw_123_counts[0][term]), str(raw_123_counts[1][term]), str(raw_123_counts[2][term])])
    
    final_table = list()
    for term, qr_count in qr_counts.most_common():
        final_table.append({'Term':str(term).capitalize(), 'All Q-R':qr_count, 'All Posts':post_counts[term], 'Used Q-R':raw_qr_counts[term], 'Used P123':(raw_123_counts[0][term]+raw_123_counts[1][term]+raw_123_counts[2][term])})
    
    print '\n\n\n'
    latex_writer.write_table(final_table,fieldnames=['Term','|','All Q-R','All Posts','Used Q-R','Used P123'], include_sorted_remaining_fields=False)
    print '\n\n\n'

    
#Borrowed from /old/code/analysis/quote_response.py...

# This distribution of terms is specific to our data from fourforums and was created by running (parts) of this code to see what
# the actual distribution was and then pruning certain terms to reach 10,000 q/r pairs.    
target_distribution = {"No terms in first 10":5000, "i know":72, "i see":54, "i think":200, "i believe":81, "i dunno":10, "you know":55, "you think":7, "you mean":55, "i":250, "you":250, "because":179, "oh":256, "and":700, "so":700, "but":300, "well":667, "just":131, "actually":343, "know":3, "see":36, "really":112, "yeah":20, "yea":19, "no":250, "yes":250}
# List of terms of interest.
terms_of_interest = [(term, tokenizer.tokenize(term)) for term in target_distribution.keys() if term != 'No terms in first 10' and term != None]
# Sorted by length descending.
terms_of_interest = sorted(terms_of_interest, key=lambda (term, term_tokens): len(term), reverse=True )
def _get_initial_term(text_tokens):
    none_in_first_ten = True
    for term, term_tokens in terms_of_interest:
        if tokenizer.is_text_initial(term_tokens, text_tokens, start_within=1):     # Starts with term
            return term
        elif tokenizer.is_text_initial(term_tokens, text_tokens, start_within=10):  # Term in words 2 - 10
            none_in_first_ten = False
    if none_in_first_ten:
        return 'No terms in first 10'   # No terms in 1-10
    else:
        return None


main()
