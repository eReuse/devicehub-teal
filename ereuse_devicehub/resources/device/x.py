import csv
import json

with open('manufacturers.csv', 'w') as o:
    writer = csv.writer(o)
    with open('manufacturers.json') as i:
        for x in json.load(i):
            writer.writerow([x['name'], x['url'], x['logo'] if x.get('logo', None) else None])
