# -*- coding: utf-8 -*-
{
    'name': 'NPAL Portal Sale Agent Orders',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Portale agenti per creazione ordini clienti con gestione stati e task automatici',
    'description': """
NPAL Portal Sale Agent Orders
==============================

Modulo professionale per la gestione ordini tramite portale agenti con workflow operativo e notifiche automatiche.

Funzionalità Principali
------------------------
* **Portale Agenti**: Accesso web sicuro per agenti esterni
* **Creazione Ordini**: Gli agenti creano ordini per conto dei loro clienti
* **Selezione Clienti**: Vista automatica solo dei clienti assegnati all'agente
* **Gestione Indirizzi**: Creazione indirizzi di consegna direttamente dal portale
* **Listini Clienti**: Prezzi automatici basati sul listino del cliente finale
* **Verifica Disponibilità**: Controllo stock in tempo reale per prodotto e magazzino
* **Stati Operativi**: Tracciamento completo del ciclo di vita dell'ordine
* **Task Automatici**: Notifiche automatiche per nuovi ordini e ordini fermi

Workflow Stati Operativi
-------------------------
1. **Preventivo**: Ordine in fase di quotazione
2. **Ordine in entrata da agente**: Nuovo ordine da confermare
3. **Ordine in produzione**: In fase di lavorazione
4. **Ordine da inserire in baia di uscita**: Pronto per logistica
5. **Ordine pronto in baia da ritirare**: Disponibile per ritiro
6. **Ordine pronto da consegnare NOI**: In consegna diretta
7. **Ordine completato**: Ciclo completato
8. **Ordine in attesa di info**: In attesa chiarimenti
9. **In ordine dal fornitore**: Approvvigionamento in corso

Sistema Attività Automatiche
-----------------------------
* **Attività Conferma Ordine**: "Da fare" creato nel chatter quando agente inserisce nuovo ordine
* **Attività Ordine Fermo**: Generata se ordine bloccato oltre X giorni
* **Configurazione Utenti**: Selezione destinatari attività nelle impostazioni
* **Soglia Personalizzabile**: Giorni configurabili per ordini fermi
* **Chatter Integration**: Attività visibili direttamente nell'ordine

Interfaccia Utente
------------------
* **Status Bar**: Barra stati cliccabile nel form ordine
* **Badge Colorati**: Indicatori visivi nella lista ordini
* **Filtri Stati**: Filtro rapido per ogni stato operativo
* **Raggruppamenti**: Group by stato operativo e agente
* **Verifica Stock**: Widget disponibilità magazzino nella pagina prodotto

Sicurezza e Permessi
--------------------
* **Separazione Dati**: Agenti vedono solo i loro clienti
* **Readonly Security**: Agenti non possono confermare ordini
* **Portal Access**: Accesso controllato tramite gruppo portale
* **Internal Views**: Viste dedicate per backoffice

Compatibilità
-------------
* Odoo 18.0 Community & Enterprise
* Odoo.sh Ready
* Integrazione con sale, website_sale, portal, mail, stock
* Estensibile da altri moduli tramite selection_add

Vantaggi Business
-----------------
* **Efficienza Agenti**: Ordini 24/7 senza intervento backoffice
* **Controllo Qualità**: Conferma ordini prima della lavorazione
* **Tracciabilità**: Stato ordine sempre visibile
* **Proattività**: Task automatici prevengono ritardi
* **Scalabilità**: Gestione multipli agenti e clienti

    """,
    'author': 'NPAL srl',
    'website': 'https://www.npal.it',
    'maintainer': 'Nicola Pallaro',
    'support': 'nicola@npal.it',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'website_sale',
        'portal',
        'mail',
    ],
    'data': [
        'security/portal_sale_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/portal_templates.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'NPAL_portal_sale_mod/static/src/js/portal_customer_select.js',
            'NPAL_portal_sale_mod/static/src/css/portal_sale.css',
        ],
    },
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
