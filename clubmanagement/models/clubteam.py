from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubTeam(models.Model):
    _name = 'club.team'
    _description = 'Team'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]
    _group_by_full = {
        'department_id': lambda self, departments, domain, order: self._read_group_department_id(departments, domain, order),
    }

    name = fields.Char(required=True, tracking=True)
    shortname = fields.Char(string=_("Short Name"), required=False, size=5, help=_("Short code, max 5 characters"), tracking=True)
    company_id = fields.Many2one(string=_("Company"), comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id = fields.Many2one(string=_('Club'), comodel_name='club.club', store=True, readonly=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    department_id = fields.Many2one(string=_('Department'), comodel_name='club.department', required=True, tracking=True)
    pool_id = fields.Many2one(string=_('Pool'), comodel_name='club.pool', required=False, tracking=True)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='team_id', string=_("Roles / Functions"))
    member_ids = fields.Many2many(string=_('Members'), comodel_name='club.member', relation='club_team_member_rel', column1='team_id', column2='member_id', tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids', store=True)
    members_count = fields.Integer(string=_("Member Cound"), compute="_compute_member_ids", store=True)
    active = fields.Boolean(default=True, tracking=True)

    price = fields.Monetary(string=_("Price"), compute="_compute_price", store=True, currency_field='currency_id')
    currency_id = fields.Many2one(string=_("Currency"), comodel_name='res.currency', related='company_id.currency_id', readonly=True)
    main_product_id = fields.Many2one(string=_("Main Product"), comodel_name="product.product", required=False)
    main_product_price = fields.Monetary(string=_("Main Product Price"), compute="_compute_main_product_price", store=False, currency_field='currency_id')
    additional_product_ids = fields.One2many(string=_("Additional Products"), comodel_name='club.member.membership.additional.product', inverse_name='membership_id')

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.model
    def _read_group_department_id(self, departments, domain, order):
        return self.env['club.department'].search([('company_id', '=', self.env.company.id)], order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'department_id' in groupby:
            departments = self.env['club.department'].search([('company_id', '=', self.env.company.id)])
            result = [{
                '__domain': [('department_id', '=', department.id), ('company_id', '=', self.env.company.id)],
                'department_id': (department.id, department.name),
                'department_id_count': self.search_count([('department_id', '=', department.id), ('company_id', '=', self.env.company.id)]),
                '__count': self.search_count([('department_id', '=', department.id), ('company_id', '=', self.env.company.id)])
            } for department in departments]
            return result
        return super(ClubTeam, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


    @api.depends('shortname')
    def _check_shortname_length(self):
        for record in self:
            if record.shortname and len(record.shortname) > 5:
                raise ValidationError(_("Short NAme must be at most 5 characters"))


    @api.depends('member_ids')
    def _compute_member_ids(self):
        for team in self:
            team.member_ids_display = [(6, 0, team.member_ids.ids)]
            team.members_count = len(team.member_ids)

    @api.depends('main_product_id')
    def _compute_main_product_price(self):
        for record in self:
            record.main_product_price = record.main_product_id.list_price if record.main_product_id else 0.0


    @api.depends('main_product_id', 'additional_product_ids')
    def _compute_price(self):
        for team in self:
            total_price = 0.0
            if team.main_product_id:
                total_price += team.main_product_id.product_tmpl_id.list_price
            if team.additional_product_ids:
                total_price += sum(product.product_tmpl_id.list_price for product in team.additional_product_ids)
            team.price = total_price

    ########################
    # CREATE HOOK
    ########################
    @api.model_create_multi
    def create(self, vals_list):

        club = self.env['club.club'].search([], limit=1)
        if not club:
            raise ValidationError(_("Club must be created first"))

        for vals in vals_list:
            if not vals.get('club_id'):
                vals['club_id'] = club.id

        teams = super(ClubTeam, self).create(vals_list)

        for team in teams:

            self.env['club.log'].log_event(
                scope_type='team',
                activity_type='create',
                model=self._name,
                res_id=team.id,
                res_name=team.name,
                description=_("Team created: %s") % team.name,
            )

        return teams

    def action_create_default_roles(self):
        self.ensure_one()

        existing_roles = self.env['club.role'].search([('team_id', '=', self.id)])
        new_roles = []
        role_types = ['lead', 'assistant']
        for rt in role_types:
            if not existing_roles.filtered(lambda r: r.role_type == rt):
                role_type_selection = dict(self.env['club.role'].fields_get(allfields=['role_type'])['role_type']['selection'])
                new_roles.append(self.env['club.role'].create({
                    'role_type': rt,
                    'club_id': self.club_id.id,
                    'scope_type': 'team',
                    'team_id': self.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                    'perm_mail': True,
                    'code': f'POOL_{self.name}_{rt}',
                    'name': f"{self.name}: {role_type_selection.get(rt, rt)}",
                }))

        return {
            'type': "ir.actions.client",
            'tag': 'reload',
        }

    ########################
    # UNLINK HOOK
    ########################
    def unlink(self):
        for team in self:
            if team.member_ids:
                raise ValidationError(
                    _("Team members assigned. Team cannot be deleted! Deactivate team instead.")
                )

            if team.role_ids:
                team.role_ids.unlink()

            self.env['club.log'].log_event(
                scope_type='team',
                activity_type='unlink',
                model=self._name,
                res_id=team.id,
                res_name=team.name,
                description=_("Team deleted: %s") % team.name
            )

        return super(ClubTeam, self).unlink()
