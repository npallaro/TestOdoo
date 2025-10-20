# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _search_product_by_barcode(self, barcode):
        """
        Override to search product using multi-barcodes
        This method is used by barcode scanning in inventory operations
        """
        # Use the search method from product.barcode model
        product = self.env['product.barcode'].search_product_by_barcode(barcode)
        if product:
            return product

        # Fallback to standard method
        return super()._search_product_by_barcode(barcode) if hasattr(super(), '_search_product_by_barcode') else self.env['product.product']


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _search_product_by_barcode(self, barcode):
        """
        Override to search product using multi-barcodes
        This method is used by barcode scanning in picking operations
        """
        # Use the search method from product.barcode model
        product = self.env['product.barcode'].search_product_by_barcode(barcode)
        if product:
            return product

        # Fallback to standard method
        return super()._search_product_by_barcode(barcode) if hasattr(super(), '_search_product_by_barcode') else self.env['product.product']
