import copy


class MetricsMix:
    """we want get the data metrics of one device"""

    def __init__(self, *args, **kwargs):
        # self.actions.sort(key=lambda x: x.created)
        self.rows = []
        self.lifetime = 0
        self.last_trade = None
        self.action_create_by = 'Receiver'
        self.status_receiver = ''
        self.status_supplier = ''
        self.act = None
        self.end_users = 0
        self.final_user_code = ''
        self.trades = {}

    def get_template_row(self):
        """
        This is a template of a row.
        """
        return {
            'type': '',
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
            'created': self.act.created,
            'start': '',
            'usageTimeAllocate': 0,
        }

    def get_metrics(self):
        """
        This method get a list of values for calculate a metrics from a spreadsheet
        """
        return self.rows


class Metrics(MetricsMix):
    """we want get the data metrics of one device"""

    def __init__(self, *args, **kwargs):
        self.device = kwargs.pop('device')
        self.actions = copy.copy(self.device.actions)
        super().__init__(*args, **kwargs)
        self.hid = self.device.chid
        self.devicehub_id = self.device.devicehub_id

    def get_action_status(self):
        """
        Mark the status of one device.
        If exist one trade before this action, then modify the trade action
        else, create one new row.
        """
        if self.act.trade not in self.trades:
            # If not exist one trade, the status is of the Receive
            self.action_create_by = 'Receiver'
            self.status_receiver = self.act.type
            self.status_supplier = ''
            row = self.get_template_row()
            row['status_supplier_created'] = ''
            row['status_receiver_created'] = self.act.created
            self.rows.append(row)
            return

        trade = self.trades[self.act.trade]

        if trade['trade_supplier'] == self.act.author.email:
            trade['status_supplier'] = self.act.type
            trade['status_supplier_created'] = self.act.created
            return

        if trade['trade_receiver'] == self.act.author.email:
            trade['status_receiver'] = self.act.type
            trade['status_receiver_created'] = self.act.created
            return

        # necesitamos poder poner un cambio de estado de un trade mas antiguo que last_trade
        # lo mismo con confirm

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
        self.action_create_by = 'Receiver'
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
        self.action_create_by = 'Receiver'
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
        self.action_create_by = 'Receiver'
        row = self.get_template_row()
        row['type'] = 'Deallocate'
        row['start'] = self.act.start_time
        self.rows.append(row)

    def get_confirms(self):
        """
        if the action is one trade action, is possible than have a list of confirmations.
        Get the doble confirm for to know if this trade is confirmed or not.
        """
        return self.device.trading(self.act.lot, simple=True)

    def get_trade(self):
        """
        If this action is a trade action modify the base row.
        """
        if self.act.author == self.act.user_from:
            self.action_create_by = 'Supplier'
            self.status_receiver = ''

        row = self.get_template_row()
        self.last_trade = row
        row['type'] = 'Trade'
        row['action_type'] = 'Trade'
        row['trade_supplier'] = self.act.user_from.email
        row['trade_receiver'] = self.act.user_to.email
        row['status_receiver'] = self.status_receiver
        row['status_supplier'] = ''
        row['trade_confirmed'] = self.get_confirms()
        self.trades[self.act] = row
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
        self.document = kwargs.pop('document')
        self.actions = copy.copy(self.document.actions)
        self.reversed_actions = copy.copy(self.document.actions)
        self.hid = self.document.file_hash
        self.devicehub_id = ''
        super().__init__(*args, **kwargs)
        self.reversed_actions.reverse()

    def get_metrics(self):
        self.last_trade = next(x for x in self.actions if x.t == 'Trade')
        self.act = self.last_trade
        row = self.get_template_row()

        row['type'] = 'Trade-Document'
        row['action_type'] = 'Trade-Document'
        if self.document.total_weight or self.document.weight:
            row['type'] = 'Trade-Container'
            row['action_type'] = 'Trade-Container'

        row['document_name'] = self.document.file_name
        row['trade_supplier'] = self.last_trade.user_from.email
        row['trade_receiver'] = self.last_trade.user_to.email
        row['trade_confirmed'] = self.get_confirms()
        row['status_receiver'] = ''
        row['status_supplier'] = ''
        row['trade_weight'] = self.document.total_weight
        if self.document.owner == self.last_trade.user_from:
            row['action_create_by'] = 'Supplier'
        elif self.document.owner == self.last_trade.user_to:
            row['action_create_by'] = 'Receiver'

        self.get_status(row)

        self.rows.append(row)

        return self.rows

    def get_status(self, row):
        """
        We want to know if receiver or supplier do some action that change the status
        of the container.
        """
        if not (self.document.total_weight and self.document.weight):
            return ''
        for ac in self.reversed_actions:
            if ac.type not in ['Use', 'Refurbish', 'Recycling', 'Management']:
                continue
            if ac.author == self.last_trade.user_from:
                row['status_supplier'] = ac.type
                row['status_supplier_created'] = ac.created
            if ac.author == self.last_trade.user_to:
                row['status_receiver'] = ac.type
                row['status_receiver_created'] = ac.created

        return ''

    def get_confirms(self):
        """
        if the action is one trade action, is possible than have a list of confirmations.
        Get the doble confirm for to know if this trade is confirmed or not.
        """
        trade = None
        confirmations = []
        confirms = []
        for ac in self.document.actions:
            if ac.t == 'Trade':
                trade = ac
            elif ac.t == 'ConfirmDocument':
                confirms.append(ac.author)
                confirmations.append(ac)
            elif ac.t in ['RevokeDocument', 'ConfirmDocumentRevoke']:
                confirmations.append(ac)

        if confirmations and confirmations[-1].t == 'ConfirmDocument':
            if trade.user_from in confirms and trade.user_to in confirms:
                return True

        return False
