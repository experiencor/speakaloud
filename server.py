from flask import Flask, request, send_file, make_response, session
import random, string, os, requests
import flask
import requests
import json
import logging
from bs4 import BeautifulSoup
import pymysql.cursors
import datetime
import regex
import pandas as pd
from dateutil import parser
from flask_web_log import Log

app = Flask(__name__, static_url_path='')
app.secret_key = b'\xd8t\xf3\x0b\x05\\\xc8\x80a\x8a\xe5\x16 \xd9\xf4d\x1dd\xa5\x9a\x82\xb6kh'

# set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app.config["LOG_TYPE"] = "CSV"
Log(app)


def make_conn():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='root',
                           db='speaktests2',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)


def normalize(word):
    if word in ["I", "I'm"]:
        return word
    return regex.sub("[\.,\"'’]", "", word).lower()


def find_word(paragraph_id, word_index):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT text FROM paragraph WHERE id={paragraph_id}"""
        )
        text = cursor.fetchall()
        
        if not text:
            return ""
        
        text = text[0]["text"].split()
        if word_index >= len(text):
            return ""
        
        return normalize(text[word_index])
    return ""


@app.route('/')
@app.route('/gymnastics')
@app.route('/homepage.html')
@app.route('/index.html')
def root():
    return app.send_static_file('index.html')


@app.route('/statistics')
def statistics():
    return app.send_static_file('statistics.html')


@app.route('/get_stats/<user_id>', methods=['POST'])
def get_stats(user_id):
    results = {"word_stats": [], "daily_stats": []}

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT user_id, session_id, word, duration, created_at FROM event WHERE user_id={user_id}"""
        )
        result = cursor.fetchall()
        sessions = pd.DataFrame(result)
        
        # compute daily statistics
        sessions["date"] = sessions.created_at.map(lambda x: x.strftime("%Y-%m-%d"))
        daily_stats = sessions.groupby("date")["duration"].mean().reset_index()
        daily_stats["word_count"] = list(sessions.groupby("date")["duration"].count())
        daily_stats.sort_values("date", inplace=True)

        for _, row in daily_stats.head(20).iterrows():
            results["daily_stats"] += [[row["date"], row["duration"], row["word_count"]]]

        # compute word statistics
        word_stats = sessions.groupby(["word"])["duration"].mean().reset_index()
        word_stats = word_stats.sort_values("duration", ascending=False)

        if len(word_stats) == 0:
            return json.dumps(results)
        
        for _, row in word_stats.head(20).iterrows():
            results["word_stats"] += [[row["word"], row["duration"]]]
    return json.dumps(results)


@app.route('/event/', methods=['POST'])
def log_event():
    data = request.get_json()
    user_id, paragraph_id, session_id, word_index, word, duration, completed_at = \
        data["user_id"], data["paragraph_id"], data["session_id"], data["word_index"], data["duration"], data["completed_at"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO event (user_id, paragraph_id, session_id, word_index, word, duration, completed_at) "
                       f"VALUES ({user_id}, \"{paragraph_id}\", {session_id}, {word_index}, \"{word}\", {completed_at})")
        connection.commit()
    return ""


@app.route('/final_sent/', methods=['POST'])
def log_final_sent():
    data = request.get_json()
    user_id, paragraph_id, session_id, sentence, completed_at = \
        data["user_id"], data["paragraph_id"], data["session_id"], data["sentence"], data["completed_at"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO final_sent (user_id, session_id, paragraph_id, sentence, completed_at) "
                       f"VALUES ({user_id}, \"{session_id}\", {paragraph_id}, \"{sentence}\", completed_at)")
        connection.commit()
    return ""


@app.route('/create_user/<username>', methods=['POST'])
def create_user(username):
    user_id = -1

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO user (name) VALUES (\"{username}\")")
        user_id = cursor.lastrowid
        connection.commit()
    return json.dumps({"user_id": user_id})


@app.route('/get_paragraph/<user_id>', methods=['POST'])
def get_paragraph(user_id):
    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT next_paragraph_id FROM user WHERE id={user_id}")
        paragraph_id = cursor.fetchone()["next_paragraph_id"]

        cursor.execute(f"SELECT * FROM paragraph WHERE id={paragraph_id};")
        content = cursor.fetchone()["content"]
        connection.commit()
    return json.dumps({"paragraph_id": paragraph_id, "content": content})


@app.route('/get_history/<user_id>/<paragraph_id>', methods=['POST'])
def get_history(user_id, paragraph_id):
    sessions = []

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM paragraph WHERE id={paragraph_id}')
        paragraph = cursor.fetchone()
        length = len(paragraph["content"].split())
        
        cursor.execute(
            f"""SELECT * FROM (
                SELECT session_id, min(word_index) as min_idx, max(word_index) as max_idx, 
                min(start_time) as start_time, max(start_time) as end_time FROM event WHERE 
                user_id={user_id} AND paragraph_id={paragraph_id} GROUP BY session_id
            ) as innerTable WHERE max_idx={length} and min_idx=0;
            """
        )
        result = cursor.fetchall()
        sessions = pd.DataFrame(result)

        if len(sessions) == 0:
            return "[]"

        sessions["duration"] = sessions.apply(lambda row: (row.end_time - row.start_time).total_seconds(), axis=1)
        sessions = sessions.sort_values("start_time")
        connection.commit()
    return json.dumps(list(json.loads(sessions.transpose().to_json()).values()))


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
    #app.run(host="0.0.0.0", port=80, debug=True)
    #app.run(host="0.0.0.0", ssl_context='adhoc')
    app.run(host="0.0.0.0", port=443, ssl_context=('certificate.crt', 'private.key',))
