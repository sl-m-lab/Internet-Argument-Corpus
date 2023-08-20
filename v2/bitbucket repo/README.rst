Internet Argument Corpus
========================
The **Internet Argument Corpus (IAC)** version 2 is a collection of corpora for research in political debate on internet forums. The data is provided in a MySQL database (`download <https://nlds.soe.ucsc.edu/iac2>`_). There is also Python code for accessing/creating the database (`here <https://bitbucket.org/nlds_iac/internet-argument-corpus-2>`_).

Dependencies
------------
Data:
  * `MySQL <https://www.mysql.com/>`_ (Or `MariaDB <https://mariadb.org/download/>`_)
    (Server for hosting, client for access)

Code:
  * `Python 3 <https://www.python.org/>`_
  * Python libraries (pip3 install <whatever>):

    * sqlalchemy
    * inflect
    * mysqlclient (or other interface such as oursql)

Install (Code)
--------------
Either clone the git repository::

    git clone git@bitbucket.org:nlds_iac/internet-argument-corpus-2.git

Or install via pip::

    pip3 install InternetArgumentCorpus

Install (Data)
--------------
Restoring from a sql dump::

    mysql --user=root -p createdebate < createdebate_20xx_xx_xx.sql

Note that you may need to create the database first::

    drop database createdebate;
    SET GLOBAL innodb_file_format=Barracuda;  # in case it isn't already
    CREATE SCHEMA createdebate DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;


Backing up::

    mysqldump createdebate -r createdebate_$(date +%Y_%m_%d).sql

Or potentially faster but much more complicated (How *I* do it)::

    dir=$(date "+%Y-%m-%d_%Hh%Mm");
    mkdir -m 777 -p /tmp/$dir
    date
    for db in convinceme fourforums createdebate createdebate_released; do 
        echo $db; 
        mkdir -m 777 /tmp/$dir/$db; 
        mysqldump --tab=/tmp/$dir/$db $db; 
        rm /tmp/$dir/$db/*.sql; 
        mysqldump --no-data $db -r /tmp/$dir/$db/$db.sql;
        echo "compressing";
        tar -czf /tmp/$dir/"$db"_$(date +%Y_%m_%d).tgz -C /tmp/$dir/ $db;
        rm -rf /tmp/$dir/$db;
    done; mv /tmp/$dir .; date;

    cd $dir
    date
    for db in convinceme fourforums createdebate createdebate_released; do 
        echo $db; 
        mysql -u root -p -e "drop database $db; CREATE SCHEMA $db DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin; SET GLOBAL foreign_key_checks=0"; 
        mysql -u root -p $db < $db/$db.sql;
        mysqlimport -u root -p --use-threads=4 --local $db $db/*.txt; 
        mysql -u root -p -e "SET GLOBAL foreign_key_checks=1"; 
    done;date;


Use
---
Python code:

.. code-block:: python

    from iacorpus import load_dataset

    dataset = load_dataset('fourforums')
    print(dataset.dataset_metadata)
    for discussion in dataset:
        print(discussion)
        for post in discussion:
            print(post)
            exit()

Contributing
------------
I welcome suggestions, pull requests, bug reports, etc.!
