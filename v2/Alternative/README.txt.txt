This is an alternative to the monolithic .sql files, it separates out tables into individual files and is likely faster to install at the expense of a more complicated commandline procedure.


#To dump the data:

dir=$(date "+%Y-%m-%d_%Hh%Mm");
mkdir -m 777 -p /tmp/$dir
date
for db in convinceme fourforums createdebate_released; do 
  echo $db; 
  mkdir -m 777 /tmp/$dir/$db; 
  mysqldump --tab=/tmp/$dir/$db $db; 
  rm /tmp/$dir/$db/*.sql; 
  mysqldump --no-data $db -r /tmp/$dir/$db/$db.sql;
  echo "compressing";
  tar -czf /tmp/$dir/"$db"_$(date +%Y_%m_%d).tgz -C /tmp/$dir/ $db;
  rm -rf /tmp/$dir/$db;
done; mv /tmp/$dir .; date;


#To load the data:

cd $dir
date
for db in convinceme fourforums createdebate_released; do 
  echo $db; 
  mysql -u root -p -e "drop database $db; CREATE SCHEMA $db DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin; SET GLOBAL foreign_key_checks=0"; 
  mysql -u root -p $db < $db/$db.sql;
  mysqlimport -u root -p --use-threads=4 --local $db $db/*.txt; 
  mysql -u root -p -e "SET GLOBAL foreign_key_checks=1"; 
done;date;
