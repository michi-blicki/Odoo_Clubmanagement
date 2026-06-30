# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import email_split, html_escape

import logging

_logger = logging.getLogger(__name__)


class ClubMemberMailWizard(models.TransientModel):
    _name = 'club.member.mail.wizard'
    _description = 'Club Member Mail Wizard'

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('preview', 'Preview'),
            ('done', 'Done'),
        ],
        default='draft',
        readonly=True,
    )

    target_model = fields.Char(string='Target Model', readonly=True)
    target_record_count = fields.Integer(string='Target Records', readonly=True)
    member_count = fields.Integer(string='Resolved Members', readonly=True)
    target_member_ids = fields.Many2many(comodel_name='club.member', string='Resolved Members (Internal)', readonly=True)

    subject = fields.Char(string='Subject', required=True)
    body_text = fields.Html(string='Message', required=True, sanitize=True)
    scheduled_date = fields.Datetime(string='Scheduled Date')

    line_ids = fields.One2many(
        comodel_name='club.member.mail.wizard.line',
        inverse_name='wizard_id',
        string='Dispatch Log',
        readonly=True,
    )

    queued_count = fields.Integer(string='Queued', compute='_compute_line_stats', store=False)
    skipped_count = fields.Integer(string='Skipped', compute='_compute_line_stats', store=False)
    failed_count = fields.Integer(string='Failed', compute='_compute_line_stats', store=False)
    result_summary_html = fields.Html(string='Result Summary', compute='_compute_result_summary_html', sanitize=True, store=False)

    preview_member_id = fields.Many2one(comodel_name='club.member', string='Preview Member', readonly=True)
    preview_recipient_email = fields.Char(string='Preview Recipient', readonly=True)
    preview_email_from = fields.Char(string='Preview Sender', readonly=True)
    preview_subject = fields.Char(string='Preview Subject', readonly=True)
    preview_body_html = fields.Html(string='Preview Body', readonly=True, sanitize=True)

    @api.depends('line_ids.status')
    def _compute_line_stats(self):
        for wizard in self:
            queued = 0
            skipped = 0
            failed = 0
            for line in wizard.line_ids:
                if line.status == 'queued':
                    queued += 1
                elif line.status == 'skipped':
                    skipped += 1
                elif line.status == 'failed':
                    failed += 1
            wizard.queued_count = queued
            wizard.skipped_count = skipped
            wizard.failed_count = failed

    @api.depends('state', 'queued_count', 'skipped_count', 'failed_count', 'member_count', 'target_model', 'target_record_count')
    def _compute_result_summary_html(self):
        for wizard in self:
            if wizard.state != 'done':
                wizard.result_summary_html = False
                continue

            status_label = _('Completed successfully') if wizard.failed_count == 0 else _('Completed with errors')
            model_label = wizard.target_model or _('Unknown target')
            wizard.result_summary_html = (
                '<div style="padding:8px 0;">'
                '<div><strong>%s</strong></div>'
                '<div>%s: <strong>%s</strong> | %s: <strong>%s</strong> | %s: <strong>%s</strong></div>'
                '<div>%s: <strong>%s</strong> | %s: <strong>%s</strong> | %s: <strong>%s</strong></div>'
                '</div>'
            ) % (
                html_escape(status_label),
                html_escape(_('Queued')),
                wizard.queued_count,
                html_escape(_('Skipped')),
                wizard.skipped_count,
                html_escape(_('Failed')),
                wizard.failed_count,
                html_escape(_('Target model')),
                html_escape(model_label),
                html_escape(_('Target records')),
                wizard.target_record_count,
                html_escape(_('Resolved members')),
                wizard.member_count,
            )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        self._ensure_key_user_permissions()

        active_model = self.env.context.get('active_model')
        active_ids = self._active_ids_from_context()

        members = self._resolve_target_members(active_model, active_ids)

        values.update({
            'target_model': active_model or False,
            'target_record_count': len(active_ids),
            'member_count': len(members),
            'target_member_ids': [(6, 0, members.ids)],
        })
        return values

    @api.model
    def _active_ids_from_context(self):
        active_ids = self.env.context.get('active_ids') or []
        active_id = self.env.context.get('active_id')
        if active_id and active_id not in active_ids:
            active_ids = [active_id] + list(active_ids)
        return list(dict.fromkeys(active_ids))

    @api.model
    def _ensure_key_user_permissions(self):
        if self.env.user.has_group('clubmanagement.group_clubmanagement_key_user'):
            return
        if self.env.user.has_group('clubmanagement.group_clubmanagement_administrator'):
            return
        raise AccessError(_('You are not allowed to use the member mail wizard.'))

    @api.model
    def _allowed_target_models(self):
        return {
            'club.member',
            'club.team',
            'club.pool',
            'club.department',
            'club.subclub',
        }

    @api.model
    def _resolve_target_members(self, active_model, active_ids):
        if active_model not in self._allowed_target_models():
            return self.env['club.member']
        if not active_ids:
            return self.env['club.member']

        records = self.env[active_model].browse(active_ids).exists()

        if active_model == 'club.member':
            members = records
        else:
            members = records.mapped('member_ids_display')

        return members.exists()

    def _resolve_members_for_dispatch(self):
        self.ensure_one()
        active_model = self.env.context.get('active_model')
        active_ids = self._active_ids_from_context()
        members = self._resolve_target_members(active_model, active_ids)

        # After preview, the wizard can be reopened without original active_ids.
        if not members and self.target_member_ids:
            members = self.target_member_ids.exists()
            active_model = self.target_model

        return active_model, active_ids, members

    @api.model
    def _get_dispatch_template(self):
        template = self.env.ref('clubmanagement.mail_template_member_manual_dispatch', raise_if_not_found=False)
        if not template:
            raise UserError(_('Mail template clubmanagement.mail_template_member_manual_dispatch was not found.'))
        return template

    @api.model
    def _resolve_sender_email_from(self):
        user_email = (self.env.user.partner_id.email or '').strip()
        if user_email:
            return user_email

        company_email = (self.env.company.email or '').strip()
        if company_email:
            return company_email

        return False

    @api.model
    def _resolve_member_recipient(self, member):
        for field_name in ('email', 'email2', 'email_work'):
            field_value = getattr(member, field_name, False)
            if not field_value:
                continue
            split_addresses = email_split(field_value)
            if split_addresses:
                return split_addresses[0].strip().lower()
        return False

    def _build_template_context(self):
        self.ensure_one()
        return {
            'club_manual_body_html': self.body_text or '',
            'club_manual_generated_at': fields.Datetime.now(),
            'club_manual_subject': self.subject,
        }

    @api.model
    def _render_template_for_member(self, template, member_id, template_ctx):
        rendered = template.with_context(**template_ctx)._generate_template(
            [member_id],
            ('subject', 'body_html', 'email_from', 'email_to'),
        )
        return rendered.get(member_id, {})

    def _pick_preview_member(self, members):
        self.ensure_one()
        for member in members:
            recipient = self._resolve_member_recipient(member)
            if recipient:
                return member, recipient
        if members:
            return members[0], False
        return self.env['club.member'], False

    def action_preview(self):
        self.ensure_one()
        self._ensure_key_user_permissions()

        active_model, active_ids, members = self._resolve_members_for_dispatch()

        if not members:
            raise UserError(_('No members were resolved for this dispatch context.'))

        preview_member, preview_recipient = self._pick_preview_member(members)
        if not preview_member:
            raise UserError(_('No preview member could be resolved.'))

        template = self._get_dispatch_template()
        template_ctx = self._build_template_context()
        rendered_values = self._render_template_for_member(template, preview_member.id, template_ctx)

        preview_email_from = self._resolve_sender_email_from() or rendered_values.get('email_from') or False
        preview_subject = rendered_values.get('subject') or self.subject
        preview_body_html = rendered_values.get('body_html') or ''

        self.write({
            'state': 'preview',
            'target_model': active_model or False,
            'target_record_count': len(active_ids) if active_ids else self.target_record_count,
            'member_count': len(members),
            'target_member_ids': [(6, 0, members.ids)],
            'preview_member_id': preview_member.id,
            'preview_recipient_email': preview_recipient,
            'preview_email_from': preview_email_from,
            'preview_subject': preview_subject,
            'preview_body_html': preview_body_html,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Mail Dispatch'),
            'res_model': 'club.member.mail.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _log_dispatch(self, member, activity_type, description):
        self.env['club.log'].log_event(
            scope_type='member',
            activity_type=activity_type,
            model='club.member',
            res_id=member.id,
            res_name=member.display_name,
            description=description,
        )

    def action_send(self):
        self.ensure_one()
        self._ensure_key_user_permissions()

        if self.state != 'preview':
            raise UserError(_('Please generate a preview before queueing emails.'))

        active_model, active_ids, members = self._resolve_members_for_dispatch()

        if not members:
            raise UserError(_('No members were resolved for this dispatch context.'))

        sender_email = self._resolve_sender_email_from()
        template = self._get_dispatch_template()

        template_ctx = self._build_template_context()

        seen_recipients = set()
        line_commands = [(5, 0, 0)]

        for member in members:
            recipient = self._resolve_member_recipient(member)
            if not recipient:
                reason = _('Skipped: missing recipient address on email, email2 and email_work.')
                line_commands.append((0, 0, {
                    'member_id': member.id,
                    'status': 'skipped',
                    'reason': reason,
                }))
                self._log_dispatch(member, 'system_action', reason)
                continue

            if recipient in seen_recipients:
                reason = _('Skipped: duplicate recipient address in this dispatch run (%s).') % recipient
                line_commands.append((0, 0, {
                    'member_id': member.id,
                    'recipient_email': recipient,
                    'status': 'skipped',
                    'reason': reason,
                }))
                self._log_dispatch(member, 'system_action', reason)
                continue

            seen_recipients.add(recipient)

            email_values = {
                'email_to': recipient,
                'subject': self.subject,
            }
            if self.scheduled_date:
                email_values['scheduled_date'] = self.scheduled_date
            if sender_email:
                email_values['email_from'] = sender_email

            try:
                mail_id = template.with_context(**template_ctx).send_mail(
                    member.id,
                    force_send=False,
                    email_values=email_values,
                )
                reason = _('Queued successfully.')
                line_commands.append((0, 0, {
                    'member_id': member.id,
                    'recipient_email': recipient,
                    'status': 'queued',
                    'mail_mail_id': mail_id,
                    'reason': reason,
                }))
                self._log_dispatch(member, 'system_action', _('Member mail queued to %s.') % recipient)
            except Exception as exc:
                _logger.exception('Failed to queue member mail for member %s', member.id)
                reason = _('Failed while queueing mail: %s') % str(exc)
                line_commands.append((0, 0, {
                    'member_id': member.id,
                    'recipient_email': recipient,
                    'status': 'failed',
                    'reason': reason,
                }))
                self._log_dispatch(member, 'system_action', reason)

        self.write({
            'line_ids': line_commands,
            'state': 'done',
            'target_model': active_model or False,
            'target_record_count': len(active_ids) if active_ids else self.target_record_count,
            'member_count': len(members),
            'target_member_ids': [(6, 0, members.ids)],
            'preview_member_id': False,
            'preview_recipient_email': False,
            'preview_email_from': False,
            'preview_subject': False,
            'preview_body_html': False,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Mail Dispatch'),
            'res_model': 'club.member.mail.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class ClubMemberMailWizardLine(models.TransientModel):
    _name = 'club.member.mail.wizard.line'
    _description = 'Club Member Mail Wizard Line'

    wizard_id = fields.Many2one(
        comodel_name='club.member.mail.wizard',
        required=True,
        ondelete='cascade',
    )
    member_id = fields.Many2one(comodel_name='club.member', string='Member', required=True, readonly=True)
    recipient_email = fields.Char(string='Recipient', readonly=True)
    status = fields.Selection(
        selection=[
            ('queued', 'Queued'),
            ('skipped', 'Skipped'),
            ('failed', 'Failed'),
        ],
        required=True,
        readonly=True,
    )
    reason = fields.Text(string='Message', readonly=True)
    mail_mail_id = fields.Many2one(comodel_name='mail.mail', string='Queued Mail', readonly=True)
