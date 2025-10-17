# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleVoucher(models.Model):
    _name = 'sale.voucher'
    _description = 'Internal Sales Voucher'
    # _inherit = ['mail.thread', 'mail.activity.mixin']  # Temporarily disabled for debugging
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Voucher Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string='Recipient (Goods Receiver)',
        required=True,
        tracking=True,
        help='Customer who physically receives the goods',
    )
    
    line_ids = fields.One2many(
        'sale.voucher.line',
        'voucher_id',
        string='Products',
        copy=True,
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        readonly=True,
        copy=False,
    )
    
    picking_state = fields.Selection(
        related='picking_id.state',
        string='Delivery Status',
        store=True,
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True,
        copy=False,
    )
    
    invoiced_to_id = fields.Many2one(
        'res.partner',
        string='Invoiced To',
        readonly=True,
        copy=False,
        tracking=True,
        help='Final customer who receives the invoice',
    )
    
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    amount_tax = fields.Monetary(
        string='Taxes',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    
    notes = fields.Text(
        string='Internal Notes',
    )
    
    internal_reference = fields.Char(
        string='Internal Reference',
        help='Internal tracking code',
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=lambda self: self.env.user,
        tracking=True,
    )
    
    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax')
    def _compute_amounts(self):
        for voucher in self:
            amount_untaxed = sum(voucher.line_ids.mapped('price_subtotal'))
            amount_tax = sum(voucher.line_ids.mapped('price_tax'))
            voucher.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.voucher'
                ) or _('New')
        return super().create(vals_list)
    
    def unlink(self):
        for voucher in self:
            if voucher.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    'You cannot delete a voucher which is not in draft or cancelled state. '
                    'You should cancel it first.'
                ))
        return super().unlink()
    
    def action_confirm(self):
        """Confirm voucher and create stock picking"""
        for voucher in self:
            if voucher.state != 'draft':
                raise UserError(_('Only draft vouchers can be confirmed.'))
            
            if not voucher.line_ids:
                raise UserError(_('You cannot confirm a voucher without products.'))
            
            # Create stock picking
            picking = voucher._create_picking()
            voucher.write({
                'state': 'confirmed',
                'picking_id': picking.id,
            })
            
            # Post message in chatter
            voucher.message_post(
                body=_('Voucher confirmed. Delivery order %s created.') % picking.name
            )
        
        return True
    
    def _create_picking(self):
        """Create stock picking for voucher delivery"""
        self.ensure_one()
        
        # Get picking type
        picking_type = self.env.ref(
            'sale_voucher.picking_type_voucher_out',
            raise_if_not_found=False
        )
        
        if not picking_type:
            raise UserError(_(
                'Voucher picking type not found. '
                'Please reinstall the module or contact support.'
            ))
        
        location_src = picking_type.default_location_src_id
        location_dest = self.env.ref(
            'sale_voucher.stock_location_voucher_customers',
            raise_if_not_found=False
        )
        
        if not location_dest:
            raise UserError(_(
                'Voucher customer location not found. '
                'Please reinstall the module or contact support.'
            ))
        
        picking_vals = {
            'partner_id': self.recipient_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'origin': self.name,
            'voucher_id': self.id,
            'company_id': self.company_id.id,
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock moves
        for line in self.line_ids:
            # Skip section and note lines
            if line.display_type:
                continue
            if line.quantity <= 0:
                continue
                
            self.env['stock.move'].create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_src.id,
                'location_dest_id': location_dest.id,
                'company_id': self.company_id.id,
            })
        
        # Confirm picking to reserve stock
        picking.action_confirm()
        
        return picking
    
    def action_set_delivered(self):
        """Mark voucher as delivered when picking is done"""
        for voucher in self:
            if voucher.state != 'confirmed':
                raise UserError(_('Only confirmed vouchers can be marked as delivered.'))
            
            if voucher.picking_id and voucher.picking_id.state != 'done':
                raise UserError(_(
                    'The delivery order must be validated before marking the voucher as delivered.'
                ))
            
            voucher.write({'state': 'delivered'})
            
            voucher.message_post(
                body=_('Voucher marked as delivered and ready for invoicing.')
            )
        
        return True
    
    def action_cancel(self):
        """Cancel voucher"""
        for voucher in self:
            if voucher.state == 'invoiced':
                raise UserError(_('You cannot cancel an invoiced voucher.'))
            
            if voucher.picking_id and voucher.picking_id.state == 'done':
                raise UserError(_(
                    'You cannot cancel a voucher with a validated delivery. '
                    'Please cancel the delivery first.'
                ))
            
            # Cancel related picking if exists and not done
            if voucher.picking_id and voucher.picking_id.state != 'done':
                voucher.picking_id.action_cancel()
            
            voucher.write({'state': 'cancelled'})
            
            voucher.message_post(body=_('Voucher cancelled.'))
        
        return True
    
    def action_draft(self):
        """Reset voucher to draft"""
        for voucher in self:
            if voucher.state == 'invoiced':
                raise UserError(_('You cannot reset an invoiced voucher to draft.'))
            
            if voucher.picking_id:
                raise UserError(_(
                    'You cannot reset a voucher with a delivery order. '
                    'Please delete the delivery first.'
                ))
            
            voucher.write({'state': 'draft'})
            
            voucher.message_post(body=_('Voucher reset to draft.'))
        
        return True
    
    def action_view_picking(self):
        """Open related picking"""
        self.ensure_one()
        
        if not self.picking_id:
            raise UserError(_('No delivery order found for this voucher.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Order'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_invoice(self):
        """Open related invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No invoice found for this voucher.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_invoice(self):
        """Open wizard to create invoice"""
        self.ensure_one()
        
        if self.state != 'delivered':
            raise UserError(_('Only delivered vouchers can be invoiced.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Invoice'),
            'res_model': 'voucher.create.invoice',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_voucher_ids': [(6, 0, self.ids)],
            },
        }

