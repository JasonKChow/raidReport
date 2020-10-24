import app


def massDBImport(id_file, db):
    # Get a list of IDs
    with open(id_file, 'r') as f:
        idList = f.readlines()

    # Strip \n
    idList = [url[0:-1] for url in idList]

    # Process each permalink
    for permalink in idList:
        print(f'Working on {permalink}')
        app.add_log(permalink, db)


if __name__ == '__main__':
    permalinks = [
        'https://dps.report/lW4P-20201011-013005_ai',
        'https://dps.report/Ela3-20201012-010240_ai',
        'https://dps.report/kUqE-20201012-005701_ai',
        'https://dps.report/576S-20201011-012144_ai'
    ]

    for permalink in permalinks:
        app.add_log(permalink, app.db)
