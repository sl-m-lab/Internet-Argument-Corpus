#Just a handy little wrapper for the built-in csv.DictReader/Writer  
#An important argument is: delimiter=';'

import csv
import codecs
import os
from utilities.misc import utils
import pdb

def write_csv(filename, rowdicts, fieldnames=None, include_sorted_remaining_fields=True, get_keys_from_first_row=False, include_header=True, restval="", extrasaction="ignore", dialect="excel", *args, **kwds):
    """@note: Differs in the default extrasaction value
        @note: include_sorted_remaining_fields=True is expensive, so use get_keys_from_first_row=True when possible
        #TODO: Allow wildcards "*"
    
    """
    
    if fieldnames == None:
        fieldnames = []
    if include_sorted_remaining_fields:
        original_fields = set(fieldnames)
        additional_fields = set()
        for row in rowdicts:
            for key in row.keys():
                if key not in original_fields:
                    additional_fields.add(key)
            if get_keys_from_first_row:
                break
        fieldnames.extend(sorted(additional_fields))
    
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    outputfile = codecs.open(filename,'w','utf-8')
    csv_writer = csv.DictWriter(outputfile, fieldnames, restval, extrasaction, dialect, quoting=csv.QUOTE_NONNUMERIC, *args, **kwds)
    
    if include_header:
        #python 2.7 has this, 2.6 does not, this provides backwards compatibility
        if hasattr(csv_writer, 'writeheader'):
            csv_writer.writeheader()
        else:
            header = dict(zip(fieldnames, fieldnames))
            rowdicts.insert(0, header)

    return csv_writer.writerows(rowdicts)

def read_csv(filename, fieldnames=None, key=None, restkey="", dialect="excel", *args, **kwds):
    """@note: You probably don't want to use fieldnames, it is for files without headers"""
    inputfile = codecs.open(filename,'r','utf-8')
    try:
       result = list(csv.DictReader(utf_8_encoder(inputfile), fieldnames, restkey, dialect, *args, **kwds))
    except Exception, e:
       pdb.set_trace()
    result = maybe_convert_csv_result(result)
    if key is not None:
        result = utils.from_dicts_to_dict(result, key, mode='strict')
    return result

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

def maybe_convert_csv_result(original):
    """Hack to avoid python csv.QUOTE_NONNUMERIC bug and nuances"""
    #To see if anything changes and shouldn't have been whatever
    ignored_fields=set()
    if len(original)>0:
        for field, value in original[0].items():
            if value!=None and value!='' and value==utils.from_str(value):
                ignored_fields.add(field)
        if len(ignored_fields)==len(original[0]):
            return original

    new = list()
    for row in original:
        new_row = dict()
        for field, value in row.items():
            if value==None or field in ignored_fields:
                new_row[field]=value
            else:
                if value=='':
                    new_value = None
                else:
                    new_value = utils.from_str(value)
                if value==new_value:
                    ignored_fields.add(field)
                    new_row[field]=value
                    #Now go back and replace everything... :(
                    for i in range(len(new)):
                        new[i][field]=original[i][field]
                else:
                    new_row[field]=new_value
        new.append(new_row)
        
    return new
