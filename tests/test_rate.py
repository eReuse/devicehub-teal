from distutils.version import StrictVersion

import pytest

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.device.models import Computer
from ereuse_devicehub.resources.enums import Bios, ComputerChassis, ImageMimeTypes, Orientation, \
    RatingSoftware
from ereuse_devicehub.resources.event.models import PhotoboxRate, WorkbenchRate
from ereuse_devicehub.resources.image.models import Image, ImageList


@pytest.mark.usefixtures('auth_app_context')
def test_workbench_rate():
    rate = WorkbenchRate(processor=0.1,
                         ram=1.0,
                         bios=Bios.A,
                         labelling=False,
                         graphic_card=0.1,
                         data_storage=4.1,
                         algorithm_software=RatingSoftware.Ereuse,
                         algorithm_version=StrictVersion('1.0'),
                         device=Computer(serial_number='24', chassis=ComputerChassis.Tower))
    db.session.add(rate)
    db.session.commit()


@pytest.mark.usefixtures('auth_app_context')
def test_photobox_rate():
    pc = Computer(serial_number='24', chassis=ComputerChassis.Tower)
    image = Image(name='foo',
                  content=b'123',
                  file_format=ImageMimeTypes.jpg,
                  orientation=Orientation.Horizontal,
                  image_list=ImageList(device=pc))
    rate = PhotoboxRate(image=image,
                        algorithm_software=RatingSoftware.Ereuse,
                        algorithm_version=StrictVersion('1.0'),
                        device=pc)
    db.session.add(rate)
    db.session.commit()
