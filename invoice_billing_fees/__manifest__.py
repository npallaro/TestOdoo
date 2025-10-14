{
    'name': 'Spese di Fatturazione',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Aggiunge automaticamente spese di fatturazione alle fatture cliente',
    'description': """
        Spese di Fatturazione
        =====================
        
        Questo modulo aggiunge automaticamente una riga di spese di fatturazione 
        alle fatture create per clienti che hanno valorizzato il campo 
        "Spese di Fatturazione" nella loro anagrafica.
        
        Caratteristiche:
        ----------------
        * Campo "Spese di Fatturazione" nell'anagrafica cliente
        * Articolo dedicato "Spese di Fatturazione" creato automaticamente
        * Aggiunta automatica della riga in fase di creazione fattura
        * Una sola riga di spesa per fattura (anche con più ordini collegati)
    """,
    'author': 'Custom Development',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': ['account', 'product'],
    'data': [
        'data/product_data.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

