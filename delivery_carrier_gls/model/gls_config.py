# -*- coding: utf-8 -*-
# Copyright 2020 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class GlsConfig(models.Model):
    _name = 'gls.config'

    name = fields.Char('Name', required=True)
    is_test = fields.Boolean('Is a test?')
    uid = fields.Char('User id')
    uid_test = fields.Char('User id test')
    url_shipment_path = fields.Char('Url shipment path', default='https://m.gls-spain.es/e/%s/%s/es')
    office_number = fields.Char('Office number')
