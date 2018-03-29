#!/usr/bin/env python

import sys
import pandas
import sqlite3


def populate_nfdump_summary(conn, filename):
    df3 = pandas.read_csv(filename)
    df3.to_sql("nfdump_summary_by_day_and_router", conn, if_exists='append', index=False) # Change to append.
    conn.execute('''
    CREATE INDEX IF NOT EXISTS idx_nfdump_by_day_and_router_asnumbers
    ON nfdump_summary_by_day_and_router (sas, das)
    ''')

def get_connection():
    conn = sqlite3.connect('db/all_traffic.sqlite', )
    conn.row_factory = sqlite3.Row
    conn.text_factory = str
    create_table_of_files(conn)
    return conn


def is_file_loaded(conn, filename):
    rv = False
    cursor = conn.execute('SELECT * FROM loaded_files WHERE filename=?', [filename])
    if len(cursor.fetchall()) > 0:
        rv = True
    conn.commit()
    return rv


def mark_file_loaded(conn, filename):
    conn.execute("INSERT INTO loaded_files VALUES (?, CURRENT_DATE, ?)", [filename, None])
    conn.commit()


def create_table_of_files(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS loaded_files (filename text, date text, checksum text)')
    conn.commit()


def make_summary_table(conn):
    conn.execute('DROP TABLE IF EXISTS "nfdump_summary"')
    query ="""
    CREATE TABLE nfdump_summary AS 
    SELECT sas, das, sum(ibyt) AS "ibyt", sum(obyt) as "obyt", sum(ipkt) AS "ipkt", sum(opkt) AS "opkt" 
    FROM nfdump_summary_by_day_and_router
    GROUP BY sas, das
    ORDER BY sas, das
    """
    conn.execute(query)
    conn.commit()
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_nfdump_as_numbers
        ON nfdump_summary (sas, das)
        ''')
    conn.commit()



# TODO - Add usage blurb here

if __name__ == '__main__':
    conn = get_connection()

    for filename in sys.argv[1:]:
        if is_file_loaded(conn, filename):
            print "Skipping " + filename
            continue
        print "Loading " + filename
        populate_nfdump_summary(get_connection(), filename)
        mark_file_loaded(conn, filename)

    make_summary_table(conn)