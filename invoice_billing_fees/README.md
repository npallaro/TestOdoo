# NPAL Invoice Billing Fees

## 🎯 Descrizione

**NPAL Invoice Billing Fees** è un modulo professionale per Odoo 18 che automatizza completamente la gestione delle spese di fatturazione, eliminando errori manuali e risparmiando tempo prezioso nella creazione delle fatture cliente.

---

## ✨ Funzionalità Principali

### 📋 Campo Personalizzato Cliente
Aggiungi un campo monetario **"Spese di Fatturazione"** direttamente nell'anagrafica di ogni cliente, visibile nella scheda "Vendite e Acquisti".

### 🤖 Aggiunta Automatica
Quando crei una nuova fattura per un cliente con spese configurate, il modulo aggiunge automaticamente una riga dedicata con l'importo corretto.

### 📦 Articolo Dedicato
Il modulo crea automaticamente un prodotto di tipo servizio chiamato **"Spese di Fatturazione"** (codice interno: `SPESE_FATT`) pronto all'uso.

### 🎯 Gestione Intelligente
**Una sola riga per fattura**: anche se la fattura è collegata a più ordini di vendita, viene aggiunta una sola riga di spese di fatturazione.

### ⚡ Zero Configurazione
Il modulo funziona immediatamente dopo l'installazione. Nessuna configurazione complessa richiesta.

---

## 💼 Vantaggi Business

| Vantaggio | Descrizione |
|-----------|-------------|
| **Automazione Completa** | Elimina completamente l'inserimento manuale delle spese di fatturazione |
| **Precisione Garantita** | Zero rischio di dimenticare le spese o inserire importi errati |
| **Risparmio Tempo** | Riduce drasticamente il tempo necessario per creare le fatture |
| **Personalizzazione** | Ogni cliente può avere spese di fatturazione diverse |
| **Conformità** | Assicura l'applicazione corretta delle spese secondo le policy aziendali |

---

## 🎬 Come Funziona

Il funzionamento è semplicissimo:

1. **Configura il Cliente**: Apri l'anagrafica cliente e imposta l'importo delle spese di fatturazione (es. 5,00 €)
2. **Crea la Fattura**: Genera una nuova fattura per quel cliente come faresti normalmente
3. **Automatico**: Il modulo aggiunge automaticamente la riga "Spese di Fatturazione" con l'importo configurato
4. **Completa**: Procedi con la conferma della fattura senza ulteriori interventi

---

## 🏢 Casi d'Uso Tipici

- **Spese Amministrative Fisse**: Aziende che applicano costi amministrativi standard per ogni fattura
- **Spese Variabili per Cliente**: Gestione di costi di fatturazione diversi in base al tipo o categoria di cliente
- **Addebiti Ricorrenti**: Automatizzazione di commissioni per servizi amministrativi o gestionali
- **Commissioni Documentali**: Applicazione di costi per la gestione documentale e amministrativa

---

## 🚀 Installazione

### Su Odoo.sh

1. Collega il repository GitHub al tuo progetto Odoo.sh
2. Il modulo verrà automaticamente rilevato nella cartella addons
3. Vai su **App** → **Aggiorna Lista App**
4. Cerca "NPAL Invoice Billing Fees"
5. Clicca su **Installa**

### Su Installazione Locale

1. Copia la cartella `invoice_billing_fees` nella directory degli addons di Odoo
2. Riavvia il server Odoo
3. Vai su **App** → **Aggiorna Lista App**
4. Cerca "NPAL Invoice Billing Fees"
5. Clicca su **Installa**

---

## 📖 Guida Utilizzo

### Configurazione Cliente

1. Vai su **Contatti** → Seleziona un cliente
2. Apri la scheda **Vendite e Acquisti**
3. Nella sezione **"Spese di Fatturazione"**, inserisci l'importo desiderato (es. 5,00 €)
4. Salva l'anagrafica

### Creazione Fattura

1. Crea una nuova fattura cliente come faresti normalmente
2. Il modulo rileva automaticamente il cliente e le sue spese configurate
3. Viene aggiunta automaticamente una riga "Spese di Fatturazione" con l'importo corretto
4. La riga appare solo **una volta per fattura**, indipendentemente dal numero di ordini collegati

### Note Operative

- Le spese vengono aggiunte **solo in fase di creazione** della fattura
- Il campo è di tipo **monetario** e supporta la valuta del cliente
- Se il campo non è valorizzato o è zero, non viene aggiunta alcuna riga
- L'articolo "Spese di Fatturazione" può essere personalizzato (tasse, conto contabile, ecc.)

---

## 🔧 Requisiti Tecnici

- **Odoo**: 18.0 Community o Enterprise
- **Moduli Dipendenti**:
  - `account` (Contabilità)
  - `product` (Prodotti)

---

## 📁 Struttura del Modulo

```
invoice_billing_fees/
├── __init__.py                    # Inizializzazione modulo
├── __manifest__.py                # Manifest con metadati e dipendenze
├── README.md                      # Documentazione (questo file)
├── data/
│   └── product_data.xml          # Dati prodotto "Spese di Fatturazione"
├── models/
│   ├── __init__.py               # Inizializzazione modelli
│   ├── res_partner.py            # Estensione anagrafica cliente
│   └── account_move.py           # Logica aggiunta automatica riga
├── views/
│   └── res_partner_views.xml     # Vista campo nell'anagrafica
└── static/
    └── description/
        └── icon.png              # Icona del modulo
```

---

## 🔐 Note Tecniche

- **Campo Tecnico**: `billing_fee_added` viene utilizzato per tracciare se le spese sono già state aggiunte (evita duplicazioni)
- **Prodotto Protetto**: L'articolo viene creato con `noupdate="1"` per preservare eventuali personalizzazioni
- **Controlli Automatici**: Il modulo verifica che la fattura sia di tipo "Fattura Cliente" e in stato "Bozza"
- **Gestione Duplicati**: Se l'articolo esiste già nella fattura, viene aggiornato il prezzo invece di creare una nuova riga

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

## 🏆 Perché Scegliere NPAL Invoice Billing Fees?

✅ **Sviluppato da Professionisti**: Creato da esperti Odoo con anni di esperienza  
✅ **Testato e Affidabile**: Codice testato e ottimizzato per performance  
✅ **Supporto Garantito**: Assistenza tecnica disponibile per i clienti  
✅ **Aggiornamenti Continui**: Mantenuto aggiornato con le ultime versioni Odoo  
✅ **ROI Immediato**: Risparmio di tempo e riduzione errori dal primo giorno  

---

**© 2024 NPAL srl - Tutti i diritti riservati**

