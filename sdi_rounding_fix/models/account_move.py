# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import re

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

    def _extract_xml_total_from_attachment(self):
        """
        Estrae il totale dal file XML allegato alla fattura.
        Gestisce file .xml e .p7m (firmati digitalmente).
        """
        self.ensure_one()
        
        # Prima prova a estrarre dai messaggi (più affidabile per file .p7m)
        total_from_messages = self._extract_total_from_messages()
        if total_from_messages:
            return total_from_messages
        
        # Se non trovato nei messaggi, prova a leggere il file XML direttamente
        # Cerca allegati XML (solo .xml, non .p7m che sono firmati)
        xml_attachments = self.attachment_ids.filtered(
            lambda a: a.name.endswith('.xml') and not a.name.endswith('.p7m')
        )
        
        if not xml_attachments:
            _logger.info("Nessun file XML non firmato trovato, il totale dovrebbe essere nei messaggi")
            return None
        
        # Prendi il primo allegato XML
        attachment = xml_attachments[0]
        
        try:
            import xml.etree.ElementTree as ET
            from decimal import Decimal, ROUND_HALF_UP
            
            # Leggi il contenuto dell'allegato
            xml_content = attachment.raw
            
            # Prova a parsare l'XML
            try:
                root = ET.fromstring(xml_content)
            except Exception as e:
                _logger.warning(f"Impossibile parsare il file XML {attachment.name}: {e}")
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
            _logger.error(f"Errore nell'estrazione del totale XML: {e}", exc_info=True)
        
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
                '• La fattura sia stata importata tramite il sistema di fatturazione elettronica\n'
                '• Il file XML sia allegato alla fattura\n'
                '• Nei messaggi della fattura sia presente il "Valore totale dal file XML"\n\n'
                'Se la fattura è stata creata manualmente, inserire il totale XML manualmente '
                'nel campo "Totale XML SDI" nel tab "Altre Informazioni".'
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
        
        # Ricalcola i totali
        self._recompute_dynamic_lines(recompute_all_taxes=True)
        
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
        
        # Ricalcola i totali
        self._recompute_dynamic_lines(recompute_all_taxes=True)
        
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

