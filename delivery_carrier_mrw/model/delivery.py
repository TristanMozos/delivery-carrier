# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 FactorLibre (http://www.factorlibre.com)
#                  Hugo Santos <hugo.santos@factorlibre.com>
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
from odoo import models, fields, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def get_mrw_url_tracking(self, picking):
        if picking.carrier_tracking_ref:
            return ['https://mrw.es/seguimiento_envios/MRW_resultados_consultas.asp?modo=nacional&envio=%s' % picking.carrier_tracking_ref]

        return ['https://www.mrw.es']

    @api.model
    def get_tracking_link(self, picking):
        if self.carrier_type == 'mrw':
            return self.get_mrw_url_tracking(picking)
        return super(DeliveryCarrier, self).get_tracking_link(picking)

    @api.model
    def _get_carrier_type_selection(self):
        """ Add MRW carrier type """
        res = super(DeliveryCarrier, self)._get_carrier_type_selection()
        res.append(('mrw', 'MRW'))
        return res

    mrw_config_id = fields.Many2one('mrw.config', string='MRW Config')
