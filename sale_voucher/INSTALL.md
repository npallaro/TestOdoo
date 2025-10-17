# Guida Installazione e Testing - NPAL Internal Sales Voucher

## 📋 Prerequisiti

Prima di installare il modulo, assicurati di avere:

- ✅ Odoo 18.0 Community o Enterprise
- ✅ Moduli base installati: `sale`, `stock`, `account`
- ✅ Accesso amministrativo al sistema Odoo
- ✅ Database di test (consigliato per prima installazione)

---

## 🚀 Installazione su Odoo.sh

### Step 1: Aggiungi il Repository

1. Accedi al tuo progetto Odoo.sh
2. Vai su **Settings → Repository**
3. Se il modulo è in un repository privato:
   - Aggiungi il repository come submodule
   - Oppure copia il modulo nella cartella principale del repository

### Step 2: Deploy

1. Fai commit e push del modulo
2. Odoo.sh rileverà automaticamente il nuovo modulo
3. Attendi il completamento del deploy

### Step 3: Installa il Modulo

1. Accedi al database Odoo.sh
2. Vai su **Apps** (attiva Developer Mode se necessario)
3. Click su **Update Apps List**
4. Cerca "NPAL Internal Sales Voucher" o "sale_voucher"
5. Click su **Install**

---

## 💻 Installazione su Server Locale

### Step 1: Copia il Modulo

```bash
# Copia la cartella sale_voucher nella directory addons
cp -r sale_voucher /path/to/odoo/addons/

# Oppure crea un symlink
ln -s /path/to/TestOdoo/sale_voucher /path/to/odoo/addons/sale_voucher
```

### Step 2: Aggiorna la Lista Addons Path

Assicurati che la directory contenente il modulo sia nel `addons_path` del file di configurazione Odoo:

```ini
[options]
addons_path = /path/to/odoo/addons,/path/to/custom/addons
```

### Step 3: Riavvia Odoo

```bash
# Riavvia il servizio Odoo
sudo systemctl restart odoo

# Oppure se esegui manualmente
./odoo-bin -c /path/to/odoo.conf
```

### Step 4: Installa il Modulo

1. Accedi a Odoo come amministratore
2. Vai su **Apps**
3. Attiva **Developer Mode** (Settings → Activate Developer Mode)
4. Click su **Update Apps List**
5. Cerca "sale_voucher"
6. Click su **Install**

---

## 🧪 Testing del Modulo

### Test 1: Verifica Installazione

**Obiettivo**: Verificare che il modulo sia installato correttamente

1. Vai su **Apps → Installed**
2. Cerca "NPAL Internal Sales Voucher"
3. Verifica che lo stato sia "Installed"
4. Verifica che nel menu principale appaia "Vouchers"

**Risultato Atteso**: ✅ Modulo installato, menu visibile

---

### Test 2: Creazione Buono Base

**Obiettivo**: Creare e confermare un buono semplice

1. Vai su **Vouchers → All Vouchers → Create**
2. Seleziona un cliente come "Recipient"
3. Aggiungi un prodotto (es. "Desk Pad", qty: 5)
4. Click su **Save**
5. Verifica che il numero buono sia generato (es. BUO/2025/0001)
6. Click su **Confirm**
7. Verifica che appaia il bottone "View Delivery"
8. Click su "View Delivery"
9. Verifica che il picking sia stato creato con tipo "Voucher Delivery"

**Risultato Atteso**: 
- ✅ Buono creato con numero sequenziale
- ✅ Picking generato automaticamente
- ✅ Stato buono = "Confirmed"

---

### Test 3: Scarico Magazzino

**Obiettivo**: Verificare che il picking scarichi il magazzino

1. Dal buono creato, click su **View Delivery**
2. Nel picking, click su **Check Availability** (se necessario)
3. Click su **Validate**
4. Conferma la validazione
5. Torna al buono (breadcrumb o Back)
6. Verifica che lo stato sia passato a "Delivered"

