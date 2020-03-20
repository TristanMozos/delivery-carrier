# -*- coding: utf-8 -*-
# Copyright 2020 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name':'GLS Deliveries WebService',
    'version':'0.1',
    'author':"Halltic eSolutions",
    'category':'Sales Management',
    'depends':[
        'delivery',
        'base_delivery_carrier_label'
    ],
    'website':'https://www.halltic.com',
    'data':[
        'security/ir.model.access.csv',
        'view/gls_config_view.xml',
        'view/delivery_view.xml',
        'view/stock_view.xml'
    ],
    'demo':[],
    'installable':True,
    'auto_install':False,
    'license':'AGPL-3',
    'external_dependencies':{
        'python':['suds'],
    }
}
