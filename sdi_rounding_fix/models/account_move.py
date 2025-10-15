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

    # Campi XML SDI (estratti dal file)
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
    
    sdi_xml_total = fields.Monetary(
        string='Totale XML SDI',
        currency_field='currency_id',
        help='Totale calcolato (Imponibile + IVA) dal file XML dello SDI.'
    )
    
    # Campo informativo: totale a pagare dal tag ImportoTotaleDocumento
    sdi_total_to_pay = fields.Monetary(
        string='Totale a Pagare SDI',
        currency_field='currency_id',
        help='Totale a pagare dal tag ImportoTotaleDocumento del file XML. '
             'Può differire dal totale contabile se ci sono omaggi/trasporti.'
    )
    
    # Campo informativo: differenza omaggi/trasporti
    sdi_gift_transport_diff = fields.Monetary(
        string='Diff. Omaggi/Trasporti',
        compute='_compute_sdi_gift_transport_diff',
        currency_field='currency_id',
        help='Differenza tra totale contabile e totale a pagare, '
             'dovuta a omaggi, trasporti non imponibili, ecc.'
    )
    
    # Campo informativo: tipo di differenza
    sdi_diff_type = fields.Char(
        string='Tipo Differenza',
        compute='_compute_sdi_gift_transport_diff',
        help='Descrizione del tipo di differenza (omaggi, trasporti, ecc.)'
    )
    
    # Campi di verifica differenze
    sdi_untaxed_diff = fields.Monetary(
        string='Diff. Imponibile',
        compute='_compute_sdi_differences',
        currency_field='currency_id',
        help='Differenza tra imponibile XML e Odoo'
    )
    
    sdi_tax_diff = fields.Monetary(
        string='Diff. IVA',
        compute='_compute_sdi_differences',
        currency_field='currency_id',
        help='Differenza tra IVA XML e Odoo'
    )
    
    sdi_total_diff = fields.Monetary(
        string='Diff. Totale',
        compute='_compute_sdi_differences',
        currency_field='currency_id',
        help='Differenza tra totale XML e Odoo'
    )
    
    # Campo per verificare se esiste già una riga di arrotondamento
    has_rounding_line = fields.Boolean(
        string='Ha Riga Arrotondamento',
        compute='_compute_has_rounding_line',
        help='Indica se la fattura contiene già una riga di arrotondamento SDI'
    )

    @api.depends('sdi_xml_total', 'sdi_total_to_pay')
    def _compute_sdi_gift_transport_diff(self):
        """Calcola la differenza dovuta a omaggi/trasporti"""
        for move in self:
            if move.sdi_xml_total and move.sdi_total_to_pay:
                diff = move.sdi_xml_total - move.sdi_total_to_pay
                move.sdi_gift_transport_diff = diff
                
                # Determina il tipo di differenza
                if abs(diff) < 0.01:
                    move.sdi_diff_type = False
                elif diff > 0:
                    move.sdi_diff_type = 'Omaggi/Trasporti non imponibili'
                else:
                    move.sdi_diff_type = 'Anomalia XML (totale a pagare > totale)'
            else:
                move.sdi_gift_transport_diff = 0.0
                move.sdi_diff_type = False

    @api.depends('sdi_xml_untaxed', 'amount_untaxed', 'sdi_xml_tax', 'amount_tax', 'sdi_xml_total', 'amount_total')
    def _compute_sdi_differences(self):
        """Calcola le differenze tra XML e Odoo"""
        for move in self:
            move.sdi_untaxed_diff = (move.sdi_xml_untaxed - move.amount_untaxed) if move.sdi_xml_untaxed else 0.0
            move.sdi_tax_diff = (move.sdi_xml_tax - move.amount_tax) if move.sdi_xml_tax else 0.0
            move.sdi_total_diff = (move.sdi_xml_total - move.amount_total) if move.sdi_xml_total else 0.0

    @api.depends('invoice_line_ids.name')
    def _compute_has_rounding_line(self):
        """Verifica se esiste già una riga di arrotondamento"""
        for move in self:
            move.has_rounding_line = any(
                line.name and 'Arrotondamento SDI' in line.name 
                for line in move.invoice_line_ids
            )

    def _decrypt_p7m_file(self, file_content):
        """Decifra un file .p7m usando OpenSSL"""
        try:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.p7m', delete=False) as tmp_p7m:
                tmp_p7m.write(file_content)
                tmp_p7m_path = tmp_p7m.name
            
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.xml', delete=False) as tmp_xml:
                tmp_xml_path = tmp_xml.name
            
            try:
                result = subprocess.run(
                    ['openssl', 'smime', '-verify', '-noverify', '-in', tmp_p7m_path, '-inform', 'DER', '-out', tmp_xml_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if os.path.exists(tmp_xml_path) and os.path.getsize(tmp_xml_path) > 0:
                    with open(tmp_xml_path, 'rb') as f:
                        xml_content = f.read()
                    _logger.info("File .p7m decifrato con successo")
                    return xml_content
                else:
                    _logger.warning(f"OpenSSL non ha prodotto output")
                    return None
            finally:
                try:
                    os.unlink(tmp_p7m_path)
                    os.unlink(tmp_xml_path)
                except:
                    pass
        except Exception as e:
            _logger.error(f"Errore decifrazione .p7m: {e}")
            return None

    def _parse_xml_and_extract_totals(self, xml_content):
        """
        Parsa il contenuto XML ed estrae:
        - Riepiloghi IVA (per ogni aliquota: imponibile e IVA)
        - Totale calcolato (Imponibile + IVA)
        - Totale a pagare (ImportoTotaleDocumento)
        """
        try:
            import xml.etree.ElementTree as ET
            from decimal import Decimal, ROUND_HALF_UP
            
            try:
                root = ET.fromstring(xml_content)
            except Exception as e:
                _logger.warning(f"Impossibile parsare XML: {e}")
                return None
            
            namespaces = {'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2'}
            
            # Estrai riepiloghi IVA
            total_imponibile = Decimal('0.00')
            total_iva = Decimal('0.00')
            riepiloghi_iva = []
            
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
                    aliquota_elem = None
                    imponibile_elem = None
                    imposta_elem = None
                    natura_elem = None
                    
                    for elem in riepilogo.iter():
                        if elem.tag.endswith('AliquotaIVA') and elem.text:
                            aliquota_elem = elem
                        elif elem.tag.endswith('ImponibileImporto') and elem.text:
                            imponibile_elem = elem
                        elif elem.tag.endswith('Imposta') and elem.text:
                            imposta_elem = elem
                        elif elem.tag.endswith('Natura') and elem.text:
                            natura_elem = elem
                    
                    if aliquota_elem is not None and imponibile_elem is not None and imposta_elem is not None:
                        try:
                            aliquota = Decimal(aliquota_elem.text)
                            imponibile = Decimal(imponibile_elem.text)
                            imposta = Decimal(imposta_elem.text)
                            natura = natura_elem.text if natura_elem is not None else None
                            
                            total_imponibile += imponibile
                            total_iva += imposta
                            
                            riepiloghi_iva.append({
                                'aliquota': float(aliquota),
                                'imponibile': float(imponibile),
                                'imposta': float(imposta),
                                'natura': natura
                            })
                            
                            _logger.info(f"Riepilogo IVA {aliquota}%: Imp {imponibile} € | IVA {imposta} €")
                        except:
                            pass
                
                total_calcolato = total_imponibile + total_iva
                _logger.info(f"Totale calcolato: Imp {total_imponibile} + IVA {total_iva} = {total_calcolato}")
                
                # Estrai ImportoTotaleDocumento
                total_to_pay = None
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
                        total_to_pay = float(Decimal(total_element.text))
                        _logger.info(f"ImportoTotaleDocumento: {total_to_pay}")
                        
                        # Verifica anomalie
                        diff = total_calcolato - Decimal(str(total_to_pay))
                        if abs(diff) > Decimal('0.01'):
                            _logger.warning(f"⚠️ Differenza tra totale calcolato ({total_calcolato}) e ImportoTotaleDocumento ({total_to_pay}): {diff}")
                    except:
                        pass
                
                return {
                    'untaxed': float(total_imponibile),
                    'tax': float(total_iva),
                    'total': float(total_calcolato),
                    'total_to_pay': total_to_pay,
                    'riepiloghi_iva': riepiloghi_iva
                }
            
            return None
            
        except Exception as e:
            _logger.error(f"Errore parsing XML: {e}", exc_info=True)
            return None

    def _extract_xml_totals_from_attachment(self):
        """Estrae i totali dal file XML allegato"""
        self.ensure_one()
        
        xml_attachments = self.attachment_ids.filtered(
            lambda a: a.name.endswith('.xml') or a.name.endswith('.p7m')
        )
        
        if not xml_attachments:
            _logger.warning("Nessun file XML trovato")
            return None
        
        for attachment in xml_attachments:
            _logger.info(f"Elaboro file: {attachment.name}")
            
            try:
                file_content = attachment.raw
                xml_content = None
                
                if attachment.name.endswith('.p7m'):
                    _logger.info("Decifro file .p7m...")
                    xml_content = self._decrypt_p7m_file(file_content)
                    if not xml_content:
                        continue
                else:
                    xml_content = file_content
                
                totals = self._parse_xml_and_extract_totals(xml_content)
                if totals:
                    return totals
                    
            except Exception as e:
                _logger.error(f"Errore elaborazione {attachment.name}: {e}")
                continue
        
        return None

    def action_add_sdi_rounding_line(self):
        """
        Estrae i totali dal file XML e crea righe di arrotondamento
        (una per ogni aliquota IVA) per allineare i totali Odoo con quelli XML.
        """
        self.ensure_one()
        
        if self.move_type not in ('in_invoice', 'in_refund'):
            raise UserError(_('Questa funzione è disponibile solo per le fatture fornitore.'))
        
        if self.state != 'draft':
            raise UserError(_('La fattura deve essere in stato bozza.'))
        
        if self.has_rounding_line:
            raise UserError(_('Esiste già una riga di arrotondamento. Rimuoverla prima di crearne una nuova.'))
        
        # Estrai totali XML
        extracted_totals = self._extract_xml_totals_from_attachment()
        
        if not extracted_totals or not extracted_totals.get('riepiloghi_iva'):
            raise UserError(_(
                'Non è stato possibile estrarre i riepiloghi IVA dal file XML.\n\n'
                'Verificare che il file XML sia allegato e in formato FatturaPA valido.'
            ))
        
        # Salva i totali estratti
        self.sdi_xml_untaxed = extracted_totals['untaxed']
        self.sdi_xml_tax = extracted_totals['tax']
        self.sdi_xml_total = extracted_totals['total']
        self.sdi_total_to_pay = extracted_totals.get('total_to_pay', extracted_totals['total'])
        
        # Calcola differenze per ogni aliquota IVA
        riepiloghi_xml = extracted_totals['riepiloghi_iva']
        
        # Ottieni i totali IVA effettivi di Odoo per ogni aliquota
        # Usa amount_by_group che contiene: (tax_name, base, tax_amount, ...)
        odoo_by_tax = {}
        
        if self.amount_by_group:
            for group in self.amount_by_group:
                # group è una tupla: (tax_name, base_amount, tax_amount, group_key)
                tax_name = group[0]
                base_amount = group[1]
                tax_amount = group[2]
                
                # Estrai l'aliquota dal nome della tassa con regex
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', tax_name)
                if match:
                    tax_rate = float(match.group(1))
                else:
                    # Fallback: prova a estrarre dalla group_key
                    tax_rate = 0.0
                
                odoo_by_tax[tax_rate] = {
                    'untaxed': base_amount,
                    'tax': tax_amount
                }
        
        _logger.info(f"Odoo per aliquota (da amount_by_group): {odoo_by_tax}")
        _logger.info(f"XML riepiloghi: {riepiloghi_xml}")
        
        # Crea righe di arrotondamento
        righe_create = []
        
        for riepilogo in riepiloghi_xml:
            aliquota = riepilogo['aliquota']
            xml_untaxed = riepilogo['imponibile']
            xml_tax = riepilogo['imposta']
            
            odoo_data = odoo_by_tax.get(aliquota, {'untaxed': 0.0, 'tax': 0.0})
            odoo_untaxed = odoo_data['untaxed']
            odoo_tax = odoo_data['tax']
            
            diff_untaxed = xml_untaxed - odoo_untaxed
            diff_tax = xml_tax - odoo_tax
            
            _logger.info(f"Aliquota {aliquota}%: XML Imp {xml_untaxed:.2f} IVA {xml_tax:.2f} | "
                        f"Odoo Imp {odoo_untaxed:.2f} IVA {odoo_tax:.2f} | "
                        f"Diff Imp {diff_untaxed:.2f} IVA {diff_tax:.2f}")
            
            if abs(diff_untaxed) >= 0.01:
                # Trova la tassa Odoo corrispondente
                tax_id = None
                if aliquota > 0:
                    tax = self.env['account.tax'].search([
                        ('amount', '=', aliquota),
                        ('type_tax_use', '=', 'purchase'),
                        ('company_id', '=', self.company_id.id)
                    ], limit=1)
                    if tax:
                        tax_id = tax.id
                
                # Cerca il prodotto di arrotondamento
                rounding_product = self.env['product.product'].search([
                    ('default_code', '=', 'SDI_ROUNDING')
                ], limit=1)
                
                if not rounding_product:
                    rounding_product = self._create_rounding_product()
                
                account = rounding_product.property_account_expense_id or \
                          rounding_product.categ_id.property_account_expense_categ_id
                
                if not account:
                    raise UserError(_('Conto contabile non trovato per il prodotto di arrotondamento.'))
                
                # Crea la riga
                line_vals = {
                    'move_id': self.id,
                    'product_id': rounding_product.id,
                    'name': f'Arrotondamento SDI - IVA {aliquota}%',
                    'account_id': account.id,
                    'quantity': 1,
                    'price_unit': diff_untaxed,
                    'tax_ids': [(6, 0, [tax_id])] if tax_id else [(5, 0, 0)],
                }
                
                righe_create.append(line_vals)
                _logger.info(f"Creo riga arrotondamento IVA {aliquota}%: {diff_untaxed:.2f} € (IVA attesa: {diff_untaxed * aliquota / 100:.2f} €)")
        
        if not righe_create:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✓ Nessun Arrotondamento Necessario'),
                    'message': _('I totali Odoo corrispondono già ai totali XML.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # Crea tutte le righe
        for line_vals in righe_create:
            self.env['account.move.line'].create(line_vals)
        
        # Ricalcola i totali
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        message = _('✓ Arrotondamento Completato\n\n'
                   'Create %d righe di arrotondamento.\n\n'
                   'Totali XML:\n'
                   '• Imponibile: %.2f €\n'
                   '• IVA: %.2f €\n'
                   '• Totale: %.2f €\n\n'
                   'I totali Odoo ora corrispondono!') % (
            len(righe_create),
            self.sdi_xml_untaxed,
            self.sdi_xml_tax,
            self.sdi_xml_total
        )
        
        if self.sdi_gift_transport_diff and abs(self.sdi_gift_transport_diff) >= 0.01:
            message += _('\n\n⚠️ Attenzione:\n'
                        'Differenza omaggi/trasporti: %.2f €\n'
                        'Totale a pagare: %.2f €') % (
                self.sdi_gift_transport_diff,
                self.sdi_total_to_pay
            )
        
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
            'description': 'Prodotto utilizzato per gestire gli arrotondamenti delle fatture elettroniche importate dallo SDI',
        })
        
        return product

    def write(self, vals):
        """Override per automazione arrotondamento"""
        result = super(AccountMove, self).write(vals)
        
        if 'attachment_ids' in vals or 'invoice_line_ids' in vals:
            for move in self:
                if move.move_type in ('in_invoice', 'in_refund') and move.state == 'draft' and not move.has_rounding_line:
                    try:
                        extracted_totals = move._extract_xml_totals_from_attachment()
                        if extracted_totals and not move.sdi_xml_total:
                            move.sdi_xml_untaxed = extracted_totals['untaxed']
                            move.sdi_xml_tax = extracted_totals['tax']
                            move.sdi_xml_total = extracted_totals['total']
                            move.sdi_total_to_pay = extracted_totals.get('total_to_pay', extracted_totals['total'])
                            
                            # Verifica se serve arrotondamento
                            diff = abs(move.sdi_xml_total - move.amount_total)
                            if diff >= 0.01:
                                _logger.info(f"Fattura {move.name}: differenza {diff} €, arrotondamento automatico disponibile")
                    except Exception as e:
                        _logger.warning(f"Errore estrazione automatica: {e}")
        
        return result

    def action_remove_sdi_rounding_lines(self):
        """Rimuove tutte le righe di arrotondamento SDI"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_('La fattura deve essere in stato bozza.'))
        
        rounding_lines = self.invoice_line_ids.filtered(
            lambda l: l.name and 'Arrotondamento SDI' in l.name
        )
        
        if not rounding_lines:
            raise UserError(_('Non sono state trovate righe di arrotondamento.'))
        
        rounding_lines.unlink()
        
        # Resetta i campi XML
        self.sdi_xml_untaxed = 0.0
        self.sdi_xml_tax = 0.0
        self.sdi_xml_total = 0.0
        self.sdi_total_to_pay = 0.0
        
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Righe di Arrotondamento Rimosse'),
                'message': _('Le righe di arrotondamento sono state rimosse.'),
                'type': 'info',
                'sticky': False,
            }
        }