**Risultato Atteso**:
- ✅ Picking validato
- ✅ Magazzino scaricato
- ✅ Stato buono = "Delivered"

---

### Test 4: Fatturazione a Cliente Diverso

**Obiettivo**: Creare fattura a un cliente diverso dal destinatario

1. Vai su **Vouchers → To Invoice**
2. Verifica che il buono creato sia visibile nella lista
3. Seleziona il buono (checkbox)
4. Click su **Action → Create Invoice**
5. Nel wizard:
   - **Customer to Invoice**: Seleziona un cliente DIVERSO dal recipient
   - **Invoice Date**: Lascia data odierna
   - **Group Products**: Lascia attivo
   - **Add Voucher References**: Lascia attivo
6. Click su **Create Invoice**
7. Verifica che la fattura si apra automaticamente
8. Verifica che:
   - Partner della fattura = Cliente selezionato nel wizard
   - Righe fattura contengano i prodotti del buono
   - Nella descrizione ci sia il riferimento al buono
9. Torna al buono
10. Verifica che:
    - Stato = "Invoiced"
    - Campo "Invoiced To" = Cliente fatturato
    - Bottone "View Invoice" sia visibile

**Risultato Atteso**:
- ✅ Fattura creata con cliente diverso dal destinatario
- ✅ Riferimento al buono presente in fattura
- ✅ Stato buono = "Invoiced"
- ✅ Collegamento buono ↔ fattura funzionante

---

### Test 5: Fatturazione Multipla

**Obiettivo**: Creare una fattura da più buoni

1. Crea 2-3 buoni diversi con lo stesso recipient
2. Conferma tutti i buoni
3. Valida tutti i picking
4. Vai su **Vouchers → To Invoice**
5. Seleziona TUTTI i buoni (checkbox multipli)
6. Click su **Action → Create Invoice**
7. Nel wizard:
   - Seleziona un cliente da fatturare
   - **Group Products**: Attiva
8. Click su **Create Invoice**
9. Verifica che:
   - La fattura contenga TUTTI i prodotti di TUTTI i buoni
   - Prodotti identici siano raggruppati in una sola riga
   - In fondo ci sia una nota con l'elenco dei buoni
10. Verifica che TUTTI i buoni siano passati a stato "Invoiced"

**Risultato Atteso**:
- ✅ Fattura unica da più buoni
- ✅ Prodotti raggruppati correttamente
- ✅ Tutti i buoni collegati alla fattura
- ✅ Tutti i buoni in stato "Invoiced"

---

### Test 6: Permessi Utente

**Obiettivo**: Verificare i gruppi di sicurezza

1. Crea un utente di test (Settings → Users → Create)
2. Assegna gruppo **Sales Voucher / User**
3. Logout e login come utente di test
4. Vai su **Vouchers → All Vouchers**
5. Verifica che l'utente veda solo i suoi buoni
6. Crea un buono
7. Prova a fatturare → Verifica che NON abbia accesso al wizard (solo Manager)
8. Logout e login come admin
9. Modifica utente e assegna gruppo **Sales Voucher / Manager**
10. Logout e login come utente di test
11. Prova a fatturare → Verifica che ABBIA accesso al wizard

**Risultato Atteso**:
- ✅ User vede solo i propri buoni
- ✅ User NON può fatturare
- ✅ Manager può fatturare
- ✅ Manager vede tutti i buoni

---

### Test 7: Report PDF

**Obiettivo**: Verificare la stampa del buono

1. Apri un buono qualsiasi
2. Click su **Print → Voucher**
3. Verifica che il PDF venga generato
4. Verifica che contenga:
   - Numero buono
   - Dati recipient
   - Lista prodotti
   - Totali
   - Nota "This is an internal document..."

**Risultato Atteso**:
- ✅ PDF generato correttamente
- ✅ Tutte le informazioni presenti
- ✅ Layout professionale

---

