import flask
from flask import Flask, render_template, request
from flask_cors import CORS
import json
import os
import dpsReportUtils
import requests

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/availableBosses', methods=['GET'])
def availableBosses():
    files = [x.split('_')[1].replace('.json', '') for x in os.listdir('data')]
    files = {'bosses': list(set(files))}
    return flask.jsonify(files)


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


@app.route("/upload", methods=["GET", "POST"])
def uploadPage():
    if request.method == 'POST':
        if request.files:
            log = request.files['file']
            log.save('uploads/'+log.filename)
            dpsReportUtils.logParser(log.filename)

            return 'Success'

    return render_template('upload.html')


if __name__ == '__main__':
    app.run(host='192.168.0.19')
