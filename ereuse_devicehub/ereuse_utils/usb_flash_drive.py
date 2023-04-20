import usb.core
import usb.util
from usb import CLASS_MASS_STORAGE

from ereuse_devicehub.ereuse_utils.naming import Naming


def plugged_usbs(multiple=True) -> map or dict:  # noqa: C901
    """
    Gets the plugged-in USB Flash drives (pen-drives).

    If multiple is true, it returns a map, and a dict otherwise.

    If multiple is false, this method will raise a :class:`.NoUSBFound` if no USB is found.
    """

    class FindPenDrives(object):
        # From https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst
        def __init__(self, class_):
            self._class = class_

        def __call__(self, device):
            # first, let's check the device
            if device.bDeviceClass == self._class:
                return True
            # ok, transverse all devices to find an
            # interface that matches our class
            for cfg in device:
                # find_descriptor: what's it?
                intf = usb.util.find_descriptor(cfg, bInterfaceClass=self._class)
                # We don't want Card readers
                if intf is not None:
                    try:
                        product = intf.device.product.lower()
                    except ValueError as e:
                        if 'langid' in str(e):
                            raise OSError(
                                'Cannot get "langid". Do you have permissions?'
                            )
                        else:
                            raise e
                    if 'crw' not in product and 'reader' not in product:
                        return True
            return False

    def get_pendrive(pen: usb.Device) -> dict:
        if not pen.manufacturer or not pen.product or not pen.serial_number:
            raise UsbDoesNotHaveHid()
        manufacturer = pen.manufacturer.strip() or str(pen.idVendor)
        model = pen.product.strip() or str(pen.idProduct)
        serial_number = pen.serial_number.strip()
        hid = Naming.hid('USBFlashDrive', manufacturer, model, serial_number)
        return {
            'id': hid,  # Make live easier to DeviceHubClient by using _id
            'hid': hid,
            'type': 'USBFlashDrive',
            'serialNumber': serial_number,
            'model': model,
            'manufacturer': manufacturer,
            'vendorId': pen.idVendor,
            'productId': pen.idProduct,
        }

    result = usb.core.find(
        find_all=multiple, custom_match=FindPenDrives(CLASS_MASS_STORAGE)
    )
    if multiple:
        return map(get_pendrive, result)
    else:
        if not result:
            raise NoUSBFound()
        return get_pendrive(result)


class NoUSBFound(Exception):
    pass


class UsbDoesNotHaveHid(Exception):
    pass
