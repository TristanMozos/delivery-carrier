# -*- coding: utf-8 -*-
# Copyright 2012 Akretion <http://www.akretion.com>.
# Copyright 2013-2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def _scheduler_import_tracking_states(self, domain=None):
        """
        Abstract method
        It need to be inhereted and
        :param domain:
        :return:
        """
        delivery_carriers = self.env['delivery.carrier'].search([])

        for delivery_carrier in delivery_carriers:
            delivery_carrier.update_non_delivered_pickings()

    @api.multi
    def get_trackings(self):
        """ Abstract method to get tracking states
        :return:

        """

        return

    @api.multi
    def update_non_delivered_pickings(self):
        """ Update non delivered trackings
        :return:

        """
        for deliver in self:
            deliver.get_trackings()

        return