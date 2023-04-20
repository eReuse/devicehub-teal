"""Functions to get values from dictionaries and list encoded key-value
strings with meaningful indentations.

Values obtained from these functions are sanitized and automatically
(or explicitly set) casted. Sanitization includes removing unnecessary
whitespaces and removing useless keywords (in the context of
computer hardware) from the texts.
"""

import re
from itertools import chain
from typing import Any, Iterable, Set, Type, Union
from unittest.mock import DEFAULT

import boltons.iterutils
import yaml

from ereuse_devicehub.ereuse_utils.text import clean


def dict(
    d: dict,
    path: Union[str, tuple],
    remove: Set[str] = set(),
    default: Any = DEFAULT,
    type: Type = None,
):
    """Gets a value from the dictionary and sanitizes it.

    Values are patterned and compared against sets
    of meaningless characters for device hardware.

    :param d: A dictionary potentially containing the value.
    :param path: The key or a tuple-path where the value should be.
    :param remove: Remove these words if found.
    :param default: A default value to return if not found. If not set,
                    an exception is raised.
    :param type: Enforce a type on the value (like ``int``). By default
                 dict tries to guess the correct type.
    """
    try:
        v = boltons.iterutils.get_path(d, (path,) if isinstance(path, str) else path)
    except KeyError:
        return _default(path, default)
    else:
        return sanitize(v, remove, type=type)


def kv(
    iterable: Iterable[str],
    key: str,
    default: Any = DEFAULT,
    sep=':',
    type: Type = None,
) -> Any:
    """Key-value. Gets a value from an iterable representing key values in the
    form of a list of strings lines, for example an ``.ini`` or yaml file,
    if they are opened with ``.splitlines()``.

    :param iterable: An iterable of strings.
    :param key: The key where the value should be.
    :param default: A default value to return if not found. If not set,
                    an exception is raised.
    :param sep: What separates the key from the value in the line.
                Usually ``:`` or ``=``.
    :param type: Enforce a type on the value (like ``int``). By default
                 dict tries to guess the correct type.
    """
    for line in iterable:
        try:
            k, value, *_ = line.strip().split(sep)
        except ValueError:
            continue
        else:
            if key == k:
                return sanitize(value, type=type)
    return _default(key, default)


def indents(iterable: Iterable[str], keyword: str, indent='  '):
    """For a given iterable of strings, returns blocks of the same
    left indentation.

    For example:
    foo1
      bar1
      bar2
    foo2
      foo2

    For that text, this method would return ``[bar1, bar2]`` for passed-in
    keyword ``foo1``.

    :param iterable: A list of strings representing lines.
    :param keyword: The title preceding the indentation.
    :param indent: Which characters makes the indentation.
    """
    section_pos = None
    for i, line in enumerate(iterable):
        if not line.startswith(indent):
            if keyword in line:
                section_pos = i
            elif section_pos is not None:
                yield iterable[section_pos:i]
                section_pos = None
    return


def _default(key, default):
    if default is DEFAULT:
        raise IndexError('Value {} not found.'.format(key))
    else:
        return default


"""Gets"""
TO_REMOVE = {'none', 'prod', 'o.e.m', 'oem', r'n/a', 'atapi', 'pc', 'unknown'}
"""Delete those *words* from the value"""
assert all(v.lower() == v for v in TO_REMOVE), 'All words need to be lower-case'

REMOVE_CHARS_BETWEEN = '(){}[]'
"""
Remove those *characters* from the value. 
All chars inside those are removed. Ex: foo (bar) => foo
"""
CHARS_TO_REMOVE = '*'
"""Remove the characters.

'*' Needs to be removed or otherwise it is interpreted
as a glob expression by regexes.
"""

MEANINGLESS = {
    'to be filled',
    'system manufacturer',
    'system product',
    'sernum',
    'xxxxx',
    'system name',
    'not specified',
    'modulepartnumber',
    'system serial',
    '0001-067a-0000',
    'partnum',
    'manufacturer',
    '0000000',
    'fffff',
    'jedec id:ad 00 00 00 00 00 00 00',
    '012000',
    'x.x',
    'sku',
}
"""Discard a value if any of these values are inside it. """
assert all(v.lower() == v for v in MEANINGLESS), 'All values need to be lower-case'


def sanitize(value, remove=set(), type=None):
    if value is None:
        return None
    remove = remove | TO_REMOVE
    regex = r'({})\W'.format('|'.join(s for s in remove))
    val = re.sub(regex, '', value, flags=re.IGNORECASE)
    val = '' if val.lower() in remove else val  # regex's `\W` != whole string
    val = re.sub(r'\([^)]*\)', '', val)  # Remove everything between
    for char_to_remove in chain(REMOVE_CHARS_BETWEEN, CHARS_TO_REMOVE):
        val = val.replace(char_to_remove, '')
    val = clean(val)
    if val and not any(meaningless in val.lower() for meaningless in MEANINGLESS):
        return type(val) if type else yaml.load(val, Loader=yaml.SafeLoader)
    else:
        return None
