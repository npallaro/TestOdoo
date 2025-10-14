# Spese di Fatturazione

## Descrizione

Modulo per Odoo 18 Enterprise che gestisce automaticamente l'aggiunta di spese di fatturazione alle fatture cliente.

## Funzionalità

Il modulo aggiunge le seguenti funzionalità a Odoo:

1. **Campo "Spese di Fatturazione" nell'anagrafica cliente**: Un campo monetario che permette di specificare l'importo delle spese di fatturazione per ogni cliente.

2. **Articolo dedicato**: Crea automaticamente un articolo di tipo servizio chiamato "Spese di Fatturazione" (codice: SPESE_FATT).

3. **Aggiunta automatica alla fattura**: Quando viene creata una nuova fattura per un cliente che ha valorizzato il campo "Spese di Fatturazione", il modulo aggiunge automaticamente una riga con l'articolo dedicato e l'importo specificato.

4. **Una sola riga per fattura**: Anche se la fattura è collegata a più ordini, viene aggiunta una sola riga di spese di fatturazione.

5. **Funzionamento in fase di creazione**: Il modulo agisce solo durante la creazione della fattura, non richiede aggiornamenti successivi.

## Installazione

### Su Odoo.sh

1. Collegare il repository GitHub al progetto Odoo.sh
2. Il modulo verrà automaticamente rilevato nella cartella addons
3. Aggiornare la lista delle app in Odoo
4. Installare il modulo "Spese di Fatturazione"

### Su installazione locale

1. Copiare la cartella `invoice_billing_fees` nella directory degli addons di Odoo
2. Riavviare il server Odoo
3. Aggiornare la lista delle app
4. Installare il modulo "Spese di Fatturazione"

## Utilizzo

1. **Configurazione cliente**:
   - Aprire l'anagrafica di un cliente
   - Andare nella tab "Vendite e Acquisti"
   - Nella sezione "Spese di Fatturazione", inserire l'importo desiderato (es. 5.00 €)
   - Salvare

2. **Creazione fattura**:
   - Creare una nuova fattura per il cliente configurato
   - Il modulo aggiungerà automaticamente una riga "Spese di Fatturazione" con l'importo specificato
   - La riga viene aggiunta solo una volta per fattura

## Requisiti tecnici

- Odoo 18.0 Enterprise
- Moduli dipendenti:
  - `account` (Contabilità)
  - `product` (Prodotti)

## Struttura del modulo

```
invoice_billing_fees/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
│   └── product_data.xml          # Dati prodotto "Spese di Fatturazione"
├── models/
│   ├── __init__.py
│   ├── res_partner.py            # Estensione anagrafica cliente
│   └── account_move.py           # Logica aggiunta automatica riga
└── views/
    └── res_partner_views.xml     # Vista campo nell'anagrafica
```

## Note tecniche

- Il campo `billing_fee_added` è un campo tecnico utilizzato per evitare duplicazioni
- L'articolo viene creato con `noupdate="1"` per preservare eventuali personalizzazioni
- Il modulo verifica che la fattura sia di tipo "out_invoice" (fattura cliente) e in stato "draft" (bozza)
- Se l'articolo "Spese di Fatturazione" esiste già nella fattura, viene aggiornato il prezzo invece di creare una nuova riga

## Licenza

LGPL-3

## Autore

Custom Development

