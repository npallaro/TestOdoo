# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VoucherCreateInvoiceWizardLine(models.TransientModel):
    _name = 'voucher.create.invoice.wizard.line'
    _description = 'Voucher Invoice Wizard Line'
    _order = 'sequence, id'
    
    wizard_id = fields.Many2one(
        'voucher.create.invoice.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    
    voucher_line_id = fields.Many2one(
        'sale.voucher.line',
        string='Voucher Line',
        required=True,
        ondelete='cascade',
    )
    
    sequence = fields.Integer(
        related='voucher_line_id.sequence',
        store=True,
    )
    
    product_id = fields.Many2one(
        related='voucher_line_id.product_id',
        string='Product',
    )
    
    product_categ_id = fields.Many2one(
        'product.category',
        string='Category',
        related='product_id.categ_id',
        store=True,
    )
    
    name = fields.Text(
        related='voucher_line_id.name',
        string='Description',
    )
    
    quantity = fields.Float(
        related='voucher_line_id.quantity',
        string='Total Qty',
        digits='Product Unit of Measure',
    )
    
    qty_invoiced = fields.Float(
        related='voucher_line_id.qty_invoiced',
        string='Already Invoiced',
        digits='Product Unit of Measure',
    )
    
    qty_to_invoice = fields.Float(
        related='voucher_line_id.qty_to_invoice',
        string='Remaining',
        digits='Product Unit of Measure',
    )
    
    product_uom_id = fields.Many2one(
        related='voucher_line_id.product_uom_id',
        string='UoM',
    )
    
    price_unit = fields.Float(
        related='voucher_line_id.price_unit',
        string='Unit Price',
        digits='Product Price',
    )
    
    to_invoice = fields.Boolean(
        string='To Invoice',
        default=True,
        help='Check to include this line in the invoice',
    )
    
    qty_invoice_now = fields.Float(
        string='Qty to Invoice Now',
        digits='Product Unit of Measure',
        help='Quantity to invoice in this operation',
    )
    
    @api.onchange('to_invoice', 'qty_to_invoice')
    def _onchange_to_invoice(self):
        """Set qty_invoice_now to remaining quantity when checked"""
        for line in self:
            if line.to_invoice and not line.qty_invoice_now:
                line.qty_invoice_now = line.qty_to_invoice
            elif not line.to_invoice:
                line.qty_invoice_now = 0.0
    
    @api.constrains('qty_invoice_now', 'qty_to_invoice')
    def _check_qty_invoice_now(self):
        for line in self:
            if line.to_invoice and line.qty_invoice_now <= 0:
                raise ValidationError(_(
                    'Quantity to invoice must be greater than 0 for line "%s".'
                ) % line.name)
            if line.qty_invoice_now > line.qty_to_invoice:
                raise ValidationError(_(
                    'Quantity to invoice (%.2f) cannot exceed remaining quantity (%.2f) for line "%s".'
                ) % (line.qty_invoice_now, line.qty_to_invoice, line.name))


class VoucherCreateInvoiceWizard(models.TransientModel):
    _name = 'voucher.create.invoice.wizard'
    _description = 'Create Invoice from Voucher'
    
    voucher_id = fields.Many2one(
        'sale.voucher',
        string='Voucher',
        required=True,
        ondelete='cascade',
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Invoice To',
        required=True,
        help='Customer who will receive the invoice (can be different from goods recipient)',
    )
    
    include_voucher_ref = fields.Boolean(
        string='Include Voucher Reference',
        default=True,
        help='Add voucher number as reference in invoice description',
    )
    
    merge_same_product = fields.Boolean(
        string='Merge Same Products',
        default=False,
        help='Merge invoice lines with the same product into a single line',
    )
    
    line_ids = fields.One2many(
        'voucher.create.invoice.wizard.line',
        'wizard_id',
        string='Lines to Invoice',
    )
    
    has_lines_to_invoice = fields.Boolean(
        compute='_compute_has_lines_to_invoice',
        string='Has Lines',
    )
    
    @api.depends('line_ids', 'line_ids.to_invoice', 'line_ids.qty_invoice_now')
    def _compute_has_lines_to_invoice(self):
        for wizard in self:
            wizard.has_lines_to_invoice = any(
                line.to_invoice and line.qty_invoice_now > 0 
                for line in wizard.line_ids
            )
    
    @api.model
    def default_get(self, fields_list):
        """Populate wizard with voucher lines"""
        res = super().default_get(fields_list)
        
        voucher_id = self.env.context.get('active_id')
        if not voucher_id:
            return res
        
        voucher = self.env['sale.voucher'].browse(voucher_id)
        
        # Set default invoice partner (last invoiced or recipient)
        res['voucher_id'] = voucher.id
        res['partner_id'] = voucher.invoiced_to_id.id or voucher.recipient_id.id
        
        # Create wizard lines for all product lines with remaining quantity
        line_vals = []
        for voucher_line in voucher.line_ids.filtered(lambda l: not l.display_type and l.qty_to_invoice > 0):
            line_vals.append((0, 0, {
                'voucher_line_id': voucher_line.id,
                'to_invoice': True,
                'qty_invoice_now': voucher_line.qty_to_invoice,
            }))
        
        res['line_ids'] = line_vals
        
        return res
    
    def action_create_invoice(self):
        """Create invoice from selected lines"""
        self.ensure_one()
        
        if not self.has_lines_to_invoice:
            raise UserError(_('Please select at least one line to invoice.'))
        
        # Get lines to invoice
        lines_to_invoice = self.line_ids.filtered(lambda l: l.to_invoice and l.qty_invoice_now > 0)
        
        if not lines_to_invoice:
            raise UserError(_('No lines selected for invoicing.'))
        
        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'voucher_id': self.voucher_id.id,
            'invoice_origin': self.voucher_id.name,
            'invoice_date': fields.Date.context_today(self),
        })
        
        # Prepare invoice lines
        invoice_lines_data = {}
        
        for wizard_line in lines_to_invoice:
            voucher_line = wizard_line.voucher_line_id
            
            # Get account from product
            account = voucher_line.product_id.property_account_income_id or \
                     voucher_line.product_id.categ_id.property_account_income_categ_id
            
            if not account:
                raise UserError(_(
                    'Please define income account for product "%s" or its category.'
                ) % voucher_line.product_id.name)
            
            # Prepare description
            description = voucher_line.name
            if self.include_voucher_ref:
                description = f"[{self.voucher_id.name}] {description}"
            
            # If merge_same_product, group by product
            if self.merge_same_product:
                key = (voucher_line.product_id.id, voucher_line.price_unit, tuple(voucher_line.tax_ids.ids))
                if key in invoice_lines_data:
                    # Merge with existing line
                    invoice_lines_data[key]['quantity'] += wizard_line.qty_invoice_now
                else:
                    # Create new line data
                    invoice_lines_data[key] = {
                        'move_id': invoice.id,
                        'product_id': voucher_line.product_id.id,
                        'name': description,
                        'quantity': wizard_line.qty_invoice_now,
                        'product_uom_id': voucher_line.product_uom_id.id,
                        'price_unit': voucher_line.price_unit,
                        'tax_ids': [(6, 0, voucher_line.tax_ids.ids)],
                        'account_id': account.id,
                    }
            else:
                # Create separate line for each voucher line
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'product_id': voucher_line.product_id.id,
                    'name': description,
                    'quantity': wizard_line.qty_invoice_now,
                    'product_uom_id': voucher_line.product_uom_id.id,
                    'price_unit': voucher_line.price_unit,
                    'tax_ids': [(6, 0, voucher_line.tax_ids.ids)],
                    'account_id': account.id,
                })
            
            # Update qty_invoiced on voucher line
            voucher_line.qty_invoiced += wizard_line.qty_invoice_now
        
        # Create merged invoice lines if merge_same_product is enabled
        if self.merge_same_product:
            for line_data in invoice_lines_data.values():
                self.env['account.move.line'].create(line_data)
        
        # Update voucher
        self.voucher_id.write({
            'invoiced_to_id': self.partner_id.id,
        })
        
        # Check if fully invoiced and archive if needed
        if self.voucher_id.is_fully_invoiced:
            self.voucher_id.write({
                'state': 'invoiced',
                'active': False,  # Archive the voucher
            })
            self.voucher_id.message_post(
                body=_('Voucher fully invoiced and archived. Invoice %s created.') % invoice.name
            )
        else:
            self.voucher_id.message_post(
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

