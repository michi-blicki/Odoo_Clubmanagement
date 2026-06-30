from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError

import logging
_logger = logging.getLogger(__name__)

class ClubDepartment(models.Model):
    _name = 'club.department'
    _description = 'Department'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
        'club.custom.field.mixin',
        'club.security.mixin',
    ]

    name                        = fields.Char(string='Name', required=True, tracking=True)
    company_id                  = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id                     = fields.Many2one(string='Club', comodel_name='club.club', required=True, readonly=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    subclub_id                  = fields.Many2one(string='Subclub', comodel_name='club.subclub', tracking=True)
    hr_department_id            = fields.Many2one(string='HR Department', comodel_name='hr.department', help='Optional HR department mapping for HR processes', tracking=True)
    account_analytic_account_id = fields.Many2one(string="Account Analytic Account", comodel_name="account.analytic.account")
    sequence                    = fields.Integer(string='Sequence', required=True, default=10)
    board_ids                   = fields.One2many(string='Boards', comodel_name='club.board', inverse_name='department_id', tracking=True)
    pool_ids                    = fields.One2many(string='Pools', comodel_name='club.pool', inverse_name='department_id', tracking=True)
    pool_count                  = fields.Integer(string='Pool Count', compute="_compute_pool_count", store=True)
    team_ids                    = fields.One2many(string='Teams', comodel_name='club.team', inverse_name='department_id', tracking=True)
    team_count                  = fields.Integer(string='Team Count', compute="_compute_team_count", store=True)
    role_ids                    = fields.One2many(string='Roles / Functions', comodel_name='club.role', inverse_name='department_id', tracking=True)
    member_ids                  = fields.Many2many(string='Members', comodel_name='club.member', relation='club_department_member_rel', column1='department_id', column2='member_id', tracking=True)
    member_ids_display          = fields.Many2many(string='All Members', comodel_name='club.member', compute='_compute_member_ids', store=True)
    members_count               = fields.Integer(string="Members Count", compute="_compute_member_ids", store=True)
    waiting_member_count        = fields.Integer(string='Waiting Member Count', compute='_compute_member_state_counters', store=False)
    active_member_count         = fields.Integer(string='Active Member Count', compute='_compute_member_state_counters', store=False)
    active                      = fields.Boolean(default=True)

    price                       = fields.Monetary(string="Price", compute="_compute_price", store=True, currency_field='currency_id', readonly=True)
    currency_id                 = fields.Many2one(string="Currency", compute="_compute_price", comodel_name='res.currency', related='company_id.currency_id', readonly=True)
    membership_id               = fields.Many2one(string="Membership", comodel_name="club.member.membership", store=True)
    effective_membership_id     = fields.Many2one(string="Effective Membership", comodel_name="club.member.membership", compute="_compute_effective_membership_id", store=True, readonly=True)

    custom_field_lines          = fields.Json(string="Custom Fields", compute="_compute_custom_fields")
    registration_mode           = fields.Selection([
                                    ('inherit', 'Inherit'),
                                    ('open', 'Open'),
                                    ('restricted', 'Restricted (Waitlist)'),
                                    ('closed', 'Closed')
                                ], string='Registration Mode', required=True, default='inherit', tracking=True)
    effective_registration_mode = fields.Selection([
                                    ('open', 'Open'),
                                    ('restricted', 'Restricted (Waitlist)'),
                                    ('closed', 'Closed')
                                ], string='Effective Registration Mode', compute='_compute_effective_registration_mode', store=True, readonly=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.depends('pool_ids')
    def _compute_pool_count(self):
        for department in self:
            department.pool_count = len(department.pool_ids)

    @api.depends('team_ids')
    def _compute_team_count(self):
        for department in self:
            department.team_count = len(department.team_ids)

    @api.depends('member_ids', 'pool_ids.member_ids_display', 'team_ids.member_ids_display')
    def _compute_member_ids(self):
        for dept in self:
            direct = dept.member_ids
            team_members = dept.team_ids.mapped('member_ids_display')
            pool_members = dept.pool_ids.mapped('member_ids_display')
            all_members = direct | team_members | pool_members
            dept.member_ids_display = [(6, 0, all_members.ids)]
            members_count = len(dept.member_ids_display)

    @api.depends('member_ids_display.current_state_id')
    def _compute_member_state_counters(self):
        waiting_states = {'registered', 'pending'}
        active_states = {'active', 'inactive', 'blocked'}
        for department in self:
            members = department.member_ids_display
            department.waiting_member_count = len(
                members.filtered(lambda member: member.current_state_id.state_type in waiting_states)
            )
            department.active_member_count = len(
                members.filtered(lambda member: member.current_state_id.state_type in active_states)
            )

    @api.depends('membership_id')
    def _compute_effective_membership_id(self):
        for department in self:
            if department.membership_id:
                department.effective_membership_id = department.membership_id
            elif department.subclub_id and department.subclub_id.membership_id:
                department.effective_membership_id = department.subclub_id.membership_id
            else:
                department.effective_membership_id = False

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

    @api.depends('registration_mode', 'subclub_id.effective_registration_mode')
    def _compute_effective_registration_mode(self):
        for department in self:
            parent_mode = department.subclub_id.effective_registration_mode or 'open'
            modes = [parent_mode]
            if department.registration_mode != 'inherit':
                modes.append(department.registration_mode)
            department.effective_registration_mode = self._merge_registration_modes(modes)

    def _compute_price(self):
        for department in self:
            price = 0.0
            if department.effective_membership_id:
                price = department.effective_membership_id.price
                currency = department.effective_membership_id.currency_id
            department.price = price
            department.currency_id = currency.id if price else False

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):
        subclub_exists = self.env['club.subclub'].search_count([
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ]) > 0

        club = self.env['club.club'].search([('company_id', '=', self.env.company.id)], limit=1)
        if not club:
            club = self.env['club.club'].search([], limit=1)

        for vals in vals_list:
            if not vals.get('club_id'):
                if not club:
                    raise ValidationError(_("Club must be created first"))
                vals['club_id'] = club.id
            if subclub_exists:
                if not vals.get('subclub_id'):
                    raise ValidationError(_('A subclub exists and must be assigned when creating a new department'))
        
        self._check_user_action_permissions('create', record=self.env['club.department'])
        departments = super(ClubDepartment, self).create(vals_list)

        for department in departments:
            self.env['club.log'].log_event(
                scope_type='department',
                activity_type='create',
                model=self._name,
                res_id=department.id,
                res_name=department.name,
                description=_("Department created: %s") % department.name
            )

        return departments

    def action_create_default_roles_and_boards(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('department_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant', 'admin']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'club_id': self.club_id.id,
                    'scope_type': 'department',
                    'department_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'CLUB_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        if not self.board_ids:
            board = self.env['club.board'].create({
                'name': _("%s - Executive Board") % self.name,
                'group_type': 'board',
                'club_id': self.club_id.id,
                'scope_type': 'department',
                'department_id': self.id,
            })

        return {
            'type': "ir.actions.client",
            'tag': 'reload',
        }

    def action_open_waiting_members_list(self):
        self.ensure_one()
        if not self.env.user.has_group('clubmanagement.group_clubmanagement_key_user'):
            raise AccessError(_('You are not allowed to access waiting members for this department.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Waiting Members'),
            'res_model': 'club.member',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('clubmanagement.club_team_department_member_waiting_list_view').id, 'list'),
                (self.env.ref('clubmanagement.club_member_form_view').id, 'form'),
            ],
            'search_view_id': self.env.ref('clubmanagement.club_team_department_member_waiting_search_view').id,
            'domain': [
                ('id', 'in', self.member_ids_display.ids),
                ('current_state_id.state_type', 'in', ['registered', 'pending']),
            ],
            'context': {
                'search_default_group_by_current_state': 1,
            },
        }

    def action_open_active_members_list(self):
        self.ensure_one()
        if not self.env.user.has_group('clubmanagement.group_clubmanagement_key_user'):
            raise AccessError(_('You are not allowed to access active members for this department.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active Members'),
            'res_model': 'club.member',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('clubmanagement.club_team_department_member_active_list_view').id, 'list'),
                (self.env.ref('clubmanagement.club_member_form_view').id, 'form'),
            ],
            'search_view_id': self.env.ref('clubmanagement.club_team_department_member_active_search_view').id,
            'domain': [
                ('id', 'in', self.member_ids_display.ids),
                ('current_state_id.state_type', 'in', ['active', 'inactive', 'blocked']),
            ],
            'context': {
                'search_default_group_by_current_state': 1,
            },
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
    # UNLINK HOOK
    ########################
    def unlink(self):
        for department in self:
            # 1. if pools under this department exists, do not delete this department
            if department.pool_ids:
                raise ValidationError(
                    _("Please remove or reassign all Pools linked to this Department before deletion.")
                )
            if department.team_ids:
                raise ValidationError(
                    _("Please remove or reassign all Teams linked to this Department before deletion.")
                )
            if department.board_ids:
                raise ValidationError(
                    _("Please remove or reassign all Boards linked to this Department before deletion.")
                )

            # 2. Perform security permission check
            self._check_user_action_permissions('unlink', record=department)

            # 3. Delete assigned roles
            if department.role_ids:
                department.role_ids.unlink()

            self.env['club.log'].log_event(
                scope_type='department',
                activity_type='unlink',
                model=self._name,
                res_id=department.id,
                res_name=department.name,
                description=_("Department deleted: %s") % department.name
            )

        return super(ClubDepartment, self).unlink()

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
            dept_ids = scopes['department_ids']
            # Additionally include departments of visible subclubs
            visible_subclubs = scopes['subclub_ids']
            dept_of_subclubs = self.with_context(club_security_internal=True).search([
                ('subclub_id', 'in', visible_subclubs.ids)
            ])
            args = [('id', 'in', (dept_ids | dept_of_subclubs).ids)] + list(args)
        return super().search(args, **kwargs)