from flask import g

from ereuse_devicehub.db import db
from ereuse_devicehub.inventory.models import Transfer
from ereuse_devicehub.resources.action.models import (
    Confirm,
    ConfirmDocument,
    ConfirmRevokeDocument,
    Revoke,
    RevokeDocument,
    Trade,
)
from ereuse_devicehub.resources.lot.views import delete_from_trade
from ereuse_devicehub.resources.user.models import User
from ereuse_devicehub.teal.marshmallow import ValidationError


class TradeView:
    """Handler for manager the trade action register from post

    request_post = {
        'type': 'Trade',
        'devices': [device_id],
        'documents': [document_id],
        'userFrom': user2.email,
        'userTo': user.email,
        'price': 10,
        'date': "2020-12-01T02:00:00+00:00",
        'lot': lot['id'],
        'confirm': True,
    }

    """

    def __init__(self, data, resource_def, schema):
        self.schema = schema
        self.data = resource_def.schema.load(data)
        self.data.pop('user_to_email', '')
        self.data.pop('user_from_email', '')
        self.create_phantom_account()
        self.trade = Trade(**self.data)
        db.session.add(self.trade)
        self.create_confirmations()
        self.create_automatic_trade()
        self.create_transfer()

    def post(self):
        db.session().final_flush()
        ret = self.schema.jsonify(self.trade)
        ret.status_code = 201
        db.session.commit()
        return ret

    def create_confirmations(self) -> None:
        """Do the first confirmation for the user than do the action"""

        # if the confirmation is mandatory, do automatic confirmation only for
        # owner of the lot
        if self.trade.confirm:
            if self.trade.devices:
                confirm_devs = Confirm(
                    user=g.user, action=self.trade, devices=self.trade.devices
                )
                db.session.add(confirm_devs)

            if self.trade.documents:
                confirm_docs = ConfirmDocument(
                    user=g.user, action=self.trade, documents=self.trade.documents
                )
                db.session.add(confirm_docs)
            return

        # check than the user than want to do the action is one of the users
        # involved in the action
        if g.user not in [self.trade.user_from, self.trade.user_to]:
            txt = "You do not participate in this trading"
            raise ValidationError(txt)

        confirm_from = Confirm(
            user=self.trade.user_from, action=self.trade, devices=self.trade.devices
        )
        confirm_to = Confirm(
            user=self.trade.user_to, action=self.trade, devices=self.trade.devices
        )
        db.session.add(confirm_from)
        db.session.add(confirm_to)

    def create_phantom_account(self) -> None:
        """
        If exist both users not to do nothing
        If exist from but not to:
            search if exist in the DB
                if exist use it
                else create new one
        The same if exist to but not from

        """
        user_from = self.data.get('user_from')
        user_to = self.data.get('user_to')
        code = self.data.get('code')

        if user_from and user_to:
            return

        if self.data['confirm']:
            return

        if user_from and not user_to:
            assert g.user == user_from
            email = "{}_{}@dhub.com".format(str(user_from.id), code)
            users = User.query.filter_by(email=email)
            if users.first():
                user = users.first()
                self.data['user_to'] = user
                return

            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
            self.data['user_to'] = user

        if not user_from and user_to:
            email = "{}_{}@dhub.com".format(str(user_to.id), code)
            users = User.query.filter_by(email=email)
            if users.first():
                user = users.first()
                self.data['user_from'] = user
                return

            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
            self.data['user_from'] = user

    def create_transfer(self):
        code = self.trade.code
        confirm = self.trade.confirm
        lot = self.trade.lot
        user_from = None
        user_to = None

        if not self.trade.user_from.phantom:
            user_from = self.trade.user_from
        if not self.trade.user_to.phantom:
            user_to = self.trade.user_to
        if (user_from and user_to) or not code or confirm:
            return

        self.transfer = Transfer(
            code=code, user_from=user_from, user_to=user_to, lot=lot
        )
        db.session.add(self.transfer)

    def create_automatic_trade(self) -> None:
        # not do nothing if it's neccesary confirmation explicity
        if self.trade.confirm:
            return

        # Change the owner for every devices
        for dev in self.trade.devices:
            dev.change_owner(self.trade.user_to)


