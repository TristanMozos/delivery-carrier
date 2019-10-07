# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018 Halltic eSolutions S.L. (http://www.halltic.com)
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
from odoo import models, fields, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def _get_carrier_type_selection(self):
        """ Add Delnext carrier type """
        res = super(DeliveryCarrier, self)._get_carrier_type_selection()
        res.append(('delnext', 'Delnext'))
        return res

    @api.model
    def _get_delnext_service_type(self):
        return [
            ('1', 'Normal'),
            ('2', 'Express'),
            ('3', 'Urgente'),
        ]

    delnext_service_type = fields.Selection('_get_delnext_service_type', string='Delnext Service')

    delnext_config_id = fields.Many2one('delnext.config', string='Delnext Config')
