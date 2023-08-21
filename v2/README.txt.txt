This folder is not under version control (too big)

 
# Backing up:
mysqldump --user=root -p --tz-utc createdebate -r createdebate_$(date +%Y_%m_%d).sql

# Restoring:
mysql --user=root -p --tz-utc createdebate < createdebate_20xx_xx_xx.sql

# Without parses:
mysqldump --user=root -p --tz-utc createdebate --ignore-table=createdebate.dependency_relation --ignore-table=createdebate.pos_tag --ignore-table=createdebate.word --ignore-table=createdebate.sentence --ignore-table=createdebate.parse_tag --ignore-table=createdebate.corenlp_parse --ignore-table=createdebate.token --ignore-table=createdebate.dependency --ignore-table=createdebate.corenlp_named_entity_tag --ignore-table=createdebate.corenlp_named_entity --ignore-table=createdebate.corenlp_coref  --ignore-table=createdebate.token_view --ignore-table=createdebate.dependency_view -r createdebate_no_parse_$(date +%Y_%m_%d).sql 


# Consider compressing the resulting file(s):
gzip *_$(date +%Y_%m_%d).sql
# or
tar -tgz datasets_$(date +%Y_%m_%d).tar.gz *_$(date +%Y_%m_%d).sql


# To clear the database and start over: (via SQL commandline)
drop database createdebate;
SET GLOBAL innodb_file_format=Barracuda;  # in case it isn't already
CREATE SCHEMA createdebate DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;


# How I do backups:
for DATASETNAME in fourforums convinceme createdebate createdebate_released; do echo $DATASETNAME; mysqldump --user=root -p -h 127.0.0.1 --tz-utc $DATASETNAME -r "$DATASETNAME"_$(date +%Y_%m_%d).sql; mysqldump --user=root -p -h 127.0.0.1 --tz-utc $DATASETNAME --ignore-table=$DATASETNAME.dependency_relation --ignore-table=$DATASETNAME.pos_tag --ignore-table=$DATASETNAME.word --ignore-table=$DATASETNAME.sentence --ignore-table=$DATASETNAME.parse_tag --ignore-table=$DATASETNAME.corenlp_parse --ignore-table=$DATASETNAME.token --ignore-table=$DATASETNAME.dependency --ignore-table=$DATASETNAME.corenlp_named_entity_tag --ignore-table=$DATASETNAME.corenlp_named_entity --ignore-table=$DATASETNAME.corenlp_coref  --ignore-table=$DATASETNAME.token_view --ignore-table=$DATASETNAME.dependency_view -r "$DATASETNAME"_no_parse_$(date +%Y_%m_%d).sql; done; ls -lh *_$(date +%Y_%m_%d).sql; gzip *_$(date +%Y_%m_%d).sql
