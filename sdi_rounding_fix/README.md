# SDI Rounding Fix - Modulo Odoo 18

## Descrizione

Modulo per Odoo 18 Enterprise che risolve i problemi di arrotondamento nelle fatture elettroniche importate dallo SDI (Sistema di Interscambio italiano).

## Il Problema

Le fatture elettroniche italiane possono contenere prezzi unitari con molte cifre decimali, mentre Odoo utilizza 2 cifre decimali. Questo causa discrepanze tra:
- Il totale calcolato da Odoo
- Il totale indicato nel file XML della fattura elettronica

## La Soluzione

Questo modulo:

1. **Estrae automaticamente** i totali dal file XML (.xml o .p7m firmato)
2. **Crea righe di arrotondamento** (una per ogni aliquota IVA) per allineare i totali
3. **Mostra campi informativi** per evidenziare omaggi, trasporti e altre differenze
4. **Evidenzia in rosso** tutte le discrepanze per alert visivo immediato

## Caratteristiche Principali

### ✅ Logica Corretta

- **NON modifica mai** i totali Odoo manualmente
- **Crea righe di arrotondamento** con IVA corretta per ogni aliquota
- **Odoo ricalcola automaticamente** imponibile, IVA e totale
- **Rispetta completamente** la logica contabile di Odoo

### 📊 Campi Informativi (Non Contabili)

Nel tab "Altre Informazioni" della fattura fornitore:

**Sezione "Valori XML":**
- Imponibile XML SDI
- IVA XML SDI
- Totale XML SDI

**Sezione "Differenze XML vs Odoo":**
- Diff. Imponibile (rosso se > 0,01 €, verde se OK)
- Diff. IVA (rosso se > 0,01 €, verde se OK)
- Diff. Totale (rosso se > 0,01 €, verde se OK)

**Sezione "Informazioni Pagamento":**
- Totale a Pagare SDI (da ImportoTotaleDocumento)
- Diff. Omaggi/Trasporti (in rosso se presente)
- Tipo Differenza (es. "Omaggi/Trasporti non imponibili")

### 🔧 Funzionalità

**Pulsante "Aggiungi Arrotondamento SDI":**
- Estrae automaticamente i riepiloghi IVA dal file XML
- Calcola la differenza per ogni aliquota IVA
- Crea una riga di arrotondamento per ogni aliquota
- Applica l'IVA corretta a ogni riga
- Odoo ricalcola automaticamente i totali

**Pulsante "Rimuovi Arrotondamento SDI":**
- Rimuove tutte le righe di arrotondamento
- Resetta i campi informativi

## Come Funziona

### Esempio Pratico

**Dati XML:**
- Imponibile: 16.911,73 €
- IVA: 3.605,03 €
- Totale: 20.516,76 €
- Totale a pagare: 19.991,54 € (omaggi: 525,22 €)

**Riepiloghi IVA XML:**
- IVA 22%: Imp 16.386,51 € | IVA 3.605,03 €
- IVA 0%: Imp 525,22 € | IVA 0,00 €

**Odoo prima dell'arrotondamento:**
- Imponibile: 16.880,00 €
- IVA: 3.599,20 €
- Totale: 20.479,20 €

**Righe create dal modulo:**
1. Arrotondamento SDI - IVA 22%: 26,51 € (con IVA 22%)
2. Arrotondamento SDI - IVA 0%: 5,22 € (senza IVA)

**Odoo dopo l'arrotondamento:**
- Imponibile: 16.911,73 € ✓
- IVA: 3.605,03 € ✓
- Totale: 20.516,76 € ✓

**Campi informativi:**
- Totale a pagare SDI: 19.991,54 € (in rosso)
- Diff. omaggi/trasporti: 525,22 € (in rosso)
- Tipo: "Omaggi/Trasporti non imponibili"

## Installazione

### Su Odoo.sh

1. Il modulo è già disponibile nel repository GitHub
2. Odoo.sh rileverà automaticamente il modulo
3. Andare su **App** → **Aggiorna Lista App**
4. Cercare "SDI Rounding Fix"
5. Cliccare su **Installa**
6. Dopo l'installazione, cliccare su **Aggiorna** per creare i nuovi campi nel database

### Requisiti

- Odoo 18 Enterprise
- OpenSSL (già disponibile su Odoo.sh)
- Modulo `account` installato

## Utilizzo

### Fatture Importate dallo SDI

1. Importare la fattura dallo SDI come di consueto
2. Aprire la fattura in bozza
3. Verificare il tab "Altre Informazioni" → "Informazioni SDI"
4. Se ci sono differenze (in rosso), cliccare su **"Aggiungi Arrotondamento SDI"**
5. Il sistema crea automaticamente le righe di arrotondamento
6. Verificare che le differenze siano ora a zero (in verde)
7. Confermare la fattura

## Autore

Sviluppato per risolvere problemi di arrotondamento nelle fatture elettroniche italiane in Odoo 18 Enterprise.

## Licenza

Proprietario
