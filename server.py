from flask import Flask, request, send_file, make_response, session
import random, string, os, requests
import flask
import requests
import json
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

debug = False
app = Flask(__name__, static_url_path='')
app.secret_key = b'\xd8t\xf3\x0b\x05\\\xc8\x80a\x8a\xe5\x16 \xd9\xf4d\x1dd\xa5\x9a\x82\xb6kh'


@app.route('/')
@app.route('/homepage.html')
@app.route('/index.html')
def root():
    return app.send_static_file('index.html')

@app.route('/transcribe/', methods=['POST'])
def transcribe():
    word = request.get_json()["word"]
    
    response = requests.post(
        "https://www.phonetizer.com/phonetizer/default/call/jsonrpc?nocache=1605357656222",
        data = '{"service":"", "method":"transcribe", "id":5, "params":["' + word + '", "British", false]}'
    )

    soup = BeautifulSoup(json.loads(response.content)["result"])
    ipa = soup.get_text().strip().split("\n")[1]

    return json.dumps({"ipa": ipa})

if __name__ == "__main__":
    #app.run(host="0.0.0.0", debug=True)
    app.run(host="0.0.0.0", port=8000, debug=True)
    #app.run(host="0.0.0.0", ssl_context='adhoc')
    #app.run(host="0.0.0.0", port=443, debug=True, ssl_context=('fullchain.pem', 'privkey.pem',))
