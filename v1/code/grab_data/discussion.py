import json
import codecs
import os
from collections import defaultdict
import re
import pdb

from utilities.file_formatting import csv_wrapper
from utilities.progress_reporter.progress_reporter import ProgressReporter


class Dataset:
    def __init__(self, name, annotation_list = None, cache_discussions=False):
        self.name = name
        
        self.cache_discussions = cache_discussions
        self.discussion_cache=dict()
        
        self.used_annotations = defaultdict(set)
        self.delayed_annotations = defaultdict(lambda:defaultdict(list)) #discussion_id->annotation_name->filenames
        self.discussion_annotations = defaultdict(lambda:defaultdict(list)) #discussion_id->annotation_name->data
        self.post_annotations = defaultdict(lambda:defaultdict(lambda:defaultdict(list))) #discussion_id->post_id->annotation_name->data
        if annotation_list != None:
            for entry in annotation_list:
                self.use_annotation(entry)
    
    #@summary: Invoke using: "for discussion in get_discussions('convinceme'):"
    #@param discussion_file_list: Used for being selective about which discussions you want. Use something like ['5.json', '22.json', '23.json',...]
    #@param lock: A mutex for the progress report printing    
    def get_discussions(self, discussion_list=None, annotation_label=None, report_progress=True, lock=None):
        if discussion_list==None:
            if annotation_label == None:
                discussion_list = self.get_list_of_discussions()
            else:
                self.use_annotation(annotation_label)
                discussion_list = list(self.used_annotations[annotation_label])
        
        discussion_list = sorted(discussion_list)
        
        if report_progress:
            progress = ProgressReporter(len(discussion_list), lock=lock)
        for discussion_id in discussion_list:
            discussion = self.load_discussion(discussion_id)
            yield discussion
            if report_progress: progress.report()

    #@summary: Invoke using: "for discussion in get_discussions_byannots('convinceme'):"
    #@param annotationList: A dict of lists to select what you want from the annotations; e.g., {"topic": ["evolution", "communism vs. capitalism"], "used_in_wassa2011" : [True]}
    #@param lock: A mutex for the progress report printing    
    def get_discussions_byannots(self, annotationList, report_progress=True, lock=None):
		for annotation in annotationList.keys():
			self.use_annotation(annotation)
		discussion_list = []
		annots = self.discussion_annotations
		for id in self.get_list_of_discussions():
			check = 1
			for annot in annotationList.keys():
				if (annots[id][annot] not in annotationList[annot]) and ("*" in annotationList[annot] and annots[id][annot] == None):
					check = 0
					break
			if check:
				discussion_list.append(id)	
		discussion_list = sorted(discussion_list)
		
		if report_progress:
			progress = ProgressReporter(len(discussion_list), lock=lock)
		for discussion_id in discussion_list:
			discussion = self.load_discussion(discussion_id)
			yield discussion
			if report_progress: progress.report()

    
    def load_discussion(self, discussion_id):
        if self.cache_discussions and discussion_id in self.discussion_cache:
            return self.discussion_cache[discussion_id]
        discussion = Discussion(self.name, discussion_id)
        self.update_discussion_annotations(discussion)
        if self.cache_discussions:
            self.discussion_cache[discussion_id]=discussion
        return discussion

    
    def get_list_of_discussions(self):
        result = list()
        for filename in os.listdir(data_root_dir+self.name+'/discussions/'):
            if filename.endswith('.json'):
                result.append(int(filename[:-5]))
        return result
    
    def update_discussion_annotations(self, discussion):        
        #from cached annotations
        discussion.annotations.update(self.discussion_annotations[discussion.id])
        for post_id in self.post_annotations[discussion.id].keys():
            if post_id in discussion.posts:
                discussion.posts[post_id].annotations.update(self.post_annotations[discussion.id][post_id])
        
        #from soon to be loaded annotations
        for annotation_name, file_list in self.delayed_annotations[discussion.id].items():
            for filename in file_list:
                new_discussion_annotations, new_post_annotations = self.__load_annotation_file(filename, annotation_name, discussion.id)
                discussion.annotations.update(new_discussion_annotations[discussion.id])
                for post_id in new_post_annotations[discussion.id].keys():
                    if post_id in discussion.posts:
                        discussion.posts[post_id].annotations.update(new_post_annotations[discussion.id][post_id])
        

    def use_annotation(self, annotation_name, force_reload=False):
        #already loaded?
        if annotation_name in self.used_annotations:
            if not force_reload:
                return
            else:
                self.remove_annotation(annotation_name)
        
        #from directory?
        dir_filename = data_root_dir+self.name+'/annotations/'+annotation_name        
        if os.path.isdir(dir_filename):
            for filename in os.listdir(dir_filename):
                if filename.startswith('.'): continue
    
                name, junk, extension = filename.rpartition('.')
                absolute_filename = dir_filename+'/'+filename
                
                if name.isdigit():
                    discussion_id = int(name)
                    self.used_annotations[annotation_name].add(discussion_id)
                    self.delayed_annotations[discussion_id][annotation_name].append(absolute_filename)
                    continue
                else:
                    new_discussion_annotations, new_post_annotations = self.__load_annotation_file(absolute_filename, name)
                    for discussion_id in new_discussion_annotations.keys():
                        self.used_annotations[annotation_name].add(discussion_id)
                        if annotation_name not in self.discussion_annotations[discussion_id]: #TODO might be a list already ... that's a problem
                            self.discussion_annotations[discussion_id][annotation_name]=dict()
                        self.discussion_annotations[discussion_id][annotation_name].update(new_discussion_annotations[discussion_id])
                    for discussion_id in new_post_annotations.keys():
                        self.used_annotations[annotation_name].add(discussion_id)
                        for post_id in new_post_annotations[discussion_id].keys():
                            if annotation_name not in self.post_annotations[discussion_id][post_id]: #TODO might be a list already ... that's a problem
                                self.post_annotations[discussion_id][post_id][annotation_name]=dict()
                            self.post_annotations[discussion_id][post_id][annotation_name].update(new_post_annotations[discussion_id][post_id])
                    
        
        #from file?
        for extension in ['csv','json','pkl']:
            if os.path.exists(dir_filename+'.'+extension):
                new_discussion_annotations, new_post_annotations = self.__load_annotation_file(dir_filename+'.'+extension, annotation_name)
                for discussion_id in new_discussion_annotations.keys():
                    self.used_annotations[annotation_name].add(discussion_id)
                    self.discussion_annotations[discussion_id].update(new_discussion_annotations[discussion_id])
                for discussion_id in new_post_annotations.keys():
                    self.used_annotations[annotation_name].add(discussion_id)
                    for post_id in new_post_annotations[discussion_id].keys():
                        self.post_annotations[discussion_id][post_id].update(new_post_annotations[discussion_id][post_id])
                        
        assert (annotation_name in self.used_annotations), 'Failed to load annotation: '+annotation_name
                        
    

    def remove_annotation(self, annotation_name):
        pass
    
    def __load_annotation_file(self, filename, annotation_name, file_discussion_id=None):
        discussion_annotations = defaultdict(lambda:defaultdict(list)) #discussion_id->annotation_name->data
        post_annotations = defaultdict(lambda:defaultdict(lambda:defaultdict(list))) #discussion_id->post_id->annotation_name->data
        
        if filename.endswith('.csv'):
            data = csv_wrapper.read_csv(filename)
            for row in data:
                if 'discussion_id' in row:
                    assert (file_discussion_id == None or file_discussion_id == int(row['discussion_id']))
                    discussion_id = int(row['discussion_id'])
                    del row['discussion_id']
                else: 
                    assert (file_discussion_id != None)
                    discussion_id = file_discussion_id
                
                if 'post_id' in row:
                    post_id = row['post_id']
                    del row['post_id']
                    post_annotations[discussion_id][post_id][annotation_name].append(row)
                else:
                    discussion_annotations[discussion_id][annotation_name].append(row)
                    
            one_per=True
            for discussion_id in post_annotations.keys():
                for post_id in post_annotations[discussion_id].keys():
                    if len(post_annotations[discussion_id][post_id][annotation_name])!=1:
                        one_per = False
                        break
            for discussion_id in post_annotations.keys():
                for post_id in post_annotations[discussion_id].keys():
                    self.__simplify_annotation(post_annotations[discussion_id][post_id], annotation_name,one_per)
            
            one_per=True
            for discussion_id in discussion_annotations.keys():
                if len(discussion_annotations[discussion_id][annotation_name])!=1:
                    one_per = False
                    break
            for discussion_id in discussion_annotations.keys():
                self.__simplify_annotation(discussion_annotations[discussion_id], annotation_name, one_per)

            return discussion_annotations, post_annotations

    def __simplify_annotation(self, obj, annotation_name, one_per):
        rows = obj[annotation_name]
        if len(rows)==0: return
        
        #if it should be a dict
        new_annot = dict()
        for row in rows:
            if 'key' not in row:
                break
            else:
                new_annot[row['key']]=row
        else:
            obj[annotation_name]=new_annot
            
        
        if one_per and len(rows)==1:
            if len(rows[0])==1 and annotation_name in rows[0]:
                obj[annotation_name]=rows[0][annotation_name]
            else:
                obj[annotation_name]=rows[0]

