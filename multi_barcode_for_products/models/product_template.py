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


class ProductTemplate(models.Model):
    """Inherits Product template for multi barcode feature"""
    _inherit = 'product.template'

    template_multi_barcode_ids = fields.One2many(
        'product.multiple.barcodes',
        'product_template_id',
        string='Multi Barcodes',
        help="Multi barcode for product template")

    def write(self, vals):
        """Updating the multi barcodes"""
        res = super(ProductTemplate, self).write(vals)
        if self.template_multi_barcode_ids and self.product_variant_ids:
            self.template_multi_barcode_ids.write({
                'product_id': self.product_variant_ids[0].id
            })
        return res

    @api.model
    def create(self, vals):
        """Creating the multi barcodes"""
        res = super(ProductTemplate, self).create(vals)
        if res.template_multi_barcode_ids and res.product_variant_ids:
            res.template_multi_barcode_ids.write({
                'product_id': res.product_variant_ids[0].id
            })
        return res
