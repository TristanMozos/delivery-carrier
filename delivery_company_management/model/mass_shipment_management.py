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
import base64
import csv
import re

import logging
import os
import shutil
import tempfile
import unicodedata

from contextlib import closing
from odoo.modules.registry import RegistryManager
from pyPdf import PdfFileWriter, PdfFileReader

from odoo import models, fields, api, exceptions, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MassShipmentManagement(models.Model):
    _name = "mass.shipment.management"
    _order = "shipment_date desc"

    shipment_date = fields.Date('Shipment date', required=True)
    label = fields.Date('Shipment Label')

    state = fields.Selection([
        ('import', 'Import'),
        ('generate', 'Generate'),
        ('confirm', 'Confirm'),
        ('closed', 'Closed')
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='import')

    stock_picking_ids = fields.One2many(comodel_name='mass.shipment.stock.picking',
                                        inverse_name='mass_delivery_id')

    imported_pending_orders = fields.Boolean('Flag pending orders', default=False, help='Flag to mark the import of orders has been done')

    error_message = fields.Char('Error message generating orders')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.shipment_date))
        return result

    def _merge_pdf(self, documents, picking_ids=None, picking_errors=[]):
        """Merge PDF files into one.

        :param documents: list of path of pdf files
        :returns: path of the merged pdf
        """
        writer = PdfFileWriter()
        streams = []  # We have to close the streams *after* PdfFilWriter's call to write()
        try:
            i = 0
            for document in documents:
                pdfreport = file(document, 'rb')
                streams.append(pdfreport)
                try:
                    reader = PdfFileReader(pdfreport)
                    for page in range(0, reader.getNumPages()):
                        writer.addPage(reader.getPage(page))
                except Exception as e:
                    if picking_ids:
                        picking_errors.append(picking_ids[i])
                    else:
                        raise e
                i += 1

            merged_file_fd, merged_file_path = tempfile.mkstemp(suffix='.pdf', prefix='label.tmp.')
            with closing(os.fdopen(merged_file_fd, 'w')) as merged_file:
                writer.write(merged_file)
        finally:
            for stream in streams:
                try:
                    stream.close()
                except Exception:
                    pass

        return merged_file_path

    def _get_carriers(self, amazon_market_product, sale):
        if not sale or not sale.shipment_service_level_category:
            return
        if 'Standard' in sale.shipment_service_level_category:
            delivery_carriers = [template_ship.delivery_standard_carrier_ids for template_ship in
                                 amazon_market_product.product_id.backend_id.shipping_template_ids
                                 if template_ship.name == amazon_market_product.merchant_shipping_group and
                                 template_ship.marketplace_id.id == amazon_market_product.marketplace_id.id]
        else:
            delivery_carriers = [template_ship.delivery_expedited_carrier_ids for template_ship in
                                 amazon_market_product.product_id.backend_id.shipping_template_ids
                                 if template_ship.name == amazon_market_product.merchant_shipping_group and
                                 template_ship.marketplace_id.id == amazon_market_product.marketplace_id.id]

        return delivery_carriers

    def eq_plain(self, s1, s2):

        if s1 == None and s2 == None:
            return True
        elif s1 != None and s2 == None or s1 == None and s2 != None:
            return False

        def normalize(c):
            return unicodedata.normalize("NFD", c)[0].upper()

        return all((normalize(c1) == normalize(c2)) for (c1, c2) in zip(s1, s2))

    @api.multi
    def check_sale_picking_task(self, name):
        return self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'), ('name', 'ilike', name)])

        return

    def _check_same_reference_task_picking(self, dict_references, picking):
        same_pick = True
        if not dict_references:
            return same_pick
        for move in picking.move_lines:
            if not dict_references.get(move.product_id.default_code) or float(dict_references[move.product_id.default_code]) != move.product_uom_qty:
                same_pick = False
        return same_pick

    def _get_dict_number_ship_reference(self, reference_ship):
        dict_references = {}
        if reference_ship:
            reference_split = reference_ship.split('|')
            for reference in reference_split:
                if not dict_references.get(reference):
                    dict_references[reference] = 1
                else:
                    dict_references[reference] = dict_references[reference] + 1
        return dict_references

    def _get_sale_type_ship_from_task(self, task_name):
        name_split = task_name.split(';')
        type_ship = None
        ship_name = None
        reference_ship = None

        if len(name_split) == 1:
            ship_name = name_split[0]
        elif len(name_split) == 2:
            type_ship = name_split[0]
            ship_name = name_split[1]
        elif len(name_split) == 3:
            type_ship = name_split[0]
            ship_name = name_split[1]
            reference_ship = name_split[2]

        ship_name = ship_name.strip() if ship_name else ''

        # If we haven't sale or we have two sales with search params we aren't manage the task
        sale = self.env['sale.order'].search(['|', ('name', 'ilike', '%s' % ship_name), ('partner_shipping_id.name', 'ilike', '%s' % ship_name)])

        if sale and len(sale) > 1:
            sale = self.env['sale.order'].search(['|', ('name', '=', ship_name)])

        if len(name_split) == 2 and not sale:
            sale = self.env['sale.order'].search(['|', ('name', 'ilike', '%s' % type_ship), ('partner_shipping_id.name', 'ilike', '%s' % type_ship)])
            if sale:
                reference_ship = ship_name

        dict_references = self._get_dict_number_ship_reference(reference_ship)

        # TODO the first line check we will need to remove when the development has be done
        if not (not type_ship or self.eq_plain(type_ship, u'envio') or self.eq_plain(type_ship, u'reenvio')) or \
                not sale or len(sale) > 1 or not self._check_same_reference_task_picking(dict_references, sale.picking_ids.sorted('create_date')[0]):
            return

        return [type_ship, sale] if sale else None

    def _choose_picking_from_task(self, task):

        picking = None

        aux = self._get_sale_type_ship_from_task(task.name)
        if aux:
            type_ship = aux[0]
            sale = aux[1]

            if not type_ship or self.eq_plain(type_ship, u'envio'):
                picking = sale.picking_ids.sorted('create_date')[0] if sale.picking_ids else None
            elif self.eq_plain(type_ship, u'reenvio'):
                # We are going to create a new picking and move the task to closed stage
                picking = sale.picking_ids.sorted('create_date')[0].copy() if sale.picking_ids else None
                picking.action_assign()
                task.stage_id = self.env['project.task.type'].search([('name', '=', 'Cerrado'),
                                                                      ('project_ids.name', '=',
                                                                       'Gesti\xf3n env\xedos')]).id
            elif self.eq_plain(type_ship, u'retorno'):
                picking = sale.picking_ids.sorted('create_date')[0].copy() if sale.picking_ids else None
            elif self.eq_plain(type_ship, u'canje'):
                picking = sale.picking_ids.sorted('create_date')[0].copy() if sale.picking_ids else None

            return (picking, sale, type_ship) if picking and sale else None

    def _create_mass_ship_from_task(self, task, carrier_id):
        data = self._choose_picking_from_task(task)

        if not data:
            return

        if not carrier_id:
            carrier_id = self._choose_carrier(data[0]) or self.env['delivery.carrier'].browse(1)

        if not data[0].id in self.stock_picking_ids.mapped('stock_picking_id').mapped('id'):
            type_ship = '0'
            if self.eq_plain(data[2], u'reenvio'):
                type_ship = '3'
            elif self.eq_plain(data[2], u'canje'):
                type_ship = '1'
            elif self.eq_plain(data[2], u'retorno'):
                type_ship = '2'

            vals = {'mass_delivery_id':self.id,
                    'stock_picking_id':data[0].id,
                    'type_ship':type_ship,
                    'sale_order_id':data[1].id,
                    'delivery_carrier_id':carrier_id.id,
                    'task_id':task.id
                    }
            return self.env['mass.shipment.stock.picking'].create(vals)
        else:
            stock_picking = self.stock_picking_ids.filtered(lambda x:x.stock_picking_id.id == data[0].id and x.mass_delivery_id.id == self.id)
            stock_picking.task_id = task.id

    @api.multi
    def _move_pending_stock_task(self):
        tasks = self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'), ('stage_id.name', 'ilike', 'Pendientes de stock')])

        picking_ids = self.stock_picking_ids.mapped('stock_picking_id').mapped('id')

        for task in tasks:
            data = self._get_sale_type_ship_from_task(task.name)
            if data:
                # Check if there is the same sale on the day
                picking = data[1].picking_ids.sorted('create_date')[0]
                if picking.id in picking_ids:
                    task.stage_id = self.env['project.task.type'].search([('name', '=', 'Cerrado'),
                                                                          ('project_ids.name', '=',
                                                                           'Gesti\xf3n env\xedos')]).id
                else:
                    move_task = True
                    picking = data[1].picking_ids.sorted('create_date')[0]
                    for move in picking.move_lines:
                        if move.product_id.qty_available < 0 or move.product_id.virtual_available < 0:
                            move_task = False

                    if move_task and data[1].amazon_bind_ids:
                        self._choose_carrier_amazon_sale(picking)
                        if picking.carrier_id and picking.carrier_id.carrier_type == 'correos':
                            task.stage_id = self.env['project.task.type'].search([('name', '=', 'Pendiente Correos'),
                                                                                  ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
                        elif picking.carrier_id and picking.carrier_id.carrier_type in ('gls', 'mrw'):
                            task.stage_id = self.env['project.task.type'].search([('name', '=', 'Pendiente GLS'),
                                                                                  ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
                        elif picking.carrier_id and picking.carrier_id.carrier_type == 'spring':
                            task.stage_id = self.env['project.task.type'].search([('name', '=', 'Pendiente Spring'),
                                                                                  ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
                        else:
                            task.stage_id = self.env['project.task.type'].search([('name', '=', 'Para Revisar'),
                                                                                  ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id

    def _get_pending_orders_from_projects(self):
        """
        Method to get the sales from "Gestión envíos" project
        :return:
        """

        task_ids = self.stock_picking_ids.mapped('task_id').mapped('id')
        tasks = self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'),
                                                 ('stage_id.name', 'ilike', 'Pendiente GLS'),
                                                 ('id', 'not in', task_ids)])
        carrier_id = self.env['delivery.carrier'].search([('name', '=', 'GLS Economy')])
        for task in tasks:
            try:
                self._create_mass_ship_from_task(task, carrier_id)
            except Exception as e:
                _logger = logging.getLogger(e.message)

        carrier_id = None
        tasks = self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'),
                                                 ('stage_id.name', 'ilike', 'Pendiente Spring'),
                                                 ('id', 'not in', task_ids)])
        for task in tasks:
            try:
                self._create_mass_ship_from_task(task, carrier_id)
            except Exception as e:
                _logger = logging.getLogger(e.message)

        tasks = self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'),
                                                 ('stage_id.name', 'ilike', 'Pendiente Correos'),
                                                 ('id', 'not in', task_ids)])
        carrier_id = self.env['delivery.carrier'].search([('name', '=', 'Correos Ordinario Nacional')])
        for task in tasks:
            try:
                self._create_mass_ship_from_task(task, carrier_id)
            except Exception as e:
                _logger = logging.getLogger(e.message)

        tasks = self.env['project.task'].search([('project_id.name', '=', 'Gesti\xf3n env\xedos'),
                                                 ('stage_id.name', 'ilike', 'Pendiente Certificado'),
                                                 ('id', 'not in', task_ids)])
        carrier_id = self.env['delivery.carrier'].search([('name', '=', 'Correos Certificado Nacional')])
        for task in tasks:
            try:
                data = self._choose_picking_from_task(task)
                if data and self._check_canarian_ship(data[1].partner_id) and data[1].partner_id.vat:
                    self._create_mass_ship_from_task(task, carrier_id)
                else:
                    task.stage_id = self.env['project.task.type'].search([('name', '=', 'Pendiente DNI Canarias/Ceuta/Melilla'),
                                                                          ('project_ids.name', '=',
                                                                           'Gesti\xf3n env\xedos')]).id

            except Exception as e:
                _logger = logging.getLogger(e.message)

        return

    @api.model
    def _manage_waiting_orders(self):
        self._generate_waiting_report()

    # Deprecated method
    @api.multi
    def _save_waiting_orders(self):
        """
        @Deprecated
        Save waiting avaiability picking on project tasks
        We are assuming the waiting available picks aren't on project before
        :return:
        """

        pendientes_stock_stage_id = self.env['project.task.type'].search([('name', '=', 'Pendientes de stock'),
                                                                          ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id

        waiting_picking_ids = self.stock_picking_ids.filtered('waiting_send')

        # We get the project to add tasks
        project = self.env['project.project'].search([('name', '=', 'Gesti\xf3n env\xedos')])
        for wait_pick in waiting_picking_ids:
            if wait_pick.is_done:
                task_count = self.env['project.task'].search_count([('project_id.name', '=', 'Gesti\xf3n env\xedos'),
                                                                    ('name', 'ilike', wait_pick.sale_order_id.name)])

                if task_count < 1:
                    project.write({'task_ids':[(0, 0, {'name':wait_pick.sale_order_id.name,
                                                       'stage_id':pendientes_stock_stage_id,
                                                       'partner_id':wait_pick.sale_order_id.partner_id.id,
                                                       'description':wait_pick.ship_reference})]})

        return

    def get_orders_from_project(self):
        try:
            self._move_pending_stock_task()
        except Exception as e:
            _logger = logging.getLogger(e.message)

        try:
            self._get_pending_orders_from_projects()
        except Exception as e:
            _logger = logging.getLogger(e.message)

        return

    def close_day(self):
        self.state = 'closed'

    def get_pending_orders(self):
        """
        Method to get the pending order to send from pickins and project
        :return:
        """
        pickings = self.env['stock.picking'].search(
            [('state', 'in', ('assigned', 'confirmed')),
             ('picking_type_code', '=', 'outgoing'),
             ('id', 'not in', self.stock_picking_ids.mapped('stock_picking_id').ids)])

        for picking in pickings:
            if picking.state == 'confirmed':
                picking.action_assign()

            # If the sale is an Amazon sale, we are going to get the carrier configurated
            if picking.sale_id.amazon_bind_ids:
                self._choose_carrier_amazon_sale(picking)

            delivery_carrier_id = self._choose_carrier(picking) or self.env['delivery.carrier'].browse(1)

            self.write({'stock_picking_ids':[(0, 0, {'stock_picking_id':picking.id,
                                                     'type_ship':'0',
                                                     'sale_order_id':picking.sale_id.id,
                                                     'delivery_carrier_id':delivery_carrier_id.id,
                                                     })
                                             ]})

        self.get_orders_from_project()
        self.state = 'generate'
        return

    def _generate_gls_order(self, order):
        """
        Method to generate the order con GLS carrier with our params
        :param order:
        :return:
        """
        _logger.info('Mass Shipment generate gls order picking: %s' % order.stock_picking_id.name)
        try:
            picking = order.stock_picking_id

            # If we haven't a tracking of the carrier we must to generate one
            if not picking.carrier_tracking_ref:
                picking.min_date = self.shipment_date
                picking.carrier_id = order.delivery_carrier_id
                if order.type_ship in ('0', '3'):
                    picking.gls_service_type = picking.carrier_id.code or '1'
                    """
                        0	10:00 Service	Para el servicio 1 (COURIER)
                        2	14:00 Service	Para el servicio 1 (COURIER)
                        3	BusinessParcel	Para el servicio 1 (COURIER)
                        5	SaturdayService
                        7	INTERDIA
                        9	Franja Horaria
                        4	Masivo	Para el servicio 1 (COURIER)
                        10	Maritimo	Para el servicio 6 (CARGA)
                        11	Rec. en NAVE.
                        13	Ent. Pto. ASM
                        18	EconomyParcel Para el servicio 37 (ECONOMY)
                        19	ParcelShop
                    """
                    if picking.gls_service_type == '1':
                        picking.gls_schedule = '4'

                try:
                    picking.action_generate_carrier_label()
                except UserError as e:
                    if e.name == u'Ya existe el albaran':
                        # Get the last label
                        if not picking.carrier_tracking_ref:
                            _logger.error('Existe albarán sin referencia: %s' % str(picking.name))
                        picking.generate_labels(package_ids=picking.name)
                    else:
                        order.error_message = e.name
                        self.env.cr.commit()

            # When we have a tracking number we validate the picking
            if picking.carrier_tracking_ref and not order.waiting_send:
                picking.action_done()
                order.write({'is_done':True, 'error_message':None})

            self.env.cr.commit()
            _logger.info('Commit executed on mass Shipment generate gls order picking: %s' % order.stock_picking_id.name)
        except UserError as e:
            order.error_message = e.name
            self.env.cr.commit()
            _logger.info('Rollback executed on mass Shipment generate gls order picking: %s' % order.stock_picking_id.name)
        except Exception as e:
            order.error_message = e.message
            self.env.cr.commit()
            _logger.info('Rollback executed on mass Shipment generate gls order picking: %s' % order.stock_picking_id.name)

    @api.model
    def _generate_correos_order(self, order):
        """
        Method to confirm the shiment
        We are going to check if the canarian partner of the order has got vat
        :param order:
        :return:
        """
        if order.waiting_send:
            return
        elif self._check_canarian_ship(order.stock_picking_id.partner_id) and not order.stock_picking_id.partner_id.vat:
            # Create task if there isn't one yet
            task = order.task_id or self.check_sale_picking_task(self.get_id_order_from_marketplace(order.stock_picking_id.sale_id))
            stage_id = self.env['project.task.type'].search([('name', '=', 'Pendiente DNI Canarias/Ceuta/Melilla'),
                                                             ('project_ids.name', '=', 'Gesti\xf3n env\xedos')])
            if not task:
                # If the order hasn't got a task, we check if there are any task with the same sale
                project = self.env['project.project'].search([('name', '=', 'Gesti\xf3n env\xedos')])
                task = self.env['project.task'].create({'project_id':project.id,
                                                        'name':order.sale_order_id.name,
                                                        'stage_id':stage_id.id,
                                                        'partner_id':order.sale_order_id.partner_id.id,
                                                        'description':order.ship_reference})
                order.task_id = task.id
            else:
                task.stage_id = stage_id.id

            order.waiting_send = True

            return

        order.stock_picking_id.carrier_id = order.delivery_carrier_id
        order.stock_picking_id.action_done()
        order.is_done = True

    def _generate_spring_order(self, order):
        _logger.info('Mass Shipment generate spring order picking: %s' % order.stock_picking_id.name)
        try:
            picking = order.stock_picking_id
            if not picking.carrier_tracking_ref:
                picking.min_date = self.shipment_date
                picking.carrier_id = order.delivery_carrier_id
                if order.type_ship in ('0', '3'):
                    picking.spring_service_type = order.delivery_carrier_id.code
                try:
                    picking.action_generate_carrier_label()
                except UserError as e:
                    if e.name == 'This Shipper Reference already exists':
                        # Get the last label
                        picking.generate_labels(package_ids=picking.name)

            # When we have a tracking number we validate the picking
            if picking.carrier_tracking_ref:
                picking.action_done()
                order.write({'is_done':True, 'error_message':None})
                self.env.cr.commit()

            _logger.info('Mass Shipment generate spring order picking: %s' % order.stock_picking_id.name)
        except UserError as e:
            order.error_message = e.name
            self.env.cr.commit()
        except Exception as e:
            order.error_message = e.message
            self.env.cr.commit()

    def _generate_gls_labels(self):
        try:
            self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', 'gls')]).unlink()
            with tools.osutil.tempdir() as path_temp_dir:
                filestore_path = self.env['ir.attachment']._filestore()

                picking_ids = []
                path_list = []
                picking_errors = []
                order_pickings = self.stock_picking_ids.sorted('ship_reference')
                for pick in order_pickings:
                    if pick.is_done and not pick.waiting_send and pick.stock_picking_id.carrier_id and 'gls' in pick.stock_picking_id.carrier_id.carrier_type:
                        # We get only the last label that we had generated
                        attachments = self.env['ir.attachment'].search([('res_id', '=', pick.stock_picking_id.id), ('res_model', '=', 'stock.picking')],
                                                                       order='id DESC',
                                                                       limit=1)
                        for attachment in attachments:
                            if attachment.store_fname:
                                shutil.copy2('%s/%s' % (filestore_path, attachment.store_fname), path_temp_dir)
                                path_list.append('%s/%s' % (path_temp_dir, attachment.checksum))
                                picking_ids.append(pick)

                if path_list:
                    mergue_file_path = self._merge_pdf(path_list, picking_ids, picking_errors)
                    attachment_vals = {
                        'name':'%s_%s' % (self.shipment_date, 'gls_labels.pdf'),
                        'datas':base64.b64encode(open(mergue_file_path, "rb").read()),
                        'datas_fname':'%s_%s' % (self.shipment_date, 'gls_labels.pdf'),
                        'res_model':self._name,
                        'res_id':self.id,
                    }
                    self.env['ir.attachment'].create(attachment_vals)

                    if picking_errors:
                        self._save_csv_error_generating_labels('gls_error_labels', picking_errors)


        except Exception as e:
            _logger.error('Error has been produced generating gls labels: %s' % e.message)
            self.error_message = e.message

    def _generate_spring_labels(self):
        try:
            self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', 'spring')]).unlink()
            with tools.osutil.tempdir() as path_temp_dir:
                filestore_path = self.env['ir.attachment']._filestore()

                picking_ids = []
                path_list = []
                picking_errors = []
                order_pickings = self.stock_picking_ids.sorted('ship_reference')
                for pick in order_pickings:
                    if pick.is_done and not pick.waiting_send and pick.stock_picking_id.carrier_id and 'spring' in pick.stock_picking_id.carrier_id.carrier_type:
                        attachments = self.env['ir.attachment'].search([('res_id', '=', pick.stock_picking_id.id), ('res_model', '=', 'stock.picking')],
                                                                       order='id DESC',
                                                                       limit=1)
                        for attachment in attachments:
                            if attachment.store_fname:
                                shutil.copy2('%s/%s' % (filestore_path, attachment.store_fname), path_temp_dir)
                                path_list.append('%s/%s' % (path_temp_dir, attachment.checksum))
                                picking_ids.append(pick)

                if path_list:
                    mergue_file_path = self._merge_pdf(path_list, picking_ids, picking_errors)
                    attachment_vals = {
                        'name':'%s_%s' % (self.shipment_date, 'spring_labels.pdf'),
                        'datas':base64.b64encode(open(mergue_file_path, "rb").read()),
                        'datas_fname':'%s_%s' % (self.shipment_date, 'spring_labels.pdf'),
                        'res_model':self._name,
                        'res_id':self.id,
                    }
                    self.env['ir.attachment'].create(attachment_vals)

                    if picking_errors:
                        self._save_csv_error_generating_labels('spring_error_labels', picking_errors)

        except Exception as e:
            _logger.error('Error has been produced generating spring labels: %s' % e)
            self.error_message = e.message

    @api.model
    def _get_address(self, partner_address):
        address = ''
        if partner_address.street:
            address = partner_address.street
        if partner_address.street2:
            address = address + ' ' + partner_address.street2
        if partner_address.street3:
            address = address + ' ' + partner_address.street3

        return address

    def _generate_correos_labels(self):
        """
        This method delete labels of correos and generate three types of labels:
        1- Pdf with invoices that we need to print
        2- Csv with ordinary shipments of correos
        3- Csv for upload certificate shipments to correos page
        :return:
        """
        with tools.osutil.tempdir() as path_temp_dir:
            try:
                self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', 'correos_labels')]).unlink()
                self.env['ir.attachment'].search(
                    [('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', 'correos_cert_invoices')]).unlink()
                self.env['ir.attachment'].search(
                    [('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', 'correos_cert_shipments')]).unlink()

                filas_csv = []
                path_list = []
                cert_csv = []
                order_pickings = self.stock_picking_ids.sorted('ship_reference')
                for stock_piking in order_pickings:
                    if stock_piking.delivery_carrier_id.carrier_type == 'correos' and stock_piking.is_done and 'Certificado' not in stock_piking.delivery_carrier_id.name:
                        fila = [stock_piking.stock_picking_id.partner_id.name.encode('utf-8', 'ignore'),
                                ('%s %s' % (stock_piking.stock_picking_id.partner_id.street, stock_piking.stock_picking_id.partner_id.street2 or '')).encode(
                                    'utf-8',
                                    'ignore'),
                                ('%s %s' % (stock_piking.stock_picking_id.partner_id.zip, stock_piking.stock_picking_id.partner_id.city)).encode('utf-8',
                                                                                                                                                 'ignore'),
                                'Ref: ' + stock_piking.ship_reference]
                        filas_csv.append(fila)
                    elif stock_piking.delivery_carrier_id.carrier_type == 'correos' and stock_piking.is_done and 'Certificado' in stock_piking.delivery_carrier_id.name:
                        path_temp_list = self._generate_invoices_correos_cert(stock_piking, path_temp_dir)
                        if path_temp_list:
                            i = 0
                            while i < 3:
                                path_list.extend(path_temp_list)
                                i += 1

                            split_name = stock_piking.stock_picking_id.partner_id.name.split(' ')
                            name = ''
                            surname = ''

                            first_piece = True
                            for piece in split_name:
                                if first_piece:
                                    first_piece = False
                                    name = piece
                                else:
                                    surname = ('%s %s' % (surname, piece)).strip()

                            split_address = self._get_address(stock_piking.stock_picking_id.partner_id).split(' ')
                            nombre_via = ''
                            numero_via = ''
                            portal_via = ''
                            number_found = False
                            for piece in split_address:
                                # If we are found a number we assume this is the number of street
                                if not number_found and re.findall('([0-9])+\w{0,10}', piece):
                                    numero_via = piece
                                    number_found = True
                                elif number_found:
                                    portal_via = ('%s %s' % (portal_via, piece)).strip()
                                else:
                                    nombre_via = ('%s %s' % (nombre_via, piece)).strip()

                            fila_cert_csv = [name.encode('utf-8', 'ignore'),  # Nombre	Nombre del destinatario
                                             surname.encode('utf-8', 'ignore') if surname else '',  # Apellido 1	Primer apellido del destinatario
                                             '',  # Apellido 2	Segundo apellido del destinatario
                                             '',  # Empresa	Empresa
                                             '',  # Tipo Documento	Documento acreditativo
                                             stock_piking.stock_picking_id.partner_id.vat,  # Número Documento	Identificador
                                             stock_piking.stock_picking_id.partner_id.phone.encode('utf-8',
                                                                                                   'ignore') if stock_piking.stock_picking_id.partner_id.phone else '',
                                             # Teléfono	Teléfono de contacto receptor
                                             stock_piking.stock_picking_id.partner_id.email.encode('utf-8',
                                                                                                   'ignore') if stock_piking.stock_picking_id.partner_id.email else '',
                                             # Email	Email del receptor
                                             '',  # Idioma	Idioma en que llegarán los mensajes de los eventos realizados con el envío
                                             '',  # Tipo vía	Tipo vía
                                             nombre_via.encode('utf-8', 'ignore') if nombre_via else '',  # Nombre vía	Nombre vía destino
                                             numero_via.encode('utf-8', 'ignore') if numero_via else '',  # Número	Número de la vía destino
                                             '',  # Bloque	Bloque del destinatario
                                             portal_via.encode('utf-8', 'ignore') if portal_via else '',  # Portal	Portal del destinatario
                                             '',  # Escalera	Escalera del destinatario
                                             '',  # Piso	Piso del destinatario
                                             '',  # Puerta	Puerta del destinatario
                                             '',  # Dirección extranjera	No aplica
                                             stock_piking.stock_picking_id.partner_id.zip,  # Código Postal	Código postal del destinatario
                                             stock_piking.stock_picking_id.partner_id.city.encode('utf-8',
                                                                                                  'ignore') if stock_piking.stock_picking_id.partner_id.city else '',
                                             # Localidad	Localidad del destinatario
                                             '',  # Provincia	Provincia del destinatario
                                             stock_piking.stock_picking_id.partner_id.country_id.code,  # País	ES
                                             '',  # Apartado postal	Apartado postal del destinatario (si aplica)
                                             '',  # Alias	Identificador del destinatario interno
                                             'E',  # Fin de Registro	Valor fijo obligatorio: E
                                             ]
                            cert_csv.append(fila_cert_csv)

                if filas_csv:
                    with tools.osutil.tempdir() as path_temp_dir:
                        myf = open('%s/temp.csv' % path_temp_dir, 'w+')
                        writer = csv.writer(myf, delimiter=',', lineterminator='\n')
                        for row in filas_csv:
                            writer.writerow(row)
                        myf.close()

                        attachment_vals = {
                            'name':'%s_%s' % (self.shipment_date, 'correos_labels.csv'),
                            'datas':base64.b64encode(open('%s/temp.csv' % path_temp_dir, "rb").read()),
                            'datas_fname':'%s_%s' % (self.shipment_date, 'correos_labels.csv'),
                            'res_model':self._name,
                            'res_id':self.id,
                        }
                        self.env['ir.attachment'].create(attachment_vals)

                if cert_csv:
                    with tools.osutil.tempdir() as path_temp_dir:
                        myf = open('%s/temp.csv' % path_temp_dir, 'w+')
                        writer = csv.writer(myf, delimiter=',', lineterminator='\n')
                        for row in cert_csv:
                            writer.writerow(row)
                        myf.close()

                        attachment_vals = {
                            'name':'%s_%s' % (self.shipment_date, 'correos_cert_shipments.txt'),
                            'datas':base64.b64encode(open('%s/temp.csv' % path_temp_dir, "rb").read()),
                            'datas_fname':'%s_%s' % (self.shipment_date, 'correos_cert_shipments.txt'),
                            'res_model':self._name,
                            'res_id':self.id,
                        }
                        self.env['ir.attachment'].create(attachment_vals)

                if path_list:
                    mergue_file_path = self._merge_pdf(path_list)
                    attachment_vals = {
                        'name':'%s_%s' % (self.shipment_date, 'correos_cert_invoices.pdf'),
                        'datas':base64.b64encode(open(mergue_file_path, "rb").read()),
                        'datas_fname':'%s_%s' % (self.shipment_date, 'correos_cert_invoices.pdf'),
                        'res_model':self._name,
                        'res_id':self.id,
                    }
                    self.env['ir.attachment'].create(attachment_vals)


            except Exception as e:
                self.error_message = e.message

        return

    def _generate_manifest_reference_count(self):
        try:
            self.env['ir.attachment'].search(['&', ('res_model', '=', self._name),
                                              ('res_id', '=', self.id),
                                              '|',
                                              ('name', 'ilike', 'manifest'),
                                              ('name', 'ilike', 'reference_count')]).unlink()

            ship_stock_pick = self.env['mass.shipment.stock.picking'].search(
                [('mass_delivery_id', '=', self.id), ('is_done', '=', True), ('waiting_send', '=', False)]).sorted(
                'ship_reference').sorted('delivery_carrier_type')
            with tools.osutil.tempdir() as path_temp_dir:
                manifest_file = open('%s/manifest.txt' % path_temp_dir, 'w+')
                reference_count_file = open('%s/reference_count.txt' % path_temp_dir, 'w+')
                carrier = None
                reference = None
                reference_count = 0
                for order_done in ship_stock_pick:
                    # Count the references
                    if not reference:
                        reference = order_done.ship_reference

                    if not carrier or carrier != order_done.delivery_carrier_id.carrier_type:
                        carrier = order_done.delivery_carrier_id.carrier_type
                        carrier_title = '-------------------------------- %s --------------------------------\n' % order_done.delivery_carrier_id.carrier_type.capitalize() if order_done.delivery_carrier_id and order_done.delivery_carrier_id.carrier_type else ''
                        manifest_file.write(carrier_title)
                        if reference_count != 0:
                            # if the carrier change, the count of reference change too
                            reference_count_file.write('%s of %s \n' % (reference_count, reference))
                            reference = order_done.ship_reference
                        reference_count = 1
                        reference_count_file.write(carrier_title)

                    elif reference != order_done.ship_reference:
                        reference_count_file.write('%s of %s \n' % (reference_count, reference))
                        reference = order_done.ship_reference
                        reference_count = 1
                    else:
                        reference_count += 1

                    ship_reference = order_done.stock_picking_id.carrier_tracking_ref or order_done.stock_picking_id.name
                    row = ('%s %s %s %s\n' % (order_done.delivery_carrier_id.carrier_type,
                                              ship_reference,
                                              order_done.stock_picking_id.partner_id.name,
                                              order_done.ship_reference)).encode('utf-8', 'ignore')
                    manifest_file.write(row)

                reference_count_file.write('%s of %s \n' % (reference_count, reference))
                manifest_file.close()
                reference_count_file.close()
                attachment_vals = {
                    'name':'%s_%s' % (self.shipment_date, 'manifest.txt'),
                    'datas':base64.b64encode(open('%s/manifest.txt' % path_temp_dir, "rb").read()),
                    'datas_fname':'%s_%s' % (self.shipment_date, 'manifest.txt'),
                    'res_model':self._name,
                    'res_id':self.id,
                }
                self.env['ir.attachment'].create(attachment_vals)
                attachment_vals = {
                    'name':'%s_%s' % (self.shipment_date, 'reference_count.txt'),
                    'datas':base64.b64encode(open('%s/reference_count.txt' % path_temp_dir, "rb").read()),
                    'datas_fname':'%s_%s' % (self.shipment_date, 'reference_count.txt'),
                    'res_model':self._name,
                    'res_id':self.id,
                }
                self.env['ir.attachment'].create(attachment_vals)

        except Exception as e:
            self.error_message = e.message

    def _generate_invoices_correos_cert(self, order, path_temp_dir):
        """

        :param order:
        :return:
        """
        path_list = []
        filestore_path = self.env['ir.attachment']._filestore()
        # If we haven't and invoice we create it
        if not order.sale_order_id.invoice_ids and order.sale_order_id.state == 'sale' and order.sale_order_id.partner_id.vat:
            sale_wizard = self.env['sale.advance.payment.inv'].create({}).with_context(active_ids=order.sale_order_id.id)
            sale_wizard.advance_payment_method = 'all'
            sale_wizard.create_invoices()

        for invoice in order.sale_order_id.invoice_ids:
            if invoice.state == 'draft':
                invoice.action_invoice_open()

            # TODO print the invoice, with the next code the invoice doesn't print and the code only is usefull if we had created the invoice before
            """
            invoice.with_context(active_id=order.sale_order_id.id,
                                 active_ids=[order.sale_order_id.id],
                                 active_model='sale.order',
                                 journal_type='sale',
                                 search_disable_custom_filters=True,
                                 type=invoice.type).invoice_print()
            """
            attachments = self.env['ir.attachment'].search([('res_id', '=', invoice.id), ('res_model', '=', 'account.invoice')])
            for attachment in attachments:
                if attachment.store_fname:
                    shutil.copy2('%s/%s' % (filestore_path, attachment.store_fname), path_temp_dir)
                    path_list.append('%s/%s' % (path_temp_dir, attachment.checksum))

        return path_list

    def _generate_waiting_report(self):
        """
        Method that generate a report with the waiting pick
        :return:
        """
        try:
            self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', 'waiting')]).unlink()
            filas_csv = []
            order_pickings = self.stock_picking_ids.sorted('ship_reference')
            for stock_piking in order_pickings:
                if stock_piking.is_done and stock_piking.waiting_send:
                    fila = [stock_piking.sale_order_id.name,
                            stock_piking.delivery_carrier_name,
                            stock_piking.delivery_carrier_type,
                            stock_piking.stock_picking_id.carrier_tracking_ref,
                            stock_piking.ship_reference,
                            ]
                    filas_csv.append(fila)

            if filas_csv:
                with tools.osutil.tempdir() as path_temp_dir:
                    myf = open('%s/temp.csv' % path_temp_dir, 'w+')
                    writer = csv.writer(myf, delimiter=',', lineterminator='\n')
                    for row in filas_csv:
                        writer.writerow(row)
                    myf.close()

                    attachment_vals = {
                        'name':'%s_%s' % (self.shipment_date, 'waiting_send.csv'),
                        'datas':base64.b64encode(open('%s/temp.csv' % path_temp_dir, "rb").read()),
                        'datas_fname':'%s_%s' % (self.shipment_date, 'waiting_send.csv'),
                        'res_model':self._name,
                        'res_id':self.id,
                    }
                    self.env['ir.attachment'].create(attachment_vals)
        except Exception as e:
            self.error_message = e.message

        return

    def _save_csv_error_generating_labels(self, name_csv, picking_refereces):
        """
                Method that generate a report with the waiting pick
                :return:
                """
        try:
            self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('name', 'ilike', name_csv)]).unlink()
            filas_csv = []
            for stock_piking in picking_refereces:
                fila = [stock_piking.sale_order_id.name,
                        stock_piking.delivery_carrier_name,
                        stock_piking.delivery_carrier_type,
                        stock_piking.stock_picking_id.carrier_tracking_ref,
                        stock_piking.ship_reference,
                        ]
                filas_csv.append(fila)

            if filas_csv:
                with tools.osutil.tempdir() as path_temp_dir:
                    myf = open('%s/temp.csv' % path_temp_dir, 'w+')
                    writer = csv.writer(myf, delimiter=',', lineterminator='\n')
                    for row in filas_csv:
                        writer.writerow(row)
                    myf.close()

                    attachment_vals = {
                        'name':'%s_%s' % (self.shipment_date, '%s.csv' % name_csv),
                        'datas':base64.b64encode(open('%s/temp.csv' % path_temp_dir, "rb").read()),
                        'datas_fname':'%s_%s' % (self.shipment_date, '%s.csv' % name_csv),
                        'res_model':self._name,
                        'res_id':self.id,
                    }
                    self.env['ir.attachment'].create(attachment_vals)
        except Exception as e:
            self.error_message = e.message

        return

    def _move_orders_to_send_task(self, task):
        """
        Method to move the task to send stage when
        :param task:
        :return:
        """
        task.stage_id = self.env['project.task.type'].search([('name', '=', 'Enviado'),
                                                              ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id
        issue = self.env['project.issue'].search([('id', '=', task.project_id.id), ('task_id', '=', task.id)])
        if issue:
            issue.stage_id = self.env['project.task.type'].search([('name', '=', 'Pedido reenviado'),
                                                                   ('project_ids.name', 'ilike', 'Incidencias de pedidos')]).id

        self.env.cr.commit()

        return

    def move_done_orders_to_send_task(self):
        """
        Method to move the task to send stage when the picking has been send
        :return:
        """
        stage_send_id = self.env['project.task.type'].search([('name', '=', 'Enviado'),
                                                              ('project_ids.name', '=', 'Gesti\xf3n env\xedos')]).id

        stock_pickins = self.stock_picking_ids.filtered(lambda pick:pick.task_id and pick.is_done and pick.task_id.id != stage_send_id)
        for pick in stock_pickins:
            self._move_orders_to_send_task(pick.task_id)

        return

    def _choose_carrier_amazon_sale(self, picking):
        for line in picking.sale_id.amazon_bind_ids.amazon_order_line_ids:
            detail_product = line.get_amazon_detail_product()
            carriers = self._get_carriers(detail_product, picking.sale_id.amazon_bind_ids)
            if carriers:
                for carrier in carriers[0]:
                    # If there are several items and one of these is not equal that "correos" we are going to choose this
                    if carrier.verify_carrier(picking.partner_id) and \
                            (not picking.carrier_id or (picking.carrier_id and picking.carrier_id.carrier_type == 'correos')):
                        picking.carrier_id = carrier

    @api.model
    def _check_canarian_ship(self, partner):
        """
        Method that check if the partner is from canarian island, Melilla or Ceuta
        :param partner:
        :return:
        """
        zip = partner.zip
        if partner.country_id.code == 'ES' and (zip[0:2] == '35' or zip[0:2] == '38' or zip[0:2] == '51' or zip[0:2] == '52'):
            return True
        return False

    def _choose_carrier(self, picking):
        delivery_carrier_id = None
        country = picking.partner_id.country_id
        zip = picking.partner_id.zip

        if not country or not zip:
            return

        # If the order is from Canary islands, Melilla or Ceuta
        if country.code == 'ES' and (zip[0:2] == '35' or zip[0:2] == '38' or zip[0:2] == '51' or zip[0:2] == '52'):
            delivery_carrier_id = self.env['delivery.carrier'].search([('name', '=', 'Correos Certificado Nacional')])
        # If the carrier is Spring but the country to send is Spain or Portugal we are going to choose GLS
        elif (not picking.carrier_id.carrier_type or 'spring' == picking.carrier_id.carrier_type) and (country.code == 'ES' or country.code == 'PT'):
            delivery_carrier_id = self.env['delivery.carrier'].search([('name', '=', 'GLS Economy')])
        # If the carrier is Spring or the country to send is not Spain or Portugal, we are going to choose Spring
        elif ('spring' == picking.carrier_id.carrier_type) or (country.code != 'ES' and country.code != 'PT'):
            carrier_name = 'Spring %s %s'

            if picking.sale_id.amount_untaxed > 60:
                carrier_name = carrier_name % (country.name, 'Signed')
            else:
                carrier_name = carrier_name % (country.name, 'Tracked')

            delivery_carrier_id = self.env['delivery.carrier'].search([('name', '=', carrier_name)])

        if delivery_carrier_id and len(delivery_carrier_id) > 1:
            raise exceptions.Warning(u'El carrier %s está duplicado %s' % (carrier_name, delivery_carrier_id.mapped('id')))
        return delivery_carrier_id or picking.carrier_id

    def generate_order_carrier(self, order):

        if order.picking_state == 'Waiting Availability':
            order.waiting_send = True

        elif order.picking_state in ('Available', 'Done'):
            if order.delivery_carrier_id.carrier_type == 'correos':
                self._generate_correos_order(order)
            elif order.delivery_carrier_id.carrier_type == 'gls':
                self._generate_gls_order(order)
            elif order.delivery_carrier_id.carrier_type == 'spring':
                self._generate_spring_order(order)

            if order.is_done and order.task_id:
                self._move_orders_to_send_task(order.task_id)

    def generate_orders(self):
        self.error_message = None
        for order in self.stock_picking_ids:
            if not order.is_done:
                self.generate_order_carrier(order)

        _logger.info('The orders have been generated, we are going to get labels')
        self._generate_gls_labels()
        self._generate_spring_labels()
        self._generate_correos_labels()
        self._generate_manifest_reference_count()
        self._manage_waiting_orders()
        self.state = 'confirm'
        return

    def _confirm_orders_on_amazon(self):
        try:
            backends = self.env['amazon.backend'].search([])
            for backend in backends:
                self.env['ir.attachment'].search(['&', ('res_model', '=', self._name),
                                                  ('res_id', '=', self.id),
                                                  ('name', 'ilike', 'amazon_confirmation_orders_%s' % backend.name)]).unlink()

                ship_stock_pick = self.stock_picking_ids.filtered(lambda pick:pick.is_done or pick.waiting_send)
                with tools.osutil.tempdir() as path_temp_dir:
                    myf = open('%s/amazon_confirmation_orders_%s.csv' % (path_temp_dir, backend.name), 'w+')
                    writer = csv.writer(myf, delimiter='\t', lineterminator='\n')
                    titles = ['order-id', 'order-item-id', 'quantity', 'ship-date', 'carrier-code', 'carrier-name', 'tracking-number', 'ship-method']
                    writer.writerow(titles)
                    for order_done in ship_stock_pick:
                        if order_done.sale_order_id.amazon_bind_ids and order_done.sale_order_id.amazon_bind_ids.backend_id.id == backend.id:
                            for amazon_order_line in order_done.sale_order_id.amazon_bind_ids.amazon_order_line_ids:
                                carrier_name = None
                                if order_done.delivery_carrier_id.carrier_type == 'gls':
                                    carrier_name = 'GLS'
                                elif order_done.delivery_carrier_id.carrier_type == 'correos':
                                    carrier_name = 'Correos'
                                elif order_done.delivery_carrier_id.carrier_type == 'spring':
                                    if not order_done.stock_picking_id.sub_carrier:
                                        carrier_name = 'Spring'
                                    elif 'PostNL' in order_done.stock_picking_id.sub_carrier:
                                        carrier_name = 'Post NL'
                                    elif 'Hermes' in order_done.stock_picking_id.sub_carrier:
                                        carrier_name = 'Hermes Logistik Gruppe'
                                    elif 'Italian Post Crono' in order_done.stock_picking_id.sub_carrier:
                                        carrier_name = 'Chronopost'
                                    elif 'Colis Prive' in order_done.stock_picking_id.sub_carrier:
                                        carrier_name = 'Colis Prive'
                                    elif 'Royal Mail' in order_done.stock_picking_id.sub_carrier:
                                        carrier_name = 'Royal Mail'

                                row = [amazon_order_line.amazon_order_id.id_amazon_order,
                                       amazon_order_line.id_item,
                                       amazon_order_line.qty_ordered,
                                       self.shipment_date,
                                       '',
                                       carrier_name,
                                       order_done.stock_picking_id.sub_carrier_tracking_ref or order_done.stock_picking_id.carrier_tracking_ref or '',
                                       ''
                                       ]

                                writer.writerow(row)
                    myf.close()

                    amazon_file_content = open('%s/amazon_confirmation_orders_%s.csv' % (path_temp_dir, backend.name), "rb").read()
                    attachment_vals = {
                        'name':'%s_%s' % (self.shipment_date, 'amazon_confirmation_orders_%s.csv' % backend.name),
                        'datas':base64.b64encode(amazon_file_content),
                        'datas_fname':'%s_%s' % (self.shipment_date, 'amazon_confirmation_orders_%s.csv' % backend.name),
                        'res_model':self._name,
                        'res_id':self.id,
                    }
                    self.env['ir.attachment'].create(attachment_vals)
                    vals = {'backend_id':backend.id,
                            'type':'_POST_FLAT_FILE_FULFILLMENT_DATA_',
                            'model':backend._name,
                            'identificator':backend.id,
                            'data':{'csv':amazon_file_content},
                            }
                    self.env['amazon.feed.tothrow'].create(vals)
        except Exception as e:
            self.error_message = e.message

    @api.model
    def get_id_order_from_marketplace(self, sale):
        """
        Method to confirm the shipments on marketplaces
        :return:
        """
        if sale.amazon_bind_ids:
            return sale.amazon_bind_ids.id_amazon_order
        return sale.name

    @api.multi
    def confirm_orders_on_marketplaces(self):
        """
        Method to confirm the shipments on marketplaces
        :return:
        """
        self._confirm_orders_on_amazon()
        return


class SaleOrderToSend(models.Model):
    _name = "mass.shipment.stock.picking"

    mass_delivery_id = fields.Many2one('mass.shipment.management', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', compute='_onchange_sale_order_id')
    stock_picking_id = fields.Many2one('stock.picking', required=True)
    picking_state = fields.Char('Picking state', compute='_compute_state')
    customer_name = fields.Char('Customer name', related='stock_picking_id.partner_id.name')
    country_customer_name = fields.Char('Customer country', related='stock_picking_id.partner_id.country_id.name')
    type_ship = fields.Selection(selection=[('0', 'First ship'),
                                            ('1', 'Change'),
                                            ('2', 'Return'),
                                            ('3', 'Re-send'), ], required=True)
    delivery_carrier_id = fields.Many2one('delivery.carrier', required=True)
    delivery_carrier_name = fields.Char('Delivery Carrier', related='delivery_carrier_id.name')
    delivery_carrier_type = fields.Char('Delivery Carrier', compute='_compute_delivery_type')
    ship_reference = fields.Char('Order Reference', store=True, compute='_onchange_ship_reference')
    limit_ship_date = fields.Date('Date limit', compute='_compute_date_limit')
    margin = fields.Date('Margen', store=True, compute='_onchange_margin')
    is_done = fields.Boolean(default=False)
    error_message = fields.Char('Error message', readonly=True)
    resend_created = fields.Boolean(default=False)
    task_id = fields.Many2one('project.task')
    waiting_send = fields.Boolean(default=False)

    @api.one
    def _compute_date_limit(self):
        for mass_ship in self:
            if mass_ship.sale_order_id.amazon_bind_ids:
                mass_ship.limit_ship_date = mass_ship.sale_order_id.amazon_bind_ids.date_latest_ship
            else:
                mass_ship.limit_ship_date = mass_ship.sale_order_id.commitment_date

    @api.one
    def _compute_delivery_type(self):
        for mass_ship in self:
            mass_ship.delivery_carrier_type = mass_ship.delivery_carrier_id.carrier_type

    @api.one
    def _compute_state(self):
        for mass_ship in self:
            mass_ship.picking_state = dict(mass_ship.stock_picking_id._fields['state'].selection).get(mass_ship.stock_picking_id.state)

    @api.onchange('stock_picking_id')
    def _onchange_sale_order_id(self):
        for picking in self:
            picking.sale_order_id = self.env['sale.order'].search([('name', '=', picking.stock_picking_id.origin)]).id

    @api.onchange('stock_picking_id')
    def _onchange_ship_reference(self):
        for picking in self:
            picking.ship_reference = picking.stock_picking_id._get_ship_reference()

    @api.onchange('stock_picking_id')
    def _onchange_margin(self):
        for picking in self:
            picking.margin = 0

    @api.model
    def create(self, vals):
        # if vals.get('type_ship') == '3' and not self.resend_created:
        # res = self.copy()
        # TODO create new stock.picking
        # res.resend_created = True
        vals['ship_reference'] = self.env['stock.picking'].browse(vals['stock_picking_id'])._get_ship_reference()
        return super(SaleOrderToSend, self).create(vals)

    @api.model
    def write(self, vals):
        if vals.get('delivery_carrier_id'):
            carrier = None
            picking = None
            if vals.get('delivery_carrier_id'):
                carrier = self.env['delivery.carrier'].browse(vals['delivery_carrier_id'])
            else:
                carrier = self.delivery_carrier_id

            if vals.get('stock_picking_id'):
                picking = self.env['stock.picking'].browse(vals['stock_picking_id'])
            else:
                picking = self.stock_picking_id

            if not carrier.verify_carrier(picking.partner_id):
                raise UserError(_('The carrier (%s) is not compatible with partner picking (%s).' % (carrier.name, picking.name)))

            if (carrier.carrier_type == 'gls' and not carrier.gls_config_id) or (carrier.carrier_type == 'spring' and not carrier.spring_config_id):
                raise UserError(_('The carrier config (%s) is not be configurated.' % carrier.name))

        # Get new shipping reference
        result = super(SaleOrderToSend, self).write(vals)
        return result
