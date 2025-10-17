# -*- coding: utf-8 -*-
{
    'name': 'NPAL Internal Sales Voucher',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Gestione buoni interni con rifatturazione a cliente diverso',
    'description': """
NPAL Internal Sales Voucher
============================

Modulo professionale per la gestione di buoni di consegna interni con fatturazione differita a cliente diverso dal destinatario.

Funzionalità Principali
------------------------
* **Buoni Interni**: Documenti di consegna non fiscali con codice univoco
* **Scarico Magazzino**: Generazione automatica di movimenti di magazzino senza DDT fiscale
* **Interfaccia Dedicata**: Vista "Buoni da Fatturare" con selezione multipla
* **Wizard Fatturazione**: Creazione fatture a cliente diverso dal destinatario della merce
* **Tracciabilità Completa**: Collegamento buono → picking → fattura
* **Gestione Stati**: Workflow completo (Bozza → Confermato → Consegnato → Fatturato)

Vantaggi Business
-----------------
* **Separazione Documenti**: I buoni sono documenti interni, separati dai flussi fiscali
* **Flessibilità Commerciale**: Consegna a un cliente, fatturazione a un altro
* **Controllo Completo**: Nessun buono perso, tutti tracciati fino alla fatturazione
* **Efficienza Operativa**: Fatturazione massiva con un click
* **Audit Trail**: Log completo di tutte le operazioni

Casi d'Uso Tipici
------------------
* Vendite a gruppi societari con riaddebiti interni
* Intermediazione commerciale con mandato
* Vendite in conto deposito con acquisto successivo
* Gestione vendite con fatturazione differita

Come Funziona
-------------
1. Crea un buono specificando cliente destinatario e prodotti
2. Conferma il buono per generare automaticamente il picking di magazzino
3. Valida la consegna per scaricare il magazzino
4. Dalla vista "Buoni da Fatturare", seleziona i buoni e crea la fattura
5. Specifica il cliente da fatturare (può essere diverso dal destinatario)
6. La fattura viene generata con riferimenti ai buoni originali

Caratteristiche Tecniche
-------------------------
* Nuovo modello `sale.voucher` con workflow completo
* Integrazione nativa con modulo Stock (magazzino)
* Tipo di picking personalizzato "Voucher Delivery"
* Ubicazione virtuale "Voucher Customers"
* Wizard di fatturazione con raggruppamento prodotti
* Gruppi di sicurezza per controllo accessi
* Report PDF per stampa buono interno

Sicurezza e Permessi
--------------------
* **Voucher User**: Creazione e visualizzazione buoni
* **Voucher Manager**: Fatturazione e report completi
* **Voucher Admin**: Accesso completo incluso cancellazioni

Compatibilità
-------------
* Odoo 18.0 Community & Enterprise
* Odoo.sh Ready
* Integrazione nativa con moduli Sales, Stock e Accounting
* Compatibile con localizzazione italiana

Conformità Fiscale
-------------------
I buoni sono documenti interni di gestione operativa, NON documenti fiscali.
La fattura finale è il documento fiscale ufficiale con tutti i dati richiesti per legge.
Si raccomanda di consultare un commercialista prima dell'utilizzo.

Supporto e Assistenza
----------------------
* Documentazione completa inclusa
* Supporto tecnico disponibile
* Aggiornamenti garantiti per Odoo 18

Licenza
-------
Odoo Proprietary License v1.0 (OPL-1)
Uso commerciale richiede acquisto licenza.

    """,
    'author': 'NPAL srl',
    'website': 'https://www.npal.it',
    'maintainer': 'Nicola Pallaro',
    'support': 'nicola@npal.it',
    'license': 'OPL-1',
    'price': 149.00,
    'currency': 'EUR',
    'depends': [
        'sale',
        'stock',
        'account',
    ],
    'data': [
        # Security
        'security/sale_voucher_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequence_data.xml',
        'data/stock_data.xml',
        
        # Views
        'views/sale_voucher_views_simple.xml',
        'views/sale_voucher_views.xml',
        'views/sale_voucher_menu.xml',  # MUST be before sale_voucher_line_views
        'views/sale_voucher_line_views.xml',
        'views/stock_picking_views.xml',
        
        # Wizard
        'wizard/voucher_create_invoice_views.xml',
        'wizard/voucher_lines_create_invoice_views.xml',
        
        # Report
        'report/sale_voucher_report.xml',
        'report/sale_voucher_templates.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

