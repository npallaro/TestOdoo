# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class VoucherCreateInvoice(models.TransientModel):
    _name = 'voucher.create.invoice'
    _description = 'Create Invoice from Vouchers'
    
    voucher_ids = fields.Many2many(
        'sale.voucher',
        string='Vouchers',
        required=True,
        domain=[('state', '=', 'delivered')],
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer to Invoice',
        required=True,
        help='Customer who will receive the invoice (can be different from voucher recipient)',
    )
    
    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.context_today,
        required=True,
    )
    
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
    )
    
    group_products = fields.Boolean(
        string='Group Identical Products',
        default=True,
        help='If checked, identical products from different vouchers will be grouped into a single invoice line',
    )
    
    add_voucher_reference = fields.Boolean(
        string='Add Voucher References',
        default=True,
        help='Add voucher numbers as references in invoice line descriptions',
    )
    
    invoice_notes = fields.Text(
        string='Invoice Notes',
        help='Additional notes to add to the invoice',
    )
    
    @api.onchange('voucher_ids')
    def _onchange_voucher_ids(self):
        """Set default customer from first voucher"""
        if self.voucher_ids and not self.partner_id:
            # Try to get the most common recipient
            recipients = self.voucher_ids.mapped('recipient_id')
            if len(recipients) == 1:
                self.partner_id = recipients[0]
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Set payment terms from customer"""
        if self.partner_id:
            self.payment_term_id = self.partner_id.property_payment_term_id
    
    def action_create_invoice(self):
        """Create invoice from selected vouchers"""
        self.ensure_one()
        
        if not self.voucher_ids:
            raise UserError(_('Please select at least one voucher.'))
        
        # Check all vouchers are in delivered state
        not_delivered = self.voucher_ids.filtered(lambda v: v.state != 'delivered')
        if not_delivered:
            raise UserError(_(
                'The following vouchers are not in delivered state and cannot be invoiced:\n%s'
            ) % ', '.join(not_delivered.mapped('name')))
        
        # Check all vouchers have the same currency
        currencies = self.voucher_ids.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(_(
                'All vouchers must have the same currency. '
                'Please select vouchers with the same currency.'
            ))
        
        # Create invoice
        invoice = self._create_invoice()
        
        # Update vouchers
        self.voucher_ids.write({
            'state': 'invoiced',
            'invoice_id': invoice.id,
            'invoiced_to_id': self.partner_id.id,
        })
        
        # Add vouchers to invoice
        invoice.write({
            'voucher_ids': [(6, 0, self.voucher_ids.ids)],
        })
        
        # Post message in vouchers
        for voucher in self.voucher_ids:
            voucher.message_post(
                body=_('Invoiced to %s via invoice %s') % (
                    self.partner_id.name,
                    invoice.name
                )
            )
        
        # Return action to open invoice
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_invoice(self):
        """Create the invoice from vouchers"""
        self.ensure_one()
        
        # Prepare invoice values
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'invoice_payment_term_id': self.payment_term_id.id if self.payment_term_id else False,
            'currency_id': self.voucher_ids[0].currency_id.id,
            'company_id': self.voucher_ids[0].company_id.id,
            'invoice_origin': ', '.join(self.voucher_ids.mapped('name')),
            'narration': self.invoice_notes or False,
        }
        
        # Create invoice
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Create invoice lines
        if self.group_products:
            self._create_grouped_invoice_lines(invoice)
        else:
            self._create_separate_invoice_lines(invoice)
        
        # Add voucher reference as note line if requested
        if self.add_voucher_reference and len(self.voucher_ids) > 1:
            voucher_list = ', '.join(self.voucher_ids.mapped('name'))
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'display_type': 'line_note',
                'name': _('Related Vouchers: %s') % voucher_list,
                'sequence': 9999,
            })
        
        return invoice
    
    def _create_grouped_invoice_lines(self, invoice):
        """Create invoice lines grouping identical products"""
        self.ensure_one()
        
        # Group lines by product, price and taxes
        grouped_lines = defaultdict(lambda: {
            'quantity': 0.0,
            'vouchers': [],
        })
        
        for voucher in self.voucher_ids:
            for line in voucher.line_ids:
                # Skip section and note lines
                if hasattr(line, 'display_type') and line.display_type:
                    continue
                
                # Create grouping key
                tax_ids = tuple(sorted(line.tax_ids.ids))
                key = (line.product_id.id, line.price_unit, tax_ids)
                
                # Add to group
                grouped_lines[key]['quantity'] += line.quantity
                grouped_lines[key]['vouchers'].append(voucher.name)
                grouped_lines[key]['line'] = line
        
        # Create invoice lines
        sequence = 10
        for key, data in grouped_lines.items():
            line = data['line']
            
            # Prepare description
            description = line.name
            if self.add_voucher_reference:
                voucher_ref = ', '.join(set(data['vouchers']))
                description += _('\nVouchers: %s') % voucher_ref
            
            # Get account
            account = line.product_id.property_account_income_id or \
                     line.product_id.categ_id.property_account_income_categ_id
            
            if not account:
                raise UserError(_(
                    'Please define income account for product "%s" or its category.'
                ) % line.product_id.display_name)
            
            # Create line
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': line.product_id.id,
                'name': description,
                'quantity': data['quantity'],
                'product_uom_id': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'account_id': account.id,
                'sequence': sequence,
            })
            
            sequence += 10
    
    def _create_separate_invoice_lines(self, invoice):
        """Create separate invoice lines for each voucher line"""
        self.ensure_one()
        
        sequence = 10
        
        for voucher in self.voucher_ids:
            # Add voucher reference as section if multiple vouchers
            if len(self.voucher_ids) > 1:
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'display_type': 'line_section',
                    'name': _('Voucher: %s') % voucher.name,
                    'sequence': sequence,
                })
                sequence += 10
            
            # Create lines for each product
            for line in voucher.line_ids:
                # Skip section and note lines
                if hasattr(line, 'display_type') and line.display_type:
                    # Copy section/note lines
                    self.env['account.move.line'].create({
                        'move_id': invoice.id,
                        'display_type': line.display_type,
                        'name': line.name,
                        'sequence': sequence,
                    })
                    sequence += 10
                    continue
                
                # Prepare description
                description = line.name
                if self.add_voucher_reference:
                    description += _('\nVoucher: %s') % voucher.name
                
                # Get account
                account = line.product_id.property_account_income_id or \
                         line.product_id.categ_id.property_account_income_categ_id
                
                if not account:
                    raise UserError(_(
                        'Please define income account for product "%s" or its category.'
                    ) % line.product_id.display_name)
                
                # Create line
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'product_id': line.product_id.id,
                    'name': description,
                    'quantity': line.quantity,
                    'product_uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'account_id': account.id,
                    'sequence': sequence,
                })
                
                sequence += 10

