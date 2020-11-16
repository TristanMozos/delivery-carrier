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
from datetime import datetime

from odoo import models, fields, api, exceptions, _
from ..json.spring_api import SpringRequest


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def _spring_tracking_request(self, spring_api):
        self.ensure_one()
        shipment_reference = {'ShipperReference': self.name}
        data = {'Command': 'TrackShipment', 'Shipment': shipment_reference}
        response = spring_api.api_request(data)
        return response if response and response.get('ErrorLevel') == 0 else None

    @api.multi
    def _get_spring_tracking(self):
        if not self.carrier_id.spring_config_id:
            raise exceptions.Warning(_('No Spring config defined in carrier'))

        # Get shipment tracking
        spring_api = SpringRequest(self.carrier_id.spring_config_id)
        response = self._spring_tracking_request(spring_api)
        if response:
            # Get before event datetimes
            state_dates = self.tracking_state_ids.mapped('state_date')
            tracking_list_vals = []
            tracking_data = response['Shipment']

            if not self.carrier_tracking_ref:
                self.carrier_tracking_ref = tracking_data['TrackingNumber']

            for state_event in tracking_data['Events']:
                date_tracking = datetime.strptime(state_event['DateTime'], '%Y-%m-%d %H:%M:%S')
                if date_tracking.strftime('%Y-%m-%d %H:%M:%S') not in state_dates:
                    event = state_event['Description']
                    code = str(state_event['Code'] or '')
                    carrier_description = state_event['CarrierDescription']
                    vals = {"state_date": date_tracking, "code": code, "event": event, "comment": carrier_description}
                    tracking_list_vals.append(vals)


            if tracking_list_vals:
                for tracking_data in tracking_list_vals:
                    tracking_vals = {'tracking_state_ids': [(0, 0, tracking_data)]}
                    if tracking_data['code'] == '20':
                        tracking_vals['received'] = True
                    elif tracking_data['code'] in ('21','2101'):
                        tracking_vals['in_transit'] = True
                    elif tracking_data['code'] == '100':
                        tracking_vals['delivered'] = True

                    self.write(tracking_vals)


        return

    @api.multi
    def get_tracking_states(self):
        """ Add states tracking for Spring picking """
        self.ensure_one()
        if self.carrier_id.carrier_type == 'spring':
            return self._get_spring_tracking()
        return super(StockPicking, self).get_tracking_states()
