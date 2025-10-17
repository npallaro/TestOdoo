# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    voucher_id = fields.Many2one(
        'sale.voucher',
        string='Related Voucher',
        copy=False,
        help='Internal sales voucher that generated this invoice',
    )
    
    def action_view_voucher(self):
        """Open related voucher"""
        self.ensure_one()
        
        if not self.voucher_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Voucher'),
            'res_model': 'sale.voucher',
            'res_id': self.voucher_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

