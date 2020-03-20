# -*- encoding: utf-8 -*-
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
import base64
from datetime import datetime
from xml.dom.minidom import parseString

from odoo import models, fields, api, exceptions, _
from ..webservice.gls_api import GlsRequest


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _get_gls_service_type(self):
        return [
            ('1', 'COURIER'),
            ('2', 'VALIJA'),
            ('5', 'BICI'),
            ('6', 'CARGA'),
            ('7', 'RECOGIDA'),
            ('8', 'RECOGIDA CRUZADA'),
            ('9', 'DEVOLUCION'),
            ('10', 'RETORNO'),
            ('11', 'IBEX'),
            ('12', 'INTERNACIONAL EXPRESS'),
            ('13', 'INTERNACIONAL ECONOMY'),
            ('14', 'DISTRIBUCION PROPIA'),
            ('15', 'OTROS PUENTES'),
            ('16', 'PROPIO AGENTE'),
            ('17', 'RECOGIDA SIN MERCANCIA'),
            ('18', 'DISTRIBUCION  RED'),
            ('19', 'OPERACIONES RED'),
            ('20', 'CARGA MARITIMA'),
            ('21', 'GLASS'),
            ('22', 'EURO SMALL'),
            ('23', 'PREPAGO'),
            ('24', 'OPTIPLUS'),
            ('25', 'EASYBAG'),
            ('26', 'CORREO INTERNO'),
            ('27', '14H SOBRES'),
            ('28', '24H SOBRES'),
            ('29', '72H SOBRES'),
            ('30', 'ASM0830'),
            ('31', 'CAN MUESTRAS'),
            ('32', 'RC.SELLADA'),
            ('33', 'RECANALIZA'),
            ('34', 'INT PAQUET'),
            ('35', 'dPRO'),
            ('36', 'Int. WEB'),
            ('37', 'ECONOMY'),
            ('38', 'SERVICIOS RUTAS'),
            ('39', 'REC. INT'),
            ('40', 'SERVICIO LOCAL MOTO'),
            ('41', 'SERVICIO LOCAL FURGONETA'),
            ('42', 'SERVICIO LOCAL F. GRANDE'),
            ('43', 'SERVICIO LOCAL CAMION'),
            ('44', 'SERVICIO LOCAL'),
            ('45', 'RECOGIDA MEN. MOTO'),
            ('46', 'RECOGIDA MEN. FURGONETA'),
            ('47', 'RECOGIDA MEN. F.GRANDE'),
            ('48', 'RECOGIDA MEN. CAMION'),
            ('49', 'RECOGIDA MENSAJERO'),
            ('50', 'SERVICIOS ESPECIALES'),
            ('51', 'REC. INT WW'),
            ('52', 'COMPRAS'),
            ('53', 'MR1'),
            ('54', 'EURO ESTANDAR'),
            ('55', 'INTERC. EUROESTANDAR'),
            ('56', 'RECOGIDA ECONOMY'),
            ('57', 'REC. INTERCIUDAD ECONOMY'),
            ('58', 'RC. PARCEL SHOP'),
            ('59', 'ASM BUROFAX'),
            ('60', 'ASM GO'),
            ('66', 'ASMTRAVELLERS'),
            ('74', 'EUROBUSINESS PARCEL'),
            ('76', 'EUROBUSINESS SMALL PARCEL')
        ]

    @api.model
    def _get_gls_schedule(self):
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
        :return:
        """
        return [
            ('0', '10:00 Service	Para el servicio 1 (COURIER)'),
            ('2', '14:00 Service	Para el servicio 1 (COURIER)'),
            ('3', 'BusinessParcel	Para el servicio 1 (COURIER)'),
            ('5', 'SaturdayService'),
            ('7', 'INTERDIA'),
            ('9', 'Franja Horaria'),
            ('4', 'Masivo Para el servicio 1 (COURIER)'),
            ('10', 'Maritimo	Para el servicio 6 (CARGA)'),
            ('11', 'Rec. en NAVE.'),
            ('13', 'Ent. Pto. ASM'),
            ('18', 'EconomyParcel Para el servicio 37 (ECONOMY)'),
            ('19', 'ParcelShop')
        ]

    def _compute_schedule(self):
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
        :return:
        """
        if self.gls_service_type == '1':
            return '3'
        elif self.gls_service_type == '37':
            return '18'
        return

    gls_service_type = fields.Selection('_get_gls_service_type', string='Gls Service')

    gls_schedule = fields.Selection('_get_gls_schedule', string='Gls Schedule')

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

    @api.model
    def _gls_graba_envio_xml(self):
        data = {'Command':'GrabaServicios'}

        warehouse_address = self.picking_type_id.warehouse_id.partner_id
        product_list = []
        package_content = None
        reference_content = None
        weigth_content = 0
        length_pack = 0
        width_pack = 0
        height_pack = 0
        for move in self.move_lines:
            product = {
                "Description":move.product_id.name,
                "Sku":move.product_id.default_code,
                "HsCode":'',
                "OriginCountry":'',
                "PurchaseUrl":'',
                "Quantity":move.product_uom_qty,
                "Value":move.product_id.standard_price
            }
            product_list.append(product)
            package_content = ('%s %s' % (package_content, move.product_id.name)).strip()
            reference_content = '%s|%s' % ((('%sx(%s)' % (int(move.product_uom_qty), move.product_id.default_code)) if move.product_uom_qty > 1
                                            else move.product_id.default_code),
                                           reference_content)
            weigth_content = weigth_content + (move.product_id.weight * move.product_uom_qty)
            length_pack = length_pack + (move.product_id.length * move.product_uom_qty)
            if width_pack < move.product_id.width:
                width_pack = move.product_id.width
            if height_pack < move.product_id.height:
                height_pack = move.product_id.height

        shipment_data = {
            'today':datetime.now().date().strftime('%d/%m/%Y'),
            'portes':'P',
            'servicio':self.gls_service_type,
            'horario':self.gls_schedule,
            'bultos':1,
            'peso':weigth_content,
            'volumen':'',
            'declarado':'',
            'dninob':'',
            'fechaentrega':'',
            'retorno':'',
            'pod':'',
            'podobligatorio':'',
            'remite_plaza':'',
            'remite_nombre':warehouse_address.name,
            'remite_direccion':self._get_address(warehouse_address),
            'remite_poblacion':warehouse_address.city,
            'remite_provincia':warehouse_address.state_id.name,
            'remite_pais':warehouse_address.country_id.code,
            'remite_cp':warehouse_address.zip,
            'remite_telefono':warehouse_address.phone,
            'remite_movil':'',
            'remite_email':warehouse_address.email,
            'remite_departamento':'',
            'remite_nif':warehouse_address.vat,
            'remite_observaciones':'',
            'destinatario_codigo':'',
            'destinatario_plaza':'',
            'destinatario_nombre':self.partner_id.name,
            'destinatario_direccion':self._get_address(self.partner_id),
            'destinatario_poblacion':self.partner_id.city,
            'destinatario_provincia':self.partner_id.state_id.name,
            'destinatario_pais':self.partner_id.country_id.code,
            'destinatario_cp':self.partner_id.zip,
            'destinatario_telefono':self.partner_id.phone,
            'destinatario_movil':self.partner_id.phone,
            'destinatario_email':self.partner_id.email,
            'destinatario_observaciones':'',
            'destinatario_att':'',
            'destinatario_departamento':'',
            'destinatario_nif':'',
            'referencia_c':self.name,
            'referencia_0':reference_content,
            'importes_debido':'',
            'importes_reembolso':'0',
            'seguro':'0',
            'seguro_descripcion':'',
            'seguro_importe':'',
            'etiqueta':'PDF',
            'etiqueta_devolucion':'PDF',
            'cliente_codigo':'',
            'cliente_plaza':'',
            'cliente_agente':'',
        }

        data['XMLData'] = shipment_data

        data['XML'] = '''<?xml version="1.0" encoding="utf-8"?>
                            <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                            <soap12:Body>
                            <GrabaServicios  xmlns="http://www.asmred.com/">
                                        <docIn>
                                            <Servicios uidcliente="${username}" xmlns="http://www.asmred.com/">
                                                <Envio codbarras="">
                                                    <Fecha>${today}</Fecha>
                                                    <Portes>${portes}</Portes>
                                                    <Servicio>${servicio}</Servicio>
                                                    <Horario>${horario}</Horario>
                                                    <Bultos>${bultos}</Bultos>
                                                    <Peso>${peso}</Peso>
                                                    <Volumen>${volumen}</Volumen>
                                                    <Declarado>${declarado}</Declarado>
                                                    <DNINomb>${dninob}</DNINomb>
                                                    <FechaPrevistaEntrega>${fechaentrega}</FechaPrevistaEntrega>
                                                    <Retorno>${retorno}</Retorno>
                                                    <Pod>${pod}</Pod>
                                                    <PODObligatorio>${podobligatorio}</PODObligatorio>
                                                    <Remite>
                                                        <Plaza>${remite_plaza}</Plaza>
                                                        <Nombre>${remite_nombre}</Nombre>
                                                        <Direccion>${remite_direccion}</Direccion>
                                                        <Poblacion>${remite_poblacion}</Poblacion>
                                                        <Provincia>${remite_provincia}</Provincia>
                                                        <Pais>${remite_pais}</Pais>
                                                        <CP>${remite_cp}</CP>
                                                        <Telefono>${remite_telefono}</Telefono>
                                                        <Movil>${remite_movil}</Movil>
                                                        <Email>${remite_email}</Email>
                                                        <Departamento>${remite_departamento}</Departamento>
                                                        <NIF>${remite_nif}</NIF>
                                                        <Observaciones>${remite_observaciones}</Observaciones>
                                                    </Remite>
                                                    <Destinatario>
                                                        <Codigo>${destinatario_codigo}</Codigo>
                                                        <Plaza>${destinatario_plaza}</Plaza>
                                                        <Nombre>${destinatario_nombre}</Nombre>
                                                        <Direccion>${destinatario_direccion}</Direccion>
                                                        <Poblacion>${destinatario_poblacion}</Poblacion>
                                                        <Provincia>${destinatario_provincia}</Provincia>
                                                        <Pais>${destinatario_pais}</Pais>
                                                        <CP>${destinatario_cp}</CP>
                                                        <Telefono>${destinatario_telefono}</Telefono>
                                                        <Movil>${destinatario_movil}</Movil>
                                                        <Email>${destinatario_email}</Email>
                                                        <Observaciones>${destinatario_observaciones}</Observaciones>
                                                        <ATT>${destinatario_att}</ATT>
                                                        <Departamento>${destinatario_departamento}</Departamento>
                                                        <NIF>${destinatario_nif}</NIF>
                                                    </Destinatario>
                                                    <Referencias>
                                                        <Referencia tipo="C">${referencia_c}</Referencia>
                                                        <Referencia tipo="0">${referencia_0}</Referencia>
                                                    </Referencias>
                                                    <Importes>
                                                        <Debidos>${importes_debido}</Debidos>
                                                        <Reembolso>${importes_reembolso}</Reembolso>
                                                    </Importes>
                                                    <Seguro tipo="${seguro}">
                                                        <Descripcion>${seguro_descripcion}</Descripcion>
                                                        <Importe>${seguro_importe}</Importe>
                                                    </Seguro>
                                                    <DevuelveAdicionales>
                                                        <PlazaDestino/>
                                                        <Etiqueta tipo="${etiqueta}"></Etiqueta>
                                                        <EtiquetaDevolucion tipo="${etiqueta_devolucion}"></EtiquetaDevolucion>
                                                    </DevuelveAdicionales>
                                                    <DevolverDatosASMDestino></DevolverDatosASMDestino>
                                                    <Cliente>
                                                        <Codigo>${cliente_codigo}</Codigo>
                                                        <Plaza>${cliente_plaza}</Plaza>
                                                        <Agente>${cliente_agente}</Agente>
                                                    </Cliente>
                                                </Envio>
                                            </Servicios>
                                        </docIn>
                                    </GrabaServicios>
                                </soap12:Body>
                            </soap12:Envelope>
        '''

        return data

    @api.multi
    def _generate_gls_label(self, package_ids=None):
        self.ensure_one()
        if not self.carrier_id.gls_config_id:
            raise exceptions.Warning(_('No Gls Config defined in carrier'))
        if not self.picking_type_id.warehouse_id.partner_id:
            raise exceptions.Warning(
                _('Please define an address in the %s warehouse') % (
                    self.warehouse_id.name))

        gls_api = GlsRequest(self.carrier_id.gls_config_id)

        if package_ids:
            label_response = self._get_gls_label(gls_api, package_ids)
            data = label_response
        else:
            data = self._gls_graba_envio_xml()


        response = gls_api.api_request(data)

        dom = parseString(response)

        label_data = None
        if package_ids:
            import wdb
            wdb.set_trace()
            etiquetas = dom.getElementsByTagName('EtiquetaEnvioResult')
            etiqueta = etiquetas[0].getElementsByTagName('base64Binary')
            label_data = etiqueta[0].firstChild.data
            reference = self.name
        else:
            envio = dom.getElementsByTagName('Envio')

            errores = envio[0].getElementsByTagName('Errores')
            if errores:
                error = errores[0].getElementsByTagName('Error')
                if error:
                    error = error[0].firstChild.data
                    raise exceptions.Warning(error)

            reference = envio[0].getAttribute('codbarras')

            etiquetas = envio[0].getElementsByTagName('Etiquetas')
            if etiquetas:
                etiqueta = etiquetas[0].getElementsByTagName('Etiqueta')
                label_data = etiqueta[0].firstChild.data

        label = {
            'file':base64.b64decode(label_data),
            'file_type':'pdf',
            'name':reference + '.pdf',
            'tracking_number':reference,
        }

        self.carrier_tracking_ref = reference

        return [label]

    @api.multi
    def _get_gls_label(self, gls_api, shipper_reference):
        self.ensure_one()

        xml = '''<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                <soap12:Body>
                <EtiquetaEnvio xmlns="http://www.asmred.com/">
                    <codigo>${reference}</codigo>
                    <tipoEtiqueta>${type_format}</tipoEtiqueta>
                </EtiquetaEnvio>
                </soap12:Body>
                </soap12:Envelope>
               '''

        data = {'Command':'EtiquetaEnvio'}
        data['XML'] = xml
        data['XMLData']={'reference':self.name, 'type_format':'PDF'}
        response = gls_api.api_request(data)
        return response if response and response.get('ErrorLevel') == 0 else None

    @api.multi
    def generate_shipping_labels(self, package_ids=None):
        """ Add label generation for Gls """
        self.ensure_one()
        if self.carrier_id.carrier_type == 'gls':
            return self._generate_gls_label(package_ids=package_ids)
        return super(StockPicking, self).generate_shipping_labels(
            package_ids=package_ids)
