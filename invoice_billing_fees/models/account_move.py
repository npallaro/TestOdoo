from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    billing_fee_added = fields.Boolean(
        string='Spese di Fatturazione Aggiunte',
        default=False,
        copy=False,
        help='Campo tecnico per tracciare se le spese di fatturazione '
             'sono già state aggiunte a questa fattura.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override del metodo create per aggiungere automaticamente 
        le spese di fatturazione alle nuove fatture cliente."""
        moves = super().create(vals_list)
        
        for move in moves:
            # Aggiungi spese solo per fatture cliente in bozza
            if move.move_type == 'out_invoice' and move.state == 'draft':
                move._add_billing_fee_line()
        
        return moves

    def _add_billing_fee_line(self):
        """Aggiunge una riga di spese di fatturazione se il cliente 
        ha il campo billing_fee_amount valorizzato."""
        self.ensure_one()
        
        # Verifica se le spese sono già state aggiunte
        if self.billing_fee_added:
            return
        
        # Verifica se il partner ha spese di fatturazione configurate
        if not self.partner_id.billing_fee_amount or self.partner_id.billing_fee_amount <= 0:
            return
        
        # Cerca l'articolo "Spese di Fatturazione"
        billing_fee_product = self.env.ref(
            'invoice_billing_fees.product_billing_fee',
            raise_if_not_found=False
        )
        
        if not billing_fee_product:
            return
        
        # Verifica se esiste già una riga con questo prodotto
        existing_line = self.invoice_line_ids.filtered(
            lambda l: l.product_id == billing_fee_product
        )
        
        if existing_line:
            # Se esiste già, aggiorna solo il prezzo
            existing_line[0].price_unit = self.partner_id.billing_fee_amount
        else:
            # Crea una nuova riga di fattura con le spese
            self.env['account.move.line'].create({
                'move_id': self.id,
                'product_id': billing_fee_product.id,
                'name': billing_fee_product.name,
                'quantity': 1.0,
                'price_unit': self.partner_id.billing_fee_amount,
                'account_id': billing_fee_product.property_account_income_id.id 
                              or billing_fee_product.categ_id.property_account_income_categ_id.id,
                'tax_ids': [(6, 0, billing_fee_product.taxes_id.ids)],
            })
        
        # Marca che le spese sono state aggiunte
        self.billing_fee_added = True

