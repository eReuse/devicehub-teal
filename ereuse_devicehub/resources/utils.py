from hashids import Hashids
from decouple import config

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
SECRET = config('TAG_HASH', '')
hashcode = Hashids(SECRET, min_length=5, alphabet=ALPHABET)
