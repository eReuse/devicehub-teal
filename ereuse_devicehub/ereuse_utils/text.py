import ast
import re
from typing import Iterator, Set, Union


def grep(text: str, value: str):
    """An easy 'grep -i' that yields lines where value is found."""
    for line in text.splitlines():
        if value in line:
            yield line


def between(text: str, begin='(', end=')'):
    """Dead easy text between two characters.
    Not recursive or repetitions.
    """
    return text.split(begin)[-1].split(end)[0]


def numbers(text: str) -> Iterator[Union[int, float]]:
    """Gets numbers in strings with other characters.

    Integer Numbers: 1 2 3 987 +4 -8
    Decimal Numbers: 0.1 2. .3 .987 +4.0 -0.8
    Scientific Notation: 1e2 0.2e2 3.e2 .987e2 +4e-1 -8.e+2
    Numbers with percentages: 49% 32.39%

    This returns int or float.
    """
    # From https://regexr.com/33jqd
    for x in re.finditer(r'[+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*)(?:[eE][+-]?\d+)?', text):
        yield ast.literal_eval(x.group())


def positive_percentages(
    text: str, lengths: Set[int] = None, decimal_numbers: int = None
) -> Iterator[Union[int, float]]:
    """Gets numbers postfixed with a '%' in strings with other characters.

    1)100% 2)56.78% 3)56 78.90% 4)34.6789% some text

    :param text: The text to search for.
    :param lengths: A set of lengths that the percentage
                    number should have to be considered valid.
                    Ex. {5,6} would validate '90.32' and '100.00'
    """
    # From https://regexr.com/3aumh
    for x in re.finditer(r'[\d|\.]+%', text):
        num = x.group()[:-1]
        if lengths:
            if not len(num) in lengths:
                continue
        if decimal_numbers:
            try:
                pos = num.rindex('.')
            except ValueError:
                continue
            else:
                if len(num) - pos - 1 != decimal_numbers:
                    continue
        yield float(num)


def macs(text: str) -> Iterator[str]:
    """Find MACs in strings with other characters."""
    for x in re.finditer('{0}:{0}:{0}:{0}:{0}:{0}'.format(r'[a-fA-F0-9.+_-]+'), text):
        yield x.group()


def clean(text: str) -> str:
    """Trims the text and replaces multiple spaces with a single space."""
    return ' '.join(text.split())
