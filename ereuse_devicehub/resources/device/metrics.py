import copy


class MetricsMix:
    """we want get the data metrics of one device"""

    def __init__(self, *args, **kwargs):
        self.actions = copy.copy(device.actions)
        self.actions.sort(key=lambda x: x.created)
        self.rows = []
        self.lifetime = 0
        self.last_trade = None
        self.action_create_by = 'Receiver'
        self.status_receiver = 'Use'
        self.status_supplier = ''
        self.act = None
        self.end_users = 0
        self.final_user_code = ''

    def get_template_row(self):
        """
        This is a template of a row.
        """
        return {'type': '',
                'action_type': 'Status',
                'document_name': '',
                'status_receiver': self.status_receiver,
                'status_supplier': self.status_supplier,
                'status_receiver_created': '',
                'status_supplier_created': '',
                'trade_supplier': '',
                'trade_receiver': self.act.author.email,
                'trade_confirmed': '',
                'trade_weight': 0,
                'action_create_by': self.action_create_by,
                'devicehubID': self.devicehub_id,
                'hid': self.hid,
                'finalUserCode': '',
                'numEndUsers': 0,
                'liveCreate': 0,
                'usageTimeHdd': self.lifetime,
                'start': self.act.created,
                'usageTimeAllocate': 0}

    def get_metrics(self):
        """
        This method get a list of values for calculate a metrics from a spreadsheet
        """
        return self.rows


class Metrics(MetricsMix):
    """we want get the data metrics of one device"""

    def __init__(self, *args, **kwargs):
        device = kwargs.pop('device')
        super().__init__(*args, **kwargs)
        self.hid = device.hid
        self.devicehub_id = device.devicehub_id

    def get_action_status(self):
        """
        Mark the status of one device.
        If exist one trade before this action, then modify the trade action
        else, create one row new.
        """
        self.status_receiver = self.act.type
        self.status_supplier = ''
        if self.act.author != self.act.rol_user:
            # It is neccesary exist one trade action before
            self.last_trade['status_supplier'] = self.act.type
            self.last_trade['status_supplier_created'] = self.act.created
            return

        self.action_create_by = 'Receiver'
        if self.last_trade:
            # if exist one trade action before
            self.last_trade['status_receiver'] = self.act.type
            self.last_trade['status_receiver_created'] = self.act.created
            return

        # If not exist any trade action for this device
        row = self.get_template_row()
        row['status_receiver_created'] = self.act.created
        self.rows.append(row)

    def get_snapshot(self):
        """
        If there are one snapshot get the last lifetime for to do a calcul of time of use.
        """
        lifestimes = self.act.get_last_lifetimes()
        if lifestimes:
            self.lifetime = lifestimes[0]['lifetime']

    def get_allocate(self):
        """
        If the action is one Allocate, need modify the row base.
        """
        self.end_users = self.act.end_users
        self.final_user_code = self.act.final_user_code
        row = self.get_template_row()
        row['type'] = 'Allocate'
        row['trade_supplier'] = ''
        row['finalUserCode'] = self.final_user_code
        row['numEndUsers'] = self.end_users
        row['start'] = self.act.start_time
        row['usageTimeAllocate'] = self.lifetime
        self.rows.append(row)

    def get_live(self):
        """
        If the action is one Live, need modify the row base.
        """
        row = self.get_template_row()
        row['type'] = 'Live'
        row['finalUserCode'] = self.final_user_code
        row['numEndUsers'] = self.end_users
        row['start'] = self.act.start_time
        row['usageTimeAllocate'] = self.lifetime
        row['liveCreate'] = self.act.created
        if self.act.usage_time_hdd:
            row['usageTimeHdd'] = self.act.usage_time_hdd.total_seconds() / 3600
        self.rows.append(row)

    def get_deallocate(self):
        """
        If the action is one Dellocate, need modify the row base.
        """
        row = self.get_template_row()
        row['type'] = 'Deallocate'
        row['start'] = self.act.start_time
        self.rows.append(row)

    def get_confirms(self):
        """
        if the action is one trade action, is possible than have a list of confirmations.
        Get the doble confirm for to know if this trade is confirmed or not.
        """
        if hasattr(self.act, 'acceptances'):
            accept = self.act.acceptances[-1]
            if accept.t == 'Confirm' and accept.user == self.act.user_to:
                return True
        return False

    def get_trade(self):
        """
        If this action is a trade action modify the base row.
        """
        if self.act.author == self.act.user_from:
            self.action_create_by = 'Supplier'
        row = self.get_template_row()
        self.last_trade = row
        row['type'] = 'Trade'
        row['action_type'] = 'Trade'
        row['trade_supplier'] = self.act.user_from.email
        row['trade_receiver'] = self.act.user_to.email
        row['self.status_receiver'] = self.status_receiver
        row['self.status_supplier'] = self.status_supplier
        row['trade_confirmed'] = self.get_confirms()
        self.rows.append(row)

    def get_metrics(self):
        """
        This method get a list of values for calculate a metrics from a spreadsheet
        """
        for act in self.actions:
            self.act = act
            if act.type in ['Use', 'Refurbish', 'Recycling', 'Management']:
                self.get_action_status()
                continue

            if act.type == 'Snapshot':
                self.get_snapshot()
                continue

            if act.type == 'Allocate':
                self.get_allocate()
                continue

            if act.type == 'Live':
                self.get_live()
                continue

            if act.type == 'Deallocate':
                self.get_deallocate()
                continue

            if act.type == 'Trade':
                self.get_trade()
                continue

        return self.rows


class TradeMetrics(MetricsMix):
    """we want get the data metrics of one device"""

    def __init__(self, *args, **kwargs):
        document = kwargs.pop('document')
        super().__init__(*args, **kwargs)
        self.hid = document.hash
        self.devicehub_id = ''

