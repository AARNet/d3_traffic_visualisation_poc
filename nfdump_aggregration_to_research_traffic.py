#!/usr/bin/env python


# Read nfdump file
# parse line
# Lookup ASN
# Print if research

import pandas
import sqlite3
import json
import re

# PE Provider-Edge Routers sampled at 1 in 100.
# BDR Boarder Routers sampled at 1 in 100
NETFLOW_PACKET_SAMPLING_MULTIPLIER = 100
DEFAULT_INSTITUTION_BUCKET = 'zz.All Other'
GB = 1000*1000*1000
MIN_TRAFFIC_THRESHOLD = 100 * GB


def populate_asn2name_mapping(conn):
    df = pandas.read_csv("asn_data.csv")
    df.to_sql("asn_data", conn, if_exists='replace', index=False)


def populate_nfdump_summary(conn):
    df3 = pandas.read_csv("aggregated_netflow_remote.csv")
    df3.to_sql("nfdump_summary", conn, if_exists='replace', index=False)  # Change to append.


def new_node_object(name):
    return {'name': name,
            'size': 0,
            'imports': []}


def parse_name(name):
    human_name = re.sub(r'^[A-Z][A-Z\-]+ -? ?', '', name)
    return human_name


query_str = """
select sum(nflow.ibyt) as "bytes",
  nflow.sas as "src_as",
  nflow.das as "dst_as",
  src_asn_data.country_code as "src_country",
  src_asn_data.as_name as "src_name",
  dst_asn_data.country_code as "dst_country",
  dst_asn_data.as_name as "dst_name"
from nfdump_summary nflow, asn_data src_asn_data, asn_data dst_asn_data
WHERE
--  (src_asn_data.country_code in ('AU', 'NZ') or dst_asn_data.country_code in ('AU', 'NZ') )
  dst_asn_data.as_number = nflow.das
  AND src_asn_data.as_number = nflow.sas
  -- AND nflow.sas != 7575
  --    AND src_asn_data.research_flag = 'Y' AND
  --    AND dst_asn_data.research_flag = 'Y'
group BY
  nflow.sas,
  nflow.das,
  src_asn_data.country_code,
  src_asn_data.as_name,
  dst_asn_data.country_code,
  dst_asn_data.as_name
ORDER BY bytes DESC
"""


def get_traffic_summary(conn, src, dst):
    query_str = """
select sum(nflow.ibyt) as "bytes"
from nfdump_summary nflow
where
  sas = {0} AND das = {1}
""".format(src, dst)
    cursor = conn.execute(query_str)
    row = cursor.fetchone()
    if row is None:
        return 0

    bytes = row[0]
    if bytes is None:
        bytes = 0
    return bytes


def by_country_key(name):
    prefix = "bb:"
    country = name[0:2]
    if country in ['AU', 'NZ', 'au', 'nz']:
        prefix = "aa:"
    return prefix + country


def get_institution_name(country_code, as_name):
    if country_code is None:
        cc = '__'
    else:
        cc = country_code.lower()
    return cc + '.' + parse_name(str(as_name))


def get_institutions_list(conn):
    group_of_8 = [
        'University of Adelaide',
        'Australian National University',
        'The University of Melbourne',
        'Monash University',
        'University of New South Wales',
        'University of Queensland',
        'University of Sydney',
        'University of Western Australia'
    ]
    ausy_extras = [
        'Commonwealth Scientific and Industrial Research Organisation',
        'Australian Academic and Reasearch Network (AARNet)'
    ]
    nz_friends = [
        'National Research and Education Network',
        'Science New Zealand',
        'The University of Auckland',
        'The University of Otago',
        'Auckland University of Technology'
    ]
    institutions = [] + map(lambda i: 'au.' + i, group_of_8 + ausy_extras) + map(lambda i: 'nz.' + i, nz_friends)

    next_biggest_query = """select as_name, country_code
    from nfdump_summary nflow, asn_data 
    WHERE asn_data.as_number = nflow.sas 
    group by as_name
    order by sum(ibyt) DESC 
    LIMIT 40"""

    next_biggest_orgs = []
    for row in conn.execute(next_biggest_query):
        institution_name = row['country_code'].lower() + '.' + parse_name(row['as_name'])
        if institution_name not in institutions:
            next_biggest_orgs.append(institution_name)

    institutions.extend(sorted(next_biggest_orgs))

    institutions.append(DEFAULT_INSTITUTION_BUCKET)
    return institutions


def build_adjacency_matrix(conn, institutions):
    adjacency_matrix = []
    for i in range(len(institutions)):
        adjacency_matrix.append([0] * len(institutions))

    name2index_map = {}
    for i in range(0, len(institutions)):
        name2index_map[institutions[i]] = i

    for row in conn.execute(query_str):
        src = get_institution_name(row['src_country'], row['src_name'])
        dst = get_institution_name(row['dst_country'], row['dst_name'])

        if src not in name2index_map:
            src = DEFAULT_INSTITUTION_BUCKET
        if dst not in name2index_map:
            dst = DEFAULT_INSTITUTION_BUCKET
        src_i = name2index_map[src]
        dst_i = name2index_map[dst]
        adjacency_matrix[src_i][dst_i] += row['bytes'] * NETFLOW_PACKET_SAMPLING_MULTIPLIER
        #adjacency_matrix[dst_i][src_i] += row['bytes'] * NETFLOW_PACKET_SAMPLING_MULTIPLIER # For grouping by downloads

    # Filter out traffic that is just noise.
    for src_row in adjacency_matrix:
        for i in range(len(src_row)):
            if src_row[i] < MIN_TRAFFIC_THRESHOLD:
                src_row[i] = 0

    return adjacency_matrix


db_conn = sqlite3.connect('db/all_traffic.sqlite')
db_conn.row_factory = sqlite3.Row
db_conn.text_factory = str

institutions = get_institutions_list(db_conn)
adjacency_matrix = build_adjacency_matrix(db_conn, institutions)
open('matrix.json', "w").write(json.dumps(adjacency_matrix))
unis = open('institutions.csv', "w")
unis.write('name\n')
unis.write('\n'.join(institutions))
