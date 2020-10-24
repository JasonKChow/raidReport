import flask
from flask import Flask, render_template, request
from flask_cors import CORS
import json
import os
from dpsReportUtils import logParser, bossIDs
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
import sys
from dataclasses import dataclass

with open('dbConfig.json') as f:
    config = json.load(f)

dbURI = f"mysql+pymysql://{config.get('user')}:" \
        f"{config.get('password')}@" \
        f"{config.get('host')}:" \
        f"{config.get('port')}/" \
        f"{config.get('db')}"

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = dbURI
db = SQLAlchemy(app)


@dataclass
class Encounter(db.Model):
    id: str
    bossID: int
    date: int
    uploadDate: int
    success: bool
    duration: int
    totalDPS: int
    isCM: bool
    permalink: str

    __tablename__ = 'encounters'

    id = db.Column(db.String(100), primary_key=True)
    bossID = db.Column(db.Integer)
    date = db.Column(db.Integer)
    uploadDate = db.Column(db.Integer)
    success = db.Column(db.Boolean)
    duration = db.Column(db.Integer)
    totalDPS = db.Column(db.Integer)
    isCM = db.Column(db.Boolean)
    permalink = db.Column(db.String(100))

    playerEntries = db.relationship('PlayerEntry', back_populates='encounter')

    def __repr__(self):
        return f"<Encounter(id={self.id}, " \
               f"date={self.date}, " \
               f"permalink={self.permalink})>"


@dataclass
class PlayerEntry(db.Model):
    accountName: str
    encID: str
    specialization: str
    weapons1Main: str
    weapons1Off: str
    weapons2Main: str
    weapons2Off: str
    buildStats: str
    subgroup: int
    totalDPS: int
    powerDPS: int
    condiDPS: int

    __tablename__ = 'playerEntries'

    accountName = db.Column(db.String(24), primary_key=True)
    encID = db.Column(db.String(100), db.ForeignKey('encounters.id'),
                      primary_key=True)

    specialization = db.Column(db.String(24))
    weapons1Main = db.Column(db.String(24), nullable=True)
    weapons1Off = db.Column(db.String(24), nullable=True)
    weapons2Main = db.Column(db.String(24), nullable=True)
    weapons2Off = db.Column(db.String(24), nullable=True)
    buildStats = db.Column(db.String(24))

    subgroup = db.Column(db.Integer)
    totalDPS = db.Column(db.Integer)
    powerDPS = db.Column(db.Integer)
    condiDPS = db.Column(db.Integer)

    encounter = db.relationship('Encounter', back_populates='playerEntries')

    def __repr__(self):
        return f"<PlayerEntry(accountName={self.accountName}, " \
               f"encID={self.encID}, " \
               f"specialization={self.specialization}, " \
               f"totalDPS={self.totalDPS})>"


def uploadLog(fileName, db):
    userToken = 'kltu2he26nvdrk0451atc1s2p2'
    params = {'json': 1, 'userToken': userToken}

    # Upload log
    print('Uploading')
    file = {'file': open('uploads/'+fileName, 'rb')}
    upload = requests.post(url='https://dps.report/uploadContent',
                           files=file,
                           data=params)
    upload.encoding = 'UTF-8'
    meta = json.loads(upload.content)
    print('Upload complete')

    add_log(meta, db)

    os.remove('uploads/' + fileName)

