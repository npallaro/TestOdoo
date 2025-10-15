# -*- coding: utf-8 -*-
{
    'name': 'SDI Rounding Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Gestione automatica arrotondamenti fatture elettroniche SDI',
    'description': """
SDI Rounding Fix
================

Questo modulo aggiunge funzionalità per gestire le discrepanze di arrotondamento
nelle fatture elettroniche importate dallo SDI italiano.

Funzionalità:
-------------
* Pulsante per calcolare automaticamente la differenza tra il totale XML e il totale Odoo
* Creazione automatica di una riga di arrotondamento per bilanciare la fattura
* Campo per memorizzare il totale originale del file XML
* Supporto per fatture fornitore (vendor bills)

Autore: Custom Development
Licenza: LGPL-3
    """,
    'author': 'Custom Development',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_it',
        'l10n_it_edi',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

