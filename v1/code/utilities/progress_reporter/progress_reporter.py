from time import time
from datetime import timedelta
from math import ceil

class ProgressReporter:
    """reports progress towards a goal and time remaining"""
    def __init__(self, total_number=None, text='Finished ', report_interval_in_sec=30, starting_number=0, lock=None):
        self.total_number = total_number
        self.text = text
        self.report_interval = report_interval_in_sec
        self.progress_start_time = self.last_report_time = time()
        self.current_number = starting_number
        self.lock = lock

    def report(self, current_number=None, total_number=None, force_report=False):
        #update current and total numbers
        self.current_number = current_number if current_number else self.current_number+1
        if total_number: self.total_number = total_number
        
        #force report on first and last
        force_report = force_report or self.current_number == 1 or self.current_number == self.total_number
        
        if force_report or self.report_interval:
            current_time = time()
            if force_report or current_time - self.last_report_time >= self.report_interval:
                time_spent = current_time - self.progress_start_time
                
                output_str = self.text + str(self.current_number)
                if self.total_number:
                    if self.current_number>0:
                        sec_remaining = ceil((self.total_number - self.current_number)/float(self.current_number)*time_spent)
                    else:
                        sec_remaining = 0
                    output_str +=' of '+str(self.total_number)+'. Time remaining: '+str(timedelta(seconds=sec_remaining))
                output_str += '. Time taken: '+str(timedelta(seconds=ceil(time_spent)))
                if self.lock != None: self.lock.acquire()
                print output_str
                if self.lock != None: self.lock.release()
                self.last_report_time = time()

if( __name__ == '__main__'):
    print 'Testing Progress Reporter...'
    foo = ProgressReporter(5)
    foo.report()
    foo.report()
    foo.report()
    foo.report()
    foo.report()
