import copy

from flask import g
from sqlalchemy.util import OrderedSet
from teal.marshmallow import ValidationError

from ereuse_devicehub.db import db
from ereuse_devicehub.resources.action.models import Trade, Confirm, ConfirmRevoke, Revoke
from ereuse_devicehub.resources.user.models import User


class TradeView():
    """Handler for manager the trade action register from post
 
       request_post = {
           'type': 'Trade',
           'devices': [device_id],
           'userFrom': user2.email,
           'userTo': user.email,
           'price': 10,
           'date': "2020-12-01T02:00:00+00:00",
           'documentID': '1',
           'lot': lot['id'],
           'confirm': True,
       }

    """

    def __init__(self, data, resource_def, schema):
        self.schema = schema
        a = resource_def.schema.load(data)
        a.pop('user_to_email', '')
        a.pop('user_from_email', '')
        self.trade = Trade(**a)
        self.create_phantom_account()
        db.session.add(self.trade)
        self.create_automatic_trade()
        self.create_confirmations()

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
            confirm = Confirm(user=g.user,
                              action=self.trade, 
                              devices=self.trade.devices)
            db.session.add(confirm)
            return

        # check than the user than want to do the action is one of the users
        # involved in the action
        if not g.user in [self.trade.user_from, self.trade.user_to]:
            txt = "You do not participate in this trading"
            raise ValidationError(txt)

        confirm_from = Confirm(user=self.trade.user_from, 
                               action=self.trade, 
                               devices=self.trade.devices)
        confirm_to = Confirm(user=self.trade.user_to, 
                             action=self.trade, 
                             devices=self.trade.devices)
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
        if self.trade.user_from and self.trade.user_to:
            return

        if self.trade.user_from and not self.trade.user_to:
            assert g.user == self.trade.user_from
            email = "{}_{}@dhub.com".format(str(self.trade.user_from.id), self.trade.code)
            users = User.query.filter_by(email=email)
            if users.first():
                user = users.first()
                self.trade.user_to = user
                return

            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
            self.trade.user_to = user

        if not self.trade.user_from and self.trade.user_to:
            email = "{}_{}@dhub.com".format(str(self.trade.user_to.id), self.trade.code)
            users = User.query.filter_by(email=email)
            if users.first():
                user = users.first()
                self.trade.user_from = user
                return

            user = User(email=email, password='', active=False, phantom=True)
            db.session.add(user)
            self.trade.user_from = user

    def create_automatic_trade(self) -> None:
        # not do nothing if it's neccesary confirmation explicity
        if self.trade.confirm:
            return

        # Change the owner for every devices
        for dev in self.trade.devices:
            dev.owner = self.trade.user_to
            if hasattr(dev, 'components'):
                for c in dev.components:
                    c.owner = self.trade.user_to


class ConfirmMixin():
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
        # import pdb; pdb.set_trace()
        real_devices = []
        for dev in data['devices']:
            actions = copy.copy(dev.actions)
            actions.reverse()
            for ac in actions:
                if ac == data['action']:
                    # If device have the last action the action Trade
                    real_devices.append(dev)
                    break

                if ac.t == Confirm.t and not ac.user == g.user:
                    # If device is confirmed we don't need confirmed again
                    real_devices.append(dev)
                    break

                if ac.t == 'Revoke' and not ac.user == g.user:
                    # If device is revoke before from other user
                    # it's not possible confirm now
                    break

                if ac.t == 'ConfirmRevoke' and ac.user == g.user:
                    # if the last action is a ConfirmRevoke this mean than not there are
                    # other confirmation from the real owner of the trade
                    break

                if ac.t == Confirm.t and ac.user == g.user:
                    # If device is confirmed we don't need confirmed again
                    break

        data['devices'] = OrderedSet(real_devices)

        # Change the owner for every devices
        for dev in data['devices']:
            dev.owner = data['action'].user_to
            if hasattr(dev, 'components'):
                for c in dev.components:
                    c.owner = data['action'].user_to


class RevokeView(ConfirmMixin):
    """Handler for manager the Revoke register from post

       request_revoke = {
           'type': 'Revoke',
           'action': trade.id,
           'devices': [device_id],
       }

    """

    Model = Revoke

    def validate(self, data):
        """If there are one device than have one confirmation,
           then remove the list this device of the list of devices of this action
        """
        real_devices = []
        for dev in data['devices']:
            actions = copy.copy(dev.actions)
            actions.reverse()
            for ac in actions:
                if ac == data['action']:
                    # data['action'] is a Trade action, if this is the first action
                    # to find mean that this devices dont have a confirmation
                    break

                if ac.t == 'Revoke' and ac.user == g.user:
                    break

                if ac.t == Confirm.t and ac.user == g.user:
                    real_devices.append(dev)
                    break

        data['devices'] = OrderedSet(real_devices)


class ConfirmRevokeView(ConfirmMixin):
    """Handler for manager the Confirmation register from post

       request_confirm_revoke = {
           'type': 'ConfirmRevoke',
           'action': action_revoke.id,
           'devices': [device_id]
       }

    """

    Model = ConfirmRevoke

    def validate(self, data):
        """If there are one device than have one confirmation,
           then remove the list this device of the list of devices of this action
        """
        real_devices = []
        for dev in data['devices']:
            actions = copy.copy(dev.actions)
            actions.reverse()
            for ac in actions:
                if ac == data['action']:
                    # If device have the last action the action for confirm
                    real_devices.append(dev)
                    break

                if ac.t == 'Revoke' and not ac.user == g.user:
                    # If device is revoke before you can Confirm now
                    # and revoke is an action of one other user
                    real_devices.append(dev)
                    break

                if ac.t == ConfirmRevoke.t and ac.user == g.user:
                    # If device is confirmed we don't need confirmed again
                    break

                if ac.t == Confirm.t:
                    # if onwer of trade confirm again before than this user Confirm the
                    # revoke, then is not possible confirm the revoke
                    #
                    # If g.user confirm the trade before do a ConfirmRevoke
                    # then g.user can not to do the ConfirmRevoke more
                    break

        devices = OrderedSet(real_devices)
        data['devices'] = devices

        # Change the owner for every devices
        # data['action'] == 'Revoke'

        trade = data['action'].action
        for dev in devices:
            # TODO @cayop if it's possible the both users insert devices into a lot, then there are problems
            dev.owner = trade.author
            if hasattr(dev, 'components'):
                for c in dev.components:
                    c.owner = trade.author

        trade.lot.devices.difference_update(devices)
