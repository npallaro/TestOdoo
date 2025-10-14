from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    billing_fee_amount = fields.Monetary(
        string='Spese di Fatturazione',
        currency_field='currency_id',
        help='Importo delle spese di fatturazione da aggiungere automaticamente '
             'alle fatture create per questo cliente. Se valorizzato, '
             'verrà aggiunta una riga con questo importo in ogni nuova fattura.',
    )

