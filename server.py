from flask import Flask, request, send_file, make_response, session
import random, string, os, requests
import flask
import requests
import json
import logging
from bs4 import BeautifulSoup
import numpy as np
import pymysql.cursors
import datetime
import time
import regex as re
import base64
from datetime import timedelta
import pandas as pd
from elasticsearch import Elasticsearch
from dateutil import parser
from flask_web_log import Log
from word_utils import normalize, stem, transcribe, normalize_ipa

# set up the app
app = Flask(__name__, static_url_path='')
app.secret_key = b'\xd8t\xf3\x0b\x05\\\xc8\x80a\x8a\xe5\x16 \xd9\xf4d\x1dd\xa5\x9a\x82\xb6kh'

# set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app.config["LOG_TYPE"] = "CSV"
Log(app)
es = Elasticsearch()
skipwords = set(word.strip() for word in open("static/js/skipwords.txt"))
word_mapping = json.load(open("static/js/word_mapping.json"))
word_mapping = [[key, val] for key,val in word_mapping.items()]

# utility functions
def make_conn():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='root',
                           db='speaktests',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)


def generate_random_string(length):
    res = np.base_repr(int(time.time() * 1000), 36)
    res += "".join([np.base_repr(np.random.randint(0,36), 36) for _ in range(length-8)])
    return res


def decode64(crypted_message):
    base64_bytes = crypted_message.encode()
    message_bytes = base64.b64decode(base64_bytes)
    return message_bytes.decode()


# api functions
@app.route('/')
@app.route('/gymnastics')
@app.route('/homepage.html')
@app.route('/index.html')
def root():
    return app.send_static_file('index.html')


@app.route('/statistics')
def statistics():
    return app.send_static_file('statistics.html')


@app.route('/create_user/<username>', methods=['POST'])
def create_user(username):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM user WHERE username=\'{username}\' LIMIT 1;")
        result = cursor.fetchone()
        if result:
            return json.dumps({"user_id": result["id"]})
        connection.commit()
    
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO user (username, next_paragraph_id, level, next_count) VALUES (\"{username}\", 25, 2, 10)")
        user_id = cursor.lastrowid
        connection.commit()
    return json.dumps({"user_id": user_id})


@app.route('/get_user_profile/<user_id>', methods=['POST'])
def get_user_profile(user_id):
    user_id = int(user_id)
    results = json.loads(get_stats(user_id))
    difficult_words = set([word for duration, word in results["word_stats"] if duration > 2000])

    average_duration, word_count = 0, 0
    if (results["daily_stats"]):
        average_duration, word_count = results["daily_stats"][-1][1:]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM user WHERE id={user_id} LIMIT 1;")
        user = cursor.fetchone()
        paragraph_id = user["next_paragraph_id"]
        next_count = user["next_count"]

        cursor.execute(f"SELECT * FROM paragraph WHERE id={paragraph_id} LIMIT 1;")
        result = cursor.fetchone()
        words = result["content"].split()
        ipas = [["".join(ipa) for ipa in transcribe(word)] for word in words]
        stems = [stem(word) for word in words]
        difficult_words = [int(normalize(word) in difficult_words) for word in words]

        cursor.execute(f"""SELECT min(completed_at) as min_completion_time FROM event WHERE 
                           paragraph_id={paragraph_id} AND word_index=(paragraph_length-1) LIMIT 1;""")
        result = cursor.fetchone()

        if len(result) == 0:
            min_completion_time = 0
        else:
            min_completion_time = result['min_completion_time']

        connection.commit()
    return json.dumps({"next_count": next_count, 
                       "paragraph_id": paragraph_id, 
                       "words": words, 
                       "ipas": ipas, 
                       "stems": stems, 
                       "average_duration": average_duration,
                       "word_count": word_count,
                       "min_completion_time": min_completion_time, 
                       "skipwords": list(skipwords), 
                       "word_mapping": word_mapping, 
                       "difficult_words": difficult_words})


@app.route('/get_history/<user_id>/<paragraph_id>', methods=['POST'])
def get_history(user_id, paragraph_id):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT content FROM paragraph WHERE id={paragraph_id} LIMIT 1;')
        paragraph = cursor.fetchone()
        length = len(paragraph["content"].split())

        cursor.execute(
            f"""SELECT * FROM final_sent WHERE 
                user_id={user_id} AND paragraph_id={paragraph_id}
            """
        )
        sessions = pd.DataFrame(cursor.fetchall())

        if len(sessions) == 0:
            return "[]"
        
        sessions["sent_len"] = sessions.sentence.map(lambda sent: len(sent.split()))
        sessions = sessions.groupby("session_id").apply(lambda row: pd.Series({
            "duration": max(row["completed_at"]), 
            "created_at": max(row["created_at"]), 
            "word_index": max(row["word_index"]), 
            "total_len": sum(row["sent_len"])})
        ).reset_index()
        sessions = sessions[sessions.word_index == length].copy()
        sessions["no_repetition"] = sessions.word_index >= sessions.total_len
        sessions.sort_values("created_at")
        sessions = sessions.tail(20)

        del sessions["word_index"]
        del sessions["total_len"]
        del sessions["session_id"]
    return json.dumps(list(json.loads(sessions.transpose().to_json()).values()))


