# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import re
import subprocess
import tempfile
import os

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Campo per memorizzare il totale originale del file XML SDI
    sdi_xml_total = fields.Monetary(
        string='Totale XML SDI',
        currency_field='currency_id',
        help='Totale della fattura come indicato nel file XML dello SDI. '
             'Questo campo viene compilato automaticamente durante l\'estrazione.'
    )
    
    # Campo calcolato per mostrare la differenza
    sdi_rounding_difference = fields.Monetary(
        string='Differenza Arrotondamento',
        compute='_compute_sdi_rounding_difference',
        currency_field='currency_id',
        help='Differenza tra il totale XML SDI e il totale calcolato da Odoo'
    )
    
    # Campo per verificare se esiste già una riga di arrotondamento
    has_rounding_line = fields.Boolean(
        string='Ha Riga Arrotondamento',
        compute='_compute_has_rounding_line',
        help='Indica se la fattura contiene già una riga di arrotondamento SDI'
    )

    @api.depends('sdi_xml_total', 'amount_total')
    def _compute_sdi_rounding_difference(self):
        """Calcola la differenza tra il totale XML e il totale Odoo"""
        for move in self:
            if move.sdi_xml_total and move.amount_total:
                move.sdi_rounding_difference = move.sdi_xml_total - move.amount_total
            else:
                move.sdi_rounding_difference = 0.0

    @api.depends('invoice_line_ids.name')
    def _compute_has_rounding_line(self):
        """Verifica se esiste già una riga di arrotondamento"""
        for move in self:
            move.has_rounding_line = any(
                line.name and 'Arrotondamento SDI' in line.name 
                for line in move.invoice_line_ids
            )

    def _decrypt_p7m_file(self, file_content):
        """
        Decifra un file .p7m usando OpenSSL e restituisce il contenuto XML.
        I file .p7m sono file PKCS#7 firmati digitalmente.
        """
        try:
            # Crea file temporanei per input e output
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.p7m', delete=False) as tmp_p7m:
                tmp_p7m.write(file_content)
                tmp_p7m_path = tmp_p7m.name
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.xml', delete=False) as tmp_xml:
                tmp_xml_path = tmp_xml.name
            
            try:
                # Usa OpenSSL per estrarre il contenuto del file .p7m
                # -verify: verifica la firma (ma non fallisce se non può verificare)
                # -noverify: non verifica i certificati (accetta file anche senza catena di certificati valida)
                # -in: file di input (.p7m)
                # -out: file di output (.xml)
                result = subprocess.run(
                    ['openssl', 'smime', '-verify', '-noverify', '-in', tmp_p7m_path, '-inform', 'DER', '-out', tmp_xml_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Anche se la verifica fallisce, il contenuto viene estratto
                # Leggi il file XML estratto
                if os.path.exists(tmp_xml_path) and os.path.getsize(tmp_xml_path) > 0:
                    with open(tmp_xml_path, 'rb') as f:
                        xml_content = f.read()
                    _logger.info("File .p7m decifrato con successo usando OpenSSL")
                    return xml_content
                else:
                    _logger.warning(f"OpenSSL non ha prodotto output. Stderr: {result.stderr}")
                    return None
                    
            finally:
                # Pulisci i file temporanei
                try:
                    os.unlink(tmp_p7m_path)
                    os.unlink(tmp_xml_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            _logger.error("Timeout durante la decifrazione del file .p7m")
            return None
        except Exception as e:
            _logger.error(f"Errore durante la decifrazione del file .p7m: {e}", exc_info=True)
            return None

    def _extract_total_from_messages(self):
        """
        Estrae il totale dai messaggi/chatter della fattura.
        Odoo scrive "Valore totale dal file XML: XXXX.XX" quando importa la fattura.
        """
        self.ensure_one()
        
        # Cerca nei messaggi della fattura
        messages = self.message_ids
        
        for message in messages:
            if message.body:
                # Cerca il pattern "Valore totale dal file XML: XXXX.XX"
                # Supporta vari formati: con virgola, punto, spazi, ecc.
                patterns = [
                    r'Valore totale dal file XML:\s*([0-9]+[.,][0-9]{2})',
                    r'Totale.*XML.*:\s*([0-9]+[.,][0-9]{2})',
                    r'ImportoTotaleDocumento.*:\s*([0-9]+[.,][0-9]{2})',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, message.body, re.IGNORECASE)
                    if match:
                        total_str = match.group(1)
                        # Sostituisci virgola con punto per conversione
                        total_str = total_str.replace(',', '.')
                        try:
                            total = float(total_str)
                            _logger.info(f"Totale estratto dai messaggi: {total}")
                            return total
                        except ValueError:
                            _logger.warning(f"Impossibile convertire il totale: {total_str}")
        
        return None

    def _parse_xml_and_extract_total(self, xml_content):
        """
        Parsa il contenuto XML e estrae il totale.
        Supporta sia il tag ImportoTotaleDocumento che il calcolo dalle righe.
        """
        try:
            import xml.etree.ElementTree as ET
            from decimal import Decimal, ROUND_HALF_UP
            
            # Prova a parsare l'XML
            try:
                root = ET.fromstring(xml_content)
            except Exception as e:
                _logger.warning(f"Impossibile parsare il contenuto XML: {e}")
                return None
            
            # Namespace per FatturaPA
            namespaces = {
                'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
            }
            
            # METODO 1: Cerca il totale documento
            total_element = None
            
            # Prova con namespace
            total_element = root.find('.//p:ImportoTotaleDocumento', namespaces)
            
            # Prova senza namespace
            if total_element is None:
                total_element = root.find('.//ImportoTotaleDocumento')
            
            # Cerca in tutti gli elementi
            if total_element is None:
                for elem in root.iter():
                    if elem.tag.endswith('ImportoTotaleDocumento'):
                        total_element = elem
                        break
            
            if total_element is not None and total_element.text:
                try:
                    total_from_tag = float(total_element.text)
                    _logger.info(f"Totale estratto da ImportoTotaleDocumento: {total_from_tag}")
                    return total_from_tag
                except ValueError:
                    _logger.warning(f"Impossibile convertire il totale: {total_element.text}")
            
            # METODO 2: Calcola il totale dalle righe
            _logger.info("Tag ImportoTotaleDocumento non trovato, calcolo il totale dalle righe...")
            
            # Trova tutte le righe fattura
            lines = []
            
            # Prova con namespace
            for line in root.findall('.//p:DettaglioLinee', namespaces):
                lines.append(line)
            
            # Prova senza namespace
            if not lines:
                for line in root.findall('.//DettaglioLinee'):
                    lines.append(line)
            
            # Cerca in tutti gli elementi
            if not lines:
                for elem in root.iter():
                    if elem.tag.endswith('DettaglioLinee'):
                        lines.append(elem)
            
            if not lines:
                _logger.warning("Nessuna riga fattura trovata nell'XML")
                return None
            
            # Calcola il totale imponibile dalle righe
            total_imponibile = Decimal('0.00')
            
            for line in lines:
                # Cerca PrezzoTotale (importo totale della riga)
                prezzo_totale = None
                
                for elem in line.iter():
                    if elem.tag.endswith('PrezzoTotale') and elem.text:
                        try:
                            prezzo_totale = Decimal(elem.text)
                            break
                        except:
                            pass
                
                # Se non c'è PrezzoTotale, calcola da PrezzoUnitario * Quantita
                if prezzo_totale is None:
                    prezzo_unitario = None
                    quantita = None
                    
                    for elem in line.iter():
                        if elem.tag.endswith('PrezzoUnitario') and elem.text:
                            try:
                                prezzo_unitario = Decimal(elem.text)
                            except:
                                pass
                        elif elem.tag.endswith('Quantita') and elem.text:
                            try:
                                quantita = Decimal(elem.text)
                            except:
                                pass
                    
                    if prezzo_unitario is not None and quantita is not None:
                        prezzo_totale = prezzo_unitario * quantita
                
                if prezzo_totale is not None:
                    total_imponibile += prezzo_totale
            
            _logger.info(f"Totale imponibile calcolato dalle righe: {total_imponibile}")
            
            # Trova i riepiloghi IVA
            total_iva = Decimal('0.00')
            
            # Cerca DatiRiepilogo
            riepiloghi = []
            for riepilogo in root.findall('.//p:DatiRiepilogo', namespaces):
                riepiloghi.append(riepilogo)
            
            if not riepiloghi:
                for riepilogo in root.findall('.//DatiRiepilogo'):
                    riepiloghi.append(riepilogo)
            
            if not riepiloghi:
                for elem in root.iter():
                    if elem.tag.endswith('DatiRiepilogo'):
                        riepiloghi.append(elem)
            
            for riepilogo in riepiloghi:
                for elem in riepilogo.iter():
                    if elem.tag.endswith('Imposta') and elem.text:
                        try:
                            total_iva += Decimal(elem.text)
                        except:
                            pass
            
            _logger.info(f"Totale IVA calcolato: {total_iva}")
            
            # Calcola il totale finale
            total_finale = total_imponibile + total_iva
            
            # Arrotonda a 2 decimali
            total_finale = float(total_finale.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            _logger.info(f"Totale finale calcolato: {total_finale}")
            
            return total_finale
            
        except Exception as e:
            _logger.error(f"Errore nel parsing dell'XML: {e}", exc_info=True)
        
        return None

    def _extract_xml_total_from_attachment(self):
        """
        Estrae il totale dal file XML allegato alla fattura.
        Gestisce file .xml e .p7m (firmati digitalmente).
        """
        self.ensure_one()
        
        # METODO 1: Cerca nei messaggi (più veloce e affidabile)
        total_from_messages = self._extract_total_from_messages()
        if total_from_messages:
            return total_from_messages
        
        # METODO 2: Leggi direttamente dai file allegati
        _logger.info("Totale non trovato nei messaggi, provo a leggere i file allegati...")
        
        # Cerca allegati XML (.xml e .p7m)
        xml_attachments = self.attachment_ids.filtered(
            lambda a: a.name.endswith('.xml') or a.name.endswith('.p7m')
        )
        
        if not xml_attachments:
            _logger.warning("Nessun file XML o .p7m trovato negli allegati")
            return None
        
        # Prova con ogni allegato trovato
        for attachment in xml_attachments:
            _logger.info(f"Provo a leggere il file: {attachment.name}")
            
            try:
                # Leggi il contenuto dell'allegato
                file_content = attachment.raw
                xml_content = None
                
                # Se è un file .p7m, decifralo con OpenSSL
                if attachment.name.endswith('.p7m'):
                    _logger.info("File .p7m rilevato, decifrazione con OpenSSL...")
                    xml_content = self._decrypt_p7m_file(file_content)
                    if not xml_content:
                        _logger.warning(f"Impossibile decifrare il file .p7m: {attachment.name}")
                        continue
                else:
                    # È già un file .xml
                    xml_content = file_content
                
                # Parsa l'XML ed estrai il totale
                total = self._parse_xml_and_extract_total(xml_content)
                if total:
                    return total
                    
            except Exception as e:
                _logger.error(f"Errore durante l'elaborazione del file {attachment.name}: {e}", exc_info=True)
                continue
        
        return None

    def action_add_sdi_rounding_line(self):
        """
        Estrae automaticamente il totale dal file XML e aggiunge una riga di arrotondamento
        per bilanciare la differenza tra il totale XML SDI e il totale calcolato da Odoo.
        Tutto in un solo click!
        """
        self.ensure_one()
        
        # Verifica che sia una fattura fornitore
        if self.move_type not in ('in_invoice', 'in_refund'):
            raise UserError(_(
                'Questa funzione è disponibile solo per le fatture fornitore.'
            ))
        
        # Verifica che la fattura sia in bozza
        if self.state != 'draft':
            raise UserError(_(
                'La fattura deve essere in stato bozza per aggiungere '
                'una riga di arrotondamento.'
            ))
        
        # Verifica se esiste già una riga di arrotondamento
        if self.has_rounding_line:
            raise UserError(_(
                'Esiste già una riga di arrotondamento in questa fattura. '
                'Rimuoverla prima di crearne una nuova.'
            ))
        
        # ESTRAZIONE AUTOMATICA DEL TOTALE XML
        extracted_total = self._extract_xml_total_from_attachment()
        
        if not extracted_total:
            raise UserError(_(
                'Non è stato possibile estrarre il totale dal file XML.\n\n'
                'Verificare che:\n'
                '• Il file XML (.xml o .p7m) sia allegato alla fattura\n'
                '• Il file sia in formato FatturaPA valido\n'
                '• OpenSSL sia disponibile sul server (per file .p7m)\n\n'
                'In alternativa, inserire manualmente il totale nel campo\n'
                '"Totale XML SDI" nel tab "Altre Informazioni" e riprovare.'
            ))
        
        # Salva il totale estratto
        self.sdi_xml_total = extracted_total
        
        # Calcola la differenza
        difference = self.sdi_rounding_difference
        
        # Se la differenza è zero o trascurabile, non fare nulla
        if abs(difference) < 0.01:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✓ Nessun Arrotondamento Necessario'),
                    'message': _(
                        'Totale XML: %.2f €\n'
                        'Totale Odoo: %.2f €\n'
                        'Differenza: %.2f €\n\n'
                        'La differenza è trascurabile, non è necessario aggiungere una riga di arrotondamento.'
                    ) % (extracted_total, self.amount_total, difference),
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # Cerca il prodotto di arrotondamento
        rounding_product = self.env['product.product'].search([
            ('default_code', '=', 'SDI_ROUNDING')
        ], limit=1)
        
        # Se non esiste, crealo
        if not rounding_product:
            rounding_product = self._create_rounding_product()
        
        # Cerca il conto contabile appropriato
        account = rounding_product.property_account_expense_id or \
                  rounding_product.categ_id.property_account_expense_categ_id
        
        if not account:
            raise UserError(_(
                'Non è stato possibile trovare un conto contabile per il prodotto '
                'di arrotondamento. Verificare la configurazione del prodotto.'
            ))
        
        # Crea la riga di arrotondamento
        self.env['account.move.line'].create({
            'move_id': self.id,
            'product_id': rounding_product.id,
            'name': f'Arrotondamento SDI - Differenza fattura elettronica',
            'account_id': account.id,
            'quantity': 1,
            'price_unit': difference,
            'tax_ids': [(5, 0, 0)],  # Nessuna tassa
        })
        
        # Ricalcola i totali della fattura
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        # Mostra notifica e ricarica la vista
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✓ Arrotondamento Completato'),
                'message': _(
                    'Totale XML estratto: %.2f €\n'
                    'Totale Odoo precedente: %.2f €\n'
                    'Riga di arrotondamento aggiunta: %.2f €\n\n'
                    'Il totale della fattura ora corrisponde al file XML!'
                ) % (extracted_total, extracted_total - difference, difference),
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _create_rounding_product(self):
        """Crea il prodotto per le righe di arrotondamento SDI"""
        
        # Cerca la categoria "Spese" o crea una categoria specifica
        expense_categ = self.env['product.category'].search([
            ('name', 'ilike', 'spese')
        ], limit=1)
        
        if not expense_categ:
            expense_categ = self.env['product.category'].search([], limit=1)
        
        # Crea il prodotto
        product = self.env['product.product'].create({
            'name': 'Arrotondamento Fatture Elettroniche SDI',
            'default_code': 'SDI_ROUNDING',
            'type': 'service',
            'categ_id': expense_categ.id if expense_categ else False,
            'purchase_ok': False,
            'sale_ok': False,
            'invoice_policy': 'order',
            'description': 'Prodotto utilizzato per gestire gli arrotondamenti '
                          'delle fatture elettroniche importate dallo SDI',
        })
        
        return product

    def write(self, vals):
        """Override del metodo write per aggiungere automaticamente l'arrotondamento dopo l'importazione"""
        result = super(AccountMove, self).write(vals)
        
        # Se vengono aggiunti allegati, potrebbe essere un'importazione di fattura elettronica
        # Verifica se serve l'arrotondamento automatico
        if 'attachment_ids' in vals or 'invoice_line_ids' in vals:
            for move in self:
                # Se è una fattura fornitore in bozza e non ha già una riga di arrotondamento
                if move.move_type in ('in_invoice', 'in_refund') and move.state == 'draft' and not move.has_rounding_line:
                    # Usa un try-except per non bloccare il salvataggio
                    try:
                        # Verifica se c'è una differenza significativa
                        extracted_total = move._extract_xml_total_from_attachment()
                        if extracted_total and not move.sdi_xml_total:
                            move.sdi_xml_total = extracted_total
                            difference = extracted_total - move.amount_total
                            
                            # Se c'è una differenza significativa, aggiungi automaticamente l'arrotondamento
                            if abs(difference) >= 0.01:
                                _logger.info(f"Fattura {move.name}: rilevata differenza di {difference} €, aggiungo arrotondamento automatico")
                                
                                # Cerca il prodotto di arrotondamento
                                rounding_product = self.env['product.product'].search([
                                    ('default_code', '=', 'SDI_ROUNDING')
                                ], limit=1)
                                
                                if not rounding_product:
                                    rounding_product = move._create_rounding_product()
                                
                                account = rounding_product.property_account_expense_id or \
                                          rounding_product.categ_id.property_account_expense_categ_id
                                
                                if account:
                                    # Crea la riga di arrotondamento
                                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                                        'move_id': move.id,
                                        'product_id': rounding_product.id,
                                        'name': 'Arrotondamento SDI - Differenza fattura elettronica (automatico)',
                                        'account_id': account.id,
                                        'quantity': 1,
                                        'price_unit': difference,
                                        'tax_ids': [(5, 0, 0)],
                                    })
                                    
                                    # Ricalcola i totali
                                    move.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
                                    
                                    # Aggiungi un messaggio nel chatter
                                    move.message_post(
                                        body=f"<p>✓ Arrotondamento SDI aggiunto automaticamente</p>"
                                             f"<ul>"
                                             f"<li>Totale XML: {extracted_total:.2f} €</li>"
                                             f"<li>Totale Odoo precedente: {extracted_total - difference:.2f} €</li>"
                                             f"<li>Arrotondamento applicato: {difference:.2f} €</li>"
                                             f"</ul>"
                                    )
                    except Exception as e:
                        # Log l'errore ma non bloccare il salvataggio
                        _logger.warning(f"Impossibile aggiungere arrotondamento automatico alla fattura {move.name}: {e}")
        
        return result

    def action_remove_sdi_rounding_lines(self):
        """Rimuove tutte le righe di arrotondamento SDI dalla fattura"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_(
                'La fattura deve essere in stato bozza per rimuovere '
                'le righe di arrotondamento.'
            ))
        
        # Trova e rimuovi le righe di arrotondamento
        rounding_lines = self.invoice_line_ids.filtered(
            lambda l: l.name and 'Arrotondamento SDI' in l.name
        )
        
        if not rounding_lines:
            raise UserError(_('Non sono state trovate righe di arrotondamento.'))
        
        rounding_lines.unlink()
        
        # Resetta anche il campo totale XML
        self.sdi_xml_total = 0.0
        
        # Ricalcola i totali della fattura
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Righe di Arrotondamento Rimosse'),
                'message': _('Le righe di arrotondamento sono state rimosse e il campo "Totale XML SDI" è stato azzerato.'),
                'type': 'info',
                'sticky': False,
            }
        }

