# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClubMemberTransferWizard(models.TransientModel):
    _name = 'club.member.transfer.wizard'
    _description = 'Club Member Transfer Wizard'

    member_ids = fields.Many2many(
        comodel_name='club.member',
        string='Selected Members',
        readonly=True,
    )
    member_count = fields.Integer(string='Selected Members', readonly=True)

    transfer_mode = fields.Selection(
        selection=[
            ('replace', 'Move and replace assignments'),
            ('add_team', 'Add team assignment (trainer process)'),
        ],
        string='Transfer Mode',
        required=True,
        default='replace',
    )

    target_scope = fields.Selection(
        selection=[
            ('subclub', 'Subclub'),
            ('department', 'Department'),
            ('pool', 'Pool'),
            ('team', 'Team'),
        ],
        string='Target Type',
        required=True,
        default='team',
    )

    target_subclub_id = fields.Many2one(
        comodel_name='club.subclub',
        string='Target Subclub',
    )
    target_department_id = fields.Many2one(
        comodel_name='club.department',
        string='Target Department',
    )
    target_pool_id = fields.Many2one(
        comodel_name='club.pool',
        string='Target Pool',
    )
    target_team_id = fields.Many2one(
        comodel_name='club.team',
        string='Target Team',
    )

    multi_team_member_count = fields.Integer(
        string='Members with multiple teams',
        compute='_compute_multi_team_member_count',
        readonly=True,
    )
    allow_replace_multi_team = fields.Boolean(
        string='Allow replacing assignments for multi-team members',
        default=False,
    )

    @api.depends('member_ids', 'member_ids.team_ids')
    def _compute_multi_team_member_count(self):
        for wizard in self:
            wizard.multi_team_member_count = len(wizard.member_ids.filtered(lambda member: len(member.team_ids) > 1))

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
            raise UserError(_('Please select at least one member before starting a transfer.'))

        values.update({
            'member_ids': [(6, 0, members.ids)],
            'member_count': len(members),
        })
        return values

    @api.onchange('target_scope')
    def _onchange_target_scope(self):
        self.target_subclub_id = False
        self.target_department_id = False
        self.target_pool_id = False
        self.target_team_id = False

    @api.onchange('transfer_mode')
    def _onchange_transfer_mode(self):
        if self.transfer_mode == 'add_team':
            self.target_scope = 'team'

    def _get_selected_target_record(self):
        self.ensure_one()
        if self.target_scope == 'subclub':
            target = self.target_subclub_id
        elif self.target_scope == 'department':
            target = self.target_department_id
        elif self.target_scope == 'pool':
            target = self.target_pool_id
        else:
            target = self.target_team_id

        if not target:
            raise UserError(_('Please select one target record.'))

        return target

    def _validate_transfer_mode(self):
        self.ensure_one()
        if self.transfer_mode == 'add_team' and self.target_scope != 'team':
            raise UserError(_('Add team assignment mode can only be used with target type Team.'))

        if self.transfer_mode != 'replace' or self.target_scope != 'team':
            return

        multi_team_members = self.member_ids.filtered(lambda member: len(member.team_ids) > 1)
        if multi_team_members and not self.allow_replace_multi_team:
            preview_names = ', '.join(multi_team_members.mapped('display_name')[:5])
            if len(multi_team_members) > 5:
                preview_names = '%s, ...' % preview_names
            raise UserError(
                _(
                    'There are %(count)s selected members assigned to multiple teams (%(names)s). '
                    'To avoid accidental data loss, either switch to "Add team assignment" mode '
                    'or enable "Allow replacing assignments for multi-team members".'
                )
                % {
                    'count': len(multi_team_members),
                    'names': preview_names,
                }
            )

    def _prepare_replace_values(self, target):
        self.ensure_one()

        if self.target_scope == 'subclub':
            return {
                'subclub_ids': [(6, 0, [target.id])],
                'department_ids': [(6, 0, [])],
                'pool_ids': [(6, 0, [])],
                'team_ids': [(6, 0, [])],
            }

        if self.target_scope == 'department':
            subclub_id = target.subclub_id.id if target.subclub_id else False
            return {
                'subclub_ids': [(6, 0, [subclub_id] if subclub_id else [])],
                'department_ids': [(6, 0, [target.id])],
                'pool_ids': [(6, 0, [])],
                'team_ids': [(6, 0, [])],
            }

        if self.target_scope == 'pool':
            subclub_id = target.subclub_id.id if target.subclub_id else False
            department_id = target.department_id.id if target.department_id else False
            return {
                'subclub_ids': [(6, 0, [subclub_id] if subclub_id else [])],
                'department_ids': [(6, 0, [department_id] if department_id else [])],
                'pool_ids': [(6, 0, [target.id])],
                'team_ids': [(6, 0, [])],
            }

        subclub_id = target.department_id.subclub_id.id if target.department_id and target.department_id.subclub_id else False
        department_id = target.department_id.id if target.department_id else False
        pool_id = target.pool_id.id if target.pool_id else False
        return {
            'subclub_ids': [(6, 0, [subclub_id] if subclub_id else [])],
            'department_ids': [(6, 0, [department_id] if department_id else [])],
            'pool_ids': [(6, 0, [pool_id] if pool_id else [])],
            'team_ids': [(6, 0, [target.id])],
        }

    def _prepare_add_team_values(self, target):
        self.ensure_one()
        values = {
            'team_ids': [(4, target.id)],
        }

        if target.department_id:
            values['department_ids'] = [(4, target.department_id.id)]
            if target.department_id.subclub_id:
                values['subclub_ids'] = [(4, target.department_id.subclub_id.id)]
        if target.pool_id:
            values['pool_ids'] = [(4, target.pool_id.id)]

        return values

    def _apply_team_transfer_state_transition(self, members, target):
        self.ensure_one()

        eligible_members = members.filtered(
            lambda member: member.current_state_id and member.current_state_id.state_type in ('registered', 'pending')
        )
        if not eligible_members:
            return

        active_state = self.env['club.member.state'].search([
            ('state_type', '=', 'active'),
            ('active', '=', True),
        ], limit=1)
        if not active_state:
            raise UserError(
                _('No active club member state (state_type = active) is configured. Please inform Administrator.')
            )

        reason = _('Automatic state change to active after transfer to team %(team)s.') % {
            'team': target.display_name,
        }
        state_rule_model = self.env['club.member.state.rule']
        now = fields.Datetime.now()
        for member in eligible_members:
            state_rule_model._change_member_state(
                member,
                active_state,
                reason,
                start_date=now,
            )

    def action_apply_transfer(self):
        self.ensure_one()

        members = self.member_ids.exists()
        if not members:
            raise UserError(_('No valid members are available for transfer.'))

        self._validate_transfer_mode()
        target = self._get_selected_target_record()

        if self.transfer_mode == 'add_team':
            vals = self._prepare_add_team_values(target)
        else:
            vals = self._prepare_replace_values(target)

        members.write(vals)

        if self.target_scope == 'team':
            self._apply_team_transfer_state_transition(members, target)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
