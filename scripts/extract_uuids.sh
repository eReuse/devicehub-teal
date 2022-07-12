for i in `ls ../snapshots/*/*.json`; do python scripts/extract_uuid.py $i; done > system_uuids.csv
