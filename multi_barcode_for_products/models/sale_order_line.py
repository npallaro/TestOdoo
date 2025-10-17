# -*- coding: utf-8 -*-
###############################################################################
#
#    Custom Development
#
#    Copyright (C) 2024-TODAY Custom Development
#    Author: Custom Development
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC
#    LICENSE (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    """Inherits Sale order line for scanning multi barcode"""
    _inherit = 'sale.order.line'

    scan_barcode = fields.Char(string='Product Barcode',
                               help="Here you can provide the barcode for "
                                    "the product")

    def _prepare_invoice_line(self, **optional_values):
        """For adding the scanned barcode in the invoice"""
        res = super()._prepare_invoice_line(**optional_values)
        if self.move_ids:
            res['scan_barcode'] = self.move_ids[0].scan_barcode if self.move_ids else False
        return res

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        """For getting the scanned barcode product"""
        if self.scan_barcode:
            product = self.env['product.multiple.barcodes'].search(
                [('product_multi_barcode', '=', self.scan_barcode)], limit=1)
            if product and product.product_id:
                self.product_id = product.product_id.id
