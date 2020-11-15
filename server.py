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

connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             db='speaktests',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


def reset_connection():
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             db='speaktests',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

def compute_duration(rows):
    timestamps = list(rows["start_time"])
    min_time, max_time = min(timestamps), max(timestamps)
    duration = parser.parse(max_time) - parser.parse(min_time)
    duration = duration.total_seconds()
    
    return pd.Series({
        "start_time": min_time,
        "end_time": min_time,
        "log_count": len(rows),
        "duration": duration
    })


@app.route('/')
@app.route('/homepage.html')
@app.route('/index.html')
def root():
    return app.send_static_file('index.html')

@app.route('/log/', methods=['POST'])
def log():
    data = request.get_json()
    user_id, trial_id, passage_id, indx = data["user_id"], data["trial_id"], data["passage_id"], data["index"]
    start_time = datetime.datetime.now().strftime(time_formt)
    print(start_time)

    with connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO log (user_id, trial_id, passage_id, indx, start_time) VALUES ({user_id}, \"{trial_id}\", {passage_id}, {indx}, \"{start_time}\")")
    connection.commit()
    return ""

@app.route('/retrieve_history/', methods=['POST'])
def retrieve_history():
    reset_connection()
    data = request.get_json()
    user_id, passage_id = data["user_id"], data["passage_id"]

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM passage WHERE id={passage_id}')
        passage = cursor.fetchone()
        length = len(passage["text"].split())
        
        cursor.execute(f'SELECT trial_id, min(indx) as min_idx, max(indx) as max_idx, min(start_time) as start_time, max(start_time) as end_time FROM log WHERE user_id={user_id} AND passage_id={passage_id} GROUP BY trial_id;')
        result = cursor.fetchall()
        sessions = pd.DataFrame(result)
        sessions = sessions[sessions.max_idx == length]

        if len(sessions) == 0:
            return "[]"

        sessions["duration"] = sessions.apply(lambda row: (parser.parse(row.end_time) - 
            parser.parse(row.start_time)).total_seconds(), axis=1)
        sessions = sessions.sort_values("start_time")

        return json.dumps(list(json.loads(sessions.transpose().to_json()).values()))

@app.route('/retrieve_passage/', methods=['POST'])
def retrieve_passage():
    data = request.get_json()
    passage_id = data["id"]

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM passage WHERE id={passage_id};")
        result = cursor.fetchone()

        return json.dumps({"passage": result["text"]})

@app.route('/transcribe/', methods=['POST'])
def transcribe():
    data = request.get_json()
    word = data["word"]
    
    response = requests.post(
        "https://www.phonetizer.com/phonetizer/default/call/jsonrpc?nocache=1605357656222",
        data = '{"service":"", "method":"transcribe", "id":5, "params":["' + word + '", "British", false]}'
    )

    soup = BeautifulSoup(json.loads(response.content)["result"])
    ipa = soup.get_text().strip().split("\n")[1]

    return json.dumps({"ipa": ipa})

if __name__ == "__main__":
    #app.run(host="0.0.0.0", debug=True)
    #app.run(host="0.0.0.0", port=80, debug=True)
    #app.run(host="0.0.0.0", ssl_context='adhoc')
    app.run(host="0.0.0.0", port=443, debug=True, ssl_context=('certificate.crt', 'private.key',))
