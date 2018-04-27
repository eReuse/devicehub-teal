from werkzeug.exceptions import Unauthorized


class WrongCredentials(Unauthorized):
    description = 'There is not an user with the matching username/password'
