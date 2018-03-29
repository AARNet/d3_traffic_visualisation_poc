#!/usr/bin/env bash

usage() {
    cat << EOM
    usage: ./go_all.sh <YYYYMM> router1 [router2 router3 ...]

    neflow records for each router will looked for in the path \$NETFLOW_BASE_DIR/router_name
EOM
    exit 1
}

if [ -z "$2" ]
then
    usage
fi

MONTH="$1"
shift
ROUTER_LIST="$*"

for day in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
do
    DATE="$MONTH$day"
    for router in `echo ${ROUTER_LIST}`
    do
        ./go.sh ${DATE} ${router} &
        wait # Make's Ctrl-C work more cleanly
    done
done
