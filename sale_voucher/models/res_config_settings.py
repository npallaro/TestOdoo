# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Fix for Odoo 18 stock module bug
    # The stock module's settings view references this field but it was removed from the model
    # We add it back as a functional field with proper implementation
    
    default_picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready'),
    ], string='Shipping Policy',
       default='direct',
       config_parameter='sale.default_picking_policy',
       help='Default shipping policy for sales orders:\n'
            '- As soon as possible: Deliver each product when available\n'
            '- When all products are ready: Deliver all products at once')
    
    @api.model
    def get_values(self):
        """Get default_picking_policy from config parameters"""
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res['default_picking_policy'] = params.get_param(
            'sale.default_picking_policy', 
            default='direct'
        )
        return res
    
    def set_values(self):
        """Save default_picking_policy to config parameters"""
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param(
            'sale.default_picking_policy',
            self.default_picking_policy or 'direct'
        )

