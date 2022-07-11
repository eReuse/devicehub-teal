import json
import sys


def get_old_smbios_version(snapshot):
    capabilities = snapshot.get('debug', {}).get('lshw', {}).get('capabilities', {})
    for x in capabilities.values():
        if "SMBIOS version" in x:
            e = x.split("SMBIOS version ")[1].split(".")
            if int(e[0]) < 3 and int(e[1]) < 6:
                return True
    return False


def get_uuid(snapshot):

    return (
        snapshot.get('debug', {}).get('lshw', {}).get('configuration', {}).get('uuid')
    )


def main():
    _file = sys.argv[1]
    with open(_file) as file_snapshot:
        snapshot = json.loads(file_snapshot.read())

    if get_old_smbios_version(snapshot):
        return

    system_uuid = get_uuid(snapshot)
    if system_uuid:
        print("{};{}".format(system_uuid, snapshot['uuid']))


if __name__ == '__main__':
    main()
