Internet Argument Corpus
Send questions to Rob Abbott, Marilyn Walker, Pranav Anand.  (abbott | maw) soe.ucsc.edu , (panand) ucsc.edu

We have a revised release in the works but it may not be ready until the end of June, 2012. 


/code
Contains Python code to load and use this dataset. 
It expects to be run from /code
See example.py  
lrec2012.py was used for generating tables in the corpus description paper. 
The code is not the cleanest, and we apologize for that. Please ask if you encounter difficulties, discover bugs, or have any questions!



/data/fourforums/discussions/
Contains our discussions in json formatted files.
Each discussion (json file) consists of a list of posts, followed by possible annotations, and finally metadata from the site and our scraping process
Each post in the list consists of a list containing: an id, side (unused), author, raw text, annotations, parent post id, category (unused), and timestamp.


/data/fourforums/ranges/
Contains things like quotes and formatting ( bold, italic, etc.)
The format is a json file with filename corresponding to the discussion id. The data consists of a post id, and a list of spans each containing character offset start/end and possibly data.

Quotes:
[
 [
  14125, #post id 
  [
   0, #quote starts at character 0
   73, #quote ends at character 73 
   { #data
    "raw_data": "So Heaven Dies?", #some source data, generally unimportant
    "quote_id": 14111, #original post's id
    "author": "So Heaven Dies?" #author of quoted text
   }
  ]
 ], 
 ...
]


/data/fourforums/annotations/
Contains annotations we have gathered in .csv files.



