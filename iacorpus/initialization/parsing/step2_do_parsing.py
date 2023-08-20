import os


# TODO: step 2A: Filter out foreign word entries
# - they take a couple orders of magnitude longer forever and produce garbage results
# Also things with excessive (repeated) punctuation ................................. :) :) :) :) :) :) :) :) :) :) :)


def main(dataset_name, parsing_dir):
    folder = os.path.join(parsing_dir, dataset_name)
    java_cmd = 'java -cp "*" -mx19g edu.stanford.nlp.pipeline.StanfordCoreNLP -filelist '+folder+'/filelist.txt -outputExtension ".xml" -outputFormat xml -threads 4 -noClobber -props '+folder+'/corenlp.properties -outputDirectory '+folder+'/xml 2>> '+folder+'/err.txt'
    print('run:')
    print(java_cmd)
