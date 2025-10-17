# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VoucherLinesCreateInvoiceWizard(models.TransientModel):
    _name = 'voucher.lines.create.invoice.wizard'
    _description = 'Create Invoice from Multiple Voucher Lines'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Invoice To',
        required=True,
        help='Customer who will receive the invoice',
    )
    
    line_ids = fields.Many2many(
        'sale.voucher.line',
        string='Selected Lines',
        help='Lines to include in the invoice',
    )
    
    @api.model
    def default_get(self, fields_list):
        """Get selected lines from context"""
        res = super().default_get(fields_list)
        
        # Get selected line IDs from context
        line_ids = self.env.context.get('active_ids', [])
        
        if line_ids:
            lines = self.env['sale.voucher.line'].browse(line_ids)
            
            # Validate lines
            for line in lines:
                if line.display_type:
                    raise UserError(_('Cannot invoice section or note lines.'))
                if line.qty_to_invoice <= 0:
                    raise UserError(_(
                        'Line "%s" has no remaining quantity to invoice.'
                    ) % line.name)
                if line.voucher_id.state != 'delivered':
                    raise UserError(_(
                        'Voucher "%s" must be in Delivered state to be invoiced.'
                    ) % line.voucher_id.name)
            
            res['line_ids'] = [(6, 0, line_ids)]
            
            # Set default partner from first line's voucher
            if lines:
                first_voucher = lines[0].voucher_id
                res['partner_id'] = first_voucher.invoiced_to_id.id or first_voucher.recipient_id.id
        
        return res
    
    def action_create_invoice(self):
        """Create invoice from selected lines"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_('Please select at least one line to invoice.'))
        
        # Group lines by voucher
        vouchers = self.line_ids.mapped('voucher_id')
        
        # Create single invoice for all lines
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': ', '.join(vouchers.mapped('name')),
            'invoice_date': fields.Date.context_today(self),
        })
        
        # Create invoice lines
        for voucher_line in self.line_ids:
            # Get account from product
            account = voucher_line.product_id.property_account_income_id or \
                     voucher_line.product_id.categ_id.property_account_income_categ_id
            
            if not account:
                raise UserError(_(
                    'Please define income account for product "%s" or its category.'
                ) % voucher_line.product_id.name)
            
            # Create invoice line with full remaining quantity
            self.env['account.move.line'].create({
                'move_id': invoice.id,
                'product_id': voucher_line.product_id.id,
                'name': f"[{voucher_line.voucher_id.name}] {voucher_line.name}",
                'quantity': voucher_line.qty_to_invoice,
                'product_uom_id': voucher_line.product_uom_id.id,
                'price_unit': voucher_line.price_unit,
                'tax_ids': [(6, 0, voucher_line.tax_ids.ids)],
                'account_id': account.id,
            })
            
            # Update qty_invoiced on voucher line
            voucher_line.qty_invoiced += voucher_line.qty_to_invoice
        
        # Update all affected vouchers
        for voucher in vouchers:
            # Link invoice to voucher
            invoice.write({'voucher_id': voucher.id})
            
            # Update invoiced_to partner
            voucher.write({'invoiced_to_id': self.partner_id.id})
            
            # Check if fully invoiced and archive if needed
            if voucher.is_fully_invoiced:
                voucher.write({
                    'state': 'invoiced',
                    'active': False,
                })
                voucher.message_post(
                    body=_('Voucher fully invoiced and archived. Invoice %s created.') % invoice.name
                )
            else:
                voucher.message_post(
                    body=_('Partial invoice %s created for customer %s.') % (invoice.name, self.partner_id.name)
                )
        
        # Return action to open the invoice
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

