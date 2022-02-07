from audioop import add
from curses import ERR
from flask import session


DEBUG = 10
INFO = 20
SUCCESS = 25
WARNING = 30
ERROR = 40

DEFAULT_LEVELS = {
    'DEBUG': DEBUG,
    'INFO': INFO,
    'SUCCESS': SUCCESS,
    'WARNING': WARNING,
    'ERROR': ERROR,
}

DEFAULT_TAGS = {
    DEBUG: 'light',
    INFO: 'info',
    SUCCESS: 'success',
    WARNING: 'warning',
    ERROR: 'danger',
}

DEFAULT_ICONS = {
    DEBUG: 'tools',
    INFO: 'info-circle',
    SUCCESS: 'check-circle',
    WARNING: 'exclamation-triangle',
    ERROR: 'exclamation-octagon',
}


def add_message(level, message):
    messages = session.get('_messages', [])

    icon = DEFAULT_ICONS[level]
    level_tag = DEFAULT_TAGS[level]

    messages.append({'level': level_tag, 'icon': icon, 'content': message})


def debug(message):
    """Add a message with the ``DEBUG`` level."""
    add_message(DEBUG, message)


def info(message):
    """Add a message with the ``INFO`` level."""
    add_message(INFO, message)


def success(message):
    """Add a message with the ``SUCCESS`` level."""
    add_message(SUCCESS, message)


def warning(message):
    """Add a message with the ``WARNING`` level."""
    add_message(WARNING, message)


def error(message):
    """Add a message with the ``ERROR`` level."""
    add_message(ERROR, message)
