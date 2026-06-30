from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
from odoo.tools import email_split
from odoo.tools import safe_eval as safe_eval_tools
from odoo.tools.safe_eval import safe_eval

import traceback

import logging

_logger = logging.getLogger(__name__)


class ClubMemberStateRule(models.Model):
    _name = 'club.member.state.rule'
    _description = 'Member State Change Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    active = fields.Boolean(string='Active', required=True, default=True)

    apply_on = fields.Selection(
        [
            ('registration', 'On Registration'),
            ('periodic', 'Periodic Check'),
        ],
        string='Apply Rule on',
        default='periodic',
        required=True,
    )

    cron_id = fields.Many2one(string='Associated Cron Job', comodel_name='ir.cron', readonly=True)

    condition = fields.Text(
        string='Python Condition',
        required=True,
        default='''
# Available variables:
# - member: club.member record
# - env: Odoo Environment on which the rule is triggered
# - datetime: datetime module
# - date: date module
# - time: time module
# - rule: current club.member.state.rule
# - result: dict for passing temporary values

# Return bool: True if the rule should be applied
member.active is True
    ''',
    )

    action_code = fields.Text(
        string='Python Action Code',
        required=True,
        default='''
# Execute your action here. Available variables:
# - member, env, rule, datetime, date, time, result, log

# Example: set member state to pending
# pending = env['club.member.state'].search([('state_type', '=', 'pending')], limit=1)
# if pending:
#     env['club.member.state.rule']._change_member_state(
#         member,
#         pending,
#         'State set by club.member.state.rule',
#     )
pass
    ''',
    )

    stop_processing_on_match = fields.Boolean(string='Stop Processing On Match', default=False)
    continue_on_error = fields.Boolean(string='Continue On Error', default=True)
    member_domain = fields.Text(string='Member Domain', default='[]')
    execution_note = fields.Text(string='Last Execution Note', readonly=True, copy=False)
    error_notify_member_id = fields.Many2one(
        string='Error Notify Member',
        comodel_name='club.member',
        help='Optional member to notify when rule processing fails and Continue On Error is disabled.',
    )

    ################################
    # CREATE HOOK
    ################################
    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)

        for rule in rules:
            if rule.apply_on == 'periodic':
                rule._create_cron_job()

        return rules

    def _create_cron_job(self):
        self.ensure_one()
        if not self.cron_id:
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1).id
            cron = self.env['ir.cron'].sudo().create(
                {
                    'name': f'Check Member State: {self.name}',
                    'model_id': model_id,
                    'state': 'code',
                    'code': f'model._run_rule({self.id})',
                    'interval_number': 1,
                    'interval_type': 'days',
                    'numbercall': -1,
                    'doall': False,
                    'active': self.active,
                }
            )
            self.cron_id = cron

    ################################
    # WRITE HOOK
    ################################
    def write(self, vals):
        res = super().write(vals)

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
        return super().unlink()

    def _unlink_cron_job(self):
        self.ensure_one()
        if self.cron_id:
            self.cron_id.unlink()
            self.cron_id = False

    ################################
    # EVAL / ERROR / LOG HELPERS
    ################################
    @api.model
    def _get_error_mail_template(self):
        return self.env.ref('clubmanagement.mail_template_club_member_state_rule_error', raise_if_not_found=False)

    def _collect_error_notify_recipients(self):
        self.ensure_one()
        notify_member = self.error_notify_member_id
        if not notify_member:
            return []

        recipients = []
        for field_name in ('email', 'email2', 'email_work'):
            value = getattr(notify_member, field_name, False)
            if value:
                recipients.extend(email_split(value))

        deduplicated = []
        seen = set()
        for recipient in recipients:
            normalized = (recipient or '').strip().lower()
            if not normalized or normalized in seen:
                continue
            deduplicated.append(normalized)
            seen.add(normalized)
        return deduplicated

    def _notify_rule_error(self, member, exc):
        self.ensure_one()
        if not self.error_notify_member_id:
            return

        recipients = self._collect_error_notify_recipients()
        if not recipients:
            _logger.warning(
                'Rule %s error notification skipped: no recipient e-mails found on notify member %s.',
                self.id,
                self.error_notify_member_id.id,
            )
            return

        template = self._get_error_mail_template()
        if not template:
            _logger.warning('Rule %s error notification skipped: mail template not found.', self.id)
            return

        trace = traceback.format_exc() if isinstance(exc, Exception) else str(exc)
        ctx = {
            'club_rule_error_member_name': member.display_name,
            'club_rule_error_member_id': member.id,
            'club_rule_error_message': str(exc),
            'club_rule_error_trace': trace,
        }
        template.with_context(**ctx).send_mail(
            self.id,
            force_send=False,
            email_values={'email_to': ','.join(recipients)},
        )

    @api.model
    def _format_execution_note(self, trigger, stats):
        return (
            'Trigger: %(trigger)s | Checked: %(checked)s | Matched: %(matched)s | '
            'Actions: %(actions)s | Errors: %(errors)s'
        ) % {
            'trigger': trigger,
            'checked': stats.get('checked', 0),
            'matched': stats.get('matched', 0),
            'actions': stats.get('actions', 0),
            'errors': stats.get('errors', 0),
        }

    @api.model
    def _safe_member_domain(self, member_domain):
        expression = (member_domain or '[]').strip() or '[]'
        parsed = safe_eval(
            expression,
            {
                'datetime': safe_eval_tools.datetime,
                'date': safe_eval_tools.datetime.date,
                'time': safe_eval_tools.time,
            },
            mode='eval',
        )
        if not isinstance(parsed, (list, tuple)):
            raise ValidationError(_('Member domain must evaluate to a list/tuple domain expression.'))
        return list(parsed)

    def _get_safe_eval_context(self, member, eval_result=None):
        self.ensure_one()
        result_bucket = eval_result if isinstance(eval_result, dict) else {}

        def _log(message, level='info'):
            log_message = (
                'Rule %(rule)s (id=%(rule_id)s) | Member %(member)s (id=%(member_id)s) | %(msg)s'
            ) % {
                'rule': self.name,
                'rule_id': self.id,
                'member': member.display_name,
                'member_id': member.id,
                'msg': message,
            }
            level_name = (level or 'info').lower()
            if level_name == 'error':
                _logger.error(log_message)
            elif level_name == 'warning':
                _logger.warning(log_message)
            else:
                _logger.info(log_message)

        return {
            'env': self.env,
            'member': member,
            'rule': self,
            'datetime': safe_eval_tools.datetime,
            'date': safe_eval_tools.datetime.date,
            'time': safe_eval_tools.time,
            'result': result_bucket,
            'log': _log,
        }

    def _log_action_execution(self, member, eval_result):
        self.ensure_one()
        self.env['club.log'].log_event(
            scope_type='member',
            activity_type='system_action',
            model='club.member.state.rule',
            res_id=self.id,
            res_name=self.display_name,
            description=_('Rule action executed for member %s') % member.display_name,
            new_value=str(
                {
                    'rule_id': self.id,
                    'rule_name': self.name,
                    'member_id': member.id,
                    'member_name': member.display_name,
                    'aux': eval_result.get('aux') if isinstance(eval_result, dict) else {},
                }
            ),
        )

    ################################
    # RULE PROCESSING
    ################################
    def _eval_condition(self, member):
        self.ensure_one()
        aux_bucket = {}
        eval_context = self._get_safe_eval_context(member, aux_bucket)
        try:
            condition_result = safe_eval(self.condition or 'False', eval_context, mode='eval')
        except Exception as exc:
            raise ValidationError(
                _("Error evaluating condition for rule '%(rule)s' on member '%(member)s': %(error)s")
                % {
                    'rule': self.name,
                    'member': member.display_name,
                    'error': str(exc),
                }
            ) from exc

        if not isinstance(condition_result, bool):
            raise ValidationError(
                _("Condition for rule '%(rule)s' must return bool, got '%(type)s'.")
                % {
                    'rule': self.name,
                    'type': type(condition_result).__name__,
                }
            )

        return {
            'matched': condition_result,
            'aux': aux_bucket,
        }

    def _execute_action_code(self, member, eval_result):
        self.ensure_one()
        eval_context = self._get_safe_eval_context(member, (eval_result or {}).get('aux'))
        try:
            safe_eval(self.action_code or 'pass', eval_context, mode='exec', nocopy=True)
        except MissingError as exc:
            _logger.warning(
                "Rule %s action skipped for member %s due to missing linked record: %s",
                self.id,
                member.id,
                exc,
            )
            return
        self._log_action_execution(member, eval_result or {})

    def _execute_match_effects(self, member, eval_result):
        self.ensure_one()
        self._execute_action_code(member, eval_result)

    def _process_rule_for_member(self, member):
        self.ensure_one()
        try:
            eval_result = self._eval_condition(member)
            if not eval_result.get('matched'):
                return {'matched': False, 'stopped': False, 'error': False}

            self._execute_match_effects(member, eval_result)
            return {
                'matched': True,
                'stopped': bool(self.stop_processing_on_match),
                'error': False,
            }
        except Exception as exc:
            _logger.exception('Error while processing rule %s for member %s.', self.id, member.id)
            if not self.continue_on_error:
                try:
                    self._notify_rule_error(member, exc)
                except Exception:
                    _logger.exception(
                        'Failed to send error notification for rule %s and member %s.',
                        self.id,
                        member.id,
                    )
            return {
                'matched': False,
                'stopped': bool(not self.continue_on_error),
                'error': str(exc),
            }

    def _apply_rule(self, members):
        self.ensure_one()
        domain = self._safe_member_domain(self.member_domain)
        candidate_members = members
        if domain:
            candidate_members = self.env['club.member'].search([('id', 'in', members.ids)] + domain)

        stats = {
            'checked': 0,
            'matched': 0,
            'actions': 0,
            'errors': 0,
        }

        for member in candidate_members:
            stats['checked'] += 1
            result = self._process_rule_for_member(member)
            if result.get('matched'):
                stats['matched'] += 1
                stats['actions'] += 1
            if result.get('error'):
                stats['errors'] += 1

        return stats

    def _simulate_rule_for_member(self, member):
        self.ensure_one()
        try:
            eval_result = self._eval_condition(member)
            return {
                'matched': bool(eval_result.get('matched')),
                'error': False,
                'would_execute_action': bool(eval_result.get('matched')),
            }
        except Exception as exc:
            return {
                'matched': False,
                'error': str(exc),
                'would_execute_action': False,
            }

    def _run_rule(self, rule_id):
        rule = self.browse(rule_id)
        if not (rule.exists() and rule.active):
            return False

        members = self.env['club.member'].search([])
        stats = rule._apply_rule(members)
        note = rule._format_execution_note('periodic', stats)
        rule.write({'execution_note': note})
        return stats

    def _run_dry_run(self, max_members=200):
        self.ensure_one()
        member_domain = self._safe_member_domain(self.member_domain)
        candidate_members = self.env['club.member'].search(member_domain, limit=max_members)
        results = []
        for member in candidate_members:
            simulation = self._simulate_rule_for_member(member)
            results.append(
                {
                    'member_id': member.id,
                    'member_name': member.display_name,
                    'matched': simulation.get('matched', False),
                    'would_execute_action': simulation.get('would_execute_action', False),
                    'error': simulation.get('error') or False,
                }
            )
        return results

    def action_open_dry_run_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rule Dry Run'),
            'res_model': 'club.member.state.rule.dry.run.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rule_ids': [(6, 0, self.ids)],
            },
        }

    ################################
    # EXISTING HELPER FUNCTIONS
    ################################
    @api.model
    def _merge_registration_modes(self, modes):
        rank = {
            'open': 1,
            'restricted': 2,
            'closed': 3,
        }
        valid_modes = [m for m in modes if m in rank]
        if not valid_modes:
            return 'open'
        return sorted(valid_modes, key=lambda m: rank[m], reverse=True)[0]

    @api.model
    def _get_member_effective_registration_mode(self, member):
        modes = ['open']
        modes.extend(member.subclub_ids.mapped('effective_registration_mode'))
        modes.extend(member.department_ids.mapped('effective_registration_mode'))
        modes.extend(member.pool_ids.mapped('effective_registration_mode'))
        modes.extend(member.team_ids.mapped('effective_registration_mode'))
        return self._merge_registration_modes(modes)

    @api.model
    def _apply_registration_mode_steering_rule(self, members):
        pending_state = self.env['club.member.state'].search([('state_type', '=', 'pending')], limit=1)
        blocked_state = self.env['club.member.state'].search([('state_type', '=', 'blocked')], limit=1)

        for member in members:
            mode = self._get_member_effective_registration_mode(member)
            if mode == 'restricted' and pending_state:
                self._change_member_state(
                    member,
                    pending_state,
                    _('Registration mode is restricted. Member moved to waiting list.'),
                )
            elif mode == 'closed' and blocked_state:
                self._change_member_state(
                    member,
                    blocked_state,
                    _('Registration mode is closed. Registration is blocked.'),
                )
            elif mode == 'closed' and not blocked_state:
                _logger.warning(
                    "Registration mode is 'closed' for member %s, but no blocked state is configured.",
                    member.id,
                )

    def _change_member_state(self, member, new_state, reason, start_date=None, end_date=None):
        if not new_state or member.current_state_id == new_state:
            return

        now = fields.Datetime.now()
        start_date = start_date or now

        current_state_history = self.env['club.member.state.history'].search(
            [
                ('member_id', '=', member.id),
                ('end_date', '=', False),
            ],
            limit=1,
        )

        if current_state_history:
            current_state_history.write({'end_date': start_date})

        self.env['club.member.state.history'].create(
            {
                'member_id': member.id,
                'state_id': new_state.id,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason,
            }
        )

        self.env['club.log'].log_event(
            scope_type='member',
            activity_type='state_change',
            model='club.member',
            res_id=member.id,
            res_name=member.display_name,
            description=_("Member state changed from '%(old_state)s' to '%(new_state)s'")
            % {
                'old_state': member.current_state_id.name,
                'new_state': new_state.name,
            },
            old_value=str(
                {
                    'state_id': member.current_state_id.id,
                    'state_name': member.current_state_id.name,
                }
            ),
            new_value=str(
                {
                    'state_id': new_state.id,
                    'state_name': new_state.name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'reason': reason,
                }
            ),
        )

    @api.model
    def _apply_registration_rules(self, members):
        """
        Initialize club.member.state.history for given members:
        1. Ensure that a 'registered' state exists.
        2. Create missing 'registered' history entries.
        3. Apply active rules that apply_on='registration'.
        """
        state_model = self.env['club.member.state']
        state_history_model = self.env['club.member.state.history']

        registered_state = state_model.search([('state_type', '=', 'registered')], limit=1)
        if not registered_state:
            raise UserError(_("No Club Member State of type 'registered' configured. Please inform Administrator"))

        existing_histories = state_history_model.search(
            [
                ('member_id', 'in', members.ids),
                ('state_id.state_type', '=', 'registered'),
            ]
        )
        existing_member_ids = set(existing_histories.mapped('member_id').ids)

        for member in members:
            if member.id not in existing_member_ids:
                state_history_model.create(
                    {
                        'member_id': member.id,
                        'state_id': registered_state.id,
                        'start_date': fields.Date.today(),
                    }
                )

        self._apply_registration_mode_steering_rule(members)

        rules = self.search(
            [
                ('active', '=', True),
                ('apply_on', '=', 'registration'),
            ],
            order='sequence,id',
        )

        stats = {
            'checked': 0,
            'matched': 0,
            'actions': 0,
            'errors': 0,
        }
        stopped_member_ids = set()

        for member in members:
            for rule in rules:
                if member.id in stopped_member_ids:
                    break

                domain = rule._safe_member_domain(rule.member_domain)
                if domain:
                    in_scope = bool(self.env['club.member'].search_count([('id', '=', member.id)] + domain))
                    if not in_scope:
                        continue

                stats['checked'] += 1
                result = rule._process_rule_for_member(member)
                if result.get('matched'):
                    stats['matched'] += 1
                    stats['actions'] += 1
                if result.get('error'):
                    stats['errors'] += 1
                if result.get('stopped'):
                    stopped_member_ids.add(member.id)

        note = self._format_execution_note('registration', stats)
        rules.write({'execution_note': note})
        return stats

    @api.model
    def _apply_registratoin_rules(self, members):
        """Backward-compatible alias. Use _apply_registration_rules instead."""
        return self._apply_registration_rules(members)
