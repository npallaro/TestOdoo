# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    task_confirmation_user_ids = fields.Many2many(
        'res.users',
        'agent_order_confirmation_task_users_rel',
        'config_id',
        'user_id',
        string='Utenti per Task Conferma Ordini',
        help='Utenti che riceveranno i task quando un agente crea un nuovo ordine',
    )

    task_stale_user_ids = fields.Many2many(
        'res.users',
        'agent_order_stale_task_users_rel',
        'config_id',
        'user_id',
        string='Utenti per Task Ordini Fermi',
        help='Utenti che riceveranno i task per ordini fermi da troppo tempo',
    )

    stale_order_days = fields.Integer(
        string='Giorni per Ordine Fermo',
        default=7,
        help='Numero di giorni dopo i quali un ordine fermo nello stesso stato genera un task',
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        config = self.env['ir.config_parameter'].sudo()

        # Leggi gli ID degli utenti
        task_confirmation_user_ids_str = config.get_param('NPAL_portal_sale_mod.task_confirmation_user_ids', '')
        task_stale_user_ids_str = config.get_param('NPAL_portal_sale_mod.task_stale_user_ids', '')

        # Converti stringhe in liste di interi
        task_confirmation_user_ids = []
        if task_confirmation_user_ids_str:
            try:
                task_confirmation_user_ids = [int(uid) for uid in task_confirmation_user_ids_str.split(',') if uid.strip()]
            except (ValueError, AttributeError):
                pass

        task_stale_user_ids = []
        if task_stale_user_ids_str:
            try:
                task_stale_user_ids = [int(uid) for uid in task_stale_user_ids_str.split(',') if uid.strip()]
            except (ValueError, AttributeError):
                pass

        res.update(
            task_confirmation_user_ids=[(6, 0, task_confirmation_user_ids)],
            task_stale_user_ids=[(6, 0, task_stale_user_ids)],
            stale_order_days=int(config.get_param('NPAL_portal_sale_mod.stale_order_days', '7')),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        config = self.env['ir.config_parameter'].sudo()

        # Salva gli ID utenti come stringa separata da virgole
        task_confirmation_user_ids_str = ','.join(str(uid) for uid in self.task_confirmation_user_ids.ids)
        task_stale_user_ids_str = ','.join(str(uid) for uid in self.task_stale_user_ids.ids)

        config.set_param('NPAL_portal_sale_mod.task_confirmation_user_ids', task_confirmation_user_ids_str)
        config.set_param('NPAL_portal_sale_mod.task_stale_user_ids', task_stale_user_ids_str)
        config.set_param('NPAL_portal_sale_mod.stale_order_days', self.stale_order_days)
