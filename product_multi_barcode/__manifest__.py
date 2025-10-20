# -*- coding: utf-8 -*-
{
    'name': 'Product Multi Barcode',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Manage multiple barcodes for products in Sales, Purchase, POS and Inventory',
    'description': """
Product Multi Barcode
=====================
This module allows you to assign multiple barcodes to a single product.

Features:
---------
* Add unlimited barcodes to products
* Unique barcode validation across all products
* Search products by any barcode in Sales Orders
* Search products by any barcode in Purchase Orders
* Search products by any barcode in Point of Sale
* Search products by any barcode in Inventory Operations
* User-friendly interface to manage barcodes
* Compatible with Odoo 18 Enterprise

Usage:
------
1. Go to Inventory > Products > Products
2. Open a product
3. Go to the 'Barcodes' tab
4. Add multiple barcodes
5. Use any barcode to search/scan the product in sales, purchase, POS, or inventory

Technical:
----------
* Creates a new model 'product.barcode' to store multiple barcodes
* Extends product.product with One2many relation
* Overrides barcode search methods in relevant models
* Maintains backward compatibility with standard barcode field
    """,
    'author': 'Custom Development',
    'website': 'https://github.com',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'stock',
        'sale_management',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_barcode_views.xml',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
    ],
    'demo': [
        'demo/product_barcode_demo.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
