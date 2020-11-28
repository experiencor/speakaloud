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
import regex
import base64
import pandas as pd
from dateutil import parser
from flask_web_log import Log

# set up the app
app = Flask(__name__, static_url_path='')
app.secret_key = b'\xd8t\xf3\x0b\x05\\\xc8\x80a\x8a\xe5\x16 \xd9\xf4d\x1dd\xa5\x9a\x82\xb6kh'

# set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app.config["LOG_TYPE"] = "CSV"
Log(app)


# utility functions
def make_conn():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='root',
                           db='speaktests',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)


def normalize(word):
    if word in ["I", "I'm"]:
        return word
    return regex.sub("[,\.!]", "", word).lower()


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
        cursor.execute(f"INSERT INTO user (username) VALUES (\"{username}\")")
        user_id = cursor.lastrowid
        connection.commit()
    return json.dumps({"user_id": user_id})


@app.route('/get_paragraph_for_user/<user_id>', methods=['POST'])
def get_paragraph_for_user(user_id):
    user_id = int(user_id)
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT next_paragraph_id FROM user WHERE id={user_id} LIMIT 1;")
        paragraph_id = cursor.fetchone()["next_paragraph_id"]

        cursor.execute(f"SELECT * FROM paragraph WHERE id={paragraph_id} LIMIT 1;")
        result = cursor.fetchone()
        content = result["content"]
        ipa = decode64(result["ipa"])

        cursor.execute(f"""SELECT min(completed_at) as min_completion_time FROM event WHERE 
                           paragraph_id={paragraph_id} AND word_index=(paragraph_length-1) LIMIT 1;""")
        result = cursor.fetchone()

        if len(result) == 0:
            min_completion_time = 0
        else:
            min_completion_time = result['min_completion_time']

        connection.commit()
    return json.dumps({"paragraph_id": paragraph_id, "content": content, "ipa": ipa, "min_completion_time": min_completion_time})


@app.route('/get_history/<user_id>/<paragraph_id>', methods=['POST'])
def get_history(user_id, paragraph_id):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT content FROM paragraph WHERE id={paragraph_id} LIMIT 1;')
        paragraph = cursor.fetchone()
        length = len(paragraph["content"].split())

        cursor.execute(
            f"""SELECT completed_at, created_at FROM event WHERE 
                user_id={user_id} AND paragraph_id={paragraph_id} AND word_index={length-1}
            """
        )
        sessions = pd.DataFrame(cursor.fetchall())
        sessions.rename(columns={"completed_at": "duration"}, inplace=True)
        connection.commit()
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

        for _, row in daily_stats.head(20).iterrows():
            results["daily_stats"] += [[row["date"], row["duration"], row["word_count"]]]

        # compute word statistics
        cursor.execute(
            f"""select o.session_id, o.completed_at, o.word_index, o.word
                FROM final_sent o
                    LEFT JOIN final_sent b
                        ON o.session_id = b.session_id AND o.completed_at < b.completed_at
                WHERE o.user_id={user_id} AND b.completed_at is NULL AND o.word!=''"""
        )
        result = cursor.fetchall()
        final_sent_words = pd.DataFrame(result)

        if len(final_sent_words) == 0:
            combined_words = words[["word", "duration"]].copy()
        else:
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


@app.route('/transcribe/<word>', methods=['POST'])  
def transcribe(word):
    response = requests.post(
        "https://www.phonetizer.com/phonetizer/default/call/jsonrpc?nocache=1605357656222",
        data = '{"service":"", "method":"transcribe", "id":5, "params":["' + word + '", "British", false]}'
    )

    soup = BeautifulSoup(json.loads(response.content)["result"], features="html.parser")
    ipa = soup.get_text().strip().split("\n")[1]
    return json.dumps({"ipa": ipa})


if __name__ == "__main__":
    #app.run(host="0.0.0.0", debug=True)
    #app.run(host="0.0.0.0", port=5000, debug=True)
    #app.run(host="0.0.0.0", ssl_context='adhoc')
    app.run(host="0.0.0.0", port=443, ssl_context=('certificate.crt', 'private.key',))
