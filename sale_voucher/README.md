# NPAL Internal Sales Voucher

## 🎯 Descrizione

**NPAL Internal Sales Voucher** è un modulo professionale per Odoo 18 che gestisce buoni di consegna interni con fatturazione differita a un cliente diverso dal destinatario della merce. Perfetto per scenari di riaddebito tra società collegate, intermediazione commerciale o vendite in conto deposito.

---

## ✨ Funzionalità Principali

### 📋 Buoni Interni
Crea documenti di consegna non fiscali con codice univoco (es. BUO/2025/0001) per tracciare le uscite di merce senza generare documenti fiscali immediati.

### 📦 Scarico Magazzino Automatico
Quando confermi un buono, il sistema genera automaticamente un ordine di prelievo (picking) che scarica il magazzino senza creare un DDT fiscale.

### 🎯 Interfaccia "Buoni da Fatturare"
Vista dedicata che mostra tutti i buoni consegnati e non ancora fatturati, con possibilità di selezione multipla per fatturazione massiva.

### 💼 Wizard di Fatturazione
Crea fatture a un cliente diverso dal destinatario della merce con un semplice wizard:
- Seleziona uno o più buoni
- Scegli il cliente da fatturare (può essere diverso dal destinatario)
- Raggruppa prodotti identici o mantienili separati
- Aggiungi note personalizzate

### 🔄 Workflow Completo
Stati del buono: **Bozza → Confermato → Consegnato → Fatturato**

### 📊 Tracciabilità Totale
Ogni buono è collegato al suo picking di magazzino e alla fattura finale, garantendo un audit trail completo.

---

## 💼 Vantaggi Business

| Vantaggio | Descrizione |
|-----------|-------------|
| **Separazione Documenti** | I buoni sono documenti interni, completamente separati dai flussi fiscali standard |
| **Flessibilità Commerciale** | Consegna a un cliente, fatturazione a un altro senza vincoli |
| **Zero Perdite** | Nessun buono può andare perso: tutti sono tracciati fino alla fatturazione |
| **Efficienza Operativa** | Fatturazione massiva con un click, risparmio di tempo significativo |
| **Conformità** | Le fatture finali sono documenti fiscali regolari con tutti i dati richiesti |
| **Audit Trail** | Log completo di tutte le operazioni nel chatter di ogni buono |

---

## 🎬 Come Funziona

### 1. Crea un Buono
Vai su **Vouchers → All Vouchers → Create**
- Seleziona il cliente destinatario (chi riceve la merce)
- Aggiungi i prodotti con quantità e prezzi
- Salva il buono

### 2. Conferma il Buono
Click su **Confirm**
- Il sistema genera automaticamente un ordine di prelievo (picking)
- Il picking è di tipo "Voucher Delivery" (non genera DDT fiscale)
- Lo stato passa a "Confirmed"

### 3. Valida la Consegna
Vai al picking collegato e click su **Validate**
- Il magazzino viene scaricato
- Lo stato del buono passa automaticamente a "Delivered"
- Il buono è ora pronto per la fatturazione

### 4. Fattura il Buono
Vai su **Vouchers → To Invoice**
- Seleziona uno o più buoni da fatturare
- Click su **Action → Create Invoice**
- Nel wizard:
  - Seleziona il cliente da fatturare (può essere diverso dal destinatario)
  - Imposta data fattura e termini di pagamento
  - Scegli se raggruppare prodotti identici
  - Aggiungi eventuali note
- Click su **Create Invoice**

### 5. Risultato
- La fattura viene creata e aperta automaticamente
- I buoni passano allo stato "Invoiced"
- La fattura contiene riferimenti ai buoni originali
- Il collegamento buono → fattura è tracciato

---

## 🏢 Casi d'Uso Tipici

### Riaddebiti tra Società Collegate
Un gruppo societario dove la Società A consegna merce a un cliente, ma la fattura deve essere intestata alla Società B dello stesso gruppo.

### Intermediazione Commerciale
Un intermediario (A) ritira la merce per conto di un cliente finale (B) che riceverà la fattura.

### Vendite in Conto Deposito
Merce consegnata a un depositario (A) che viene fatturata solo quando venduta al cliente finale (B).

### Vendite con Fatturazione Differita
Consegne immediate con fatturazione posticipata a un soggetto diverso dal ritirante.

---

## 🚀 Installazione

### Su Odoo.sh

1. Aggiungi il repository GitHub al tuo progetto Odoo.sh
2. Il modulo verrà automaticamente rilevato nella cartella addons
3. Vai su **Apps** → **Update Apps List**
4. Cerca "NPAL Internal Sales Voucher"
5. Click su **Install**

### Su Installazione Locale

1. Copia la cartella `sale_voucher` nella directory degli addons di Odoo
2. Riavvia il server Odoo
3. Vai su **Apps** → **Update Apps List**
4. Cerca "NPAL Internal Sales Voucher"
5. Click su **Install**

---

## 📖 Configurazione

### Gruppi di Sicurezza

Il modulo crea tre gruppi di accesso:

