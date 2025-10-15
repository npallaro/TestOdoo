# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

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

    def _extract_xml_total_from_attachment(self):
        """Estrae il totale dal file XML allegato alla fattura"""
        self.ensure_one()
        
        # Cerca allegati XML
        xml_attachments = self.attachment_ids.filtered(
            lambda a: a.name.endswith('.xml') or 'xml' in a.name.lower()
        )
        
        if not xml_attachments:
            return None
        
        # Prendi il primo allegato XML
        attachment = xml_attachments[0]
        
        try:
            import xml.etree.ElementTree as ET
            
            # Leggi il contenuto dell'allegato
            xml_content = attachment.raw
            
            # Prova a parsare l'XML
            try:
                root = ET.fromstring(xml_content)
            except:
                # Se fallisce, potrebbe essere un p7m o corrotto
                _logger.warning(f"Impossibile parsare il file XML {attachment.name}")
                return None
            
            # Namespace per FatturaPA
            namespaces = {
                'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
            }
            
            # Cerca il totale documento con vari metodi
            total_element = None
            
            # Metodo 1: con namespace
            total_element = root.find('.//p:ImportoTotaleDocumento', namespaces)
            
            # Metodo 2: senza namespace
            if total_element is None:
                total_element = root.find('.//ImportoTotaleDocumento')
            
            # Metodo 3: cerca in tutti gli elementi
            if total_element is None:
                for elem in root.iter():
                    if elem.tag.endswith('ImportoTotaleDocumento'):
                        total_element = elem
                        break
            
            if total_element is not None and total_element.text:
                try:
                    return float(total_element.text)
                except ValueError:
                    _logger.warning(f"Impossibile convertire il totale: {total_element.text}")
                    return None
            
        except Exception as e:
            _logger.warning(f"Errore nell'estrazione del totale XML: {e}")
        
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
                'Non è stato possibile estrarre il totale dal file XML allegato.\n\n'
                'Verificare che:\n'
                '• Il file XML (.xml o .p7m) sia allegato alla fattura\n'
                '• Il file sia in formato FatturaPA valido\n'
                '• Il file contenga il tag <ImportoTotaleDocumento>\n\n'
                'Se il problema persiste, contattare il supporto tecnico.'
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
                    'title': _('Nessun Arrotondamento Necessario'),
                    'message': _(
                        'Il totale XML (%.2f €) corrisponde già al totale calcolato da Odoo.\n'
                        'Non è necessario aggiungere una riga di arrotondamento.'
                    ) % extracted_total,
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

