# -*- coding: utf-8 -*-

from datetime import timedelta
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

    # Campo per tracciare lo stato dell'ordine nel flusso operativo
    agent_order_status = fields.Selection([
        ('quotation', 'Preventivo'),
        ('agent_incoming', 'Ordine in entrata da agente'),
        ('in_production', 'Ordine in produzione'),
        ('ready_warehouse', 'Ordine da inserire in baia di uscita'),
        ('ready_pickup', 'Ordine pronto in baia da ritirare'),
        ('ready_delivery', 'Ordine pronto da consegnare NOI'),
        ('completed', 'Ordine completato'),
        ('waiting_info', 'Ordine in attesa di info'),
        ('supplier_order', 'In ordine dal fornitore'),
    ], string='Stato Operativo', tracking=True,
       help='Stato operativo dell\'ordine nel flusso di lavoro',
       copy=False)

    # Campo per tracciare l'ultimo cambio di stato (per task automatici)
    agent_status_date = fields.Datetime(
        string='Data Ultimo Cambio Stato',
        readonly=True,
        copy=False,
        help='Data e ora dell\'ultimo cambio di stato operativo'
    )

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
        Traccia i cambi di stato operativo e crea task automatici.
        """
        if self.env.user.has_group('base.group_portal'):
            for order in self:
                if order.state not in ['draft', 'sent']:
                    raise UserError(_(
                        "Puoi modificare solo ordini in stato bozza. "
                        "L'ordine %s è in stato '%s'."
                    ) % (order.name, order.state))

        # Se cambia lo stato operativo, aggiorna la data
        if 'agent_order_status' in vals and vals['agent_order_status']:
            vals['agent_status_date'] = fields.Datetime.now()

        result = super(SaleOrder, self).write(vals)

        # Crea task se l'ordine passa a "Ordine in entrata da agente"
        if 'agent_order_status' in vals and vals['agent_order_status'] == 'agent_incoming':
            for order in self:
                order._create_agent_order_confirmation_task()

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Se un utente portale crea un ordine, salva l'agente che lo ha creato.
        Imposta automaticamente lo stato operativo se non specificato.
        """
        for vals in vals_list:
            # Se è un utente portale, salva l'agente
            if self.env.user.has_group('base.group_portal') and not self.env.user._is_public():
                vals['created_by_agent_id'] = self.env.user.partner_id.id

            # Imposta lo stato operativo automaticamente se non già impostato
            if 'agent_order_status' not in vals or not vals.get('agent_order_status'):
                # Se creato da agente portale, lo stato dipende dal tipo di ordine
                # Verrà impostato nei controller specifici
                # Altrimenti default a 'quotation' per ordini interni
                if not self.env.user.has_group('base.group_portal'):
                    vals['agent_order_status'] = 'quotation'

            # Imposta la data di cambio stato
            if vals.get('agent_order_status'):
                vals['agent_status_date'] = fields.Datetime.now()

        orders = super(SaleOrder, self).create(vals_list)

        # Crea task per ordini da agente
        for order in orders:
            if order.agent_order_status == 'agent_incoming':
                order._create_agent_order_confirmation_task()

        return orders

    def action_confirm(self):
        """
        Gli utenti portale non possono confermare ordini.
        """
        if self.env.user.has_group('base.group_portal'):
            raise UserError(_("Gli agenti non possono confermare gli ordini. Contatta il back office."))

        return super(SaleOrder, self).action_confirm()

    def _create_agent_order_confirmation_task(self):
        """
        Crea un'attività (mail.activity) per confermare un ordine arrivato da un agente.
        L'attività appare nel chatter dell'ordine.
        """
        self.ensure_one()

        import logging
        _logger = logging.getLogger(__name__)

        _logger.info(f'[AGENT ORDER] Tentativo creazione attività per ordine {self.name}')

        # Ottieni gli utenti configurati per ricevere le attività
        config = self.env['ir.config_parameter'].sudo()
        user_ids_str = config.get_param('NPAL_portal_sale_mod.task_confirmation_user_ids', '')

        _logger.info(f'[AGENT ORDER] Utenti configurati: {user_ids_str}')

        if not user_ids_str:
            # Se non ci sono utenti configurati, skip
            _logger.warning('[AGENT ORDER] Nessun utente configurato per attività conferma ordini!')
            return

        try:
            user_ids = [int(uid) for uid in user_ids_str.split(',') if uid.strip()]
        except (ValueError, AttributeError) as e:
            _logger.error(f'[AGENT ORDER] Errore parsing user_ids: {e}')
            return

        if not user_ids:
            _logger.warning('[AGENT ORDER] Lista user_ids vuota dopo parsing')
            return

        _logger.info(f'[AGENT ORDER] Creazione attività per utenti: {user_ids}')

        # Ottieni il tipo di attività "Da fare" (TODO)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            _logger.error('[AGENT ORDER] Tipo attività TODO non trovato!')
            return

        # Ottieni l'ID del modello sale.order
        model_id = self.env['ir.model']._get('sale.order').id

        # Crea un'attività per ogni utente configurato
        for user_id in user_ids:
            activity_vals = {
                'res_model_id': model_id,
                'res_id': self.id,
                'activity_type_id': activity_type.id,
                'summary': f'Conferma Ordine da Agente {self.created_by_agent_id.name}',
                'note': f'''<p>Nuovo ordine ricevuto da agente che necessita conferma.</p>
<ul>
<li><strong>Ordine:</strong> {self.name}</li>
<li><strong>Cliente:</strong> {self.partner_id.name}</li>
<li><strong>Agente:</strong> {self.created_by_agent_id.name}</li>
<li><strong>Importo:</strong> {self.amount_total} {self.currency_id.name}</li>
<li><strong>Data richiesta consegna:</strong> {self.commitment_date or 'Non specificata'}</li>
</ul>
<p>Verifica l'ordine e conferma oppure contatta l'agente per chiarimenti.</p>''',
                'user_id': user_id,
                'date_deadline': fields.Date.today(),
            }

            try:
                activity = self.env['mail.activity'].sudo().create(activity_vals)
                _logger.info(f'[AGENT ORDER] Attività creata con successo! ID: {activity.id}, Utente: {user_id}')
            except Exception as e:
                _logger.error(f'[AGENT ORDER] Errore creazione attività per utente {user_id}: {e}', exc_info=True)

    @api.model
    def _check_stale_orders_and_create_tasks(self):
        """
        Cron job che controlla ordini fermi nello stesso stato da troppo tempo.
        Crea attività (mail.activity) che appaiono nel chatter degli ordini.
        Chiamato automaticamente da scheduled action.
        """
        import logging
        _logger = logging.getLogger(__name__)

        # Ottieni configurazione giorni di attesa
        config = self.env['ir.config_parameter'].sudo()
        days_limit = int(config.get_param('NPAL_portal_sale_mod.stale_order_days', '7'))
        user_ids_str = config.get_param('NPAL_portal_sale_mod.task_stale_user_ids', '')

        if not user_ids_str:
            return

        try:
            user_ids = [int(uid) for uid in user_ids_str.split(',') if uid.strip()]
        except (ValueError, AttributeError):
            return

        if not user_ids:
            return

        # Ottieni il tipo di attività "Da fare" (TODO)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            _logger.error('[AGENT ORDER] Tipo attività TODO non trovato per ordini fermi!')
            return

        # Ottieni l'ID del modello sale.order
        model_id = self.env['ir.model']._get('sale.order').id

        # Calcola la data limite
        limit_date = fields.Datetime.now() - timedelta(days=days_limit)

        # Cerca ordini fermi (escludi preventivi e completati)
        stale_orders = self.search([
            ('agent_order_status', 'not in', ['quotation', 'completed', False]),
            ('agent_status_date', '<=', limit_date),
            ('state', 'not in', ['cancel', 'done']),
        ])

        # Per ogni ordine fermo, controlla se esiste già un'attività recente
        for order in stale_orders:
            # Cerca attività già create negli ultimi N giorni per questo ordine
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('summary', 'ilike', f'Ordine fermo'),
                ('create_date', '>=', limit_date),
            ], limit=1)

            if existing_activity:
                # Attività già creata di recente, skip
                continue

            # Calcola giorni di fermo
            days_stuck = (fields.Datetime.now() - order.agent_status_date).days

            # Ottieni la label dello stato
            status_label = dict(order._fields['agent_order_status'].selection).get(order.agent_order_status, order.agent_order_status)

            # Crea un'attività per ogni utente configurato
            for user_id in user_ids:
                activity_vals = {
                    'res_model_id': model_id,
                    'res_id': order.id,
                    'activity_type_id': activity_type.id,
                    'summary': f'Ordine fermo: {order.name} - {status_label}',
                    'note': f'''<p><strong>Ordine fermo da {days_stuck} giorni</strong> nello stato "{status_label}".</p>
<ul>
<li><strong>Ordine:</strong> {order.name}</li>
<li><strong>Cliente:</strong> {order.partner_id.name}</li>
<li><strong>Stato:</strong> {status_label}</li>
<li><strong>Fermo dal:</strong> {order.agent_status_date.strftime("%d/%m/%Y %H:%M") if order.agent_status_date else "N/D"}</li>
<li><strong>Giorni di fermo:</strong> {days_stuck}</li>
</ul>
<p>Verifica lo stato dell'ordine e aggiornalo o contatta il cliente.</p>''',
                    'user_id': user_id,
                    'date_deadline': fields.Date.today(),
                }

                try:
                    activity = self.env['mail.activity'].sudo().create(activity_vals)
                    _logger.info(f'[AGENT ORDER] Attività ordine fermo creata! ID: {activity.id}, Ordine: {order.name}, Utente: {user_id}')
                except Exception as e:
                    _logger.error(f'[AGENT ORDER] Errore creazione attività ordine fermo per {order.name}, utente {user_id}: {e}', exc_info=True)
