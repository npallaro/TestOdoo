# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    voucher_ids = fields.Many2many(
        'sale.voucher',
        'account_move_sale_voucher_rel',
        'invoice_id',
        'voucher_id',
        string='Related Vouchers',
        copy=False,
        help='Internal sales vouchers included in this invoice',
    )
    
    voucher_count = fields.Integer(
        string='Voucher Count',
        compute='_compute_voucher_count',
    )
    
    @api.depends('voucher_ids')
    def _compute_voucher_count(self):
        for move in self:
            move.voucher_count = len(move.voucher_ids)
    
    def action_view_vouchers(self):
        """Open related vouchers"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Vouchers'),
            'res_model': 'sale.voucher',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.voucher_ids.ids)],
            'context': {'create': False},
        }

