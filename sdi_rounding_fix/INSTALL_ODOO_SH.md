# Guida Installazione su Odoo.sh

## Prerequisiti

- Accesso al repository GitHub del progetto Odoo.sh
- Permessi di amministratore sul database Odoo
- Git installato sul computer locale

## Metodo 1: Upload Diretto (Consigliato per Test)

### Passo 1: Preparare il Repository Locale

```bash
# Clonare il repository del progetto Odoo.sh
git clone git@github.com:VOSTRO_USERNAME/VOSTRO_PROGETTO.git
cd VOSTRO_PROGETTO

# Creare la cartella per i moduli custom (se non esiste)
mkdir -p custom_modules

# Copiare il modulo nella cartella
cp -r /percorso/a/sdi_rounding_fix custom_modules/
```

### Passo 2: Commit e Push

```bash
# Aggiungere i file al repository
git add custom_modules/sdi_rounding_fix

# Fare commit
git commit -m "Add SDI Rounding Fix module"

# Push sul branch desiderato (es. main o production)
git push origin main
```

### Passo 3: Installare il Modulo

1. Attendere che Odoo.sh aggiorni il branch (circa 1-2 minuti)
2. Accedere al database Odoo
3. Attivare la **Modalità Sviluppatore**:
   - Andare su **Impostazioni**
   - Scorrere fino in fondo
   - Cliccare su **Attiva la modalità sviluppatore**
4. Andare su **App**
5. Cliccare su **Aggiorna Lista App** (icona con le frecce circolari)
6. Cercare "SDI Rounding Fix"
7. Cliccare su **Installa**

## Metodo 2: Tramite Git Submodule (Per Repository Separato)

Se si desidera mantenere il modulo in un repository separato:

### Passo 1: Creare Repository per il Modulo

1. Creare un nuovo repository su GitHub (es. `sdi-rounding-fix`)
2. Pushare il codice del modulo:

```bash
cd sdi_rounding_fix
git init
git add .
git commit -m "Initial commit"
git remote add origin git@github.com:VOSTRO_USERNAME/sdi-rounding-fix.git
git push -u origin main
```

### Passo 2: Aggiungere come Submodule

```bash
# Nel repository del progetto Odoo.sh
cd VOSTRO_PROGETTO
git submodule add -b main git@github.com:VOSTRO_USERNAME/sdi-rounding-fix.git custom_modules/sdi_rounding_fix
git commit -m "Add SDI Rounding Fix as submodule"
git push origin main
```

### Passo 3: Configurare Deploy Key (se repository privato)

1. Andare su Odoo.sh → Impostazioni → Submodules
2. Copiare la **Deploy Key**
3. Andare su GitHub → Repository sdi-rounding-fix → Settings → Deploy keys
4. Aggiungere la chiave copiata

## Verifica Installazione

Dopo l'installazione, verificare che:

1. Il modulo appaia nella lista delle app installate
2. Aprendo una fattura fornitore in bozza, si vedano:
   - I nuovi campi nel tab "Altre Informazioni"
   - I pulsanti "Aggiungi Arrotondamento SDI" e "Rimuovi Arrotondamento SDI"

## Struttura Directory Consigliata

```
VOSTRO_PROGETTO/
├── .git/
├── custom_modules/
│   └── sdi_rounding_fix/
│       ├── __init__.py
│       ├── __manifest__.py
│       ├── README.md
│       ├── models/
│       │   ├── __init__.py
│       │   └── account_move.py
│       ├── views/
│       │   └── account_move_views.xml
│       └── static/
│           └── description/
│               └── index.html
└── README.md
```

## Aggiornamento del Modulo

Per aggiornare il modulo dopo modifiche:

```bash
# Modificare i file necessari
# Fare commit e push
git add custom_modules/sdi_rounding_fix
git commit -m "Update SDI Rounding Fix module"
git push origin main

# Su Odoo:
# 1. Andare su App
# 2. Cercare "SDI Rounding Fix"
# 3. Cliccare su "Aggiorna" (icona con freccia circolare)
```

## Risoluzione Problemi

### Il modulo non appare nella lista

1. Verificare che i file siano stati pushati correttamente
2. Verificare che Odoo.sh abbia completato il build del branch
3. Aggiornare la lista delle app
4. Verificare che la modalità sviluppatore sia attiva

### Errore durante l'installazione

1. Controllare i log di Odoo.sh
2. Verificare che tutte le dipendenze siano installate (`account`, `l10n_it`, `l10n_it_edi`)
3. Verificare che non ci siano errori di sintassi nei file Python

### I pulsanti non appaiono

1. Verificare che si stia aprendo una **fattura fornitore** (non cliente)
2. Verificare che la fattura sia in stato **bozza**
3. Fare refresh della pagina (F5)
4. Provare a riavviare il browser

## Supporto

Per ulteriori problemi, contattare l'amministratore del sistema o consultare la documentazione di Odoo.sh:
https://www.odoo.com/documentation/18.0/administration/odoo_sh/

