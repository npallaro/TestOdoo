# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductBarcode(models.Model):
    _name = 'product.barcode'
    _description = 'Product Barcode'
    _order = 'sequence, id'

    name = fields.Char(
        string='Barcode',
        required=True,
        index=True,
        help='Barcode value. Must be unique across all products.'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for ordering barcodes'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product Variant',
        ondelete='cascade',
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        ondelete='cascade',
        index=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, this barcode will not be used for searching products.'
    )
    notes = fields.Char(
        string='Notes',
        help='Additional notes about this barcode (e.g., supplier barcode, internal code, etc.)'
    )

    _sql_constraints = [
        ('barcode_unique', 'unique(name)', 'This barcode already exists! Barcodes must be unique.'),
    ]

    @api.constrains('name')
    def _check_barcode_value(self):
        """Validate barcode value"""
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_('Barcode value cannot be empty.'))

            # Check if barcode already exists in product.product standard barcode field
            if self.env['product.product'].search([('barcode', '=', record.name.strip())], limit=1):
                raise ValidationError(_(
                    'This barcode "%s" is already used in the standard barcode field of another product.'
                ) % record.name)

    @api.constrains('product_id', 'product_tmpl_id')
    def _check_product_relation(self):
        """Ensure barcode is linked to either product or template, not both"""
        for record in self:
            if record.product_id and record.product_tmpl_id:
                raise ValidationError(_(
                    'A barcode cannot be linked to both a product variant and a product template. '
                    'Please choose only one.'
                ))
            if not record.product_id and not record.product_tmpl_id:
                raise ValidationError(_(
                    'A barcode must be linked to either a product variant or a product template.'
                ))

    @api.model
    def search_product_by_barcode(self, barcode):
        """
        Search for a product by barcode (including multi-barcodes)
        Returns product.product recordset
        """
        if not barcode:
            return self.env['product.product']

        # First try standard barcode field
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if product:
            return product

        # Then search in multi-barcodes for product variants
        barcode_record = self.search([
            ('name', '=', barcode),
            ('active', '=', True),
            ('product_id', '!=', False)
        ], limit=1)

        if barcode_record and barcode_record.product_id:
            return barcode_record.product_id

        # Finally search in multi-barcodes for product templates
        barcode_record = self.search([
            ('name', '=', barcode),
            ('active', '=', True),
            ('product_tmpl_id', '!=', False)
        ], limit=1)

        if barcode_record and barcode_record.product_tmpl_id:
            # Return the first variant of the template
            return barcode_record.product_tmpl_id.product_variant_ids[:1]

        return self.env['product.product']

    def name_get(self):
        """Custom display name"""
        result = []
        for record in self:
            name = record.name
            if record.notes:
                name = f"{name} ({record.notes})"
            result.append((record.id, name))
        return result
