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

time_formt = '%Y-%m-%dT%H:%M:%S.%f'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

debug = False
app = Flask(__name__, static_url_path='')
app.config["LOG_TYPE"] = "CSV"
app.secret_key = b'\xd8t\xf3\x0b\x05\\\xc8\x80a\x8a\xe5\x16 \xd9\xf4d\x1dd\xa5\x9a\x82\xb6kh'


Log(app)

def make_conn():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='root',
                           db='speaktests',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

def normalize(word):
    word = regex.sub("[\.,\"'’]", "", word)
    if word == "I":
        return word
    return word.lower()

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


@app.route('/retrieve_statistics/<user_id>', methods=['POST'])
def retrieve_statistics(user_id):
    results = {"word_stats": [], "daily_stats": []}

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT session_id, paragraph_id, word_index, start_time FROM event WHERE user_id={user_id}"""
        )
        result = cursor.fetchall()
        sessions = pd.DataFrame(result)
        
        # compute average time per (paragraph_id, word_index)
        sessions.sort_values(['session_id', 'start_time'], inplace=True)
        sessions['duration'] = sessions.groupby(['session_id'])['start_time'].transform(lambda x: (x.shift(-1) - x))
        sessions['duration'] = sessions['duration'].map(lambda x: x.total_seconds())
        sessions.dropna(inplace=True)
        
        # compute daily statistics
        sessions["date"] = sessions.start_time.map(lambda x: x.strftime("%Y-%m-%d"))
        daily_stats = sessions.groupby("date")["duration"].mean().reset_index()
        daily_stats["word_count"] = list(sessions.groupby("date")["duration"].count())
        daily_stats.sort_values("date", inplace=True)

        for _, row in daily_stats.head(20).iterrows():
            results["daily_stats"] += [[row["date"], row["duration"], row["word_count"]]]

        # compute word statistics
        word_stats = sessions.groupby(["paragraph_id", "word_index"])["duration"].mean().reset_index()
        word_stats = word_stats.sort_values("duration", ascending=False)

        if len(word_stats) == 0:
            return json.dumps(results)
        
        word_stats = word_stats.head(200)
        word_stats["word"] = word_stats.apply(lambda row: find_word(row["paragraph_id"], int(row["word_index"])), axis=1)
        word_stats = word_stats.groupby("word")["duration"].mean().reset_index()
        word_stats.sort_values("duration", inplace=True, ascending=False)

        for _, row in word_stats.head(20).iterrows():
            results["word_stats"] += [[row["word"], row["duration"]]]
    return json.dumps(results)


@app.route('/event/', methods=['POST'])
def log_event():
    data = request.get_json()
    user_id, session_id, paragraph_id, index = data["user_id"], data["session_id"], data["paragraph_id"], data["index"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO event (user_id, session_id, paragraph_id, word_index) "
                       f"VALUES ({user_id}, \"{session_id}\", {paragraph_id}, {index})")
        connection.commit()
    return ""


@app.route('/final_sent/', methods=['POST'])
def log_final_sent():
    data = request.get_json()
    user_id, session_id, paragraph_id, sentence = data["user_id"], data["session_id"], data["paragraph_id"], data["sentence"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO final_sent (user_id, session_id, paragraph_id, sentence) "
                       f"VALUES ({user_id}, \"{session_id}\", {paragraph_id}, \"{sentence}\")")
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


@app.route('/retrieve_history/<user_id>/<paragraph_id>', methods=['POST'])
def retrieve_history(user_id, paragraph_id):
    sessions = []

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM paragraph WHERE id={paragraph_id}')
        paragraph = cursor.fetchone()
        length = len(paragraph["text"].split())
        
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


@app.route('/retrieve_paragraph/<id>', methods=['POST'])
def retrieve_paragraph(id):
    text = ""

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM paragraph WHERE id={id};")
        text = cursor.fetchone()["text"]
        connection.commit()
    return json.dumps({"paragraph": text})


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
    app.run(host="0.0.0.0", port=443, debug=True, ssl_context=('certificate.crt', 'private.key',))
