# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2020 Halltic eSolutions (http://halltic.com)
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

from odoo import fields, models, api


class WizardMoveStockPendingProduct(models.TransientModel):
    _name = 'delivery.move.stock.pending.product.wizard'
    _description = 'Wizard to move a number of products from stock pending project'

    product_id = fields.Many2one('product.product', required=True)
    number_of_products = fields.Integer('Number of products', required=True)


    @api.multi
    def move_pending_products(self):
        """
        Method for get the pending orders of the project of one product and move this to make the pickings
        :return:
        """
        i = 0
        tasks = self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'), ('stage_id.name', 'ilike', 'Pendientes de stock')], order='create_date asc')
        mass_shipment = self.env['mass.shipment.management'].browse(self._context.get('active_ids', []))
        for task in tasks:
            data = mass_shipment._get_sale_type_ship_from_task(task.name)
            if data:
                picking = data[1].picking_ids.sorted('create_date')[0]
                if picking.move_lines and len(picking.move_lines) == 1:
                    for move in picking.move_lines:
                        if move.product_id.id == self.product_id.id and i+move.product_uom_qty <= self.number_of_products:
                            i = i + move.product_uom_qty
                            if picking.sale_id.amazon_bind_ids:
                                mass_shipment._choose_carrier_amazon_sale(picking)
                                if picking.carrier_id and picking.carrier_id.carrier_type == 'correos':
                                    task.stage_id = self.env['project.task.type'].search(
                                        [('name', '=', 'Pendiente Correos'),
                                         ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
                                elif picking.carrier_id and picking.carrier_id.carrier_type in ('gls', 'mrw'):
                                    task.stage_id = self.env['project.task.type'].search(
                                        [('name', '=', 'Pendiente GLS'),
                                         ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
                                elif picking.carrier_id and picking.carrier_id.carrier_type == 'spring':
                                    task.stage_id = self.env['project.task.type'].search(
                                        [('name', '=', 'Pendiente Spring'),
                                         ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
                                else:
                                    task.stage_id = self.env['project.task.type'].search([('name', '=', 'Para Revisar'),
                                                                                          ('project_ids.name', '=',
                                                                                           'Gesti\xf3n env\xedos')]).id




        return {'type':'ir.actions.act_window_close'}
