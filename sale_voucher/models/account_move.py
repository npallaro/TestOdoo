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
    
    def unlink(self):
        """Restore qty_invoiced on voucher lines when invoice is deleted"""
        for move in self:
            if move.voucher_id and move.move_type == 'out_invoice':
                # Find voucher lines that were invoiced in this invoice
                # by matching product and voucher
                for invoice_line in move.invoice_line_ids.filtered(lambda l: l.product_id):
                    # Find corresponding voucher line
                    voucher_lines = move.voucher_id.line_ids.filtered(
                        lambda vl: vl.product_id == invoice_line.product_id and not vl.display_type
                    )
                    
                    # Decrease qty_invoiced by the quantity in this invoice line
                    for voucher_line in voucher_lines:
                        new_qty_invoiced = max(0, voucher_line.qty_invoiced - invoice_line.quantity)
                        voucher_line.write({'qty_invoiced': new_qty_invoiced})
                
                # Reactivate voucher if it was archived (regardless of state)
                if not move.voucher_id.active:
                    move.voucher_id.write({
                        'active': True,
                        'state': 'delivered',
                    })
                    move.voucher_id.message_post(
                        body=_('Invoice %s deleted. Voucher reactivated and set back to Delivered state.') % move.name
                    )
                # If voucher was in 'invoiced' state but still active, set back to 'delivered'
                elif move.voucher_id.state == 'invoiced':
                    move.voucher_id.write({'state': 'delivered'})
                    move.voucher_id.message_post(
                        body=_('Invoice %s deleted. Voucher set back to Delivered state.') % move.name
                    )
        
        return super().unlink()
    
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