#for example...
#discussion = Discussion('carm', '42.json')
#print discussion.posts[0].text
#print discussion.posts[3].ranges['quotes'][0].start
class Discussion:
    loaded_annotations = defaultdict(dict) #dataset->label->data
    
    #restrict_to_range_labels should be a set of labels (e.g. set(['quotes']) ) that you want to save. restrict_to_range_labels=None means load all; =set() means load none 
    def __init__(self, data_set=None, id_number=None, restrict_to_range_labels = None):
        self.posts = dict()
        self.annotations = dict()
        self.metadata = dict()
        self.data_set = data_set #not stored
        self.authors = set() #not stored
        self.id = id_number
        if data_set and id_number:
            self.get_discussion(restrict_to_range_labels)

    def get_discussion(self, restrict_to_range_labels = None):
        data_file = codecs.open(data_root_dir+self.data_set+'/discussions/'+str(self.id)+'.json', 'r','utf-8')
        (posts, self.annotations, self.metadata) =  json.load(data_file)
        posts = map(Post, posts)
        for post in posts:
            self.posts[post.id] = post
            self.authors.add(post.author)
        self.load_ranges(restrict_to_range_labels)
    
    #@param data: a dict
    def add_annotation(self, data):
        self.annotations.update(data)
    
    def load_ranges(self, restrict_to_labels=None):
        if not os.path.exists(data_root_dir+self.data_set+'/ranges/'): return
        if not restrict_to_labels:
            restrict_to_labels = set()
            for folder in os.listdir(data_root_dir+self.data_set+'/ranges/'):
                if not folder.startswith('.'):
                    restrict_to_labels.add(folder)
        for label in restrict_to_labels:
            try:
                data_file = codecs.open(data_root_dir+self.data_set+'/ranges/'+label+'/'+str(self.id)+'.json', 'r','utf-8')
            except:
                continue
            range_tuples = json.load(data_file)
            data_file.close()
            for post_id, range_tuple in range_tuples:
                if post_id in self.posts:
                    self.posts[post_id].ranges[label].append(build_range(label, range_tuple))
            
    def store_discussion(self, restrict_to_range_labels=None):
        filename = str(self.id)+'.json'
        directory = data_root_dir+self.data_set+'/discussions/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        dumpfile = codecs.open(directory+filename, 'w','utf-8')
        json.dump(self.to_tuple(), dumpfile, indent = True, encoding = 'utf-8')
        dumpfile.close()
        self.store_ranges(restrict_to_range_labels)
    
    def store_ranges(self, restrict_to_labels=None):
        filename = str(self.id)+'.json'
        ranges = defaultdict(list)
        for post in self.posts.values():
            for label, range_list in post.ranges.items():
                if not restrict_to_labels or label in restrict_to_labels:
                    for range in range_list:
                        ranges[label].append((post.id, range.to_tuple()))
        for label, range_tuples in ranges.items():
            directory = data_root_dir+self.data_set+'/ranges/'+label+'/'
            if not os.path.exists(directory):
                os.makedirs(directory)
            dumpfile = codecs.open(directory+filename, 'w','utf-8')
            json.dump(range_tuples, dumpfile, indent = True, encoding = 'utf-8')
            dumpfile.close()
        
    def to_tuple(self):
        posts = map(lambda post: post.to_tuple(), sorted(self.posts.values(), key=lambda arg: arg.id))
        return (posts, self.annotations, self.metadata)
    
    #just to make things cleaner. if sort: then sort by id
    def get_posts(self, sort=False):
        if sort:
            return sorted(self.posts.values(), key=lambda post: post.id)
        else:
            return self.posts.values()
    

