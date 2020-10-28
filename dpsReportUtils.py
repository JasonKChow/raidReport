import app


def massDBImport(id_file, db):
    db.drop_all()
    db.create_all()

    # Get a list of IDs
    with open(id_file, 'r') as f:
        idList = f.readlines()

    # Strip \n
    idList = [url[0:-1] for url in idList]

    # Process each permalink
    for permalink in idList:
        print(f'Working on {permalink}')
        app.add_log(permalink, db)


def massDBExport(id_file, db):
    # Get permalinks
    permalinks = db.session.query(app.Encounter.permalink).all()

    with open(id_file, 'w') as f:
        for permalink in permalinks:
            f.write(f'{permalink[0]}\n')


if __name__ == '__main__':
    # permalinks = [
    #     'https://dps.report/lW4P-20201011-013005_ai',
    #     'https://dps.report/Ela3-20201012-010240_ai',
    #     'https://dps.report/kUqE-20201012-005701_ai',
    #     'https://dps.report/576S-20201011-012144_ai'
    # ]
    #
    # for permalink in permalinks:
    #     app.add_log(permalink, app.db)

    # count = app.db.session.query(app.db.func.count(app.PlayerEntry.encID))\
    #     .group_by(app.PlayerEntry.encID)\
    #     .all()

    # data = app.PlayerEntry.query.join(app.Encounter, app.PlayerEntry.encID == app.Encounter.id)\
    #     .filter_by(bossID=15438)\
    #     .add_columns(app.Encounter.date, app.Encounter.duration, app.Encounter.totalDPS)\
    #     .order_by(app.PlayerEntry.totalDPS.desc())\
    #     .all()

    # massDBImport('ids.txt', app.db)

    data = app.Encounter.query.filter(app.Encounter.bossID == 15438)\
        .filter(app.Encounter.numPlayers.between(1, 10))\
        .order_by(app.Encounter.date.desc()).all()

    encounterEntries = []
    for encounter in data:
        encData = app.PlayerEntry.query.filter_by(encID=encounter.id)\
            .order_by(app.PlayerEntry.subgroup,
                      app.PlayerEntry.totalDPS.desc()).all()
        encounterEntries += [encData]
