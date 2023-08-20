#  -*- coding: utf-8 -*-
import os
import random
from collections import defaultdict

class random_guard:
    def __init__(self, random_seed=None):
        self.random_seed = random_seed
    def __enter__(self):
        if self.random_seed != None:
            self.original_random_state = random.getstate()
            random.seed(self.random_seed)
        return
    def __exit__(self, type, value, traceback):
        if self.random_seed != None:
            random.setstate(self.original_random_state)

def maybe_convert(obj, func = int):
    """@summary: Tries to call func on obj, 
    if that fails it assumes obj is an iterable
     and tries to call maybe_convert on each item in obj, 
    if that fails, it returns obj unaltered
    
    """
    try: return func(obj)
    except: pass
    
    try: return [maybe_convert(elem, func) for elem in obj]
    except: pass
    
    return obj

def from_str(obj):
    temp_obj = obj.strip()
    
    if temp_obj.isdigit() or (temp_obj.startswith('-') and temp_obj[1:].isdigit()):
        return int(temp_obj)
    
    try: return float(temp_obj)
    except: pass

    if temp_obj.capitalize() == 'True':
        return True
    if temp_obj.capitalize() == 'False':
        return False
    
    return obj
    
def from_dicts_to_dict(dict_list, key, delete_key=False, mode='strict'):
    """
    @var mode: 'strict' = raise exception if key found twice
               'ignore' = go with the latest
               'update' = update entry !!Note: Update not implemented yet!!
    @note: This is destructive - it does a shallow copy and if you specify delete_key,
     that key will be gone from the list's items too!

    """
    result = dict()
    for entry in dict_list:
        if mode=='strict' and entry[key] in result:
            raise Exception('Key already in dict!')
        result[entry[key]]=entry
        if delete_key:
            del result[entry[key]][key]
    return result
