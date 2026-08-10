# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class ClubMemberStateChangeWizard(models.TransientModel):
    _name = 'club.member.state.change.wizard'
    _description = 'Club Member State Change Wizard'

    _FORBIDDEN_TARGET_STATE_TYPES = ('registered', 'deleted')

    member_id = fields.Many2one(
        comodel_name='club.member',
        string='Member',
        required=True,
        readonly=True,
    )
    current_state_id = fields.Many2one(
        comodel_name='club.member.state',
        string='Current State',
        readonly=True,
    )
    target_state_id = fields.Many2one(
        comodel_name='club.member.state',
        string='New State',
        required=True,
        domain="[('state_type', 'not in', ('registered', 'deleted'))]",
    )
    start_date = fields.Datetime(
        string='Start Date',
        required=True,
        default=fields.Datetime.now,
    )
    reason = fields.Text(string='Reason')

    def action_confirm(self):
        self.ensure_one()

        member = self.member_id.exists()
        if not member:
            raise UserError(_('The selected member no longer exists.'))

        if self.target_state_id.state_type in self._FORBIDDEN_TARGET_STATE_TYPES:
            raise UserError(
                _('State type %(state_type)s is not allowed as target state via this wizard.')
                % {'state_type': self.target_state_id.state_type}
            )

        member.action_change_state_with_history(
            new_state=self.target_state_id,
            start_date=self.start_date,
            reason=self.reason,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
