# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    created_by_agent_id = fields.Many2one(
        'res.partner',
        string='Creato da Agente',
        help='Agente (utente portale) che ha creato questo ordine per conto del cliente',
        readonly=True,
        tracking=True,
    )

    is_agent_order = fields.Boolean(
        string='Ordine Agente',
        compute='_compute_is_agent_order',
        store=True,
        help='Indica se questo ordine è stato creato da un agente per un cliente',
    )

    # Campo custom solo per il metodo di trasporto (gli altri usano campi standard Odoo)
    agent_transport_method = fields.Selection([
        ('sender', 'Mittente'),
        ('recipient', 'Destinatario'),
        ('carrier', 'Vettore'),
    ], string='Metodo di Trasporto', tracking=True, help='Chi gestisce il trasporto della merce')

    @api.depends('created_by_agent_id')
    def _compute_is_agent_order(self):
        for order in self:
            order.is_agent_order = bool(order.created_by_agent_id)

    def _check_agent_access(self):
        """
        Verifica che l'utente portale abbia accesso a questo ordine.
        Un agente può accedere agli ordini dei clienti associati a lui.
        """
        self.ensure_one()
        if self.env.user._is_public():
            raise AccessError(_("Gli utenti pubblici non possono accedere agli ordini."))

        # Gli utenti interni hanno sempre accesso
        if not self.env.user.has_group('base.group_portal'):
            return True

        # Per gli utenti portale, verifica che siano l'agente del cliente
        partner = self.env.user.partner_id
        if self.partner_id.user_id != self.env.user and self.partner_id.user_id != partner.user_id:
            # Verifica se il partner dell'ordine ha come venditore l'agente corrente
            if self.partner_id.user_id != partner or self.created_by_agent_id != partner:
                raise AccessError(_("Non hai il permesso di accedere a questo ordine."))

        return True

    def write(self, vals):
        """
        Permette agli agenti di modificare solo ordini in stato bozza.
        """
        if self.env.user.has_group('base.group_portal'):
            for order in self:
                if order.state not in ['draft', 'sent']:
                    raise UserError(_(
                        "Puoi modificare solo ordini in stato bozza. "
                        "L'ordine %s è in stato '%s'."
                    ) % (order.name, order.state))

        return super(SaleOrder, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Se un utente portale crea un ordine, salva l'agente che lo ha creato.
        """
        if self.env.user.has_group('base.group_portal') and not self.env.user._is_public():
            for vals in vals_list:
                vals['created_by_agent_id'] = self.env.user.partner_id.id

        return super(SaleOrder, self).create(vals_list)

    def action_confirm(self):
        """
        Gli utenti portale non possono confermare ordini.
        """
        if self.env.user.has_group('base.group_portal'):
            raise UserError(_("Gli agenti non possono confermare gli ordini. Contatta il back office."))

        return super(SaleOrder, self).action_confirm()
