# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.tools import groupby as groupbyelem
from operator import itemgetter


class CustomerPortalAgent(CustomerPortal):

    @http.route(['/my/customers'], type='http', auth='user', website=True)
    def portal_my_customers(self, **kw):
        """
        Pagina che mostra i clienti associati all'agente.
        """
        if request.env.user._is_public() or not request.env.user.has_group('base.group_portal'):
            return request.redirect('/my')

        partner = request.env.user.partner_id
        customers = partner.get_agent_customers()

        values = {
            'customers': customers,
            'page_name': 'customers',
        }

        return request.render('NPAL_portal_sale_mod.portal_my_customers', values)

    @http.route(['/my/orders/new'], type='http', auth='user', website=True)
    def portal_create_order(self, customer_id=None, **kw):
        """
        Pagina per creare un nuovo ordine per un cliente.
        Mostra la selezione del cliente e poi reindirizza al checkout.
        """
        if request.env.user._is_public() or not request.env.user.has_group('base.group_portal'):
            return request.redirect('/my')

        partner = request.env.user.partner_id
        customers = partner.get_agent_customers()

        if not customers:
            return request.render('NPAL_portal_sale_mod.portal_no_customers', {})

        # Se è stato selezionato un cliente, salva in sessione e reindirizza allo shop
        if customer_id:
            customer_id = int(customer_id)
            customer = request.env['res.partner'].browse(customer_id)

            # Verifica che il cliente sia associato all'agente
            if customer not in customers:
                raise AccessError(_("Non hai il permesso di creare ordini per questo cliente."))

            # Salva il cliente selezionato nella sessione
            request.session['agent_selected_customer_id'] = customer_id

            # Reindirizza allo shop
            return request.redirect('/shop')

        # Mostra il form di selezione cliente
        values = {
            'customers': customers,
            'page_name': 'create_order',
        }

        return request.render('NPAL_portal_sale_mod.portal_select_customer', values)

    @http.route(['/my/orders/clear_customer'], type='json', auth='user')
    def portal_clear_selected_customer(self, **kw):
        """
        Rimuove il cliente selezionato dalla sessione.
        """
        if 'agent_selected_customer_id' in request.session:
            del request.session['agent_selected_customer_id']
        return {'status': 'ok'}

    @http.route(['/my/orders/change_customer'], type='http', auth='user', website=True)
    def portal_change_customer(self, **kw):
        """
        Permette di cambiare il cliente selezionato.
        Se c'è un ordine in corso, lo salva prima.
        """
        if request.env.user._is_public() or not request.env.user.has_group('base.group_portal'):
            return request.redirect('/my')

        # Se c'è un ordine in corso, salvalo
        order = request.website.sale_get_order()
        if order and order.order_line:
            # L'ordine rimane in stato draft/sent, accessibile dall'agente
            # Reset del carrello per permettere nuovo ordine con altro cliente
            request.website.sale_reset()

        # Rimuovi il cliente selezionato dalla sessione
        if 'agent_selected_customer_id' in request.session:
            del request.session['agent_selected_customer_id']

        # Reindirizza alla selezione del nuovo cliente
        return request.redirect('/my/orders/new')

    @http.route(['/my/orders/add_address'], type='http', auth='user', website=True, methods=['POST'])
    def portal_add_shipping_address(self, **post):
        """
        Aggiunge un nuovo indirizzo di spedizione per un cliente.
        """
        if request.env.user._is_public() or not request.env.user.has_group('base.group_portal'):
            return request.redirect('/my')

        customer_id = request.session.get('agent_selected_customer_id') or post.get('customer_id')
        if not customer_id:
            return request.redirect('/my/orders/new')

        customer = request.env['res.partner'].sudo().browse(int(customer_id))
        if not customer.exists():
            return request.redirect('/my/orders/new')

        # Crea il nuovo indirizzo come child del cliente
        address_vals = {
            'parent_id': customer.id,
            'type': 'delivery',
            'name': post.get('address_name'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
        }

        # Aggiungi paese se fornito, altrimenti usa quello del cliente
        if post.get('country_id'):
            address_vals['country_id'] = int(post.get('country_id'))
        elif customer.country_id:
            address_vals['country_id'] = customer.country_id.id

        # Aggiungi provincia se fornita
        if post.get('state_id'):
            address_vals['state_id'] = int(post.get('state_id'))

        new_address = request.env['res.partner'].sudo().create(address_vals)

        # Reindirizza alla pagina di finalizzazione
        return request.redirect('/shop/agent/cart/finalize')
