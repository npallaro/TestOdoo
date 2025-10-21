# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_agent_customers(self):
        """
        Restituisce i clienti associati all'agente corrente (utente portale).
        Un cliente è associato se ha l'agente come 'user_id' (Addetto vendite).
        Restituisce solo le aziende principali, non gli indirizzi di consegna.
        """
        self.ensure_one()
        if not self.user_id:
            return self.env['res.partner']

        # Cerca tutti i partner che hanno questo utente come venditore
        # Filtra solo i partner principali (senza parent_id) o le aziende (is_company=True)
        # Esclude gli indirizzi di consegna/fatturazione (parent_id != False)
        customers = self.env['res.partner'].search([
            ('user_id', '=', self.user_id.id),
            ('id', '!=', self.id),  # Esclude l'agente stesso
            ('parent_id', '=', False),  # Solo partner principali, non indirizzi child
        ])

        return customers

    @api.model
    def get_customers_for_portal_user(self):
        """
        Helper method per ottenere i clienti dell'utente portale corrente.
        Usato nei controller.
        """
        if self.env.user._is_public() or not self.env.user.has_group('base.group_portal'):
            return self.env['res.partner']

        agent_partner = self.env.user.partner_id
        return agent_partner.get_agent_customers()

    def can_agent_access_partner(self, partner_id):
        """
        Verifica se l'agente corrente può accedere al partner specificato.
        """
        self.ensure_one()
        if not partner_id:
            return False

        partner = self.env['res.partner'].browse(partner_id)
        customers = self.get_agent_customers()

        return partner in customers