def get_stats_for_one_date(user_id, date):
    next_date = (parser.parse(date) + timedelta(1)).strftime('%Y-%m-%d')
    stats = {}
    connection = make_conn()
    
    # stats from table event
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT user_id, session_id, word_index, word, duration, completed_at, created_at 
                FROM event WHERE user_id={user_id} AND '{date}'<=created_at AND created_at<'{next_date}'"""
        )
        words = pd.DataFrame(cursor.fetchall())

    if len(words) == 0:
        words = pd.DataFrame(columns=["user_id", "session_id", "word_index", "word", "duration", \
                                      "completed_at", "created_at"])
    else:
        stats["word_count"] = len(words)
        stats["duration"] = sum(words["duration"])
        
    # stats from table final_sent
    with connection.cursor() as cursor:
        cursor.execute(
            f"""select session_id, created_at, completed_at, word_index, word
                FROM final_sent WHERE user_id={user_id} AND completed_at>0 AND word!=''
                AND '{date}'<=created_at AND created_at<'{next_date}'"""
        )
        final_sent_words = pd.DataFrame(cursor.fetchall())
    if len(final_sent_words) == 0:
        final_sent_words = pd.DataFrame(columns=["session_id", "created_at", "completed_at", "word_index", "word"])
    
    # combine the stats from 2 tables
    final_sent_words = final_sent_words.sort_values(["session_id", "completed_at"])
    final_sent_words = final_sent_words.groupby("session_id").last().reset_index()
    
    word_sessions = words.groupby("session_id")["completed_at"].max().reset_index()
    word_sessions.set_index("session_id", inplace=True)
    final_sent_words.set_index("session_id", inplace=True)
    final_sent_words = final_sent_words.merge(word_sessions, left_index=True, right_index=True, how="left")
    final_sent_words.completed_at_y.fillna(0, inplace=True)
    final_sent_words = final_sent_words[final_sent_words.completed_at_x > \
                                        final_sent_words.completed_at_y]
    final_sent_words["duration"] = final_sent_words.completed_at_x - \
                                   final_sent_words.completed_at_y
    combined_words = pd.concat([words[["word", "duration"]], 
                                final_sent_words[["word", "duration"]]])
    
    # compute the overall stats
    if len(combined_words) > 0:        
        dictionary = {}
        for _, row in combined_words.iterrows():
            if row["word"] not in dictionary:
                dictionary[row["word"]] = [0, 0]
            dictionary[row["word"]][0] += 1
            dictionary[row["word"]][1] += row["duration"]
        stats["dictionary"] = dictionary
        
    return stats


@app.route('/get_stats/<user_id>', methods=['POST'])
def get_stats(user_id):
    results = {"word_stats": [], "daily_stats": []}
    curr_date = datetime.datetime.today().strftime('%Y-%m-%d')
    curr_stats = get_stats_for_one_date(user_id, curr_date)

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT stat_date, stats FROM stats WHERE user_id={user_id}"""
        )
        stats = pd.DataFrame(cursor.fetchall())
    if len(stats) == 0:
        stats = pd.DataFrame(columns=["stat_date", "stats"])
    stats["stats"] = stats["stats"].map(lambda text: json.loads(text))
    stats = stats.append({"stat_date": curr_date,
                          "stats": curr_stats}, ignore_index=True)
    stats.sort_values("stat_date", inplace=True)

    words = {}
    for _, row in stats.iterrows():
        if "dictionary" in row["stats"]:
            for word, [count, duration] in row["stats"]["dictionary"].items():
                word = normalize(word)
                if word not in words:
                    words[word] = duration/count
                else:
                    discount = (1-0.5) ** count
                    words[word] = discount * words[word] + (1 - discount) * (duration/count)

        if "word_count" in row["stats"]:
            results["daily_stats"] += [[row["stat_date"], row["stats"]["duration"], row["stats"]["word_count"]]]
    words = sorted([[duration, word] for word, duration in words.items() if word not in skipwords], reverse=True)
    results["word_stats"] = words[:20]
    results["daily_stats"] = results["daily_stats"][-20:]

    return json.dumps(results)


