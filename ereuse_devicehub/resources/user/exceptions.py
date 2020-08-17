from werkzeug.exceptions import Unauthorized, Forbidden


class WrongCredentials(Unauthorized):
    description = 'There is not an user with the matching username/password'


class InsufficientPermission(Forbidden):
    description = (
        "You don't have the permissions to access the requested"
        "resource. It is either read-protected or not readable by the"
        "server."
    )
