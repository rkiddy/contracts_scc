
echo ""
echo "This script will remove the data from the contract_uniqs table"
echo "and re-build the connections fot it in the contracts table and"
echo "the supporting_docs table. To continue, hit return. To abort,"
echo "hit Control-C."

read a

echo "delete from contract_uniqs;" | mysql ca_scc_contracts

echo "update contracts set uniq_pk = NULL;" | mysql ca_scc_contracts

echo "update supporting_docs set contract_uniq_pk = NULL;" | mysql ca_scc_contracts

echo "select ariba_id, sap_id, contract_id from contracts;" | \
    mysql --skip-column-names ca_scc_contracts | \
    sort | uniq | \
    awk 'BEGIN{FS="\t"}
         {print "insert into contract_uniqs values";
          print "("NR",'\''"$1"'\',\''"$2"'\',\''"$3"'\'');"}' | \
    sed 's/'\''NULL'\''/NULL/g' | \
    mysql ca_scc_contracts

echo "select pk, ariba_id, sap_id, contract_id from contract_uniqs;" | \
    mysql --skip-column-names ca_scc_contracts | \
   awk '{print "update contracts set uniq_pk = "$1;
          print "where ariba_id = '\''"$2"'\'' and sap_id = '\''"$3"'\''";
          print "    and contract_id = '\''"$4"'\'';"}' | \
    sed 's/= '\''NULL'\''/is NULL/g' | mysql ca_scc_contracts       

echo "select pk, ariba_id, sap_id, contract_id from contract_uniqs;" | \
    mysql --skip-column-names ca_scc_contracts | \
    awk '{print "update supporting_docs set contract_uniq_pk = "$1;
          print "where ariba_id = '\''"$2"'\'' and sap_id = '\''"$3"'\''";
          print "    and contract_id = '\''"$4"'\'';"}' | \
    sed 's/= '\''NULL'\''/is NULL/g' | mysql ca_scc_contracts 

