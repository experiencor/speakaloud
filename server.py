from flask import Flask, request, send_file, make_response, session
import random, string, os, requests
import flask
import requests
import json
import logging
from bs4 import BeautifulSoup
import pymysql.cursors
import datetime
import pandas as pd
from dateutil import parser

time_formt = '%Y-%m-%dT%H:%M:%S.%f'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

debug = False
app = Flask(__name__, static_url_path='')
app.secret_key = b'\xd8t\xf3\x0b\x05\\\xc8\x80a\x8a\xe5\x16 \xd9\xf4d\x1dd\xa5\x9a\x82\xb6kh'


def make_conn():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='root',
                           db='speaktests',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)


@app.route('/')
@app.route('/homepage.html')
@app.route('/index.html')
def root():
    return app.send_static_file('index.html')


@app.route('/log/', methods=['POST'])
def log():
    data = request.get_json()
    user_id, session_id, paragraph_id, index = data["user_id"], data["session_id"], data["paragraph_id"], data["index"]

    connection = make_conn()
    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO event (user_id, session_id, paragraph_id, word_index) VALUES ({user_id}, \"{session_id}\", {paragraph_id}, {index})")
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
        
        cursor.execute(f'SELECT session_id, min(word_index) as min_idx, max(word_index) as max_idx, min(start_time) as start_time, max(start_time) as end_time FROM event WHERE user_id={user_id} AND paragraph_id={paragraph_id} GROUP BY session_id;')
        result = cursor.fetchall()
        sessions = pd.DataFrame(result)

        if len(sessions) == 0:
            return "[]"
        sessions = sessions[sessions.max_idx == length]
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
