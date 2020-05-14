from teal.marshmallow import ValidationError


class MismatchBetweenIds(ValidationError):
    def __init__(self, other_device_id: int, field: str, value: str):
        message = 'The device {} has the same {} than this one ({}).'.format(other_device_id,
                                                                             field, value)
        super().__init__(message, field_names=[field])


class NeedsId(ValidationError):
    def __init__(self):
        message = 'We couldn\'t get a complete HID for this device. Type, manufacturer, model and serial number are empty'
        super().__init__(message)


class DeviceIsInAnotherDevicehub(ValidationError):
    def __init__(self,
                 tag_id,
                 message=None,
                 field_names=None,
                 fields=None,
                 data=None,
                 valid_data=None,
                 **kwargs):
        message = message or 'Device {} is from another Devicehub.'.format(tag_id)
        super().__init__(message, field_names, fields, data, valid_data, **kwargs)