class ConfirmMixin:
    """
    Very Important:
    ==============
    All of this Views than inherit of this class is executed for users
    than is not owner of the Trade action.

    The owner of Trade action executed this actions of confirm and revoke from the
    lot

    """

    Model = None

    def __init__(self, data, resource_def, schema):
        self.schema = schema
        a = resource_def.schema.load(data)
        self.validate(a)
        if not a['devices']:
            raise ValidationError('Devices not exist.')
        self.model = self.Model(**a)

    def post(self):
        db.session().final_flush()
        ret = self.schema.jsonify(self.model)
        ret.status_code = 201
        db.session.commit()
        return ret


class ConfirmView(ConfirmMixin):
    """Handler for manager the Confirmation register from post

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'devices': [device_id]
    }
    """

    Model = Confirm

    def validate(self, data):
        """If there are one device than have one confirmation,
        then remove the list this device of the list of devices of this action
        """
        real_devices = []
        trade = data['action']
        lot = trade.lot
        for dev in data['devices']:
            if dev.trading(lot, simple=True) not in [
                'NeedConfirmation',
                'NeedConfirmRevoke',
            ]:
                raise ValidationError('Some devices not possible confirm.')

        # Change the owner for every devices
        for dev in data['devices']:
            if dev.trading(lot) == 'NeedConfirmation':
                user_to = data['action'].user_to
                dev.change_owner(user_to)


class RevokeView(ConfirmMixin):
    """Handler for manager the Revoke register from post

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'devices': [device_id],
    }

    """

    Model = Revoke

    def __init__(self, data, resource_def, schema):
        self.schema = schema
        a = resource_def.schema.load(data)
        self.validate(a)

    def validate(self, data):
        """All devices need to have the status of DoubleConfirmation."""

        devices = data['devices']
        if not devices:
            raise ValidationError('Devices not exist.')

        lot = data['action'].lot
        self.model = delete_from_trade(lot, devices)


class ConfirmDocumentMixin:
    """
    Very Important:
    ==============
    All of this Views than inherit of this class is executed for users
    than is not owner of the Trade action.

    The owner of Trade action executed this actions of confirm and revoke from the
    lot

    """

    Model = None

    def __init__(self, data, resource_def, schema):
        self.schema = schema
        a = resource_def.schema.load(data)
        self.validate(a)
        if not a['documents']:
            raise ValidationError('Documents not exist.')
        self.model = self.Model(**a)

    def post(self):
        db.session().final_flush()
        ret = self.schema.jsonify(self.model)
        ret.status_code = 201
        db.session.commit()
        return ret


class ConfirmDocumentView(ConfirmDocumentMixin):
    """Handler for manager the Confirmation register from post

    request_confirm = {
        'type': 'Confirm',
        'action': trade.id,
        'documents': [document_id],
    }
    """

    Model = ConfirmDocument

    def validate(self, data):
        """If there are one device than have one confirmation,
        then remove the list this device of the list of devices of this action
        """
        for doc in data['documents']:
            ac = doc.trading
            if not doc.trading in ['Confirm', 'Need Confirmation']:
                txt = 'Some of documents do not have enough to confirm for to do a Doble Confirmation'
                ValidationError(txt)
        ### End check ###


class RevokeDocumentView(ConfirmDocumentMixin):
    """Handler for manager the Revoke register from post

    request_revoke = {
        'type': 'Revoke',
        'action': trade.id,
        'documents': [document_id],
    }

    """

    Model = RevokeDocument

    def validate(self, data):
        """All devices need to have the status of DoubleConfirmation."""

        ### check ###
        if not data['documents']:
            raise ValidationError('Documents not exist.')

        for doc in data['documents']:
            if not doc.trading in ['Document Confirmed', 'Confirm']:
                txt = (
                    'Some of documents do not have enough to confirm for to do a revoke'
                )
                ValidationError(txt)
        ### End check ###


class ConfirmRevokeDocumentView(ConfirmDocumentMixin):
    """Handler for manager the Confirmation register from post

    request_confirm_revoke = {
        'type': 'ConfirmRevoke',
        'action': action_revoke.id,
        'documents': [document_id],
    }

    """

    Model = ConfirmRevokeDocument

    def validate(self, data):
        """All devices need to have the status of revoke."""

        if not data['action'].type == 'RevokeDocument':
            txt = 'Error: this action is not a revoke action'
            ValidationError(txt)

        for doc in data['documents']:
            if not doc.trading == 'Revoke':
                txt = 'Some of documents do not have revoke to confirm'
                ValidationError(txt)
