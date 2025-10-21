# -*- coding: utf-8 -*-
{
    'name': 'NPAL Portal Sale Modification',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Permette agli agenti (utenti portale) di creare ordini per i loro clienti',
    'description': """
        Portal Sale Agent Orders
        =========================
        Questo modulo permette agli utenti portale (agenti) di:
        - Creare ordini e-commerce per conto dei loro clienti
        - Vedere solo i clienti associati a loro tramite il campo 'Addetto vendite'
        - Modificare ordini in stato bozza
        - Utilizzare i listini prezzi dei clienti finali
    """,
    'author': 'NPAL',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'website_sale',
        'portal',
    ],
    'data': [
        'security/portal_sale_security.xml',
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'NPAL_portal_sale_mod/static/src/js/portal_customer_select.js',
            'NPAL_portal_sale_mod/static/src/css/portal_sale.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
