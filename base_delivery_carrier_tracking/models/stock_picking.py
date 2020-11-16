# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2020 Halltic eSolutions S.L. (http://www.halltic.com)
#                  Tristán Mozos <tristan.mozos@halltic.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_state_ids = fields.One2many('tracking.carrier.state', 'picking_id', string='Tracking states', ondelete="cascade")
    received = fields.Boolean('Picking received')
    in_transit = fields.Boolean('Picking in transit')
    delivered = fields.Boolean('Picking delivered')

    @api.multi
    def get_default_tracking(self):
        """ Abstract method

        :return: [tracking.carrier.state]

        """
        raise UserError(_('There is\'t way to get tracking states from the carrier company.'))


    @api.multi
    def get_tracking_states(self):
        """ Get tracking states

        This method can be inherited to get specific tracking states
        Get a list of tracking states of the picking

        """
        for pick in self:
            pick.get_default_tracking()

    @api.multi
    def get_tracking_pick(self):
        """ Get tracking states
        :return:


        """
        for pick in self:
            pick.get_tracking_states()

    @api.multi
    def action_get_carrier_tracking(self):
        """ Method for the 'Get Tracking' button.

        It will generate the labels for all the packages of the picking.

        """
        return self.get_tracking_pick()
