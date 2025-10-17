# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    voucher_id = fields.Many2one(
        'sale.voucher',
        string='Related Voucher',
        copy=False,
        index=True,
        help='Internal sales voucher that generated this delivery',
    )
    
    # Compatibility field for standard Odoo views that expect sale_id
    # This prevents errors when opening picking forms from vouchers
    sale_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False,
        help='Compatibility field - not used by voucher module',
    )
    
    def button_validate(self):
        """Override to update voucher state when picking is validated"""
        res = super().button_validate()
        
        # Update related vouchers to delivered state
        for picking in self:
            if picking.voucher_id and picking.voucher_id.state == 'confirmed':
                picking.voucher_id.action_set_delivered()
        
        return res

