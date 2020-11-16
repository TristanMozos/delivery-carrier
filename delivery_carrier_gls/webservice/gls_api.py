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
import os
import logging
import urllib2

from string import Template
from suds.plugin import MessagePlugin
from odoo import api

_logger = logging.getLogger(__name__)


class LogPlugin(MessagePlugin):
    def sending(self, context):
        _logger.info(context.envelope.decode('utf-8', errors='ignore'))

    def received(self, context):
        _logger.info(context.reply.decode('utf-8', errors='ignore'))


class GlsBase(object):

    def __init__(self, gls_config):
        self._url = 'https://wsclientes.asmred.com/b2b.asmx?wsdl'
        self.gls_config = gls_config


class GlsRequest(GlsBase):

    def api_request(self, data):
        xml = self.return_xml(data)
        _logger.info(xml)
        headers = {
            'Content-Type':'application/soap+xml; charset=utf-8',
            'Content-Type':'text/xml; charset=utf-8',
            'Content-Length':len(xml),
        }
        request = urllib2.Request(self._url, xml.encode('utf8'), headers)
        response = urllib2.urlopen(request)
        return response.read()

    @api.model
    def return_xml(self, vals):
        """
        :param vals:
        :param gls_config:
        :return:
        """
        xml = ''
        if vals.get('Command') in ('GrabaServicios', 'GetExpCli'):
            vals['XMLData']['username'] = self.gls_config.uid_test if self.gls_config.is_test else self.gls_config.uid

        t = Template(vals['XML'])
        xml = t.substitute(**vals['XMLData'])
        return xml
