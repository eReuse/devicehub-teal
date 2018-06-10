from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.orm import relationship

from ereuse_devicehub.resources.device.models import Device
from ereuse_devicehub.resources.enums import ImageMimeTypes, Orientation
from ereuse_devicehub.resources.models import Thing


class ImageList(Thing):
    id = ...  # type: Column
    device = ...  # type: Column
    images = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.device = ...  # type: Device
        self.images = ...  # types: List[Image]


class Image(Thing):
    id = ...  # type: Column
    position = ...  #type: Column
    name = ...  # type: Column
    content = ...  # type: Column
    file_format = ...  # type: Column
    orientation = ...  # type: Column
    image_list = ...  # type: relationship

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = ...  # type: UUID
        self.position = ...  # type: int
        self.name = ''  # type: str
        self.content = ...  # type: bytes
        self.file_format = ...  # type: ImageMimeTypes
        self.orientation = ...  # type: Orientation
        self.image_list_id = ...  # type: UUID
        self.image_list = ...  # type: ImageList
