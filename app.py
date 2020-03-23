import flask
from flask import Flask, render_template
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/encounterData', methods=['POST'])
def encounterData():
    selectedBoss = flask.request.json['Boss']

    encounters = {}
    files = os.listdir('data')
    for file in files:
        if selectedBoss+'.json' == file.split('_')[-1]:
            with open('data/'+file) as json_file:
                fileURL = file.replace('.json', '')
                encounters[fileURL] = json.load(json_file)

    return flask.jsonify(encounters)


if __name__ == '__main__':
    app.run(host='192.168.0.4',
            ssl_context=('/etc/letsencrypt/live/andrexia.com/fullchain.pem',
                         '/etc/letsencrypt/live/andrexia.com/privkey.pem'))
