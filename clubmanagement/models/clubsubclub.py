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
    ]

    name = fields.Char(string=_("Name"), required=True, tracking=True)
    company_id = fields.Many2one(string=_("Company"), comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id = fields.Many2one(comodel_name='club.club', string=_("Parent Club / Association"), required=True, readonly=True, default=lambda self: self.env['club.club'].search([], limit=1).id)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), required=True, help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    board_ids = fields.One2many(comodel_name='club.board', inverse_name='subclub_id', string=_("Board"), tracking=True)
    department_ids = fields.One2many(comodel_name='club.department', inverse_name='subclub_id', string=_("Departments"), tracking=True)
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='subclub_id', string=_("Roles / Functions"), tracking=True)
    member_ids = fields.Many2many(string=_('Members'), comodel_name='club.member', relation='club_subclub_member_rel', column1='subclub_id', column2='member_id', tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids')
    active = fields.Boolean(default=True, tracking=True)

    boards_count = fields.Integer(string=_("No Boards"), compute="_compute_counts")
    departments_count = fields.Integer(string=_("No Departments"), compute="_compute_counts")
    roles_count = fields.Integer(string=_("No Roles"), compute="_compute_counts")
    members_count = fields.Integer(string=_("No Members"), compute="_compute_counts")

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

    ########################
    # PERMISSION CHECK
    ########################




    ########################
    # CREATION HOOK
    ########################

    def create(self, vals_list):

        club = self.env['club.club'].search([], limit=1)
        if not club:
            raise ValidationError(_("Club must be created first"))


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


    ########################
    # DELETION HOOKS
    ########################

    def unlink(self):
        for subclub in self:
            if subclub.board_ids:
                raise ValidationError(
                    _("Please remove or reassign all Boards linked to this Department before deletion")
                )
            if subclub.department_ids:
                raise ValidationError(
                    _("Please remove or reassign all Departments linked to this Department before deletion.")
                )
            # 2. Delete ClubRole (scope_type=subclub and subclub_id=id)
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
