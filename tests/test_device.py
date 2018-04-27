from ereuse_devicehub.db import db
from ereuse_devicehub.devicehub import Devicehub
from ereuse_devicehub.resources.device.models import Desktop, Device, GraphicCard, NetworkAdapter
from ereuse_devicehub.resources.device.schemas import Device as DeviceS


def test_device_model(app: Devicehub):
    """
    Tests that the correctness of the device model and its relationships.
    """
    with app.test_request_context():
        pc = Desktop(model='p1mo', manufacturer='p1ma', serial_number='p1s')
        pc.components = components = [
            NetworkAdapter(model='c1mo', manufacturer='c1ma', serial_number='c1s'),
            GraphicCard(model='c2mo', manufacturer='c2ma', memory=1500)
        ]
        db.session.add(pc)
        db.session.commit()
        pc = Desktop.query.one()
        assert pc.serial_number == 'p1s'
        assert pc.components == components
        network_adapter = NetworkAdapter.query.one()
        assert network_adapter.parent == pc

        # Removing a component from pc doesn't delete the component
        del pc.components[0]
        db.session.commit()
        pc = Device.query.first()  # this is the same as querying for Desktop directly
        assert pc.components[0].type == GraphicCard.__name__
        network_adapter = NetworkAdapter.query.one()
        assert network_adapter not in pc.components
        assert network_adapter.parent is None

        # Deleting the pc deletes everything
        gcard = GraphicCard.query.one()
        db.session.delete(pc)
        assert pc.id == 1
        assert Desktop.query.first() is None
        db.session.commit()
        assert Desktop.query.first() is None
        assert network_adapter.id == 2
        assert NetworkAdapter.query.first() is not None, 'We removed the network adaptor'
        assert gcard.id == 3, 'We should still hold a reference to a zombie graphic card'
        assert GraphicCard.query.first() is None, 'We should have deleted it –it was inside the pc'


def test_device_schema():
    """Ensures the user does not upload non-writable or extra fields."""
    device_s = DeviceS()
    device_s.load({'serial_number': 'foo1', 'model': 'foo', 'manufacturer': 'bar2'})

    device_s.dump({'id': 1})
