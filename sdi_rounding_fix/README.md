# SDI Rounding Fix - Gestione Arrotondamenti Fatture Elettroniche

## Descrizione

Modulo **completo e autonomo** per risolvere automaticamente il problema delle discrepanze di totale nelle fatture elettroniche importate dallo SDI italiano.

## Il Problema

Quando si importano fatture elettroniche dallo SDI, può capitare che il totale della fattura nel file XML sia diverso dal totale calcolato da Odoo:

- I fornitori usano prezzi unitari con **fino a 8 cifre decimali** nel file XML
- Odoo arrotonda i prezzi unitari a **2 cifre decimali**
- Questa differenza, moltiplicata per grandi quantità, genera **discrepanze significative** nei totali

**Esempio reale**: Prezzo unitario XML `0.00886292` → Odoo `0.01` → su 24.000 pezzi = **€ 27,29 di differenza**!

## La Soluzione

Un **pulsante intelligente** che fa tutto automaticamente:

1. ✅ **Estrae il totale** dal file XML (anche .p7m firmati digitalmente)
2. ✅ **Calcola la differenza** tra XML e Odoo
3. ✅ **Crea automaticamente** una riga di arrotondamento

**Tutto in un solo click!** 🚀

## Funzionalità Avanzate

### Supporto File .p7m (Firmati Digitalmente)

Il modulo **decifra automaticamente** i file .p7m usando OpenSSL:
- Estrae il contenuto XML dai file firmati
- Funziona anche se la verifica della firma fallisce
- Gestione sicura con file temporanei

### Estrazione Intelligente Multi-Livello

Il modulo prova **5 metodi** in sequenza fino a trovare il totale:

1. **Messaggi/Chatter**: Legge "Valore totale dal file XML: XXX" (più veloce)
2. **File .p7m**: Decifra con OpenSSL ed estrae l'XML
3. **File .xml**: Legge direttamente i file XML non firmati
4. **Tag XML**: Cerca `<ImportoTotaleDocumento>`
5. **Calcolo**: Somma righe + IVA se il tag non c'è

### Calcolo Automatico dalle Righe

Se il tag `<ImportoTotaleDocumento>` non è presente:
- Estrae tutte le righe `<DettaglioLinee>`
- Somma i `<PrezzoTotale>` (o calcola `PrezzoUnitario × Quantità`)
- Estrae l'IVA dai `<DatiRiepilogo>`
- Calcola: **Totale = Imponibile + IVA**

## Utilizzo

### Procedura Semplificata (2 passi)

1. Aprire la fattura fornitore in bozza
2. Cliccare **"Aggiungi Arrotondamento SDI"**

**Fatto!** Il sistema fa tutto automaticamente.

### Cosa Succede

Il pulsante:
- Cerca il file XML/p7m allegato
- Lo decifra se necessario (file .p7m)
- Estrae il totale con uno dei 5 metodi
- Calcola la differenza
- Crea la riga di arrotondamento
- Mostra un messaggio di conferma

### Esempio Pratico

**Scenario**: Fattura XML totale € 3.220,21 ma Odoo calcola € 3.255,07

1. Importare la fattura
2. Cliccare "Aggiungi Arrotondamento SDI"
3. ✓ Messaggio:
   ```
   ✓ Arrotondamento Completato
   
   Totale XML estratto: 3.220,21 €
   Totale Odoo precedente: 3.255,07 €
   Riga di arrotondamento aggiunta: -34,86 €
   
   Il totale della fattura ora corrisponde al file XML!
   ```

## Installazione su Odoo.sh

1. Il modulo è già nel repository GitHub
2. Attendere che Odoo.sh aggiorni il branch (1-2 minuti)
3. **App** → **Aggiorna Lista App**
4. Cercare "SDI Rounding Fix" → **Installa**

## Aggiornamento

Dopo ogni modifica al codice:
1. Attendere che Odoo.sh aggiorni il branch
2. **App** → Cercare "SDI Rounding Fix" → **Aggiorna**

## Requisiti Tecnici

- Odoo 18.0 Enterprise o Community
- Moduli: `account`, `l10n_it`, `l10n_it_edi`
- OpenSSL (già presente in Odoo.sh)

## Vantaggi

- ⚡ **Veloce**: Un solo click
- 🤖 **Automatico**: Nessun input manuale
- 🔓 **Decifra .p7m**: Supporto completo file firmati
- 🎯 **Preciso**: Estrae dal file XML ufficiale
- 🧮 **Intelligente**: Calcola anche senza tag totale
- 🔒 **Sicuro**: Controlli e validazioni integrate
- 📊 **Trasparente**: Mostra tutti i dettagli

## Controlli di Sicurezza

- ✓ Solo fatture fornitore (non cliente)
- ✓ Solo fatture in bozza
- ✓ Impedisce righe duplicate
- ✓ Non crea arrotondamenti se differenza < 0.01 €
- ✓ Verifica file allegati validi

## Risoluzione Problemi

### "Non è stato possibile estrarre il totale"

**Soluzioni**:
1. Verificare che il file .xml o .p7m sia allegato
2. Verificare che sia in formato FatturaPA valido
3. Inserire manualmente il totale nel campo "Totale XML SDI"

### Il pulsante non appare

**Verificare**:
- Fattura di tipo **Fornitore** (non Cliente)
- Fattura in stato **Bozza**
- Non esiste già una riga di arrotondamento

## Licenza

LGPL-3

## Changelog

### v2.0.0 (Corrente)
- 🎉 **Decifrazione file .p7m con OpenSSL**
- 🎉 **Estrazione multi-livello (5 metodi)**
- 🎉 **Calcolo automatico dalle righe XML**
- ✨ Estrazione dai messaggi/chatter
- ✨ Gestione file temporanei sicura
- 🐛 Risolti tutti gli errori di parsing

### v1.0.0
- ✓ Versione iniziale
- ✓ Estrazione base da file XML

