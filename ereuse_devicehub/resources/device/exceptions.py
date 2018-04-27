from marshmallow import ValidationError


class MismatchBetweenIds(ValidationError):
    def __init__(self, other_device_id: int, field: str, value: str):
        message = 'The device {} has the same {} than this one ({}).'.format(other_device_id,
                                                                             field, value)
        super().__init__(message, field_names=[field])


class NeedsId(ValidationError):
    def __init__(self):
        message = 'We couldn\'t get an ID for this device. Is this a custom PC?'
        super().__init__(message)
