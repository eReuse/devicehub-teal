for i in `ls ../snapshots/*/*.json`; do python examples/extract_uuid.py $i; done > system_uuids.csv