| Gruppo | Permessi |
|--------|----------|
| **Voucher User** | Creazione e visualizzazione buoni propri e del team |
| **Voucher Manager** | Fatturazione, visualizzazione di tutti i buoni, accesso report |
| **Voucher Administrator** | Accesso completo incluso cancellazioni e configurazione |

### Assegnazione Permessi

Vai su **Settings → Users & Companies → Users**
- Seleziona un utente
- Nella sezione "Sales Voucher", assegna il gruppo appropriato

### Configurazione Magazzino

Il modulo crea automaticamente:
- **Ubicazione virtuale**: "Voucher Customers" (destinazione merce buoni)
- **Tipo di picking**: "Voucher Delivery" (codice VOUT)
- **Sequenza**: BUO/YYYY/#### per i buoni

Nessuna configurazione manuale richiesta.

---

## 🔧 Requisiti Tecnici

- **Odoo**: 18.0 Community o Enterprise
- **Moduli Dipendenti**:
  - `sale` (Vendite)
  - `stock` (Magazzino)
  - `account` (Contabilità)

---

## 📁 Struttura del Modulo

```
sale_voucher/
├── __init__.py
├── __manifest__.py
├── README.md
├── security/
│   ├── sale_voucher_security.xml    # Gruppi e regole di accesso
│   └── ir.model.access.csv          # Permessi modelli
├── data/
│   ├── sequence_data.xml            # Sequenza BUO/YYYY/####
│   └── stock_data.xml               # Ubicazione e tipo picking
├── models/
│   ├── __init__.py
│   ├── sale_voucher.py              # Modello principale buono
│   ├── sale_voucher_line.py         # Righe prodotti buono
│   ├── stock_picking.py             # Estensione picking
│   └── account_move.py              # Estensione fattura
├── wizard/
│   ├── __init__.py
│   ├── voucher_create_invoice.py    # Wizard fatturazione
│   └── voucher_create_invoice_views.xml
├── views/
│   ├── sale_voucher_views.xml       # Viste buono (form, tree, kanban, ecc.)
│   ├── sale_voucher_menu.xml        # Menu e azioni
│   └── stock_picking_views.xml      # Vista picking con riferimento buono
├── report/
│   ├── sale_voucher_report.xml      # Definizione report PDF
│   └── sale_voucher_templates.xml   # Template QWeb report
└── static/
    └── description/
        └── icon.png                 # Icona modulo
```

---

## 🔐 Note Tecniche

### Workflow Stati

```
Draft → Confirm → Confirmed → Validate Picking → Delivered → Create Invoice → Invoiced
```

### Campi Chiave

- `name`: Codice buono (sequenza automatica)
- `recipient_id`: Cliente che riceve la merce
- `invoiced_to_id`: Cliente che riceve la fattura
- `picking_id`: Riferimento al picking di magazzino
- `invoice_id`: Riferimento alla fattura finale
- `state`: Stato del workflow

### Integrazioni

- **Stock**: Creazione automatica picking al confirm
- **Account**: Generazione fattura con wizard
- **Mail**: Chatter per tracking operazioni

### Ubicazione Virtuale

La merce consegnata via buono viene movimentata verso l'ubicazione virtuale "Voucher Customers". Questo permette di:
- Scaricare il magazzino fisico
- Tracciare la merce "in attesa di fatturazione"
- Non generare documenti fiscali (DDT)

---

## ⚠️ Conformità Fiscale

### Importante

I **buoni** sono documenti interni di gestione operativa, **NON documenti fiscali**.

La **fattura finale** è il documento fiscale ufficiale con tutti i dati richiesti per legge.

### Raccomandazione

Prima di utilizzare questo modulo, **consultare un commercialista o consulente fiscale** per verificare che il flusso operativo sia conforme alla normativa fiscale nel vostro contesto specifico.

### In Caso di Controllo Fiscale

- Le fatture sono regolari e complete
- I movimenti di magazzino sono tracciati correttamente
- I buoni sono documenti interni gestionali
- La corrispondenza buono → fattura è documentata per audit interno

---

## 📞 Supporto e Assistenza

- **Autore**: NPAL srl
- **Maintainer**: Nicola Pallaro
- **Email**: nicola@npal.it
- **Website**: https://www.npal.it

---

## 📄 Licenza

**Odoo Proprietary License v1.0 (OPL-1)**

Questo modulo è protetto da licenza proprietaria. L'uso commerciale richiede l'acquisto di una licenza.

---

## 🏆 Perché Scegliere NPAL Internal Sales Voucher?

✅ **Sviluppato da Professionisti**: Creato da esperti Odoo con anni di esperienza  
✅ **Codice Pulito**: Seguendo le best practices di Odoo  
✅ **Documentazione Completa**: README dettagliato e commenti nel codice  
✅ **Supporto Garantito**: Assistenza tecnica disponibile  
✅ **Aggiornamenti Continui**: Mantenuto aggiornato con Odoo 18  
✅ **ROI Immediato**: Efficienza operativa dal primo giorno  

---

**© 2025 NPAL srl - Tutti i diritti riservati**