@app.route('/event/', methods=['POST'])
def log_event():
    data = request.get_json()
    user_id, paragraph_id, session_id, word_index, word, paragraph_length, duration, completed_at = \
        data["user_id"], data["paragraph_id"], data["session_id"], data["word_index"], data["word"], data["paragraph_length"], data["duration"], data["completed_at"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO event (user_id, paragraph_id, session_id, word_index, word, paragraph_length, duration, completed_at) "
                       f"VALUES ({user_id}, {paragraph_id}, \"{session_id}\", {word_index}, \"{word}\", {paragraph_length}, {duration}, {completed_at})")
        connection.commit()
    return "done"


@app.route('/final_sent/', methods=['POST'])
def log_final_sent():
    data = request.get_json()
    user_id, paragraph_id, session_id, sentence, word_index, word, started_at, completed_at = \
        data["user_id"], data["paragraph_id"], data["session_id"], data["sentence"], data["word_index"], data["word"], data["started_at"], data["completed_at"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO final_sent (user_id, paragraph_id, session_id, sentence, word_index, word, started_at, completed_at) "
                       f"VALUES ({user_id}, {paragraph_id}, \"{session_id}\", \"{sentence}\", {word_index}, \"{word}\", {started_at}, {completed_at})")
        connection.commit()
    return "done"


def set_next_para(user_id, paragraph_id):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"update user set next_paragraph_id={paragraph_id} where id={user_id};")
        connection.commit()


def get_user(user_id):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM user WHERE id={user_id} LIMIT 1;')
        user = cursor.fetchone()
        connection.commit()
    return user


@app.route('/next_para/<user_id>', methods=['POST'])
def next_para(user_id):
    # get the level of the user
    user = get_user(user_id)
    level, next_paragraph_id, next_count = user["level"], user["next_paragraph_id"], user["next_count"]
    if next_count == 0:
        return json.dumps({"next_count": next_count})

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE user SET next_count=next_count-1 WHERE id={user_id};")
        connection.commit()
    next_count -= 1

    # get the word stats of the user
    results = json.loads(get_stats(user_id))

    # find a suitable paragraph
    top, select = 10, 3
    trial_count, max_tries = 0, 10
    paragraph_id = None
    while trial_count < max_tries:
        if trial_count == max_tries-1 or not results["word_stats"]:
            query = f"*"
        else:
            probs = np.array([prob for [prob, _] in results["word_stats"][:top]])
            top = min(top, len(probs))
            probs = probs / sum(probs)
            select_indices = set(np.random.choice(list(range(top)), size=select, replace=False, p=probs))

            select_words = []
            un_select_words = []
            for i in range(top):
                if i in select_indices:
                    select_words += [results["word_stats"][i][1]]
                else:
                    un_select_words += [results["word_stats"][i][1]]
            query = " ".join(select_words)
            #query = "(" + " ".join(select_words) + ") AND !(" + " ".join(un_select_words) + ") AND (level: " + str(level) + ")"
        ipas = []
        for word in query.split():
            ipas += ["".join(ipa) for ipa in transcribe(word)]
        ipas = normalize_ipa(" ".join(ipas))
        print(query)
        print(ipas)

        if query != "*":
            res = es.search(index="paragraph", body={
                "size": 10,
                "query": {
                  "bool": {
                      "should": 
                        [
                          {
                            "match": {
                              "ipa": {
                                  "query": f"\"{ipas}\""
                              }
                            }
                          },
                          {
                            "match": {
                              "content": {
                                "query": f"\"{query}\""
                              }
                            }
                          }
                        ],
                        "filter": {
                            "term": {
                                "level": level
                            }
                        }
                    }
                }
            })
        else:
            res = es.search(index="paragraph", body={
                "size": 10,
                "query": {
                    "query_string": {
                        "query": f"(level: {level})",
                    }
                }
            })

        if (res["hits"]["hits"]):
            paragraph_ids = [int(paragraph["_id"]) for paragraph in res["hits"]["hits"] if int(paragraph["_id"]) != next_paragraph_id]
            scores = [float(paragraph["_score"]) for paragraph in res["hits"]["hits"] if int(paragraph["_id"]) != next_paragraph_id]
            if not paragraph_ids:
                continue
            else:
                scores = np.array(scores)
                scores = scores / sum(scores)
                paragraph_id = np.random.choice(paragraph_ids, p=scores)
            break
        trial_count += 1

    set_next_para(user_id, paragraph_id)
    return json.dumps({"next_count": next_count})


if __name__ == "__main__":
    #app.run(host="0.0.0.0", debug=True)
    #app.run(host="0.0.0.0", port=5000, debug=True)
    #app.run(host="0.0.0.0", ssl_context='adhoc')
    app.run(host="0.0.0.0", port=443, ssl_context=('certificate.crt', 'private.key',))

