# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def _onchange_product_id_set_barcode_domain(self):
        """Override to allow searching by multi-barcodes"""
        # This method can be extended if needed
        pass

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Override name search to search products by multi-barcodes in product_id field"""
        # The product_id field will use the product.product _name_search
        # which already includes our multi-barcode search
        return super()._name_search(name=name, args=args, operator=operator, limit=limit, order=order)
