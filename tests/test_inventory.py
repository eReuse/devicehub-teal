import pytest


@pytest.mark.xfail(reason='Test not developed')
def test_create_inventory():
    """Tests creating an inventory with an user."""


@pytest.mark.xfail(reason='Test not developed')
def test_create_existing_inventory():
    pass


@pytest.mark.xfail(reason='Test not developed')
def test_delete_inventory():
    """Tests deleting an inventory without
    disturbing other inventories (ex. keeping commmon db), and
    removing its traces in common (no inventory row in inventory table).
    """
