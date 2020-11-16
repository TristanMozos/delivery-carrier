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
import base64
import logging
import urllib
from datetime import datetime

from odoo import models, api, exceptions
from xml.dom.minidom import parseString
from ..webservice.gls_api import GlsRequest

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def _get_gls_digitalizations(self, dom):
        """
        Attach the sign of the delivery if
        :param dom:
        :return:
        """
        try:
            attach_firma = self.env['ir.attachment'].search_count([('res_model', '=', self._name), ('res_id', '=', self.id),('name', '=', '%s_firma.jpeg' % self.carrier_tracking_ref)])
            if attach_firma==0:
                digitalizaciones = dom.getElementsByTagName('digitalizaciones')
                digi_list = digitalizaciones[0].getElementsByTagName('digitalizacion')
                for digitalizacion in digi_list:
                    url_firma = digitalizacion.getElementsByTagName('imagen')[0].firstChild.data if digitalizacion.getElementsByTagName('imagen')[0].firstChild else ''
                    (filename, header) = urllib.urlretrieve(url_firma)
                    with open(filename, 'rb') as f:
                        attachment_vals = {
                            'name': '%s_firma.jpeg' % self.carrier_tracking_ref,
                            'datas': base64.b64encode(f.read()),
                            'datas_fname': '%s_firma.jpeg' % self.carrier_tracking_ref,
                            'res_model': self._name,
                            'res_id': self.id,
                        }
                        self.env['ir.attachment'].create(attachment_vals)

        except Exception as e:
            _logger.error('Error has been ocurred getting sign of delivery: %s' % self.name)

    @api.multi
    def _get_gls_tracking(self):
        if not self.carrier_id.gls_config_id:
            raise exceptions.Warning(_('No Gls Config defined in carrier'))

        gls_api = GlsRequest(self.carrier_id.gls_config_id)
        tracking_request = self._get_gls_ship_data()
        tracking_response = gls_api.api_request(tracking_request)
        dom = parseString(tracking_response)
        if dom.getElementsByTagName('expediciones'):
            expediciones = dom.getElementsByTagName('expediciones')
            tracking_list = expediciones[0].getElementsByTagName('tracking')
            tracking_list_vals = []
            # Get before event datetimes
            state_dates = self.tracking_state_ids.mapped('state_date')
            if tracking_list:
                for tracking in tracking_list:
                    date_tracking = datetime.strptime(tracking.getElementsByTagName('fecha')[0].firstChild.data, '%d/%m/%Y %H:%M:%S')
                    if date_tracking.strftime('%Y-%m-%d %H:%M:%S') not in state_dates:
                        event= tracking.getElementsByTagName('evento')[0].firstChild.data if tracking.getElementsByTagName('evento')[0].firstChild else ''
                        code = tracking.getElementsByTagName('codigo')[0].firstChild.data if tracking.getElementsByTagName('codigo')[0].firstChild else ''
                        name = tracking.getElementsByTagName('nombreplaza')[0].firstChild.data if tracking.getElementsByTagName('nombreplaza')[0].firstChild else ''
                        vals = {"state_date":date_tracking, "code":code, "event": event, "comment": name}
                        tracking_list_vals.append(vals)

            if tracking_list_vals:
                for tracking_data in tracking_list_vals:
                    tracking_vals={'tracking_state_ids':[(0, 0, tracking_data)]}
                    if tracking_data['code'] == '0':
                        tracking_vals['received'] = True
                    elif tracking_data['code'] == '3':
                        tracking_vals['in_transit'] = True
                    elif tracking_data['code'] == '7':
                        tracking_vals['delivered'] = True
                    self.write(tracking_vals)


            self._get_gls_digitalizations(dom)


    @api.multi
    def get_tracking_states(self):
        """ Add states tracking for GLS picking """
        self.ensure_one()
        if self.carrier_id.carrier_type == 'gls':
            return self._get_gls_tracking()
        return super(StockPicking, self).get_tracking_states()
