# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import UserError


class WebsiteSaleAgent(WebsiteSale):

    def _get_mandatory_fields_billing(self):
        """Override per evitare che l'agente debba compilare i dati di fatturazione."""
        if request.session.get('agent_selected_customer_id') and request.env.user.has_group('base.group_portal'):
            return []
        return super()._get_mandatory_fields_billing()

    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, **post):
        """
        Override dello shop per applicare il listino del cliente selezionato.
        """
        # Se c'è un cliente selezionato, forza il suo listino
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if customer.exists() and customer.property_product_pricelist:
                # Forza il listino del cliente nella sessione
                request.session['website_sale_current_pl'] = customer.property_product_pricelist.id

                # Aggiorna anche l'ordine corrente se esiste
                order = request.website.sale_get_order()
                if order:
                    order.sudo().write({
                        'partner_id': customer.id,
                        'partner_invoice_id': customer.id,
                        'partner_shipping_id': customer.id,
                        'pricelist_id': customer.property_product_pricelist.id,
                    })

        return super().shop(page=page, category=category, search=search, min_price=min_price, max_price=max_price, **post)

    def _get_shop_payment_values(self, order, **kwargs):
        """
        Override per assicurarsi che gli ordini creati da agenti usino
        il partner del cliente selezionato, non l'agente stesso.
        """
        values = super()._get_shop_payment_values(order, **kwargs)

        # Se c'è un cliente selezionato da un agente, aggiorna i valori
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].browse(customer_id)

            if customer.exists():
                values['partner'] = customer

        return values

    def cart(self, **post):
        """
        Override del carrello per gestire il partner del cliente selezionato.
        """
        # Se c'è un cliente selezionato, assicurati che l'ordine usi quel partner e listino
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if customer.exists():
                order = request.website.sale_get_order()
                if order:
                    # Aggiorna il partner E il listino dell'ordine
                    pricelist = customer.property_product_pricelist or request.website.get_current_pricelist()

                    order.sudo().write({
                        'partner_id': customer.id,
                        'partner_invoice_id': customer.id,
                        'partner_shipping_id': customer.id,
                        'pricelist_id': pricelist.id,
                    })

                    # Ricalcola i prezzi delle righe ordine con il nuovo listino
                    for line in order.order_line:
                        line.sudo()._compute_price_unit()

        # Se l'agente clicca su "Procedi" nel carrello, reindirizza alla finalizzazione
        if post.get('type') == 'click_checkout' and request.session.get('agent_selected_customer_id'):
            return request.redirect('/shop/agent/cart/finalize')

        return super().cart(**post)

    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def checkout(self, **post):
        """
        Override del checkout: se è un agente, reindirizza alla finalizzazione.
        """
        # Se c'è un cliente selezionato da un agente, reindirizza alla finalizzazione agente
        if request.session.get('agent_selected_customer_id') and request.env.user.has_group('base.group_portal'):
            return request.redirect('/shop/agent/cart/finalize')

        # Se c'è un cliente selezionato, assicurati che l'ordine usi quel partner
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if customer.exists():
                order = request.website.sale_get_order()
                if order and order.partner_id != customer:
                    # Aggiorna il partner dell'ordine
                    order.sudo().write({
                        'partner_id': customer.id,
                        'partner_invoice_id': customer.id,
                        'partner_shipping_id': customer.id,
                    })
                    # Ricalcola i prezzi con il listino del cliente
                    order.sudo()._onchange_partner_id()

        return super().checkout(**post)

    def address(self, **kw):
        """
        Override per gestire gli indirizzi del cliente selezionato.
        """
        # Se c'è un cliente selezionato, usa i suoi indirizzi
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if customer.exists():
                order = request.website.sale_get_order()
                if order:
                    order.sudo().write({
                        'partner_id': customer.id,
                        'partner_invoice_id': customer.id,
                        'partner_shipping_id': customer.id,
                    })

        return super().address(**kw)

    def payment_transaction(self, *args, **kwargs):
        """
        Override per assicurarsi che la transazione sia associata al cliente corretto.
        """
        result = super().payment_transaction(*args, **kwargs)

        # Dopo la conferma, pulisci il cliente selezionato dalla sessione
        if 'agent_selected_customer_id' in request.session:
            del request.session['agent_selected_customer_id']

        return result

    @http.route(['/shop/agent/cart/finalize'], type='http', auth='user', website=True)
    def agent_cart_finalize(self, **post):
        """
        Pagina finale per l'agente: scelta tra preventivo o ordine.
        Questa pagina sostituisce il checkout standard per gli agenti.
        """
        if not request.env.user.has_group('base.group_portal') or request.env.user._is_public():
            return request.redirect('/shop/cart')

        if not request.session.get('agent_selected_customer_id'):
            return request.redirect('/my/orders/new')

        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return request.redirect('/shop')

        # Assicurati che il partner sia quello del cliente selezionato
        customer_id = request.session.get('agent_selected_customer_id')
        customer = request.env['res.partner'].sudo().browse(customer_id)

        if order.partner_id != customer:
            order.sudo().write({
                'partner_id': customer.id,
                'partner_invoice_id': customer.id,
                'partner_shipping_id': customer.id,
            })
            order.sudo()._onchange_partner_id()

        # Recupera magazzini
        warehouses = request.env['stock.warehouse'].sudo().search([
            ('company_id', '=', request.env.company.id)
        ])

        # Recupera indirizzi di spedizione del cliente
        shipping_addresses = request.env['res.partner'].sudo().search([
            '|',
            ('id', '=', customer.id),
            '&',
            ('parent_id', '=', customer.id),
            ('type', '=', 'delivery')
        ])

        # Verifica se sale_voucher è installato
        voucher_module_installed = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'sale_voucher'),
            ('state', '=', 'installed')
        ], limit=1)

        values = {
            'order': order,
            'customer': customer,
            'agent': request.env.user.partner_id,
            'warehouses': warehouses,
            'shipping_addresses': shipping_addresses,
            'voucher_module_installed': bool(voucher_module_installed),
        }

        return request.render('NPAL_portal_sale_mod.agent_cart_finalize', values)

    @http.route(['/shop/agent/create_quotation'], type='http', auth='user', website=True, methods=['POST'])
    def agent_create_quotation(self, **post):
        """
        Crea un preventivo (quotation) senza confermare l'ordine.
        """
        if not request.env.user.has_group('base.group_portal') or request.env.user._is_public():
            return request.redirect('/shop/cart')

        order = request.website.sale_get_order()
        if not order:
            return request.redirect('/shop')

        # Assicurati che il partner sia corretto
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if order.partner_id != customer:
                order.sudo().write({
                    'partner_id': customer.id,
                    'partner_invoice_id': customer.id,
                    'partner_shipping_id': customer.id,
                })

        # Salva i campi obbligatori
        order_vals = {
            'state': 'draft',
            'is_agent_order': True,
            'created_by_agent_id': request.env.user.id,
            'agent_order_status': 'quotation',  # Imposta stato a Preventivo
        }

        if post.get('order_note'):
            order_vals['note'] = post.get('order_note')

        # Usa campi standard Odoo invece di campi custom
        if post.get('warehouse_id'):
            order_vals['warehouse_id'] = int(post.get('warehouse_id'))

        if post.get('delivery_date'):
            # Converti formato datetime-local HTML (2025-10-10T15:19) -> Odoo (2025-10-10 15:19:00)
            delivery_date = post.get('delivery_date').replace('T', ' ')
            if len(delivery_date) == 16:  # 2025-10-10 15:19
                delivery_date += ':00'  # Aggiungi secondi
            order_vals['commitment_date'] = delivery_date

        if post.get('transport_method'):
            order_vals['agent_transport_method'] = post.get('transport_method')

        if post.get('shipping_address_id'):
            order_vals['partner_shipping_id'] = int(post.get('shipping_address_id'))

        order.sudo().write(order_vals)

        # Pulisci la sessione
        request.session['sale_last_order_id'] = order.id
        request.website.sale_reset()
        if 'agent_selected_customer_id' in request.session:
            del request.session['agent_selected_customer_id']

        return request.redirect('/shop/agent/confirmation?quotation=1')

    @http.route(['/shop/agent/create_order'], type='http', auth='user', website=True, methods=['POST'])
    def agent_create_order(self, **post):
        """
        Crea un ordine in bozza (da confermare dal backoffice).
        """
        if not request.env.user.has_group('base.group_portal') or request.env.user._is_public():
            return request.redirect('/shop/cart')

        order = request.website.sale_get_order()
        if not order:
            return request.redirect('/shop')

        # Assicurati che il partner sia corretto
        if request.session.get('agent_selected_customer_id'):
            customer_id = request.session.get('agent_selected_customer_id')
            customer = request.env['res.partner'].sudo().browse(customer_id)

            if order.partner_id != customer:
                order.sudo().write({
                    'partner_id': customer.id,
                    'partner_invoice_id': customer.id,
                    'partner_shipping_id': customer.id,
                })

        # Salva i campi obbligatori
        order_vals = {
            'state': 'sent',
            'is_agent_order': True,
            'created_by_agent_id': request.env.user.id,
            'agent_order_status': 'agent_incoming',  # Imposta stato a Ordine in entrata da agente
        }

        if post.get('order_note'):
            order_vals['note'] = post.get('order_note')

        # Usa campi standard Odoo invece di campi custom
        if post.get('warehouse_id'):
            order_vals['warehouse_id'] = int(post.get('warehouse_id'))

        if post.get('delivery_date'):
            # Converti formato datetime-local HTML (2025-10-10T15:19) -> Odoo (2025-10-10 15:19:00)
            delivery_date = post.get('delivery_date').replace('T', ' ')
            if len(delivery_date) == 16:  # 2025-10-10 15:19
                delivery_date += ':00'  # Aggiungi secondi
            order_vals['commitment_date'] = delivery_date

        if post.get('transport_method'):
            order_vals['agent_transport_method'] = post.get('transport_method')

        if post.get('shipping_address_id'):
            order_vals['partner_shipping_id'] = int(post.get('shipping_address_id'))

        order.sudo().write(order_vals)

        # Pulisci la sessione
        request.session['sale_last_order_id'] = order.id
        request.website.sale_reset()
        if 'agent_selected_customer_id' in request.session:
            del request.session['agent_selected_customer_id']

        return request.redirect('/shop/agent/confirmation?order=1')

    @http.route(['/shop/agent/create_voucher'], type='http', auth='user', website=True, methods=['POST'])
    def agent_create_voucher(self, **post):
        """
        Crea un buono interno utilizzando il modulo sale_voucher.
        """
        if not request.env.user.has_group('base.group_portal') or request.env.user._is_public():
            return request.redirect('/shop/cart')

        # Verifica che il modulo sale_voucher sia installato
        if 'sale.voucher' not in request.env:
            return request.redirect('/shop/cart')

        order = request.website.sale_get_order()
        if not order:
            return request.redirect('/shop')

        # Recupera il cliente
        customer_id = request.session.get('agent_selected_customer_id')
        if not customer_id:
            return request.redirect('/my/orders/new')

        customer = request.env['res.partner'].sudo().browse(int(customer_id))

        # Crea il buono
        voucher_vals = {
            'recipient_id': customer.id,
            'warehouse_id': int(post.get('warehouse_id')) if post.get('warehouse_id') else False,
            'date': fields.Date.today(),
        }

        voucher = request.env['sale.voucher'].sudo().create(voucher_vals)

        # Aggiungi le righe del buono dall'ordine
        for line in order.order_line:
            # I campi di sale.voucher.line potrebbero essere diversi da sale.order.line
            voucher_line_vals = {
                'voucher_id': voucher.id,
                'product_id': line.product_id.id,
            }

            # Prova diversi nomi di campo per la quantità
            if 'quantity' in request.env['sale.voucher.line']._fields:
                voucher_line_vals['quantity'] = line.product_uom_qty
            elif 'qty' in request.env['sale.voucher.line']._fields:
                voucher_line_vals['qty'] = line.product_uom_qty
            elif 'product_qty' in request.env['sale.voucher.line']._fields:
                voucher_line_vals['product_qty'] = line.product_uom_qty

            # Aggiungi altri campi se esistono
            if 'price_unit' in request.env['sale.voucher.line']._fields:
                voucher_line_vals['price_unit'] = line.price_unit
            if 'description' in request.env['sale.voucher.line']._fields:
                voucher_line_vals['description'] = line.name
            elif 'name' in request.env['sale.voucher.line']._fields:
                voucher_line_vals['name'] = line.name

            request.env['sale.voucher.line'].sudo().create(voucher_line_vals)

        # Aggiungi note se fornite
        if post.get('order_note'):
            voucher.sudo().write({'note': post.get('order_note')})

        # Pulisci la sessione
        request.session['sale_voucher_id'] = voucher.id
        request.website.sale_reset()
        if 'agent_selected_customer_id' in request.session:
            del request.session['agent_selected_customer_id']

        return request.redirect('/shop/agent/confirmation?voucher=1')

    @http.route(['/shop/product/stock'], type='json', auth='user', website=True)
    def get_product_stock(self, product_id=None, warehouse_id=None):
        """
        Restituisce la quantità disponibile di un prodotto in un magazzino specifico.
        """
        if not product_id or not warehouse_id:
            return {'error': 'Missing parameters'}

        try:
            product = request.env['product.product'].sudo().browse(int(product_id))
            warehouse = request.env['stock.warehouse'].sudo().browse(int(warehouse_id))

            if not product.exists() or not warehouse.exists():
                return {'error': 'Product or warehouse not found'}

            # Ottieni la quantità disponibile nel magazzino specifico
            stock_quant = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id', 'child_of', warehouse.lot_stock_id.id)
            ])

            qty_available = sum(stock_quant.mapped('quantity')) - sum(stock_quant.mapped('reserved_quantity'))

            return {
                'qty_available': qty_available,
                'uom_name': product.uom_id.name,
                'product_name': product.display_name,
                'warehouse_name': warehouse.name,
            }

        except Exception as e:
            return {'error': str(e)}

    @http.route(['/shop/agent/confirmation'], type='http', auth='user', website=True)
    def agent_order_confirmation(self, **post):
        """
        Pagina di conferma dopo la creazione dell'ordine/preventivo/buono.
        """
        is_quotation = post.get('quotation') == '1'
        is_voucher = post.get('voucher') == '1'

        if is_voucher:
            voucher_id = request.session.get('sale_voucher_id')
            if not voucher_id:
                return request.redirect('/my/orders')

            voucher = request.env['sale.voucher'].sudo().browse(voucher_id)

            values = {
                'voucher': voucher,
                'is_voucher': True,
                'is_quotation': False,
            }
        else:
            order_id = request.session.get('sale_last_order_id')
            if not order_id:
                return request.redirect('/my/orders')

            order = request.env['sale.order'].sudo().browse(order_id)

            values = {
                'order': order,
                'is_quotation': is_quotation,
                'is_voucher': False,
            }

        return request.render('NPAL_portal_sale_mod.agent_order_confirmation', values)
