import requests
import json
import os
import shutil
import time


def logUploader(overwrite=False):
    userToken = 'kltu2he26nvdrk0451atc1s2p2'
    params = {'json': 1, 'userToken': userToken}

    if 'logArchive' not in os.listdir('.'):
        os.mkdir('logArchive')

    if 'trash' not in os.listdir('.'):
        os.mkdir('trash')

    # Check for ids
    if ('ids.txt' not in os.listdir('.')) or overwrite:
        idFile = open('ids.txt', 'w')
    else:
        idFile = open('ids.txt', 'a')

    # Iterate through bosses
    bosses = os.listdir('logs')
    for boss in bosses:
        print('Working on {}'.format(boss))
        logs = os.listdir('logs/{}'.format(boss))

        if boss not in os.listdir('logArchive'):
            os.mkdir('logArchive/{}'.format(boss))

        if boss not in os.listdir('trash'):
            os.mkdir('trash/{}'.format(boss))

        for logFile in logs:
            file = {'file': open('logs/{}/{}'.format(boss, logFile), 'rb')}

            print('Uploading log: {}'.format(logFile))
            upload = requests.post(url='https://dps.report/uploadContent',
                                   files=file,
                                   data=params)

            log = json.loads(upload.content)

            # Save IDs for successes
            if log['encounter']['success']:
                idFile.write(log['permalink']+'\n')
                print('Saving log: {}'.format(log['permalink']))

                # Move file to archive
                os.rename('logs/{}/{}'.format(boss, logFile),
                          'logArchive/{}/{}'.format(boss, logFile))
            else:
                print('Not a success, trashing!')
                os.rename('logs/{}/{}'.format(boss, logFile),
                          'trash/{}/{}'.format(boss, logFile))

    idFile.close()


def dataBuilder(overwrite=False):
    # Create data directory
    if 'data' in os.listdir('.'):
        if overwrite:
            shutil.rmtree('data')
            os.mkdir('data')
    else:
        os.mkdir('data')

    # Get list of data files
    dataFiles = [file[:-5] for file in os.listdir('data')]

    # Get a list of IDs
    idFile = open('ids.txt', 'r')
    idList = idFile.readlines()
    idFile.close()

    # Iterate through IDs
    for logID in idList:
        permalink = logID[:-1]
        fileName = permalink.replace('https://dps.report/', '')
        if fileName not in dataFiles:
            print('Processing '+permalink)
            with open('data/{}.json'.format(fileName), 'w') as f:
                json.dump(dataPreProcess(permalink), f)


def dataPreProcess(permalink):
    # Get json
    jsonData = requests.post(url='https://dps.report/getJson',
                             params={'permalink': permalink})
    data = json.loads(jsonData.text)

    # Remove extra info
    keysToKeep = ['fightName', 'duration', 'timeEnd', 'players']
    data = {key: data[key] for key in keysToKeep}

    data['permalink'] = permalink
    data['encID'] = permalink.replace('https://dps.report/', '')

    # Encounter duration information
    data['duration'] = ' '.join(data['duration'].split(' ')[0:2])
    encDur = [int(piece[:-1]) for piece in data['duration'].split(' ')]
    data['encSecs'] = encDur[0]*60 + encDur[1]

    # Conjured Amalgamate fix
    if data['fightName'] == 'Conjured Amalgamate':
        data['players'] = [player for player in data['players']
                           if not player['profession'] == 'Sword']

    # Twins fix
    if data['fightName'] == 'Twin Largos':
        for i in range(len(data['players'])):
            data['players'][i]['dpsTargets'][0][0]['dps'] += \
                data['players'][i]['dpsTargets'][1][0]['dps']
            data['players'][i]['dpsTargets'][0][0]['powerDps'] += \
                data['players'][i]['dpsTargets'][1][0]['powerDps']
            data['players'][i]['dpsTargets'][0][0]['condiDps'] += \
                data['players'][i]['dpsTargets'][1][0]['condiDps']

    # Total DPS information
    dps = sum([player['dpsTargets'][0][0]['dps'] for player in data['players']])
    data['teamDPS'] = dps

    # Subgroup information
    subgroups = [player['group'] for player in data['players']]
    data['subgroups'] = list(set(subgroups))
    data['subgroupCount'] = [subgroups.count(group)
                             for group in data['subgroups']]

    # Time end information
    timeStr = '%Y-%m-%d %H:%M:%S %z'
    parsedTime = time.strptime(data['timeEnd']+'00', timeStr)
    data['timeEnd'] = int(time.mktime(parsedTime))
    data['date'] = time.strftime('%m/%d/%Y, %-I:%M %p', parsedTime)

    # Filter keys
    playerKeysToKeep = ['account', 'group', 'profession', 'weapons',
                        'buildStats', 'encID', 'date', 'teamDPS',
                        'totalDPS', 'powerDPS', 'condiDPS', 'duration']
    newPlayers = []
    for player in data['players']:
        # Add redundant encounter information to players
        player['encID'] = permalink.replace('https://dps.report/', '')
        player['date'] = data['date']
        player['teamDPS'] = dps
        player['duration'] = data['duration']

        # Only save the first four weapons
        player['weapons'] = player['weapons'][0:4]

        # Save dps
        player['totalDPS'] = player['dpsTargets'][0][0]['dps']
        player['powerDPS'] = player['dpsTargets'][0][0]['powerDps']
        player['condiDPS'] = player['dpsTargets'][0][0]['condiDps']

        # Determine build
        player['buildStats'] = []
        if player['healing'] != 0 or player['concentration'] != 0:
            if player['healing'] >= player['concentration']:
                player['buildStats'] += ['healing']
            else:
                player['buildStats'] += ['concentration']
        else:
            if player['condition'] > 0:
                player['buildStats'] += ['condition']
            else:
                player['buildStats'] += ['power']

        if player['toughness'] == 10:
            player['buildStats'] += ['toughness']

        # Save player
        newPlayers += [{key: player[key] for key in playerKeysToKeep}]

    data['players'] = newPlayers

    # Sort players
    data['players'].sort(key=lambda i: (i['group'], -i['totalDPS']))

    return data


if __name__ == '__main__':
    # logUploader(overwrite=False)
    dataBuilder(overwrite=True)

