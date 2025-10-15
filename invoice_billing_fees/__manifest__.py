# -*- coding: utf-8 -*-
{
    'name': 'NPAL Invoice Billing Fees',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Gestione automatica delle spese di fatturazione per cliente',
    'description': """
NPAL Invoice Billing Fees
==========================

Modulo professionale per la gestione automatica delle spese di fatturazione nelle vendite.

Funzionalità Principali
------------------------
* **Campo Personalizzato Cliente**: Imposta le spese di fatturazione direttamente nell'anagrafica cliente
* **Aggiunta Automatica**: Le spese vengono aggiunte automaticamente ad ogni nuova fattura
* **Articolo Dedicato**: Prodotto "Spese di Fatturazione" creato automaticamente dal modulo
* **Gestione Intelligente**: Una sola riga di spesa per fattura, anche con ordini multipli
* **Zero Configurazione**: Funziona immediatamente dopo l'installazione

Vantaggi Business
-----------------
* **Automazione Completa**: Elimina l'inserimento manuale delle spese di fatturazione
* **Precisione Garantita**: Nessun rischio di dimenticare le spese o inserire importi errati
* **Risparmio Tempo**: Riduce drasticamente il tempo di creazione delle fatture
* **Personalizzazione Cliente**: Ogni cliente può avere spese di fatturazione diverse
* **Conformità**: Assicura l'applicazione corretta delle spese secondo policy aziendali

Casi d'Uso Tipici
------------------
* Aziende che applicano spese amministrative fisse per cliente
* Gestione di costi di fatturazione variabili in base al tipo di cliente
* Automatizzazione di addebiti ricorrenti per servizi amministrativi
* Applicazione di commissioni di gestione documentale

Come Funziona
-------------
1. Configura l'importo delle spese nell'anagrafica cliente
2. Crea una nuova fattura per quel cliente
3. Il modulo aggiunge automaticamente la riga "Spese di Fatturazione"
4. L'importo viene preso dal campo configurato sul cliente

Caratteristiche Tecniche
-------------------------
* Attivazione solo in fase di creazione fattura (non richiede aggiornamenti)
* Controllo anti-duplicazione integrato
* Compatibile con workflow standard di fatturazione
* Supporto multi-valuta tramite campo monetario

Compatibilità
-------------
* Odoo 18.0 Community & Enterprise
* Odoo.sh Ready
* Integrazione nativa con modulo Contabilità
* Compatibile con altri moduli di fatturazione

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
    'price': 49.00,
    'currency': 'EUR',
    'depends': [
        'account',
        'product',
    ],
    'data': [
        'data/product_data.xml',
        'views/res_partner_views.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

