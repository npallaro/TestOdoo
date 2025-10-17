# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleVoucherLine(models.Model):
    _name = 'sale.voucher.line'
    _description = 'Sales Voucher Line'
    _order = 'voucher_id, sequence, id'
    
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    
    voucher_id = fields.Many2one(
        'sale.voucher',
        string='Voucher',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    voucher_state = fields.Selection(
        related='voucher_id.state',
        string='Voucher Status',
        store=True,
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain=[('sale_ok', '=', True)],
    )
    
    name = fields.Text(
        string='Description',
    )
    
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
        digits='Product Unit of Measure',
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
    )
    
    price_unit = fields.Float(
        string='Unit Price',
        required=True,
        digits='Product Price',
    )
    
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain=[('type_tax_use', '=', 'sale')],
    )
    
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    
    price_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    
    currency_id = fields.Many2one(
        related='voucher_id.currency_id',
        store=True,
        string='Currency',
    )
    
    company_id = fields.Many2one(
        related='voucher_id.company_id',
        store=True,
        string='Company',
    )
    
    # Invoicing tracking fields
    qty_invoiced = fields.Float(
        string='Invoiced Quantity',
        default=0.0,
        digits='Product Unit of Measure',
        help='Quantity already invoiced',
    )
    
    qty_to_invoice = fields.Float(
        string='To Invoice',
        compute='_compute_qty_to_invoice',
        store=True,
        digits='Product Unit of Measure',
        help='Quantity remaining to be invoiced',
    )
    
    is_fully_invoiced = fields.Boolean(
        string='Fully Invoiced',
        compute='_compute_qty_to_invoice',
        store=True,
        help='True when all quantity has been invoiced',
    )
    
    @api.depends('quantity', 'qty_invoiced', 'display_type')
    def _compute_qty_to_invoice(self):
        for line in self:
            if line.display_type:
                line.qty_to_invoice = 0.0
                line.is_fully_invoiced = False
            else:
                line.qty_to_invoice = line.quantity - line.qty_invoiced
                line.is_fully_invoiced = line.qty_invoiced >= line.quantity
    
    @api.depends('quantity', 'price_unit', 'tax_ids', 'display_type')
    def _compute_amount(self):
        for line in self:
            if line.display_type:
                line.update({
                    'price_subtotal': 0.0,
                    'price_tax': 0.0,
                    'price_total': 0.0,
                })
                continue
                
            price = line.price_unit * line.quantity
            
            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    price,
                    currency=line.currency_id,
                    quantity=1.0,
                    product=line.product_id,
                    partner=line.voucher_id.recipient_id,
                )
                line.update({
                    'price_subtotal': taxes['total_excluded'],
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                })
            else:
                line.update({
                    'price_subtotal': price,
                    'price_tax': 0.0,
                    'price_total': price,
                })
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default UoM if not provided"""
        for vals in vals_list:
            # Skip for display_type lines
            if vals.get('display_type'):
                continue
            
            # If product_id is set but product_uom_id is not
            if vals.get('product_id') and not vals.get('product_uom_id'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['product_uom_id'] = product.uom_id.id
        
        return super().create(vals_list)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        
        # Set product name
        self.name = self.product_id.get_product_multiline_description_sale()
        
        # Set UoM
        self.product_uom_id = self.product_id.uom_id
        
        # Set price
        if self.voucher_id.recipient_id:
            pricelist = self.voucher_id.recipient_id.property_product_pricelist
            if pricelist:
                self.price_unit = pricelist._get_product_price(
                    self.product_id,
                    self.quantity or 1.0,
                    partner=self.voucher_id.recipient_id,
                    date=self.voucher_id.date,
                    uom_id=self.product_uom_id.id,
                )
            else:
                self.price_unit = self.product_id.lst_price
        else:
            self.price_unit = self.product_id.lst_price
        
        # Set taxes
        if self.voucher_id.recipient_id:
            fpos = self.voucher_id.recipient_id.property_account_position_id
            taxes = self.product_id.taxes_id.filtered(
                lambda t: t.company_id == self.company_id
            )
            self.tax_ids = fpos.map_tax(taxes) if fpos else taxes
        else:
            self.tax_ids = self.product_id.taxes_id.filtered(
                lambda t: t.company_id == self.company_id
            )
    
    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if not self.product_id or not self.product_uom_id:
            return
        
        if self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            self.product_uom_id = self.product_id.uom_id
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _(
                        'The unit of measure must be in the same category as the product unit of measure.'
                    ),
                }
            }
    
    @api.constrains('quantity', 'display_type')
    def _check_quantity(self):
        for line in self:
            if line.display_type:
                continue
            if line.quantity <= 0:
                raise ValidationError(_(
                    'The quantity must be positive.'
                ))

