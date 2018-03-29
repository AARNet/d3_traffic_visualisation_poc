#!/usr/bin/env python

# Read in the a CSV file of AS Numbers, Names & Countries
# Infer if it's a research institution based upon the name
# Store the revised mapping table in a sqlite db

# TODO - SHould probably change this to write to CSV only then leave CSV->DB->DB.join work in nfdump_aggregation script

import pandas
import sqlite3
import re
from pathlib import Path


def get_db_connection():
    conn = sqlite3.connect('db/all_traffic.sqlite')
    conn.row_factory = sqlite3.Row
    conn.text_factory = str
    return conn


def readable_name(name):
    human_name = re.sub(r'^[A-Z][A-Z\-]+ -? ?', '', str(name))
    return human_name


research_strings = map(lambda s: s.lower(), ["Uni", "Research", "Foundation", "School", "Lab", "Institute", "College",
                                             "CERN", "ESNet", "Supercomputer", "Reseau", "Telescope",
                                             "AARNet", "SurfNet", "Internet2", "GEANT", "NorduNet", "GRNet", "JaNet"])
def is_research_institution(name):
    lower_name = str(name).lower()
    for s in research_strings:
        if s in lower_name:
            return True
    return False


research_flag_result_cache = {}
def research_flag(name):
    if name in research_flag_result_cache:
        return research_flag_result_cache[name]

    answer = None
    if is_research_institution(name):
        answer = 'Y'
    else:
        answer = 'N'

    research_flag_result_cache[name] = answer
    return answer


def populate_asn2name_mapping(conn, filename, aux_file):
    as_map = {}
    df = pandas.read_csv(filename, usecols=['as_number', 'as_name', 'country_code', 'research_flag'], )
    for (i, row) in df.iterrows():
        as_map[int(row[0])] = {'as_number': row[0],
                          'as_name': readable_name(row[1]),
                          'country_code': row[2],
                          'research_flag': research_flag(row[1])
                          }

    if aux_file is not None and Path(aux_file).is_file():
        df2 = pandas.read_csv(aux_file, usecols=['as_number', 'as_name', 'country_code', 'research_flag'], )
        for (i, row) in df2.iterrows():
            as_map[int(row[0])] = {'as_number': row[0],
                                'as_name': readable_name(row[1]),
                                'country_code': row[2],
                                'research_flag': research_flag(row[1])
                            }

    df_out = pandas.DataFrame.from_dict(as_map, 'index')
    df_out.to_sql("asn_data", conn, if_exists='replace', index=False)
    df_out.to_csv('asn_data.csv', header=True, index=False)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_asn_data_pkey ON asn_data(as_number)");


populate_asn2name_mapping( get_db_connection(), 'autnums.csv', 'private_asnums.csv')
