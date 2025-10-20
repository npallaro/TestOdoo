# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode_ids = fields.One2many(
        'product.barcode',
        'product_id',
        string='Additional Barcodes',
        help='Additional barcodes for this product variant'
    )
    barcode_count = fields.Integer(
        string='Barcode Count',
        compute='_compute_barcode_count',
        store=True,
        help='Total number of additional barcodes'
    )

    @api.depends('barcode_ids')
    def _compute_barcode_count(self):
        """Compute total number of barcodes"""
        for product in self:
            product.barcode_count = len(product.barcode_ids)

    @api.constrains('barcode')
    def _check_barcode_unique(self):
        """Check that standard barcode is not used in multi-barcodes"""
        for product in self:
            if product.barcode:
                # Check in product.barcode table
                existing = self.env['product.barcode'].search([
                    ('name', '=', product.barcode),
                    '|',
                    ('product_id', '!=', product.id),
                    ('product_id', '=', False)
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        'The barcode "%s" is already used in additional barcodes. '
                        'Please use a different barcode.'
                    ) % product.barcode)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Override name search to include barcode search"""
        args = args or []

        # If searching by barcode-like value (no spaces, could be a barcode)
        if name and operator in ('=', 'ilike') and not ' ' in name:
            # Search in additional barcodes
            barcode_recs = self.env['product.barcode'].search([
                ('name', '=', name),
                ('active', '=', True),
                ('product_id', '!=', False)
            ], limit=limit)

            if barcode_recs:
                product_ids = barcode_recs.mapped('product_id').ids
                args = [('id', 'in', product_ids)] + args
                return self._search(args, limit=limit, order=order)

        return super()._name_search(name=name, args=args, operator=operator, limit=limit, order=order)

    def action_view_barcodes(self):
        """Open barcodes view for this product"""
        self.ensure_one()
        return {
            'name': _('Barcodes for %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.barcode',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'default_product_tmpl_id': False,
            },
        }

    def get_all_barcodes(self):
        """
        Get all barcodes for this product (standard + additional)
        Returns a list of barcode strings
        """
        self.ensure_one()
        barcodes = []

        # Add standard barcode if exists
        if self.barcode:
            barcodes.append(self.barcode)

        # Add additional barcodes
        barcodes.extend(self.barcode_ids.filtered('active').mapped('name'))

        return barcodes
