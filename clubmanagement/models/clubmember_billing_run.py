from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class ClubMemberBillingRun(models.Model):
    _name = 'club.member.billing.run'
    _description = 'Club Member Billing Run'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'club.log.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Run Name', required=True, default='New', readonly=True, copy=False)
    run_type = fields.Selection(
        selection=[
            ('annual', 'Annual Billing'),
            ('single', 'Single Billing'),
        ],
        string='Run Type',
        required=True,
        default='annual',
        tracking=True,
    )
    billing_year = fields.Integer(string='Billing Year', required=True, default=lambda self: fields.Date.today().year, tracking=True)
    run_date = fields.Date(string='Run Date', required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company, tracking=True)
    club_id = fields.Many2one(
        string='Club',
        comodel_name='club.club',
        required=True,
        tracking=True,
        default=lambda self: self.env['club.club'].search([], limit=1).id,
    )
    journal_id = fields.Many2one(
        string='Sales Journal',
        comodel_name='account.journal',
        required=True,
        domain="[('type', '=', 'sale')]",
        tracking=True,
        default=lambda self: self._default_membership_billing_journal(),
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    line_ids = fields.One2many(string='Run Lines', comodel_name='club.member.billing.run.line', inverse_name='run_id')
    selection_team_id = fields.Many2one(
        string='Selection Team',
        comodel_name='club.team',
        domain="[('club_id', '=', club_id)]",
    )
    selection_pool_id = fields.Many2one(
        string='Selection Pool',
        comodel_name='club.pool',
        domain="[('club_id', '=', club_id)]",
    )
    selection_department_id = fields.Many2one(
        string='Selection Department',
        comodel_name='club.department',
        domain="[('club_id', '=', club_id)]",
    )
    selection_subclub_id = fields.Many2one(
        string='Selection Subclub',
        comodel_name='club.subclub',
        domain="[('club_id', '=', club_id)]",
    )
    selected_member_ids = fields.Many2many(
        string='Preselected Members',
        comodel_name='club.member',
        relation='club_member_billing_run_selected_member_rel',
        column1='run_id',
        column2='member_id',
        domain="[('club_id', '=', club_id)]",
        help='Members loaded from one selected source (team, pool, department, or subclub) and manually adjustable before invoice generation.',
    )
    selected_member_count = fields.Integer(
        string='Preselected Member Count',
        compute='_compute_selected_member_count',
    )
    note = fields.Text(string='Notes')

    rerun_of_id = fields.Many2one(string='Rerun Of', comodel_name='club.member.billing.run', readonly=True, copy=False)
    replaced_run_ids = fields.Many2many(
        string='Replaced Runs',
        comodel_name='club.member.billing.run',
        relation='club_member_billing_run_replaced_rel',
        column1='run_id',
        column2='replaced_run_id',
        readonly=True,
        copy=False,
    )

    draft_move_count = fields.Integer(string='Draft Invoice Count', compute='_compute_draft_move_count')
    fee_exempt_member_ids = fields.Many2many(
        string='Skipped Fee Exempt Members',
        comodel_name='club.member',
        relation='club_member_billing_run_fee_exempt_rel',
        column1='run_id',
        column2='member_id',
        readonly=True,
        copy=False,
    )
    fee_exempt_member_count = fields.Integer(
        string='Skipped Fee Exempt Count',
        compute='_compute_fee_exempt_member_count',
    )

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.model
    def _default_membership_billing_journal(self):
        journal_id = self.env['ir.config_parameter'].sudo().get_param('clubmanagement.membership_billing_journal_id')
        try:
            journal_id = int(journal_id) if journal_id else False
        except (TypeError, ValueError):
            journal_id = False

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            if journal.exists() and journal.type == 'sale':
                return journal.id

        return False

    @api.depends('line_ids.move_id.state')
    def _compute_draft_move_count(self):
        for run in self:
            run.draft_move_count = len(run.line_ids.mapped('move_id').filtered(lambda move: move.state == 'draft'))

    @api.depends('selected_member_ids')
    def _compute_selected_member_count(self):
        for run in self:
            run.selected_member_count = len(run.selected_member_ids)

    @api.depends('fee_exempt_member_ids')
    def _compute_fee_exempt_member_count(self):
        for run in self:
            run.fee_exempt_member_count = len(run.fee_exempt_member_ids)

    @api.constrains('selection_team_id', 'selection_pool_id', 'selection_department_id', 'selection_subclub_id')
    def _check_selection_scope_exclusivity(self):
        for run in self:
            selected_scopes = [
                bool(run.selection_team_id),
                bool(run.selection_pool_id),
                bool(run.selection_department_id),
                bool(run.selection_subclub_id),
            ]
            if sum(selected_scopes) > 1:
                raise ValidationError(
                    _("Only one selection scope is allowed. Choose exactly one of team, pool, department, or subclub.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == 'New':
                record.name = _("Billing Run %(year)s - %(company)s - %(id)s") % {
                    'year': record.billing_year,
                    'company': record.company_id.display_name,
                    'id': record.id,
                }
        return records

    def _check_run_start_permissions(self):
        user = self.env.user
        if user.login in ('admin', '__system__'):
            return
        if not (
            user.has_group('account.group_account_invoice')
            or user.has_group('account.group_account_manager')
        ):
            raise AccessError(_("You are not allowed to start or rerun billing runs."))

    def _cleanup_replaced_draft_moves(self):
        self.ensure_one()

        previous_runs = self.search([
            ('id', '!=', self.id),
            ('run_type', '=', self.run_type),
            ('billing_year', '=', self.billing_year),
            ('company_id', '=', self.company_id.id),
            ('journal_id', '=', self.journal_id.id),
        ], order='id desc')

        if not previous_runs:
            return self.env['club.member.billing.run']

        draft_moves = previous_runs.mapped('line_ids.move_id').filtered(lambda move: move.state == 'draft')
        if draft_moves:
            draft_moves.unlink()

        return previous_runs

    def _cleanup_current_run_draft_moves(self):
        self.ensure_one()
        draft_moves = self.line_ids.mapped('move_id').filtered(lambda move: move.state == 'draft')
        non_draft_moves = self.line_ids.mapped('move_id').filtered(lambda move: move.state != 'draft')
        if non_draft_moves:
            raise ValidationError(_("Current run already has non-draft invoices. Reset those invoices before regeneration."))
        if draft_moves:
            draft_moves.unlink()
        if self.line_ids:
            self.line_ids.unlink()

    def _get_candidate_members(self):
        self.ensure_one()
        selected_member_ids = self.env.context.get('club_selected_member_ids') or self.selected_member_ids.ids

        # For explicit member selection, include the selected records and let
        # _validate_member_for_run return precise, user-facing reasons.
        if selected_member_ids:
            domain = [
                ('active', '=', True),
                ('club_id', '=', self.club_id.id),
                ('id', 'in', selected_member_ids),
            ]
        else:
            domain = [
                ('active', '=', True),
                ('club_id', '=', self.club_id.id),
                ('effective_membership_id', '!=', False),
                ('invoice_partner_id', '!=', False),
            ]
        members = self.env['club.member'].search(domain)
        _logger.info(
            "Billing run %s candidate selection | run_type=%s | club=%s | selected_member_ids=%s | found_member_ids=%s",
            self.id,
            self.run_type,
            self.club_id.id,
            selected_member_ids,
            members.ids,
        )
        return members

    def _get_selected_scope_record(self):
        self.ensure_one()

        selected_scopes = [
            ('team', self.selection_team_id),
            ('pool', self.selection_pool_id),
            ('department', self.selection_department_id),
            ('subclub', self.selection_subclub_id),
        ]
        selected_scopes = [(scope_type, record) for scope_type, record in selected_scopes if record]

        if len(selected_scopes) > 1:
            raise ValidationError(
                _("Only one selection scope is allowed. Choose exactly one of team, pool, department, or subclub.")
            )

        if not selected_scopes:
            raise ValidationError(
                _("Please choose one selection scope (team, pool, department, or subclub) before loading members.")
            )

        return selected_scopes[0]

    def action_load_selected_members(self):
        for run in self:
            if run.state != 'draft':
                raise ValidationError(_("Members can only be loaded while the run is in draft state."))

            scope_type, scope_record = run._get_selected_scope_record()
            members = scope_record.member_ids_display.filtered(lambda member: member.club_id == run.club_id)

            run.write({
                'selected_member_ids': [(6, 0, members.ids)],
            })

            _logger.info(
                "Loaded preselected members for billing run | run_id=%s | scope_type=%s | scope_record_id=%s | selected_member_ids=%s",
                run.id,
                scope_type,
                scope_record.id,
                members.ids,
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Members loaded'),
                'message': _('Preselection updated. You can still adjust the member list manually.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def _validate_member_for_run(self, member):
        self.ensure_one()

        if not member.effective_membership_id:
            return _("Member '%s' has no effective membership.") % member.display_name

        membership = member.effective_membership_id

        if membership.company_id != self.company_id:
            return _("Member '%(member)s' membership company '%(membership_company)s' does not match run company '%(run_company)s'.") % {
                'member': member.display_name,
                'membership_company': membership.company_id.display_name,
                'run_company': self.company_id.display_name,
            }

        if len(member.subclub_ids.mapped('company_id')) > 1:
            return _("Member '%s' is linked to multiple subclub companies. Resolve data quality before billing.") % member.display_name

        if membership.is_fee_exempt:
            _logger.info(
                "Member is fee exempt and skipped from billing entries | run_id=%s | member_id=%s | membership_id=%s",
                self.id,
                member.id,
                membership.id,
            )
            return False

        invoice_partner = member.invoice_partner_id
        if not invoice_partner:
            return _("Member '%s' has no invoice partner.") % member.display_name

        missing_address_fields = []
        if not invoice_partner.name:
            missing_address_fields.append('name')
        if not invoice_partner.street:
            missing_address_fields.append('street')
        if not invoice_partner.zip:
            missing_address_fields.append('zip')
        if not invoice_partner.city:
            missing_address_fields.append('city')
        if missing_address_fields:
            return _("Invoice partner '%(partner)s' is missing required fields: %(fields)s") % {
                'partner': invoice_partner.display_name,
                'fields': ', '.join(missing_address_fields),
            }

        if not membership.main_product_id:
            return _("Membership '%s' has no main product configured.") % membership.display_name

        return False

    def _build_member_product_entries(self, member):
        self.ensure_one()
        membership = member.effective_membership_id

        if membership.is_fee_exempt:
            return []

        if not membership.main_product_id:
            return []

        entries = []

        entries.append({
            'member': member,
            'membership': membership,
            'invoice_partner': member.invoice_partner_id,
            'product': membership.main_product_id,
            'quantity': 1.0,
            'price_unit': membership.main_product_id.list_price,
            'once_per_invoice': False,
        })

        for additional in membership.additional_product_ids:
            entries.append({
                'member': member,
                'membership': membership,
                'invoice_partner': member.invoice_partner_id,
                'product': additional.product_id,
                'quantity': 1.0,
                'price_unit': additional.product_id.list_price,
                'once_per_invoice': bool(additional.once_per_invoice),
            })

        return entries

    def _validate_product_accounting(self, product, invoice_partner):
        self.ensure_one()
        income_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        if not income_account:
            return _("Product '%s' has no income account configured.") % product.display_name

        return False

    def _build_group_key(self, entry):
        if entry['member'].invoice_grouping_mode == 'single':
            return ('single', entry['member'].id)
        return ('by_payer', entry['invoice_partner'].id)

    def _create_invoice_for_group(self, group_entries):
        self.ensure_one()
        first_entry = group_entries[0]
        invoice_partner = first_entry['invoice_partner']

        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': invoice_partner.id,
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
            'invoice_date': self.run_date,
            'invoice_payment_term_id': invoice_partner.property_payment_term_id.id or False,
            'invoice_origin': self.name,
            'ref': _("Billing Run: %s") % self.name,
            'invoice_line_ids': [],
        }

        processed_once_products = set()
        run_line_commands = []

        for entry in group_entries:
            product = entry['product']
            if entry['once_per_invoice'] and product.id in processed_once_products:
                continue

            validation_error = self._validate_product_accounting(product, invoice_partner)
            if validation_error:
                raise ValidationError(validation_error)

            product_taxes = product.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)
            if not product_taxes:
                _logger.info(
                    "No company tax matched for product line, using tax-exempt line | run_id=%s | product_id=%s | product_name=%s | run_company_id=%s | configured_tax_ids=%s | configured_tax_companies=%s",
                    self.id,
                    product.id,
                    product.display_name,
                    self.company_id.id,
                    product.taxes_id.ids,
                    [tax.company_id.id for tax in product.taxes_id],
                )
            line_name = _("%(member)s - %(product)s") % {
                'member': entry['member'].display_name,
                'product': product.display_name,
            }

            move_vals['invoice_line_ids'].append((0, 0, {
                'name': line_name,
                'product_id': product.id,
                'quantity': entry['quantity'],
                'price_unit': entry['price_unit'],
                'tax_ids': [(6, 0, product_taxes.ids)],
            }))

            run_line_commands.append((0, 0, {
                'member_id': entry['member'].id,
                'membership_id': entry['membership'].id,
                'effective_membership_source_scope': entry['member'].effective_membership_source_scope,
                'effective_membership_source_model': entry['member'].effective_membership_source_model,
                'effective_membership_source_res_id': entry['member'].effective_membership_source_res_id,
                'effective_membership_source_name': entry['member'].effective_membership_source_name,
                'invoice_partner_id': invoice_partner.id,
                'product_id': product.id,
                'quantity': entry['quantity'],
                'price_unit': entry['price_unit'],
                'tax_ids': [(6, 0, product_taxes.ids)],
                'snapshot_data': {
                    'run_name': self.name,
                    'run_type': self.run_type,
                    'billing_year': self.billing_year,
                    'member_name': entry['member'].display_name,
                    'membership_name': entry['membership'].display_name,
                    'base_membership_name': entry['member'].current_membership_id.display_name,
                    'effective_membership_source_scope': entry['member'].effective_membership_source_scope,
                    'effective_membership_source_model': entry['member'].effective_membership_source_model,
                    'effective_membership_source_res_id': entry['member'].effective_membership_source_res_id,
                    'effective_membership_source_name': entry['member'].effective_membership_source_name,
                    'product_name': product.display_name,
                    'invoice_partner_name': invoice_partner.display_name,
                    'once_per_invoice': entry['once_per_invoice'],
                },
            }))

            if entry['once_per_invoice']:
                processed_once_products.add(product.id)

        move = self.env['account.move'].create(move_vals)

        for command in run_line_commands:
            command[2]['move_id'] = move.id

        return run_line_commands

    def action_prepare_rerun_cleanup(self):
        for run in self:
            run._check_run_start_permissions()
            if run.state != 'draft':
                raise ValidationError(_("Only draft runs can prepare rerun cleanup."))

            replaced_runs = run._cleanup_replaced_draft_moves()
            if replaced_runs:
                run.write({
                    'rerun_of_id': replaced_runs[0].id,
                    'replaced_run_ids': [(6, 0, replaced_runs.ids)],
                })

    def action_generate_draft_invoices(self):
        for run in self:
            run._check_run_start_permissions()
            if run.state != 'draft':
                raise ValidationError(_("Invoices can only be generated from draft runs."))

            selected_member_ids = run.env.context.get('club_selected_member_ids') or run.selected_member_ids.ids
            _logger.info(
                "Start draft invoice generation | run_id=%s | run_type=%s | company=%s | club=%s | selected_member_ids=%s | skip_replaced_cleanup=%s",
                run.id,
                run.run_type,
                run.company_id.id,
                run.club_id.id,
                selected_member_ids,
                bool(run.env.context.get('club_skip_replaced_cleanup')),
            )

            run._cleanup_current_run_draft_moves()
            if not self.env.context.get('club_skip_replaced_cleanup'):
                replaced_runs = run._cleanup_replaced_draft_moves()
                if replaced_runs:
                    run.write({
                        'rerun_of_id': replaced_runs[0].id,
                        'replaced_run_ids': [(6, 0, replaced_runs.ids)],
                    })

            members = run._get_candidate_members()
            if not members:
                _logger.warning(
                    "No billable members found | run_id=%s | run_type=%s | company=%s | club=%s | selected_member_ids=%s",
                    run.id,
                    run.run_type,
                    run.company_id.id,
                    run.club_id.id,
                    selected_member_ids,
                )
                raise ValidationError(_("No billable members found for this run."))

            _logger.info(
                "Applying billing defaults before validation | run_id=%s | member_ids=%s",
                run.id,
                members.ids,
            )
            members.with_context(club_billing_internal=True)._apply_billing_defaults()

            errors = []
            all_entries = []
            fee_exempt_members = self.env['club.member']
            for member in members:
                _logger.info(
                    "Member billing snapshot | run_id=%s | member_id=%s | member_partner_id=%s | is_minor=%s | membership_id=%s | invoice_partner_id=%s | invoice_partner_source=%s | primary_guardian_id=%s | guardian_partner_ids=%s | grouping_mode=%s",
                    run.id,
                    member.id,
                    member.partner_id.id if member.partner_id else False,
                    member._is_minor_for_billing(member.birthdate_date),
                    member.effective_membership_id.id if member.effective_membership_id else False,
                    member.invoice_partner_id.id if member.invoice_partner_id else False,
                    member.invoice_partner_source,
                    member.primary_guardian_id.id if member.primary_guardian_id else False,
                    member.guardian_ids.mapped('guardian_id').ids,
                    member.invoice_grouping_mode,
                )

                if member.effective_membership_id and member.effective_membership_id.is_fee_exempt:
                    fee_exempt_members |= member
                    continue

                error_message = run._validate_member_for_run(member)
                if error_message:
                    _logger.warning(
                        "Member skipped in billing run | run_id=%s | member_id=%s | member_name=%s | reason=%s",
                        run.id,
                        member.id,
                        member.display_name,
                        error_message,
                    )
                    errors.append(error_message)
                    continue
                all_entries.extend(run._build_member_product_entries(member))

            _logger.info(
                "Billing run validation summary | run_id=%s | candidate_count=%s | fee_exempt_count=%s | error_count=%s | entry_count=%s",
                run.id,
                len(members),
                len(fee_exempt_members),
                len(errors),
                len(all_entries),
            )

            if errors:
                raise ValidationError("\n".join(errors))

            groups = {}
            for entry in all_entries:
                key = run._build_group_key(entry)
                groups.setdefault(key, [])
                groups[key].append(entry)

            _logger.info(
                "Billing run grouping summary | run_id=%s | group_count=%s",
                run.id,
                len(groups),
            )

            all_run_line_commands = []
            for group_entries in groups.values():
                all_run_line_commands.extend(run._create_invoice_for_group(group_entries))

            run_write_vals = {
                'fee_exempt_member_ids': [(6, 0, fee_exempt_members.ids)],
            }
            if all_run_line_commands:
                run_write_vals['line_ids'] = all_run_line_commands
            run.write(run_write_vals)

            _logger.info(
                "Finished draft invoice generation | run_id=%s | generated_line_count=%s | generated_move_count=%s | fee_exempt_count=%s",
                run.id,
                len(all_run_line_commands),
                len(run.line_ids.mapped('move_id')),
                len(run.fee_exempt_member_ids),
            )

    def action_mark_done(self):
        for run in self:
            run._check_run_start_permissions()
            run.state = 'done'

    def action_cancel(self):
        for run in self:
            run.state = 'cancelled'

    def action_reset_to_draft(self):
        for run in self:
            run.state = 'draft'


class ClubMemberBillingRunLine(models.Model):
    _name = 'club.member.billing.run.line'
    _description = 'Club Member Billing Run Line'
    _order = 'id'

    run_id = fields.Many2one(string='Billing Run', comodel_name='club.member.billing.run', required=True, ondelete='cascade')
    company_id = fields.Many2one(string='Company', comodel_name='res.company', related='run_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(string='Currency', comodel_name='res.currency', related='company_id.currency_id', store=True, readonly=True)

    member_id = fields.Many2one(string='Member', comodel_name='club.member', required=True)
    membership_id = fields.Many2one(string='Membership', comodel_name='club.member.membership')
    effective_membership_source_scope = fields.Selection(
        selection=[
            ('team', 'Team'),
            ('pool', 'Pool'),
            ('department', 'Department'),
            ('subclub', 'Subclub'),
            ('base', 'Base Membership'),
        ],
        string='Membership Source',
    )
    effective_membership_source_model = fields.Char(string='Membership Source Model')
    effective_membership_source_res_id = fields.Integer(string='Membership Source ID')
    effective_membership_source_name = fields.Char(string='Membership Source Name')
    invoice_partner_id = fields.Many2one(string='Invoice Partner', comodel_name='res.partner')

    product_id = fields.Many2one(string='Product', comodel_name='product.product')
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id')
    tax_ids = fields.Many2many(string='Taxes', comodel_name='account.tax')

    move_id = fields.Many2one(string='Invoice', comodel_name='account.move')
    move_line_id = fields.Many2one(string='Invoice Line', comodel_name='account.move.line')

    has_error = fields.Boolean(string='Has Error', default=False)
    error_message = fields.Text(string='Error Message')
    snapshot_data = fields.Json(string='Snapshot Data')

    _sql_constraints = [
        ('quantity_positive', 'CHECK(quantity > 0)', 'Quantity must be greater than zero.'),
    ]
