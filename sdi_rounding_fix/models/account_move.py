    def action_add_sdi_rounding_line(self):
        """
        Estrae i totali dal file XML e crea righe di arrotondamento
        (una per ogni aliquota IVA) per allineare i totali Odoo con quelli XML.
        """
        self.ensure_one()
        
        if self.move_type not in ('in_invoice', 'in_refund'):
            raise UserError(_('Questa funzione è disponibile solo per le fatture fornitore.'))
        
        if self.state != 'draft':
            raise UserError(_('La fattura deve essere in stato bozza.'))
        
        if self.has_rounding_line:
            raise UserError(_('Esiste già una riga di arrotondamento. Rimuoverla prima di crearne una nuova.'))
        
        # Estrai totali XML
        extracted_totals = self._extract_xml_totals_from_attachment()
        
        if not extracted_totals or not extracted_totals.get('riepiloghi_iva'):
            raise UserError(_(
                'Non è stato possibile estrarre i riepiloghi IVA dal file XML.\n\n'
                'Verificare che il file XML sia allegato e in formato FatturaPA valido.'
            ))
        
        # Salva i totali estratti
        self.sdi_xml_untaxed = extracted_totals['untaxed']
        self.sdi_xml_tax = extracted_totals['tax']
        self.sdi_xml_total = extracted_totals['total']
        self.sdi_total_to_pay = extracted_totals.get('total_to_pay', extracted_totals['total'])
        
        # Calcola differenze per ogni aliquota IVA
        riepiloghi_xml = extracted_totals['riepiloghi_iva']
        
        # Ottieni i totali IVA effettivi di Odoo per ogni aliquota
        # Usa amount_by_group che contiene: (tax_name, base, tax_amount, ...)
        odoo_by_tax = {}
        
        if self.amount_by_group:
            for group in self.amount_by_group:
                # group è una tupla: (tax_name, base_amount, tax_amount, group_key)
                # Estrai l'aliquota dal nome della tassa
                tax_name = group[0]
                base_amount = group[1]
                tax_amount = group[2]
                
                # Cerca la tassa per estrarre l'aliquota
                # Il formato del nome è tipo "IVA 22%" o "IVA al 22%"
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', tax_name)
                if match:
                    tax_rate = float(match.group(1))
                else:
                    # Se non trova l'aliquota nel nome, prova a cercare dalla group_key
                    # group_key contiene l'ID della tassa
                    tax_id = group[3] if len(group) > 3 else None
                    if tax_id:
                        tax = self.env['account.tax'].browse(tax_id)
                        tax_rate = tax.amount if tax else 0.0
                    else:
                        tax_rate = 0.0
                
                odoo_by_tax[tax_rate] = {
                    'untaxed': base_amount,
                    'tax': tax_amount
                }
        
        _logger.info(f"Odoo per aliquota (da amount_by_group): {odoo_by_tax}")
        _logger.info(f"XML riepiloghi: {riepiloghi_xml}")
        
        # Crea righe di arrotondamento
        righe_create = []
        
        for riepilogo in riepiloghi_xml:
            aliquota = riepilogo['aliquota']
            xml_untaxed = riepilogo['imponibile']
            xml_tax = riepilogo['imposta']
            
            odoo_data = odoo_by_tax.get(aliquota, {'untaxed': 0.0, 'tax': 0.0})
            odoo_untaxed = odoo_data['untaxed']
            odoo_tax = odoo_data['tax']
            
            diff_untaxed = xml_untaxed - odoo_untaxed
            diff_tax = xml_tax - odoo_tax
            
            _logger.info(f"Aliquota {aliquota}%: XML Imp {xml_untaxed:.2f} IVA {xml_tax:.2f} | "
                        f"Odoo Imp {odoo_untaxed:.2f} IVA {odoo_tax:.2f} | "
                        f"Diff Imp {diff_untaxed:.2f} IVA {diff_tax:.2f}")
            
            if abs(diff_untaxed) >= 0.01:
                # Trova la tassa Odoo corrispondente
                tax_id = None
                if aliquota > 0:
                    tax = self.env['account.tax'].search([
                        ('amount', '=', aliquota),
                        ('type_tax_use', '=', 'purchase'),
                        ('company_id', '=', self.company_id.id)
                    ], limit=1)
                    if tax:
                        tax_id = tax.id
                
                # Cerca il prodotto di arrotondamento
                rounding_product = self.env['product.product'].search([
                    ('default_code', '=', 'SDI_ROUNDING')
                ], limit=1)
                
                if not rounding_product:
                    rounding_product = self._create_rounding_product()
                
                account = rounding_product.property_account_expense_id or \
                          rounding_product.categ_id.property_account_expense_categ_id
                
                if not account:
                    raise UserError(_('Conto contabile non trovato per il prodotto di arrotondamento.'))
                
                # Crea la riga
                line_vals = {
                    'move_id': self.id,
                    'product_id': rounding_product.id,
                    'name': f'Arrotondamento SDI - IVA {aliquota}%',
                    'account_id': account.id,
                    'quantity': 1,
                    'price_unit': diff_untaxed,
                    'tax_ids': [(6, 0, [tax_id])] if tax_id else [(5, 0, 0)],
                }
                
                righe_create.append(line_vals)
                _logger.info(f"Creo riga arrotondamento IVA {aliquota}%: {diff_untaxed:.2f} € (IVA attesa: {diff_untaxed * aliquota / 100:.2f} €)")
        
        if not righe_create:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✓ Nessun Arrotondamento Necessario'),
                    'message': _('I totali Odoo corrispondono già ai totali XML.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        # Crea tutte le righe
        for line_vals in righe_create:
            self.env['account.move.line'].create(line_vals)
        
        # Ricalcola i totali
        self.invalidate_recordset(['amount_total', 'amount_untaxed', 'amount_tax'])
        
        message = _('✓ Arrotondamento Completato\n\n'
                   'Create %d righe di arrotondamento.\n\n'
                   'Totali XML:\n'
                   '• Imponibile: %.2f €\n'
                   '• IVA: %.2f €\n'
                   '• Totale: %.2f €\n\n'
                   'I totali Odoo ora corrispondono!') % (
            len(righe_create),
            self.sdi_xml_untaxed,
            self.sdi_xml_tax,
            self.sdi_xml_total
        )
        
        self.message_post(body=message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✓ Arrotondamento Completato'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