### Test 8: Workflow Completo End-to-End

**Obiettivo**: Testare l'intero flusso operativo

**Scenario**: Cliente A ritira merce, Cliente B riceve fattura

1. **Creazione Buono**
   - Cliente destinatario: "Azure Interior" (A)
   - Prodotti: 
     - Desk Pad × 10 @ €5.00
     - Desk Organizer × 5 @ €15.00
   - Totale: €125.00

2. **Conferma e Consegna**
   - Conferma buono
   - Valida picking
   - Verifica scarico magazzino

3. **Fatturazione**
   - Cliente da fatturare: "Deco Addict" (B) ← DIVERSO da A
   - Termini pagamento: 30 giorni
   - Note: "Riaddebito interno - Rif. Buono BUO/2025/0001"

4. **Verifica Finale**
   - Fattura intestata a "Deco Addict"
   - Merce consegnata a "Azure Interior"
   - Tracciabilità completa: Buono → Picking → Fattura
   - Tutti i documenti collegati

**Risultato Atteso**:
- ✅ Flusso completo senza errori
- ✅ Cliente A ha ricevuto merce
- ✅ Cliente B ha ricevuto fattura
- ✅ Tracciabilità 100%

---

## 🐛 Troubleshooting

### Problema: Modulo non appare in Apps

**Soluzione**:
1. Verifica che il modulo sia nella directory addons
2. Riavvia Odoo
3. Attiva Developer Mode
4. Click su "Update Apps List"

### Problema: Errore durante installazione

**Soluzione**:
1. Verifica i log di Odoo (`/var/log/odoo/odoo.log`)
2. Controlla che le dipendenze siano installate (`sale`, `stock`, `account`)
3. Verifica permessi file (devono essere leggibili da utente Odoo)

### Problema: Picking non viene creato

**Soluzione**:
1. Verifica che il warehouse sia configurato
2. Controlla che esista la location "Stock" (WH/Stock)
3. Verifica nei log eventuali errori

### Problema: Wizard fatturazione non appare

**Soluzione**:
1. Verifica che l'utente abbia gruppo "Voucher Manager" o superiore
2. Verifica che i buoni siano in stato "Delivered"
3. Controlla i permessi del modello `voucher.create.invoice`

### Problema: Fattura non si crea

**Soluzione**:
1. Verifica che i prodotti abbiano un account income configurato
2. Controlla che il piano dei conti sia installato
3. Verifica che il partner abbia dati fiscali completi

---

## 📊 Checklist Post-Installazione

- [ ] Modulo installato senza errori
- [ ] Menu "Vouchers" visibile
- [ ] Sequenza BUO/YYYY/#### funzionante
- [ ] Picking type "Voucher Delivery" creato
- [ ] Location "Voucher Customers" creata
- [ ] Gruppi di sicurezza configurati
- [ ] Test creazione buono OK
- [ ] Test conferma e picking OK
- [ ] Test fatturazione OK
- [ ] Test report PDF OK
- [ ] Test permessi utenti OK

---

## 🎓 Formazione Utenti

### Per Operatori (Voucher User)

1. Come creare un buono
2. Come confermare un buono
3. Come stampare un buono
4. Come verificare lo stato di un buono

### Per Manager (Voucher Manager)

1. Tutto quanto sopra +
2. Come fatturare singoli buoni
3. Come fatturare più buoni insieme
4. Come scegliere il cliente da fatturare
5. Come usare le opzioni di raggruppamento
6. Come leggere i report

### Per Amministratori

1. Tutto quanto sopra +
2. Gestione permessi utenti
3. Configurazione sequenze
4. Troubleshooting
5. Backup e manutenzione

---

## 📞 Supporto

In caso di problemi durante l'installazione o il testing:

- **Email**: nicola@npal.it
- **Website**: https://www.npal.it
- **GitHub**: Apri una issue nel repository

---

**Buon lavoro con NPAL Internal Sales Voucher! 🚀**

