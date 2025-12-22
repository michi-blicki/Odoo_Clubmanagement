from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from datetime import datetime
import time

import logging
_logger = logging.getLogger(__name__)

class ClubMemberStateRule(models.Model):
    _name = 'club.member.state.rule'
    _description = 'Member State Change Rule'
    _order = 'sequence, id'

    name        = fields.Char(string='Name', required=True)
    sequence    = fields.Integer(string='Sequence', required=True, default=10)
    active      = fields.Boolean(string='Active', required=True, default=True)

    apply_on    = fields.Selection([
                    ('registration', 'On Registration'),
                    ('periodic', 'Periodic Check')
                ], string='Apply Rule on', default='periodic', required=True)
                
    cron_id      = fields.Many2one(string='Associated Cron Job', comodel_name="ir.cron", readonly=True)

    new_state_id = fields.Many2one(string='New State', comodel_name='club.member.state', required=True)

    condition    = fields.Text(string='Python Condition', required=True, default='''
# Available variables:
# - member: club.member record
# - env: Odoo Environment on wich the rule is triggered
# - datetime: datetime module
#

# Return (bool, start_date, end_date) tuple
# bool: True, if the rule should be applied
# start_date: datetime object for the start of the new state (or None for Now)
#             start_date will also be used to end member's current state!
# end_date: datetime object for the end of the new state (or None for open-ended)
return True, None, None
    ''')

    reason          = fields.Text(string='Reason for Change')


    ################################
    # CREATE HOOK
    ################################
    @api.model_create_multi
    def create(self, vals_list):
        rules = super(ClubMemberStateRule, self).create(vals_list)

        for rule in rules:
            if rule.apply_on == 'periodic':
                rule._create_cron_job()

        return rules

    def _create_cron_job(self):
        self.ensure_one()
        if not self.cron_id:
            cron = self.env['ir.cron'].sudo().create({
                'name': f"Check Member State: {self.name}",
                'model_id': self.env['ir.model'].search(['model', '=', self._name], limit=1).id,
                'state': 'code',
                'code': f"model._run_rule({self.id})",
                'interval_number': 1,
                'interval_type': 'days',
                'numbercall': -1,
                'doall': False,
                'active': self.active,
            })
            self.cron_id = cron

    ################################
    # WRITE HOOK
    ################################
    def write(self, vals):
        res = super(ClubMemberStateRule, self).write(vals)

        if 'apply_on' in vals or 'active' in vals:
            for rule in self:
                if rule.apply_on == 'periodic' and rule.active:
                    rule._create_cron_job()
                else:
                    rule._unlink_cron_job()
        return res

    ################################
    # UNLINK HOOK
    ################################
    def unlink(self):
        for rule in self:
            rule._unlink_cron_job()
        return super(ClubMemberStateRule, self).unlink()

    def _unlink_cron_job(self):
        self.ensure_one()
        if self.cron_id:
            self.cron_id.unlink()
            self.cron_id = False

    ################################
    # HELPER FUNCTIONS
    ################################
    def _run_rule(self, rule_id):
        rule = self.browse(rule_id)
        if rule.exists() and rule.active:
            members = self.env['club.member'].search([])
            rule._apply_rule(members)

    def _apply_rule(self, members):
        self.ensure_one()
        for member in members:
            try:
                result = eval(self.condition, {
                    'member': member, 
                    'env': self.env,
                    'datetime': datetime
                })
                if isinstance(result, tuple) and len(result) == 3:
                    apply_rule, start_date, end_date = result
                    if apply_rule:
                        self._change_member_state(member, self.new_state_id, self.reason, start_date, end_date)
                else:
                    _logger.warning(f"Invalid return format for rule {self.name}")
            except Exception as e:
                _logger.error(f"Error evaluating rule {self.name} for member {member.name}: {str(e)}")


    def _change_member_state(self, member, new_state, reason, start_date=None, end_date=None):
        if member.current_state_id != new_state:
            now = fields.Datetime.now()
            start_date = start_date or now
            
            # End the current state
            current_state_history = self.env['club.member.state.history'].search([
                ('member_id', '=', member.id),
                ('end_date', '=', False)
            ], limit=1)
            
            if current_state_history:
                current_state_history.write({
                    'end_date': start_date,
                })

            # Create new state history entry
            self.env['club.member.state.history'].create({
                'member_id': member.id,
                'state_id': new_state.id,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason,
            })

            # The current_state_id will be automatically updated due to the compute method

            # Log the state change
            self.env['club.log'].log_event(
                scope_type='member',
                activity_type='state_change',
                model='club.member',
                res_id=member.id,
                res_name=member.display_name,
                description=_("Member state changed from '%(old_state)s' to '%(new_state)s'") % {
                    'old_state': member.current_state_id.name,
                    'new_state': new_state.name,
                },
                old_value=str({
                    'state_id': member.current_state_id.id,
                    'state_name': member.current_state_id.name,
                }),
                new_value=str({
                    'state_id': new_state.id,
                    'state_name': new_state.name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'reason': reason,
                })
            )

    @api.model
    def _apply_registratoin_rules(self, members):
        rules = self.search([('active', '=', True), ('apply_on', '=', 'registration')])

        if rules:
            for rule in rules:
                rule._apply_rule(members)

        else:
            registered_state = self.env['club.member.state'].search([('state_type', '=', 'registered')], limit=1)
            if registered_state:
                for member in members:
                    self.env['club.member.state.history'].create({
                        'member_id': member.id,
                        'state_id': registered_state.id,
                        'start_date': fields.Date.today(),
                    })
            else:
                raise UserError(_('Club Member State not configured. Please configure at least one state with type "registered"'))