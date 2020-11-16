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
{'name': 'Base module for carrier tracking',
 'version': '10.0.0.0.0',
 'author': "Halltic eSolutions S.L.",
 'maintainer': 'Halltic eSolutions S.L.',
 'category': 'Delivery',
 'complexity': 'normal',
 'depends': ['delivery'],
 'website': 'http://www.halltic.com/',
 'data': [
     'data/delivery_carrier_scheduler.xml',
     'views/stock.xml',
     'views/tracking.xml',
     'data/delivery_carrier_scheduler.xml',
     'security/ir.model.access.csv',
 ],
 'tests': [],
 'installable': True,
 'auto_install': False,
 'license': 'AGPL-3',
 }