def add_log(inp, db):
    if type(inp) == str:
        # Probably a permalink
        # Get meta data
        meta = requests.post(url='https://dps.report/getUploadMetadata',
                             params={'permalink': inp})
        meta.encoding = 'UTF-8'
        meta = json.loads(meta.text)
    else:
        # It's probably the metadata
        meta = inp

    # Get log data
    r = requests.post(url='https://dps.report/getJson',
                      params={'permalink': meta.get('permalink')})
    r.encoding = 'UTF-8'
    log = json.loads(r.text)

    # Check if this is a valid id
    if log.get('triggerID') not in bossIDs.keys():
        print('Encounter not in boss IDs')
        sys.stdout.flush()
        return None

    # Conjured Amalgamate fix
    if log['fightName'] == 'Conjured Amalgamate':
        log['players'] = [player for player in log['players']
                          if not player['profession'] == 'Sword']

    # Twins fix
    if log['fightName'] == 'Twin Largos':
        for i in range(len(log['players'])):
            log['players'][i]['dpsTargets'][0][0]['dps'] += \
                log['players'][i]['dpsTargets'][1][0]['dps']
            log['players'][i]['dpsTargets'][0][0]['powerDps'] += \
                log['players'][i]['dpsTargets'][1][0]['powerDps']
            log['players'][i]['dpsTargets'][0][0]['condiDps'] += \
                log['players'][i]['dpsTargets'][1][0]['condiDps']

    # Only save if log is success
    if not (success := log.get('success')):
        print('Encounter failed, not saving.')
        sys.stdout.flush()
        return None

    # Fill in encounter meta data
    if (uniqueID := meta['encounter'].get('uniqueId')) is None:
        uniqueID = meta.get('permalink')

    # Check whether or not this is unique
    if Encounter.query.filter_by(id=uniqueID).scalar() is not None:
        print('This has already been uploaded, not saving.')
        sys.stdout.flush()
        return None

    # Get easy info
    bossID = log.get('triggerID')
    date = int(datetime.strptime(log.get('timeEnd')+'00',
                                 '%Y-%m-%d %H:%M:%S %z').timestamp())
    uploadDate = meta.get('uploadTime')
    isCM = meta['encounter'].get('isCm')
    permalink = meta.get('permalink')

    # Parse duration
    duration = 0
    for piece in log.get('duration').split(' '):
        if 'ms' in piece:  # Round milliseconds
            duration += round(float(piece[:-2]) / 1000)
        elif 'm' in piece:  # Minutes
            duration += int(piece[:-1]) * 60
        elif 's' in piece:  # Seconds
            duration += int(piece[:-1])

    # Get total DPS
    totalDPS = sum([player['dpsTargets'][0][0].get('dps')
                    for player in log.get('players')])

    # Add encounter instance
    enc = Encounter(
        id=uniqueID,
        bossID=bossID,
        date=date,
        uploadDate=uploadDate,
        success=success,
        duration=duration,
        totalDPS=totalDPS,
        isCM=isCM,
        permalink=permalink
    )
    db.session.add(enc)

    # Build playerEntries
    players = log.get('players')

    # Get relevant for each person
    playerData = []
    for player in players:
        # Determine build
        buildStats = []
        if player.get('healing') != 0 or player.get('concentration') != 0:
            if player.get('healing') >= player.get('concentration'):
                buildStats += ['healing']
            else:
                buildStats += ['concentration']
        else:
            if player.get('condition') > 0:
                buildStats += ['condition']
            else:
                buildStats += ['power']

        if player.get('toughness') == 10:
            buildStats += ['toughness']

        buildStats = '-'.join(buildStats)

        playerData += [PlayerEntry(
            accountName=player.get('account'),
            encID=uniqueID,
            specialization=player.get('profession'),
            weapons1Main=player.get('weapons')[0],
            weapons1Off=player.get('weapons')[1],
            weapons2Main=player.get('weapons')[2],
            weapons2Off=player.get('weapons')[3],
            buildStats=buildStats,
            subgroup=player.get('group'),
            totalDPS=player.get('dpsTargets')[0][0].get('dps'),
            powerDPS=player.get('dpsTargets')[0][0].get('powerDps'),
            condiDPS=player.get('dpsTargets')[0][0].get('condiDps')
        )]
    db.session.add_all(playerData)

    # Commit all data from this log
    db.session.commit()


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
            logParser(log.filename)

            return 'Success'

    return render_template('upload.html')

@app.route("/uploadV2", methods=["GET", "POST"])
def uploadPageV2():
    if request.method == 'POST':
        if request.files:
            log = request.files['file']
            log.save('uploads/'+log.filename)
            uploadLog(log.filename, db)

            return 'Success'

    return render_template('uploadV2.html')

@app.route('/encounterDataV2', methods=['GET'])
def encounterDataV2():
    selectedBoss = flask.request.args.get('bossID')

    data = Encounter.query.filter_by(bossID=selectedBoss).all()

    return flask.jsonify(data)


@app.route('/encounterEntries', methods=['GET'])
def entryData():
    encID = flask.request.args.get('ID')

    data = PlayerEntry.query.filter_by(encID=encID).all()

    return flask.jsonify(data)

if __name__ == '__main__':
    test = Encounter.query.filter_by(bossID=15438).all()
