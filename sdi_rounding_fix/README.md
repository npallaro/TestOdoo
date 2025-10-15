# SDI Rounding Fix - Gestione Arrotondamenti Fatture Elettroniche

## Descrizione

Questo modulo risolve il problema delle discrepanze di totale nelle fatture elettroniche importate dallo SDI italiano quando i fornitori utilizzano prezzi unitari con un numero di decimali superiore a quello gestito da Odoo.

## Problema

Quando si importano fatture elettroniche (file XML .p7m) dallo SDI, può capitare che il totale della fattura nel file XML sia diverso dal totale calcolato da Odoo. Questo accade perché:

- I fornitori possono utilizzare prezzi unitari con fino a 8 cifre decimali nel file XML
- Odoo arrotonda i prezzi unitari a 2 cifre decimali
- Questa differenza, moltiplicata per grandi quantità, genera discrepanze significative nei totali

## Soluzione

Il modulo aggiunge:

1. **Campo "Totale XML SDI"**: Permette di inserire manualmente il totale indicato nel file XML della fattura elettronica
2. **Campo "Differenza Arrotondamento"**: Calcola automaticamente la differenza tra il totale XML e il totale Odoo
3. **Pulsante "Aggiungi Arrotondamento SDI"**: Crea automaticamente una riga di arrotondamento per bilanciare la fattura
4. **Pulsante "Rimuovi Arrotondamento SDI"**: Rimuove le righe di arrotondamento se necessario

## Installazione

### Su Odoo.sh

1. Creare una cartella `custom_modules` nel repository del progetto (se non esiste già)
2. Copiare la cartella `sdi_rounding_fix` dentro `custom_modules`
3. Fare commit e push delle modifiche
4. Attendere che Odoo.sh aggiorni il branch
5. Andare su **App** → **Aggiorna Lista App**
6. Cercare "SDI Rounding Fix" e installarlo

### Su installazione locale

1. Copiare la cartella `sdi_rounding_fix` nella directory degli addons di Odoo
2. Aggiornare la lista dei moduli: `./odoo-bin -u all -d <database>`
3. Installare il modulo dall'interfaccia web

## Utilizzo

### Procedura Manuale

1. Aprire la fattura fornitore in bozza
2. Nel tab "Altre Informazioni", sezione "Informazioni SDI", inserire il totale del file XML nel campo "Totale XML SDI"
3. Il campo "Differenza Arrotondamento" mostrerà automaticamente la discrepanza
4. Cliccare sul pulsante "Aggiungi Arrotondamento SDI" nella barra superiore
5. Verrà creata automaticamente una riga con la differenza
6. Confermare la fattura

### Esempio Pratico

**Scenario**: Fattura con totale XML di € 3.220,21 ma Odoo calcola € 3.255,07

1. Importare/creare la fattura fornitore
2. Inserire `3220.21` nel campo "Totale XML SDI"
3. Il sistema mostrerà `-34.86` come differenza
4. Cliccare "Aggiungi Arrotondamento SDI"
5. Verrà aggiunta una riga "Arrotondamento SDI - Differenza fattura elettronica" con importo -34.86 €
6. Il totale della fattura sarà ora € 3.220,21, corrispondente al file XML

## Prodotto di Arrotondamento

Il modulo crea automaticamente un prodotto di servizio chiamato "Arrotondamento Fatture Elettroniche SDI" (codice: `SDI_ROUNDING`) la prima volta che si utilizza la funzione.

È possibile personalizzare:
- Il conto contabile associato
- La descrizione
- Altre proprietà del prodotto

Andare su **Inventario → Prodotti → Prodotti** e cercare "SDI_ROUNDING".

## Dipendenze

- `account` (Contabilità Odoo)
- `l10n_it` (Localizzazione Italiana)
- `l10n_it_edi` (Fatturazione Elettronica Italiana)

## Compatibilità

- Odoo 18.0 Enterprise
- Odoo 18.0 Community (con moduli di fatturazione elettronica italiana)

## Licenza

LGPL-3

## Autore

Custom Development per gestione fatture elettroniche SDI

## Supporto

Per problemi o domande, contattare l'amministratore del sistema Odoo.

