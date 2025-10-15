# SDI Rounding Fix - Gestione Arrotondamenti Fatture Elettroniche

## Descrizione

Questo modulo risolve automaticamente il problema delle discrepanze di totale nelle fatture elettroniche importate dallo SDI italiano quando i fornitori utilizzano prezzi unitari con un numero di decimali superiore a quello gestito da Odoo.

## Problema

Quando si importano fatture elettroniche (file XML .p7m) dallo SDI, può capitare che il totale della fattura nel file XML sia diverso dal totale calcolato da Odoo. Questo accade perché:

- I fornitori possono utilizzare prezzi unitari con fino a 8 cifre decimali nel file XML
- Odoo arrotonda i prezzi unitari a 2 cifre decimali
- Questa differenza, moltiplicata per grandi quantità, genera discrepanze significative nei totali

## Soluzione

Il modulo aggiunge un **pulsante intelligente** che fa tutto automaticamente:

1. **Estrae il totale** dal file XML allegato alla fattura
2. **Calcola la differenza** tra il totale XML e il totale Odoo
3. **Crea automaticamente** una riga di arrotondamento per bilanciare la fattura

**Tutto in un solo click!** ✨

## Utilizzo

### Procedura Semplificata (2 passi)

1. **Aprire** la fattura fornitore in bozza
2. **Cliccare** sul pulsante "Aggiungi Arrotondamento SDI"

**Fatto!** Il sistema fa tutto automaticamente.

### Cosa fa il pulsante

- Cerca il file XML allegato alla fattura
- Estrae il totale dal tag `<ImportoTotaleDocumento>`
- Calcola la differenza con il totale Odoo
- Crea una riga di arrotondamento
- Mostra un messaggio con i dettagli

## Installazione su Odoo.sh

1. Il modulo è già nel repository GitHub
2. Attendere che Odoo.sh aggiorni il branch
3. **App** → **Aggiorna Lista App**
4. Cercare "SDI Rounding Fix" → **Installa**

## Dipendenze

- `account`, `l10n_it`, `l10n_it_edi`

## Licenza

LGPL-3