class Post:
    def __init__(self, post_tuple = None):
        if post_tuple != None:
            self.id, self.side, self.author, self.text, self.annotations, self.parent_id, self.category, self.timestamp = post_tuple
        else:
            self.id = None
            self.side = None
            self.author = None
            self.text = None
            self.annotations = None
            self.parent_id = None
            self.category = None
            self.timestamp = None
        self.ranges = defaultdict(list) #label, list of ranges

    def to_tuple(self):
        return (self.id, self.side, self.author, self.text, self.annotations, self.parent_id, self.category, self.timestamp)

    #e.g. post.delete_ranges('quotes') #will delete all quotes and return the new text
    #returns a new text minus the ranges, leaves old alone - existing ranges are invalid for this new_text
    #side effect: also deletes null characters, if this is ever an issue, it's easy to resolve, but not worth it if not an issue
    #replacement is a string you want to replace contiguous range things (so if there are two abutting ranges, they get 1 replacement, same for contained ranges
    def delete_ranges(self, range_label, new_text = None, null_char='\0', replacement = None):
        new_text = self.zero_ranges(range_label, new_text, null_char)
        if replacement == None:
            new_text = new_text.replace(null_char,'')
        else:
            replacement = replacement.replace('\\','\\\\')
            null_char = re.escape(null_char)
            new_text = re.sub(null_char+'+',replacement, new_text)
        return new_text
    
    def zero_ranges(self, range_label, new_text = None, null_char='\0'):
        if new_text == None:
            new_text = self.text
        for range in self.ranges[range_label]:
            new_text = self.zero_range(range, new_text, null_char)
        return new_text
        
    def zero_range(self, range, new_text = None, null_char='\0'):
        if new_text == None:
            new_text = self.text
        new_text = new_text[:range.start]+(null_char*(range.end - range.start))+new_text[range.end:]
        return new_text
        
    def get_range_text(self, range):
        return self.text[range.start:range.end]
    
    def get_ranges(self, range_label, sort=True):
        if sort:
            return sorted(self.ranges[range_label], key=lambda obj: obj.start)
        else:
            return self.ranges[range_label]
        
    
    #expects quotes to be a valid range field
    def get_quote_response_pairs(self, include_empty=False, include_range=False):
        q_r_list = list()
        
        zeroed_text = self.zero_ranges('quotes')
        quotes = self.get_ranges('quotes')
        if include_empty:
            if len(quotes) == 0:
                if include_range:
                    q_r_list.append(('',self.text.strip(),None))
                else:
                    q_r_list.append(('',self.text.strip()))
            elif quotes[0].start != 0:
                if include_range:
                    q_r_list.append(('',self.text[:quotes[0].start].strip(),None))
                else:
                    q_r_list.append(('',self.text[:quotes[0].start].strip()))
                
        for quote in quotes:
            quote_text = self.text[quote.start:quote.end].strip()
            try:
                response_text = self.text[quote.end:zeroed_text.index('\0', quote.end)].strip()
            except:
                response_text = self.text[quote.end:].strip()
            if include_empty or (quote_text != '' and response_text != ''):
                if include_range:
                    q_r_list.append((quote_text,response_text,quote))
                else:
                    q_r_list.append((quote_text,response_text))
                
        return q_r_list
        

    
#feel free to extend to meet your needs
#data should be json compatible
class Range:
    #TODO - modify to load any subclass of Range with appropriate constructor
            
    def __init__(self, range_tuple = None):
        if range_tuple != None:
            self.start, self.end, self.data = range_tuple
        else:
            self.start = None
            self.end = None
            self.data = dict()

    def to_tuple(self):
        return (self.start, self.end, self.data)

#basically a factory method anticipating future complexities
def build_range(label, range_tuple):
    return Range(range_tuple)

data_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))+'/'
results_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../results'))+'/'
