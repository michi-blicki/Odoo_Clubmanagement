# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class SubClub(models.Model):
    _name = 'club.subclub'
    _description = 'Sub Club / Sub-Association'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
        'club.custom.field.mixin',
        'club.security.mixin',
    ]

    name                        = fields.Char(string='Name', required=True, tracking=True)
    company_id                  = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id                     = fields.Many2one(string='Parent Club / Association',comodel_name='club.club', required=True, readonly=True)
    hr_department_id            = fields.Many2one(string='HR Department', comodel_name='hr.department', required=True, help='Optional HR department mapping for HR processes', tracking=True)
    account_analytic_account_id = fields.Many2one(string="Account Analytic Account", comodel_name="account.analytic.account")
    sequence                    = fields.Integer(string='Sequence', required=True, default=10)
    board_ids                   = fields.One2many(string='Board', comodel_name='club.board', inverse_name='subclub_id', tracking=True)
    department_ids              = fields.One2many(string='Departments', comodel_name='club.department', inverse_name='subclub_id', tracking=True)
    role_ids                    = fields.One2many(string='Roles / Functions', comodel_name='club.role', inverse_name='subclub_id', tracking=True)
    member_ids                  = fields.Many2many(string='Members', comodel_name='club.member', relation='club_subclub_member_rel', column1='subclub_id', column2='member_id', tracking=True)
    member_ids_display          = fields.Many2many(string='All Members', comodel_name='club.member', compute='_compute_member_ids')
    active                      = fields.Boolean(default=True, tracking=True)

    price                       = fields.Monetary(string="Price", compute="_compute_price", store=True, currency_field='currency_id', readonly=True)
    currency_id                 = fields.Many2one(string="Currency", compute="_compute_price", comodel_name='res.currency', related='company_id.currency_id', readonly=True)
    membership_id               = fields.Many2one(string="Membership", comodel_name="club.member.membership", store=True)
    effective_membership_id     = fields.Many2one(string="Effective Membership", comodel_name="club.member.membership", compute="_compute_effective_membership_id", store=True, readonly=True)

    boards_count                = fields.Integer(string='No Boards', compute="_compute_counts")
    departments_count           = fields.Integer(string='No Departments', compute="_compute_counts")
    roles_count                 = fields.Integer(string='No Roles', compute="_compute_counts")
    members_count               = fields.Integer(string='No Members', compute="_compute_counts")

    custom_field_lines          = fields.Json(string="Custom Fields", compute="_compute_custom_fields")
    registration_mode           = fields.Selection([
                                    ('inherit', 'Inherit'),
                                    ('open', 'Open'),
                                    ('restricted', 'Restricted (Waitlist)'),
                                    ('closed', 'Closed')
                                ], string='Registration Mode', required=True, default='open', tracking=True)
    effective_registration_mode = fields.Selection([
                                    ('open', 'Open'),
                                    ('restricted', 'Restricted (Waitlist)'),
                                    ('closed', 'Closed')
                                ], string='Effective Registration Mode', compute='_compute_effective_registration_mode', store=True, readonly=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.depends('member_ids', 'department_ids.member_ids_display')
    def _compute_member_ids(self):
        for subclub in self:
            direct = subclub.member_ids
            dept_members = subclub.department_ids.mapped('member_ids_display')
            all_members = direct | dept_members
            subclub.member_ids_display = [(6, 0, all_members.ids)]

    @api.depends('board_ids', 'department_ids', 'role_ids', 'member_ids_display')
    def _compute_counts(self):
        for subclub in self:
            subclub.boards_count = len(subclub.board_ids)
            subclub.departments_count = len(subclub.department_ids)
            subclub.roles_count = len(subclub.role_ids)
            subclub.members_count = len(subclub.member_ids_display)

    @api.depends('membership_id')
    def _compute_effective_membership_id(self):
        for subclub in self:
            subclub.effective_membership_id = subclub.membership_id

    @api.depends('registration_mode')
    def _compute_effective_registration_mode(self):
        for subclub in self:
            mode = subclub.registration_mode
            subclub.effective_registration_mode = 'open' if mode == 'inherit' else mode

    @api.depends('effective_membership_id')
    def _compute_price(self):
        for subclub in self:
            price = 0.0
            if subclub.effective_membership_id:
                price = subclub.effective_membership_id.price
                currency = subclub.effective_membership_id.currency_id
            subclub.price = price
            subclub.currency_id = currency.id if price else False


    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):

        #
        #self.env.flush_all()
        #club = self.env['club.club'].search([], limit=1)
        #if not club:
        #    raise ValidationError(_("Club must be created first"))

        self._check_user_action_permissions('create', record=self.env['club.subclub'])
        new_subclubs = super().create(vals_list)

        for new_subclub in new_subclubs:

            self.env['club.log'].log_event(
                scope_type='subclub',
                activity_type='create',
                model=self._name,
                res_id=new_subclub.id,
                res_name=new_subclub.name,
                description=_("Subclub created: %s") % new_subclub.name
            )

        return new_subclubs

    def action_create_default_roles_and_boards(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('subclub_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant', 'admin']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'club_id': self.club_id.id,
                    'scope_type': 'subclub',
                    'subclub_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'SUBCLUB_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        if not self.board_ids:
            board = self.env['club.board'].create({
                'name': _("%s - Executive Board") % self.name,
                'group_type': 'board',
                'club_id': self.club_id.id,
                'scope_type': 'subclub',
                'subclub_id': self.id,
            })

        return {
            'type': "ir.actions.client",
            'tag': 'reload',
        }

    #######################################
    # WRITE HOOK
    #######################################
    def write(self, vals):
        for rec in self:
            rec._check_user_action_permissions('write', record=rec)

        res = super().write(vals)

        # Update custom fields, if available and required
        if 'custom_field_lines' in vals:
            for rec in self:
                rec.write_custom_fields(vals['custom_field_lines'])

        return res

    ########################
    # UNLINK HOOKS
    ########################
    def unlink(self):
        for subclub in self:
            # 1. Perform Security Checks
            if subclub.board_ids:
                raise ValidationError(
                    _("Please remove or reassign all Boards linked to this Department before deletion")
                )
            if subclub.department_ids:
                raise ValidationError(
                    _("Please remove or reassign all Departments linked to this Department before deletion.")
                )

            # 2. Perform Security Check
            self._check_user_action_permissions('unlink', record=subclub)

            # 3. Delete ClubRole (scope_type=subclub and subclub_id=id)
            if subclub.role_ids:
                subclub.role_ids.unlink()
            
            self.env['club.log'].log_event(
                scope_type='subclub',
                activity_type='unlink',
                model=self._name,
                res_id=subclub.id,
                res_name=subclub.name,
                description=_("Subclub deleted: %s") % subclub.name
            )

        return super(SubClub, self).unlink()

    ########################
    # SECURITY MIXIN
    ########################
    @api.model
    def search(self, args, **kwargs):
        if self.env.su or self._context.get('club_security_internal'):
            return super().search(args, **kwargs)

        user = self.env.user
        if not user.has_group('clubmanagement.group_clubmanagement_administrator'):
            scopes = self._get_user_scope_entities(user)
            args = [('id', 'in', scopes['subclub_ids'].ids)] + list(args)
        return super().search(args, **kwargs)