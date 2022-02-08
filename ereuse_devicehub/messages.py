from flask import flash, session

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
    DEFAULT_TAGS[DEBUG]: 'tools',
    DEFAULT_TAGS[INFO]: 'info-circle',
    DEFAULT_TAGS[SUCCESS]: 'check-circle',
    DEFAULT_TAGS[WARNING]: 'exclamation-triangle',
    DEFAULT_TAGS[ERROR]: 'exclamation-octagon',
}


def add_message(level, message):
    level_tag = DEFAULT_TAGS[level]
    if '_message_icon' not in session:
        session['_message_icon'] = DEFAULT_ICONS

    flash(message, level_tag)


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
