from odoo import _, api, fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class ClubMemberSingleBillingWizard(models.TransientModel):
    _name = 'club.member.single.billing.wizard'
    _description = 'Club Member Single Billing Wizard'

    member_ids = fields.Many2many(
        comodel_name='club.member',
        string='Selected Members',
        readonly=True,
    )
    member_count = fields.Integer(string='Selected Members', readonly=True)

    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    club_id = fields.Many2one(
        string='Club',
        comodel_name='club.club',
        required=True,
    )
    journal_id = fields.Many2one(
        string='Sales Journal',
        comodel_name='account.journal',
        required=True,
        domain="[('type', '=', 'sale')]",
        default=lambda self: self._default_journal_id(),
    )

    run_date = fields.Date(
        string='Invoice Date',
        required=True,
        default=fields.Date.context_today,
    )
    billing_year = fields.Integer(
        string='Billing Year',
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    note = fields.Text(string='Notes')

    @api.model
    def _default_journal_id(self):
        return self.env['club.member.billing.run']._default_membership_billing_journal()

    @api.model
    def _active_members_from_context(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []

        if active_model != 'club.member':
            return self.env['club.member']

        if not active_ids:
            active_id = self.env.context.get('active_id')
            if active_id:
                active_ids = [active_id]

        return self.env['club.member'].browse(active_ids).exists()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)

        members = self._active_members_from_context()
        if not members:
            raise UserError(_('Please select at least one member before starting single billing.'))

        clubs = members.mapped('club_id')
        if len(clubs) != 1:
            raise UserError(_('Please select members from exactly one club.'))

        values.update({
            'member_ids': [(6, 0, members.ids)],
            'member_count': len(members),
            'club_id': clubs.id,
        })
        _logger.info(
            "Open single billing wizard | active_model=%s | selected_member_ids=%s | selected_count=%s | club_id=%s",
            self.env.context.get('active_model'),
            members.ids,
            len(members),
            clubs.id,
        )
        return values

    def action_generate_draft_invoices(self):
        self.ensure_one()

        members = self.member_ids.exists()
        if not members:
            raise UserError(_('No valid members are available for billing.'))

        _logger.info(
            "Single billing wizard submit | wizard_id=%s | member_ids=%s | company_id=%s | club_id=%s | journal_id=%s | run_date=%s | billing_year=%s",
            self.id,
            members.ids,
            self.company_id.id,
            self.club_id.id,
            self.journal_id.id,
            self.run_date,
            self.billing_year,
        )

        run_vals = {
            'run_type': 'single',
            'billing_year': self.billing_year,
            'run_date': self.run_date,
            'company_id': self.company_id.id,
            'club_id': self.club_id.id,
            'journal_id': self.journal_id.id,
            'note': self.note,
        }
        run = self.env['club.member.billing.run'].create(run_vals)
        _logger.info(
            "Single billing created run | wizard_id=%s | run_id=%s",
            self.id,
            run.id,
        )

        run.with_context(
            club_selected_member_ids=members.ids,
            club_skip_replaced_cleanup=True,
        ).action_generate_draft_invoices()

        moves = run.line_ids.mapped('move_id').exists()
        _logger.info(
            "Single billing result | wizard_id=%s | run_id=%s | generated_move_ids=%s",
            self.id,
            run.id,
            moves.ids,
        )
        if not moves:
            raise UserError(_('No draft invoices were generated for the selected members.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Draft Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
            'context': {
                'create': False,
            },
        }
