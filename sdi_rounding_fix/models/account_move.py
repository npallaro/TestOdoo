# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from decimal import Decimal


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Campo per memorizzare il totale originale del file XML SDI
    sdi_xml_total = fields.Monetary(
        string='Totale XML SDI',
        currency_field='currency_id',
        help='Totale della fattura come indicato nel file XML dello SDI. '
             'Questo campo può essere compilato manualmente o automaticamente '
             'durante l\'importazione della fattura elettronica.'
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

    def action_add_sdi_rounding_line(self):
        """
        Aggiunge una riga di arrotondamento per bilanciare la differenza
        tra il totale XML SDI e il totale calcolato da Odoo
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
        
        # Verifica che sia stato impostato il totale XML
        if not self.sdi_xml_total:
            raise UserError(_(
                'È necessario inserire il totale del file XML SDI nel campo '
                '"Totale XML SDI" prima di procedere.'
            ))
        
        # Verifica se esiste già una riga di arrotondamento
        if self.has_rounding_line:
            raise UserError(_(
                'Esiste già una riga di arrotondamento in questa fattura. '
                'Rimuoverla prima di crearne una nuova.'
            ))
        
        # Calcola la differenza
        difference = self.sdi_rounding_difference
        
        # Se la differenza è zero o trascurabile, non fare nulla
        if abs(difference) < 0.01:
            raise UserError(_(
                'La differenza è troppo piccola (< 0.01 €) e non richiede '
                'una riga di arrotondamento.'
            ))
        
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
                'title': _('Riga di Arrotondamento Aggiunta'),
                'message': _(
                    'È stata aggiunta una riga di arrotondamento di %.2f € '
                    'per bilanciare la fattura.'
                ) % difference,
                'type': 'success',
                'sticky': False,
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
        
        # Ricalcola i totali
        self._recompute_dynamic_lines(recompute_all_taxes=True)
        
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

