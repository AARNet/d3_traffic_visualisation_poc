#! /bin/sh
set -e

usage() {
    cat << EOM
    usage: ./go.sh <YYYYMMDD> router1 [router2 router3 ...]

    netflow records for each router will looked for in the path \$NETFLOW_BASE_DIR/router_name
EOM
    exit 1
}

if [ -z "$2" ]
then
    usage
fi


#
# Configure these
#
DAY="$1"
shift
ROUTER_LIST="$*"

if [ -z "$NETFLOW_BASE_DIR" ]
then
    NETFLOW_BASE_DIR="./netflow"
fi
echo "Using base netflow directory of $NETFLOW_BASE_DIR"


[ -d data ] || mkdir data
[ -d db   ] || mkdir db

generate_asn_data_in_csv() {
    ASN_PROCESSED_FILE='asn_data.csv'
    if [ ! -f $ASN_PROCESSED_FILE ]
    then
        echo "Generating list of research related ASNs ..."
        python ./asn_tagging.py
    fi
}

aggregate_flows_to_csv() {
    ROUTER=$1
    AGGREGATE_FILE="data/aggregated_netflow.$ROUTER.$DAY.csv"
    AGGREGATE_HEADER="ts,te,td,sa,da,sp,dp,pr,flg,fwd,stos,ipkt,ibyt,opkt,obyt,in,out,sas,das,smk,dmk,dtos,dir,nh,nhb,svln,dvln,ismc,odmc,idmc,osmc,mpls1,mpls2,mpls3,mpls4,mpls5,mpls6,mpls7,mpls8,mpls9,mpls10,cl,sl,al,ra,eng,exid,tr"
    NETFLOW_DIR="$NETFLOW_BASE_DIR/$ROUTER"
    [ -d "${NETFLOW_DIR}/ipv4" ] && NETFLOW_DIR="${NETFLOW_DIR}/ipv4"
    FILTER=""
    FILERANGE="nfcapd.${DAY}0000:nfcapd.${DAY}2355"


    if [ ! -f "$NETFLOW_DIR/nfcapd.${DAY}0000" ]
    then
        echo "Could not find starting netflow file <$NETFLOW_DIR/nfcapd.${DAY}000> "
    elif [ ! -f $AGGREGATE_FILE ]
    then
        echo "Generating summary of flows for $ROUTER on $DAY ..."
        echo $AGGREGATE_HEADER > $AGGREGATE_FILE
        nfdump -R $NETFLOW_DIR/$FILERANGE -a -A srcas,dstas,router -o csv -q -O bytes -n 1000  "$FILTER" >> $AGGREGATE_FILE
    else
        echo "Aggregate file <$AGGREGATE_FILE> already exists. Skipping reprocessing"
    fi
}

aggregate_flows_to_csv_for_all_routers() {
    for r in $ROUTER_LIST
    do
        aggregate_flows_to_csv $r
    done
}

load_csv_to_database() {
    echo "Loading aggregate data into DB ..."
    python ./load_asn_data_to_db.py $AGGREGATE_FILE
}

generate_static_data_for_webpage() {
    echo "Regenerating static data ..."
    python ./nfdump_aggregration_to_research_traffic.py
}



generate_asn_data_in_csv
aggregate_flows_to_csv_for_all_routers
load_csv_to_database
generate_static_data_for_webpage


echo "Completed successfully."



