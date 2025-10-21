# NPAL Portal Sale Modification

## Descrizione

Modulo Odoo 18 Enterprise che permette agli utenti portale (agenti) di creare ordini e-commerce per conto dei loro clienti.

## Funzionalità Principali

- **Creazione ordini per conto terzi**: Gli agenti possono creare ordini utilizzando un cliente diverso dal proprio account
- **Visibilità clienti limitata**: Ogni agente vede solo i clienti a lui associati tramite il campo "Addetto vendite" (user_id)
- **Gestione prezzi**: Gli ordini utilizzano automaticamente i listini prezzi del cliente finale
- **Modifica ordini in bozza**: Gli agenti possono modificare solo ordini in stato "bozza" o "inviato"
- **Tracking agente**: Ogni ordine traccia quale agente lo ha creato

## Requisiti

- Odoo 18 Enterprise
- Moduli dipendenti:
  - `base`
  - `sale`
  - `website_sale`
  - `portal`

## Installazione

### Su Odoo.sh

1. Carica il modulo nella cartella `/custom/addons/` del tuo repository
2. Esegui git push al branch appropriato
3. Attendi che Odoo.sh completi il deployment
4. Vai su App → Aggiorna lista applicazioni
5. Cerca "NPAL Portal Sale Modification"
6. Clicca su "Installa"

### Installazione locale

1. Copia la cartella del modulo in uno dei percorsi addons di Odoo
2. Riavvia il server Odoo
3. Attiva la modalità sviluppatore
4. Vai su App → Aggiorna lista applicazioni
5. Cerca "NPAL Portal Sale Modification"
6. Clicca su "Installa"

## Configurazione

### 1. Configurare gli agenti

1. Vai su **Contatti**
2. Apri il contatto che sarà l'agente
3. Assicurati che abbia un utente associato con gruppo "Portale"

### 2. Associare clienti agli agenti

1. Vai su **Contatti**
2. Apri il contatto del cliente
3. Nel campo **Addetto vendite** (user_id), seleziona l'utente dell'agente
4. Salva

### 3. Configurare l'e-commerce

1. Assicurati che il modulo `website_sale` sia installato e configurato
2. Pubblica i prodotti che vuoi rendere disponibili
3. Configura i listini prezzi per i clienti

## Utilizzo

### Per l'agente (utente portale)

1. **Accedi al portale** con le credenziali dell'agente
2. Nella home del portale vedrai:
   - Il numero di clienti associati
   - Un pulsante "Crea nuovo ordine per un cliente"
3. **Visualizzare i clienti**: Clicca su "Clienti" per vedere l'elenco dei tuoi clienti
4. **Creare un ordine**:
   - Clicca su "Crea nuovo ordine per un cliente"
   - Seleziona il cliente per cui vuoi creare l'ordine
   - Verrai reindirizzato allo shop
   - Completa l'ordine come faresti normalmente
   - L'ordine sarà associato al cliente selezionato, non a te
5. **Gestire gli ordini**: Nella sezione "I miei ordini" vedrai tutti gli ordini dei tuoi clienti

### Per il back office

1. Vai su **Vendite → Ordini**
2. Gli ordini creati da agenti avranno il campo "Creato da Agente" compilato
3. Puoi filtrare:
   - **Ordini da Agenti**: Mostra solo ordini creati da agenti
   - **Ordini Diretti**: Mostra solo ordini creati direttamente dai clienti
4. Puoi raggruppare per "Agente Creatore" per vedere gli ordini per agente

## Sicurezza

Il modulo implementa le seguenti regole di sicurezza:

- **Visibilità clienti**: Gli agenti vedono solo i clienti con loro come "Addetto vendite"
- **Visibilità ordini**: Gli agenti vedono solo gli ordini dei loro clienti
- **Modifica ordini**: Gli agenti possono modificare solo ordini in stato bozza/inviato
- **Conferma ordini**: Gli agenti NON possono confermare ordini (solo il back office)
- **Eliminazione ordini**: Gli agenti NON possono eliminare ordini

## Struttura File

```
NPAL_portal_sale_mod/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── sale_order.py          # Estensione modello sale.order
│   └── res_partner.py         # Estensione modello res.partner
├── controllers/
│   ├── __init__.py
│   ├── portal.py              # Controller portale
│   └── main.py                # Override website_sale
├── views/
│   ├── portal_templates.xml   # Template QWeb portale
│   └── sale_order_views.xml   # Viste backend
├── security/
│   ├── portal_sale_security.xml  # Regole di sicurezza
│   └── ir.model.access.csv       # Diritti di accesso
└── static/
    └── src/
        ├── js/
        │   └── portal_customer_select.js  # JavaScript frontend
        └── css/
            └── portal_sale.css            # Stili CSS
```

## Campi Aggiunti

### sale.order

- `created_by_agent_id` (Many2one): Agente che ha creato l'ordine
- `is_agent_order` (Boolean): Indica se l'ordine è stato creato da un agente

## Troubleshooting

### L'agente non vede i clienti

- Verifica che i clienti abbiano il campo "Addetto vendite" impostato sull'utente dell'agente
- Verifica che l'agente abbia un utente con gruppo "Portale"

### I prezzi non sono corretti

- Verifica che il cliente abbia un listino prezzi configurato
- Il sistema usa automaticamente il listino del cliente finale

### L'agente non può modificare un ordine

- Verifica che l'ordine sia in stato "bozza" o "inviato"
- Gli ordini confermati non possono essere modificati dagli agenti

### Errore di accesso

- Verifica le regole di sicurezza in Impostazioni → Tecnico → Sicurezza → Regole di Registrazione
- Verifica i diritti di accesso in Impostazioni → Tecnico → Sicurezza → Diritti di Accesso

## Note Tecniche

- Il modulo utilizza la sessione per memorizzare il cliente selezionato durante il processo di checkout
- Gli override dei controller di `website_sale` garantiscono che venga usato il partner corretto
- Le regole di sicurezza vengono applicate automaticamente a livello di ORM

## Supporto

Per problemi o domande, contattare NPAL.

## Licenza

LGPL-3

## Versione

- **Versione modulo**: 18.0.1.0.0
- **Compatibilità Odoo**: 18.0 Enterprise
