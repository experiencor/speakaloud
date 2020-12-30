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
        cursor.execute(f"INSERT INTO user (username, next_paragraph_id, level) VALUES (\"{username}\", 25, 2)")
        user_id = cursor.lastrowid
        connection.commit()
    return json.dumps({"user_id": user_id})


@app.route('/get_user_profile/<user_id>', methods=['POST'])
def get_user_profile(user_id):
    user_id = int(user_id)
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

        cursor.execute(f"""SELECT min(completed_at) as min_completion_time FROM event WHERE 
                           paragraph_id={paragraph_id} AND word_index=(paragraph_length-1) LIMIT 1;""")
        result = cursor.fetchone()

        if len(result) == 0:
            min_completion_time = 0
        else:
            min_completion_time = result['min_completion_time']

        connection.commit()
    return json.dumps({"next_count": next_count, "paragraph_id": paragraph_id, "words": words, "ipas": ipas, "stems": stems, "min_completion_time": min_completion_time, "skipwords": list(skipwords), "word_mapping": word_mapping})


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


@app.route('/get_stats/<user_id>', methods=['POST'])
def get_stats(user_id):
    results = {"word_stats": [], "daily_stats": []}
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT user_id, session_id, word_index, word, duration, completed_at, created_at FROM event 
                WHERE user_id={user_id}"""
        )
        result = cursor.fetchall()
        words = pd.DataFrame(result)

        if len(words) == 0:
            words = pd.DataFrame(columns=["user_id", "session_id", "word_index", "word", "duration", \
                                          "completed_at", "created_at"])

        # compute daily statistics
        words["date"] = words.created_at.map(lambda x: x.strftime("%Y-%m-%d"))
        daily_stats = words.groupby("date").apply(lambda row: pd.Series({
            "duration": row["duration"].mean(), 
            "word_count": len(row)
        })).reset_index()
        daily_stats.sort_values("date", inplace=True)

        for _, row in daily_stats.tail(20).iterrows():
            results["daily_stats"] += [[row["date"], row["duration"], row["word_count"]]]
        if results["daily_stats"]:
            words = words[words.date >= results["daily_stats"][0][0]].copy()

        # compute word statistics
        cursor.execute(
            f"""select session_id, completed_at, word_index, word
                FROM final_sent WHERE user_id={user_id} AND completed_at>0 and word!=''"""
        )
        result = cursor.fetchall()
        final_sent_words = pd.DataFrame(result)

        if len(final_sent_words) == 0:
            combined_words = words[["word", "duration"]].copy()
        else:
            final_sent_words = final_sent_words.sort_values(["session_id", "completed_at"])
            final_sent_words = final_sent_words.groupby("session_id").last().reset_index()
            word_sessions = words.groupby("session_id")["completed_at"].max().reset_index()
            final_sent_words = final_sent_words.merge(word_sessions, on="session_id", how="left")
            final_sent_words.completed_at_y.fillna(0, inplace=True)
            final_sent_words = final_sent_words[final_sent_words.completed_at_x > \
                                                final_sent_words.completed_at_y]
            final_sent_words["duration"] = final_sent_words.completed_at_x - \
                                           final_sent_words.completed_at_y
            combined_words = pd.concat([words[["word", "duration"]], 
                                        final_sent_words[["word", "duration"]]])

        if len(combined_words) == 0:
            return json.dumps(results)
            
        combined_words["word"] = combined_words.word.map(normalize)
        word_stats = combined_words.groupby("word")["duration"].mean().reset_index()
        word_stats = word_stats.sort_values("duration", ascending=False)
        word_stats = word_stats[~word_stats.word.isin(skipwords)]

        for _, row in word_stats.head(20).iterrows():
            results["word_stats"] += [[row["word"], row["duration"]]]
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
            probs = np.array([prob for [_, prob] in results["word_stats"][:top]])
            top = min(top, len(probs))
            probs = probs / sum(probs)
            select_indices = set(np.random.choice(list(range(top)), size=select, replace=False, p=probs))

            select_words = []
            un_select_words = []
            for i in range(top):
                if i in select_indices:
                    select_words += [results["word_stats"][i][0]]
                else:
                    un_select_words += [results["word_stats"][i][0]]
            query = " ".join(select_words)
            #query = "(" + " ".join(select_words) + ") AND !(" + " ".join(un_select_words) + ") AND (level: " + str(level) + ")"
        morphemes = []
        for word in query.split():
            morphemes += [morpheme for ipa in transcribe(word) for morpheme in ipa]
        morphemes = normalize_ipa(" ".join(morphemes))
        print(query)
        print(morphemes)

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
                                        "query": f"\"{morphemes}\"",
                                        "fuzziness": "AUTO"
                                    }
                                }
                            },
                            {
                              "match": {
                                "content": {
                                        "query": f"\"{query}\"",
                                        "fuzziness": "AUTO"
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
