# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2019 Halltic eSolutions (https://www.halltic.com)
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

import logging
from datetime import datetime, timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleOrderToSend(models.Model):
    _name = "delivery.issue"

    sale_id = fields.Many2one('sale.order', required=True)
    picking_id = fields.Many2one('stock.picking', required=True)
    mass_ship_id = fields.Many2one('mass.shipment.management', required=True)
    customer_name = fields.Char('Customer name', related='picking_id.partner_id.name')
    country_customer_name = fields.Char('Customer country', related='picking_id.partner_id.country_id.name')
    type_issue = fields.Selection(selection=[('0', 'Delivery late'),
                                             ('1', 'Warning delivery late'),
                                             ('2', 'Ship doesn\'t arrive to carrier'),
                                             ('3', 'Cold tracking'),
                                             ], required=True)
    delivery_carrier_id = fields.Many2one('delivery.carrier', required=True)
    delivery_carrier_name = fields.Char('Delivery carrier', related='delivery_carrier_id.name')
    delivery_carrier_type = fields.Char('Delivery carrier type', compute='_compute_delivery_type')
    ship_reference = fields.Char('Order Reference', store=True, compute='_onchange_ship_reference')
    picking_state = fields.Selection(related='picking_id.state')
    limit_ship_date = fields.Datetime('Date limit to ship', related='sale_id.commitment_date')
    limit_delivery_date = fields.Datetime('Date limit to delivery', related='sale_id.commitment_date')
    current_ship_state = fields.Char('Current ship state', compute='_compute_current_state')
    is_solved = fields.Boolean('Is solved?')

    @api.model
    def check_next_days_weekend(self, ana_date, days=0):
        """
        Method that analize if the next days is weekend
        :param ana_date:
        :param days:
        :return:
        """
        if not ana_date:
            ana_date = datetime.now()
        if ana_date.weekday() + days >= 5:
            return True
        return False

    @api.model
    def is_picking_late_received(self, picking, mass_ship_date, days):
        today = datetime.now()
        ship_date = datetime.strptime(mass_ship_date, '%Y-%m-%d')
        if picking and days:
            if self.check_next_days_weekend(ana_date=ship_date, days=days):
                days = days + 2
            if (ship_date + timedelta(days=days)) < today:
                return True

        return False

    @api.model
    def warning_delivery_late(self, picking, days):
        today = datetime.now()
        if picking and days and picking.sale_id.commitment_date:
            commit_date = datetime.strptime(picking.sale_id.commitment_date, '%Y-%m-%d %H:%M:%S')
            if self.check_next_days_weekend(ana_date=commit_date, days=days):
                days = days + 2
            if (commit_date + timedelta(days=days)) < today:
                return True

        return False

    @api.model
    def is_picking_late_delivery(self, picking):
        today = datetime.now()
        if picking and picking.sale_id.commitment_date:
            commit_date = datetime.strptime(picking.sale_id.commitment_date, '%Y-%m-%d %H:%M:%S')
            if commit_date <= today:
                return True

        return False

    @api.multi
    def _analyze_shipment(self, picking, days_check_received, days_check_delivery):
        """
        Method to analyze problems on national picking
        :param picking: picking to analyze
        :return:
        """
        try:

            mass_ship_stock_pick = self.env['mass.shipment.stock.picking'].search([('stock_picking_id', '=', picking.id)], order='create_date desc').filtered(
                'is_done')
            if mass_ship_stock_pick:
                mass_ship_stock_pick = mass_ship_stock_pick[0]
                # If the picking is not received we need to know if the picking has been received
                if not picking.received and self.is_picking_late_received(picking=picking,
                                                                          mass_ship_date=mass_ship_stock_pick.mass_delivery_id.shipment_date,
                                                                          days=days_check_received):
                    issue = self.search([('picking_id', '=', picking.id), ('type_issue', '=', '2')])
                    if not issue:
                        vals = {'picking_id':picking.id,
                                'sale_id':picking.sale_id.id,
                                'delivery_carrier_id':picking.carrier_id.id,
                                'mass_ship_id': mass_ship_stock_pick.mass_delivery_id.id,
                                'type_issue':'2',
                                }
                        self.create(vals)
                if not picking.delivered:

                    if self.is_picking_late_delivery(picking=picking):

                        issue = self.search([('picking_id', '=', picking.id), ('type_issue', '=', '0')])
                        if not issue:
                            vals = {'picking_id':picking.id,
                                    'sale_id':picking.sale_id.id,
                                    'delivery_carrier_id':picking.carrier_id.id,
                                    'mass_ship_id': mass_ship_stock_pick.mass_delivery_id.id,
                                    'type_issue':'0',
                                    }
                            self.create(vals)
                    elif self.warning_delivery_late(picking=picking, days=days_check_delivery):

                        issue = self.search([('picking_id', '=', picking.id), ('type_issue', '=', '1')])
                        if not issue:
                            vals = {'picking_id': picking.id,
                                    'sale_id': picking.sale_id.id,
                                    'delivery_carrier_id': picking.carrier_id.id,
                                    'mass_ship_id': mass_ship_stock_pick.mass_delivery_id.id,
                                    'type_issue': '1',
                                    }
                            self.create(vals)
        except Exception as e:
            _logger.error('Delivery check log: exception with picking: %s message: [%s]' % (picking.name, e.message))

    @api.multi
    def _scheduler_compute_delivery_issues(self):
        today = datetime.now()
        date_from = today - timedelta(days=30)
        pickings = self.env['stock.picking'].search([('delivered', '=', False),
                                                     ('min_date', '>', date_from.isoformat()), ])

        for pick in pickings:
            if pick.sale_id.state != 'cancel' and pick.carrier_tracking_ref and len(pick.sale_id.picking_ids) == 1 and pick.tracking_state_ids:
                if pick.partner_id.country_id.code == 'ES' or pick.partner_id.country_id.code == 'PT':
                    self._analyze_shipment(picking=pick, days_check_received=2, days_check_delivery=1)
                else:
                    self._analyze_shipment(picking=pick, days_check_received=3, days_check_delivery=2)

    @api.onchange('picking_id')
    def _onchange_ship_reference(self):
        for picking in self:
            picking.ship_reference = picking.stock_picking_id._get_ship_reference()

    @api.one
    def _compute_current_state(self):
        for issue in self:
            if issue.picking_id.tracking_state_ids:
                issue.current_ship_state = issue.picking_id.tracking_state_ids.sorted('state_date', reverse=True)[0].event if issue.picking_id.tracking_state_ids else ''

    @api.one
    def _compute_delivery_type(self):
        for issue in self:
            issue.delivery_carrier_type = issue.delivery_carrier_id.carrier_type
