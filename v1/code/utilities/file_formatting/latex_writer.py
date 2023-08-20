import os, sys
import codecs

from utilities.file_formatting import csv_wrapper

def write_table(rowdicts, filename=None, fieldnames=None, decimal_places=3, include_sorted_remaining_fields=True, get_keys_from_first_row=False, include_header=True, missing_value='', label='', caption='', escape_entries=True, fields_with_percents=None):
    """
    @param rowdicts: should be a list of dicts. '|' rows will be treated as \hlines. e.g.: [{'category':'foo','numbers':5}, '|', {'category':'bar','numbers':0.39283}]
    @param filename: file to store this table. If unspecified the table will be printed to the console. 
    @param fieldnames: a list of column names. Use '|' to indicate a line should be drawn, don't worry about first and last.
    @param fields_with_percents: an iterable of field names which should be percentages
    @warning: Don't accidentally overwrite your .tex file!!!!! 
    Please feel free/encouraged to improve/replace with something better!
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
    if filename is not None:
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        outputfile = codecs.open(filename,'w','utf-8')
    else:
        outputfile = sys.stdout
    
    field_types = _get_field_types(fieldnames, rowdicts)

    outputfile.write('\\begin{table}[ht!]\n')
    outputfile.write('\\begin{scriptsize}\n')
    outputfile.write('\\begin{center}\n')
    outputfile.write('\\begin{tabular}{|')
    for field in fieldnames:
        if field=='|':
            outputfile.write('|')#| as in vertical line
        elif field_types[field]=='string':
            outputfile.write('l')#l as in L
        else:
            outputfile.write('r')
    outputfile.write('|}\n')
    outputfile.write('\\hline\n')
    
    #feel free to make not O(n^2)....
    while '|' in fieldnames:
        fieldnames.remove('|')
    
    #Write header
    if include_header:
        for field in fieldnames:
            if field != fieldnames[0]:
                outputfile.write(' & ')
            if escape_entries:
                field = _escape_latex(field) 
            outputfile.write('\\bf '+field)
        outputfile.write('\\\\ \\hline \\hline\n')
    
    #Write data
    for row in rowdicts:
        if row=='|':
            outputfile.write('\\hline\n')
            continue
        for field in fieldnames:
            if field != fieldnames[0]:
                outputfile.write(' & ')
            value = row.get(field)
            if value is None:
                outputfile.write(missing_value)
            elif isinstance(value, basestring):
                if escape_entries:
                    value = _escape_latex(value)
                outputfile.write(value)
            elif field_types[field]=='integer':
                outputfile.write(str(value))
                if fields_with_percents and field in fields_with_percents:
                    outputfile.write('\\%')
            else:
                entry = ("%."+str(decimal_places)+"f") % float(value) #TODO: round using: +0.5/10**decimal_places ?
                outputfile.write(entry)
                if fields_with_percents and field in fields_with_percents:
                    outputfile.write('\\%')
        outputfile.write('\\\\\n')
    outputfile.write('\\hline\n')
    outputfile.write('\\end{tabular}\n')
    outputfile.write('\\end{center}\n')
    outputfile.write('\\caption{\\label{'+label+'}'+caption+' }\n')
    outputfile.write('\\end{scriptsize}\n')
    outputfile.write('\\end{table}\n')

def _escape_latex(text):
    for ch in ['{','}','_']:#TODO, some other stuff
        text = text.replace(ch,'\\'+ch)
    for ch in ['>','<']:#TODO, some other stuff
        text = text.replace(ch,'$'+ch+'$')
    return text

def _get_field_types(fieldnames, rowdicts):
    field_types = dict()#string, float, integer, TODO: make parameter, add percent
    for field in fieldnames:
        for row in rowdicts:
            if hasattr(row,'get') and row.get(field) is not None:
                value = row.get(field)
                try:
                    float(value)
                except:
                    if value.strip() in ['','NA','N/A']:#ignore these 
                        continue 
                    field_types[field]='string'
                    break
                if field_types.get(field)=='float':
                    continue
                if str(value).isdigit():
                    field_types[field]='integer'
                else:
                    field_types[field]='float'
    return field_types

def from_csv(csv_filename, output_filename=None):
    csv_data = csv_wrapper.read_csv(csv_filename)
    
    #I hope this works...
    first_line = codecs.open(csv_filename, encoding='utf-8').readline()
    fieldnames = first_line.strip().split(',') 
    fieldnames = [entry.strip().strip('"') for entry in fieldnames]
    
    write_table(csv_data, filename=output_filename,fieldnames=fieldnames)

if( __name__ == '__main__'):
    try:
        if len(sys.argv[1:]) == 0:
            raise
        csv_filename = sys.argv[1]
        if len(sys.argv)>2:
            output_filename = sys.argv[2]
        else:
            output_filename=None
        from_csv(csv_filename, output_filename)
    except:
        print 'Usage: \n  latex_writer.py csv_filename [latex_filename]'
        print 'If latex filename is unspecified, output will be printed to console.'
        print 'Try not to overwrite your main LatTex file!'
        raise
