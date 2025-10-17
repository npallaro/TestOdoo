# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Dummy field to fix Odoo 18 stock module bug
    # The stock module references this deprecated field in its settings view
    default_picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready'),
    ], string='Shipping Policy', default='direct',
       help='Deprecated field - kept for compatibility with stock settings view')

