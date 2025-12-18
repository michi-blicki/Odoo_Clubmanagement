from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubDepartment(models.Model):
    _name = 'club.department'
    _description = 'Department'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name = fields.Char(string=_("Name"), required=True, tracking=True)
    company_id = fields.Many2one(string=_("Company"), comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id = fields.Many2one(comodel_name='club.club', string=_('Club'), required=True, readonly=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    subclub_id = fields.Many2one(comodel_name='club.subclub', string=_('Sub Club'), tracking=True)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    board_ids = fields.One2many(comodel_name='club.board', inverse_name='department_id', string=_('Boards'), tracking=True)
    pool_ids = fields.One2many(comodel_name='club.pool', inverse_name='department_id', string=_('Pools'), tracking=True)
    pool_count = fields.Integer(string=_('Pool Count'), compute="_compute_pool_count", store=True)
    team_ids = fields.One2many(comodel_name='club.team', inverse_name='department_id', string=_('Teams'), tracking=True)
    team_count = fields.Integer(string=_('Team Count'), compute="_compute_team_count", store=True)
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='department_id', string=_("Roles / Functions"), tracking=True)
    member_ids = fields.Many2many(string=_('Members'), comodel_name='club.member', relation='club_department_member_rel', column1='department_id', column2='member_id', tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids', store=True)
    member_count = fields.Integer(string=_("Member Count"), compute="_compute_member_ids", store=True)
    active = fields.Boolean(default=True)

    price = fields.Monetary(string=_("Price"), compute="_compute_price", store=True, currency_field='currency_id')
    currency_id = fields.Many2one(string=_("Currency"), comodel_name='res.currency', related='company_id.currency_id', readonly=True)
    main_product_id = fields.Many2one(string=_("Main Product"), comodel_name="product.product", required=False)
    main_product_price = fields.Monetary(string=_("Main Product Price"), compute="_compute_main_product_price", store=False, currency_field='currency_id')
    additional_product_ids = fields.One2many(string=_("Additional Products"), comodel_name='club.member.membership.additional.product', inverse_name='membership_id')

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
            member_count = len(dept.member_ids_display)

    @api.depends('main_product_id')
    def _compute_main_product_price(self):
        for record in self:
            record.main_product_price = record.main_product_id.list_price if record.main_product_id else 0.0


    @api.depends('main_product_id', 'additional_product_ids')
    def _compute_price(self):
        for department in self:
            total_price = 0.0
            if department.main_product_id:
                total_price += department.main_product_id.product_tmpl_id.list_price
            if department.additional_product_ids:
                total_price += sum(product.product_tmpl_id.list_price for product in department.additional_product_ids)
            department.price = total_price

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):
        subclub_exists = self.env['club.subclub'].search_count([('active', '=', True)]) > 0

        club = self.env['club.club'].search([], limit=1)
        if not club:
            raise ValidationError(_("Club must be created first"))

        for vals in vals_list:
            if not vals.get('club_id'):
                vals['club_id'] = club.id
            if subclub_exists:
                if not vals.get('subclub_id'):
                    raise ValidationError(_('A subclub exists and must be assigned when creating a new department'))
                else:
                    vals['subclub_id'] = False
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