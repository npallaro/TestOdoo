# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_ids = fields.One2many(
        'product.barcode',
        'product_tmpl_id',
        string='Template Barcodes',
        help='Barcodes for this product template (applies to all variants)'
    )
    template_barcode_count = fields.Integer(
        string='Template Barcode Count',
        compute='_compute_template_barcode_count',
        store=True,
        help='Total number of template barcodes'
    )
    total_barcode_count = fields.Integer(
        string='Total Barcodes',
        compute='_compute_total_barcode_count',
        help='Total barcodes including template and variant barcodes'
    )

    @api.depends('barcode_ids')
    def _compute_template_barcode_count(self):
        """Compute number of template barcodes"""
        for template in self:
            template.template_barcode_count = len(template.barcode_ids)

    @api.depends('barcode_ids', 'product_variant_ids.barcode_ids')
    def _compute_total_barcode_count(self):
        """Compute total number of all barcodes"""
        for template in self:
            variant_barcodes = sum(template.product_variant_ids.mapped('barcode_count'))
            template.total_barcode_count = template.template_barcode_count + variant_barcodes

    def action_view_all_barcodes(self):
        """Open view with all barcodes (template + variants)"""
        self.ensure_one()

        domain = [
            '|',
            ('product_tmpl_id', '=', self.id),
            ('product_id', 'in', self.product_variant_ids.ids)
        ]

        return {
            'name': _('All Barcodes for %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.barcode',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id if len(self.product_variant_ids) == 1 else False,
            },
        }

    def action_view_template_barcodes(self):
        """Open barcodes view for this template only"""
        self.ensure_one()
        return {
            'name': _('Template Barcodes for %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.barcode',
            'view_mode': 'tree,form',
            'domain': [('product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_tmpl_id': self.id,
                'default_product_id': False,
            },
        }
