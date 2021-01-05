import pymysql.cursors
import json
import pandas as pd
import argparse
from server import get_stats_for_one_date, get_stats

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             db='speaktests',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

with connection.cursor() as cursor:
    cursor.execute(
        f"""SELECT id from user"""
    )
    result = cursor.fetchall()
    users = pd.DataFrame(result)
user_ids = list(users["id"])

def update_stats(date):
    for user_id in user_ids:
        stats = get_stats_for_one_date(user_id, date)

        if not stats:
            continue
        print("updating... ")
        print("\tuser_id: ", user_id)
        print("\tstats: ", stats, "\n")

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM stats WHERE user_id={user_id} AND stat_date='{date}';")
            data = pd.DataFrame(cursor.fetchall())
        if len(data) > 0:
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM stats WHERE user_id={user_id} AND stat_date='{date}';")
                connection.commit()

        stats = pymysql.escape_string(json.dumps(stats))
        insertion_command = f"INSERT INTO stats (user_id, stat_date, stats) VALUES ({user_id}, '{date}', '{stats}');"
        with connection.cursor() as cursor:
            cursor.execute(insertion_command)
            connection.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Daily stats update')
    parser.add_argument('-d', '--date', type=str, help='date')

    args = parser.parse_args()
    update_stats(args.date)