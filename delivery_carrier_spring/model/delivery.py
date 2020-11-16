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
import logging

from datetime import datetime, timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.model
    def get_spring_url_tracking(self, picking):
        if picking.carrier_tracking_ref:
            return ['https://www.mailingtechnology.com/tracking/?tn=%s&testMode=%s' % (
            picking.carrier_tracking_ref, '0' if not self.spring_config_id.is_test else '1')]

        return [
            'https://www.mailingtechnology.com/tracking/?tn=&testMode=%s' % '0' if not self.spring_config_id.is_test else '1']

    @api.model
    def get_tracking_link(self, picking):

        if self.carrier_type == 'spring':
            return self.get_spring_url_tracking(picking)
        return super(DeliveryCarrier, self).get_tracking_link(picking)



    @api.model
    def _get_spring_carrier_tracks(self):
        date_from = datetime.now() - timedelta(days=self.spring_config_id.days_since_get_tracking)

        pickings = self.env['stock.picking'].search([('delivered', '=', False), ('carrier_id', '=', self.id), ('create_date', '>', date_from.isoformat())])
        for pick in pickings:
            try:
                pick.get_tracking_states()
            except Exception as e:
                _logger.error('Error has been produced getting tracking of picking: %s' % pick.name)

        return

    @api.multi
    def get_trackings(self):
        """ Get tracking states
        :return:

        """

        """ Add states tracking for Spring picking """
        self.ensure_one()
        if self.carrier_type == 'spring':
            return self._get_spring_carrier_tracks()
        return super(DeliveryCarrier, self).get_trackings()

    @api.model
    def _get_carrier_type_selection(self):
        """ Add Spring carrier type, it is mandatory """
        res = super(DeliveryCarrier, self)._get_carrier_type_selection()
        res.append(('spring', 'Spring'))
        return res

    spring_config_id = fields.Many2one('spring.config', string='Spring Config')
