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
    
    sdi_xml_untaxed = fields.Monetary(
        string='Imponibile XML SDI',
        currency_field='currency_id',
        help='Imponibile totale estratto dal file XML dello SDI.'
    )
    
    sdi_xml_tax = fields.Monetary(
        string='IVA XML SDI',
        currency_field='currency_id',
        help='IVA totale estratta dal file XML dello SDI.'
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
                result = subprocess.run(
                    ['openssl', 'smime', '-verify', '-noverify', '-in', tmp_p7m_path, '-inform', 'DER', '-out', tmp_xml_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
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
                patterns = [
                    r'Valore totale dal file XML:\s*([0-9]+[.,][0-9]{2})',
                    r'Totale.*XML.*:\s*([0-9]+[.,][0-9]{2})',
                    r'ImportoTotaleDocumento.*:\s*([0-9]+[.,][0-9]{2})',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, message.body, re.IGNORECASE)
                    if match:
                        total_str = match.group(1)
                        total_str = total_str.replace(',', '.')
                        try:
                            total = float(total_str)
                            _logger.info(f"Totale estratto dai messaggi: {total}")
                            return {'total': total, 'untaxed': None, 'tax': None}
                        except ValueError:
                            _logger.warning(f"Impossibile convertire il totale: {total_str}")
        
        return None

    def _parse_xml_and_extract_totals(self, xml_content):
        """
        Parsa il contenuto XML ed estrae imponibile, IVA e totale.
        NUOVA LOGICA: Estrae sempre dai DatiRiepilogo (più affidabile) e verifica ImportoTotaleDocumento.
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
            
            # METODO PRINCIPALE: Estrai da DatiRiepilogo (più affidabile)
            total_imponibile = Decimal('0.00')
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
            
            if riepiloghi:
                _logger.info(f"Trovati {len(riepiloghi)} riepiloghi IVA")
                
                for riepilogo in riepiloghi:
                    imponibile_elem = None
                    imposta_elem = None
                    
                    for elem in riepilogo.iter():
                        if elem.tag.endswith('ImponibileImporto') and elem.text:
                            imponibile_elem = elem
                        elif elem.tag.endswith('Imposta') and elem.text:
                            imposta_elem = elem
                    
                    if imponibile_elem is not None:
                        try:
                            total_imponibile += Decimal(imponibile_elem.text)
                        except:
                            pass
                    
                    if imposta_elem is not None:
                        try:
                            total_iva += Decimal(imposta_elem.text)
                        except:
                            pass
                
                _logger.info(f"Imponibile totale da DatiRiepilogo: {total_imponibile}")
                _logger.info(f"IVA totale da DatiRiepilogo: {total_iva}")
                
                # Calcola il totale
                total_calcolato = total_imponibile + total_iva
                _logger.info(f"Totale calcolato (Imp + IVA): {total_calcolato}")
                
                # Verifica con ImportoTotaleDocumento
                total_element = None
                total_element = root.find('.//p:ImportoTotaleDocumento', namespaces)
                if total_element is None:
                    total_element = root.find('.//ImportoTotaleDocumento')
                if total_element is None:
                    for elem in root.iter():
                        if elem.tag.endswith('ImportoTotaleDocumento'):
                            total_element = elem
                            break
                
                if total_element is not None and total_element.text:
                    try:
                        total_documento = Decimal(total_element.text)
                        _logger.info(f"ImportoTotaleDocumento: {total_documento}")
                        
                        # Verifica se c'è una discrepanza nel file XML stesso
                        diff_xml = total_calcolato - total_documento
                        if abs(diff_xml) > Decimal('0.01'):
                            _logger.warning(
                                f"⚠️ ANOMALIA NEL FILE XML: "
                                f"ImportoTotaleDocumento ({total_documento}) != "
                                f"Imponibile + IVA ({total_calcolato}). "
                                f"Differenza: {diff_xml}. "
                                f"Userò il totale calcolato."
                            )
                    except:
                        pass
                
                # Arrotonda a 2 decimali
                return {
                    'total': float(total_calcolato.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                    'untaxed': float(total_imponibile.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                    'tax': float(total_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                }
            
            # FALLBACK: Se non ci sono DatiRiepilogo, calcola dalle righe
            _logger.info("DatiRiepilogo non trovati, calcolo dalle righe...")
            
            lines = []
            for line in root.findall('.//p:DettaglioLinee', namespaces):
                lines.append(line)
            if not lines:
                for line in root.findall('.//DettaglioLinee'):
                    lines.append(line)
            if not lines:
                for elem in root.iter():
                    if elem.tag.endswith('DettaglioLinee'):
                        lines.append(elem)
            
            if not lines:
                _logger.warning("Nessuna riga fattura trovata nell'XML")
                return None
            
            total_imponibile = Decimal('0.00')
            
            for line in lines:
                prezzo_totale = None
                
                for elem in line.iter():
                    if elem.tag.endswith('PrezzoTotale') and elem.text:
                        try:
                            prezzo_totale = Decimal(elem.text)
                            break
                        except:
                            pass
                
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
            
            # Cerca il totale documento
            total_element = root.find('.//p:ImportoTotaleDocumento', namespaces)
            if total_element is None:
                total_element = root.find('.//ImportoTotaleDocumento')
            if total_element is None:
                for elem in root.iter():
                    if elem.tag.endswith('ImportoTotaleDocumento'):
                        total_element = elem
                        break
            
            if total_element is not None and total_element.text:
                try:
                    total_documento = Decimal(total_element.text)
                    total_iva = total_documento - total_imponibile
                    
                    return {
                        'total': float(total_documento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                        'untaxed': float(total_imponibile.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                        'tax': float(total_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                    }
                except:
                    pass
            
            return None
            
        except Exception as e:
            _logger.error(f"Errore nel parsing dell'XML: {e}", exc_info=True)
        
        return None

    def _extract_xml_totals_from_attachment(self):
        """
        Estrae imponibile, IVA e totale dal file XML allegato alla fattura.
        Gestisce file .xml e .p7m (firmati digitalmente).
        """
        self.ensure_one()
        
        # METODO 1: Cerca nei messaggi (più veloce)
        totals_from_messages = self._extract_total_from_messages()
        if totals_from_messages and totals_from_messages.get('total'):
            # Dai messaggi abbiamo solo il totale, non imponibile e IVA
            # Proviamo comunque a leggere il file per avere i dettagli
            pass
        
        # METODO 2: Leggi direttamente dai file allegati
        _logger.info("Provo a leggere i file allegati per estrarre i dettagli...")
        
        xml_attachments = self.attachment_ids.filtered(
            lambda a: a.name.endswith('.xml') or a.name.endswith('.p7m')
        )
        
        if not xml_attachments:
            _logger.warning("Nessun file XML o .p7m trovato negli allegati")
            # Se abbiamo il totale dai messaggi, restituiscilo
            if totals_from_messages:
                return totals_from_messages
            return None
        
        # Prova con ogni allegato trovato
        for attachment in xml_attachments:
            _logger.info(f"Provo a leggere il file: {attachment.name}")
            
            try:
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
                    xml_content = file_content
                
                # Parsa l'XML ed estrai i totali
                totals = self._parse_xml_and_extract_totals(xml_content)
                if totals:
                    return totals
                    
            except Exception as e:
                _logger.error(f"Errore durante l'elaborazione del file {attachment.name}: {e}", exc_info=True)
                continue
        
        # Se non abbiamo trovato nulla nei file ma abbiamo il totale dai messaggi
        if totals_from_messages:
            return totals_from_messages
        
        return None

    def action_add_sdi_rounding_line(self):
        """
        Estrae automaticamente imponibile, IVA e totale dal file XML e aggiunge una riga di arrotondamento
        per bilanciare la differenza tra il totale XML SDI e il totale calcolato da Odoo.
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
        
        # ESTRAZIONE AUTOMATICA DEI TOTALI XML
        extracted_totals = self._extract_xml_totals_from_attachment()
        
        if not extracted_totals or not extracted_totals.get('total'):
            raise UserError(_(
                'Non è stato possibile estrarre il totale dal file XML.\n\n'
                'Verificare che:\n'
                '• Il file XML (.xml o .p7m) sia allegato alla fattura\n'
                '• Il file sia in formato FatturaPA valido\n'
                '• OpenSSL sia disponibile sul server (per file .p7m)\n\n'
                'In alternativa, inserire manualmente il totale nel campo\n'
                '"Totale XML SDI" nel tab "Altre Informazioni" e riprovare.'
            ))
        
        # Salva i totali estratti
        self.sdi_xml_total = extracted_totals['total']
        self.sdi_xml_untaxed = extracted_totals.get('untaxed', 0.0)
        self.sdi_xml_tax = extracted_totals.get('tax', 0.0)
        
        # Calcola le differenze
        diff_total = self.sdi_xml_total - self.amount_total
        diff_untaxed = self.sdi_xml_untaxed - self.amount_untaxed if self.sdi_xml_untaxed else 0.0
        diff_tax = self.sdi_xml_tax - self.amount_tax if self.sdi_xml_tax else 0.0
        
        _logger.info(f"Differenze: Totale={diff_total}, Imponibile={diff_untaxed}, IVA={diff_tax}")
        
        # Se la differenza è zero o trascurabile, non fare nulla
        if abs(diff_total) < 0.01:
            message = _('Totale XML: %.2f €\nTotale Odoo: %.2f €\nDifferenza: %.2f €\n\n'
                       'La differenza è trascurabile, non è necessario aggiungere una riga di arrotondamento.') % (
                self.sdi_xml_total, self.amount_total, diff_total)
            
            if self.sdi_xml_untaxed and self.sdi_xml_tax:
                message += _('\n\nDettagli:\nImponibile XML: %.2f € | Odoo: %.2f € | Diff: %.2f €\n'
                           'IVA XML: %.2f € | Odoo: %.2f € | Diff: %.2f €') % (
                    self.sdi_xml_untaxed, self.amount_untaxed, diff_untaxed,
                    self.sdi_xml_tax, self.amount_tax, diff_tax)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✓ Nessun Arrotondamento Necessario'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # Cerca il prodotto di arrotondamento
        rounding_product = self.env['product.product'].search([
            ('default_code', '=', 'SDI_ROUNDING')
        ], limit=1)
        
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
        # La differenza totale include già l'IVA, quindi usiamo quella
        self.env['account.move.line'].create({
            'move_id': self.id,
            'product_id': rounding_product.id,
            'name': f'Arrotondamento SDI - Differenza fattura elettronica',
            'account_id': account.id,
            'quantity': 1,
            'price_unit': diff_total,
            'tax_ids': [(5, 0, 0)],  # Nessuna tassa
        })
        
        # Ricalcola i totali della fattura
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        # Prepara il messaggio di conferma
        message = _('Totale XML estratto: %.2f €\nTotale Odoo precedente: %.2f €\n'
                   'Riga di arrotondamento aggiunta: %.2f €\n\n'
                   'Il totale della fattura ora corrisponde al file XML!') % (
            self.sdi_xml_total, self.sdi_xml_total - diff_total, diff_total)
        
        if self.sdi_xml_untaxed and self.sdi_xml_tax:
            message += _('\n\nDettagli XML:\nImponibile: %.2f € (Odoo: %.2f € | Diff: %.2f €)\n'
                       'IVA: %.2f € (Odoo: %.2f € | Diff: %.2f €)') % (
                self.sdi_xml_untaxed, self.amount_untaxed, diff_untaxed,
                self.sdi_xml_tax, self.amount_tax, diff_tax)
        
        # Mostra notifica e ricarica la vista
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✓ Arrotondamento Completato'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _create_rounding_product(self):
        """Crea il prodotto per le righe di arrotondamento SDI"""
        
        expense_categ = self.env['product.category'].search([
            ('name', 'ilike', 'spese')
        ], limit=1)
        
        if not expense_categ:
            expense_categ = self.env['product.category'].search([], limit=1)
        
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
        if 'attachment_ids' in vals or 'invoice_line_ids' in vals:
            for move in self:
                if move.move_type in ('in_invoice', 'in_refund') and move.state == 'draft' and not move.has_rounding_line:
                    try:
                        extracted_totals = move._extract_xml_totals_from_attachment()
                        if extracted_totals and extracted_totals.get('total') and not move.sdi_xml_total:
                            move.sdi_xml_total = extracted_totals['total']
                            move.sdi_xml_untaxed = extracted_totals.get('untaxed', 0.0)
                            move.sdi_xml_tax = extracted_totals.get('tax', 0.0)
                            
                            difference = move.sdi_xml_total - move.amount_total
                            
                            if abs(difference) >= 0.01:
                                _logger.info(f"Fattura {move.name}: rilevata differenza di {difference} €, aggiungo arrotondamento automatico")
                                
                                rounding_product = self.env['product.product'].search([
                                    ('default_code', '=', 'SDI_ROUNDING')
                                ], limit=1)
                                
                                if not rounding_product:
                                    rounding_product = move._create_rounding_product()
                                
                                account = rounding_product.property_account_expense_id or \
                                          rounding_product.categ_id.property_account_expense_categ_id
                                
                                if account:
                                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                                        'move_id': move.id,
                                        'product_id': rounding_product.id,
                                        'name': 'Arrotondamento SDI - Differenza fattura elettronica (automatico)',
                                        'account_id': account.id,
                                        'quantity': 1,
                                        'price_unit': difference,
                                        'tax_ids': [(5, 0, 0)],
                                    })
                                    
                                    move.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
                                    
                                    diff_untaxed = move.sdi_xml_untaxed - move.amount_untaxed if move.sdi_xml_untaxed else 0.0
                                    diff_tax = move.sdi_xml_tax - move.amount_tax if move.sdi_xml_tax else 0.0
                                    
                                    body = f"<p>✓ Arrotondamento SDI aggiunto automaticamente</p><ul>"
                                    body += f"<li>Totale XML: {move.sdi_xml_total:.2f} €</li>"
                                    body += f"<li>Totale Odoo precedente: {move.sdi_xml_total - difference:.2f} €</li>"
                                    body += f"<li>Arrotondamento applicato: {difference:.2f} €</li>"
                                    if move.sdi_xml_untaxed and move.sdi_xml_tax:
                                        body += f"<li>Imponibile XML: {move.sdi_xml_untaxed:.2f} € (Odoo: {move.amount_untaxed:.2f} € | Diff: {diff_untaxed:.2f} €)</li>"
                                        body += f"<li>IVA XML: {move.sdi_xml_tax:.2f} € (Odoo: {move.amount_tax:.2f} € | Diff: {diff_tax:.2f} €)</li>"
                                    body += "</ul>"
                                    
                                    move.message_post(body=body)
                    except Exception as e:
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
        
        rounding_lines = self.invoice_line_ids.filtered(
            lambda l: l.name and 'Arrotondamento SDI' in l.name
        )
        
        if not rounding_lines:
            raise UserError(_('Non sono state trovate righe di arrotondamento.'))
        
        rounding_lines.unlink()
        
        # Resetta anche i campi totale XML
        self.sdi_xml_total = 0.0
        self.sdi_xml_untaxed = 0.0
        self.sdi_xml_tax = 0.0
        
        # Ricalcola i totali della fattura
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Righe di Arrotondamento Rimosse'),
                'message': _('Le righe di arrotondamento sono state rimosse e i campi XML sono stati azzerati.'),
                'type': 'info',
                'sticky': False,
            }
        }

