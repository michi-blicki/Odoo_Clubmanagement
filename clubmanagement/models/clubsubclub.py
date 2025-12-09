from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class SubClub(models.Model):
    _name = 'club.subclub'
    _description = 'Sub Club / Sub-Association'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company)
    club_id = fields.Many2one(comodel_name='club.club', string=_("Parent Club / Association"), required=True)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), required=True, help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    board_ids = fields.One2many(comodel_name='club.board', inverse_name='subclub_id', string="Board", tracking=True)
    department_ids = fields.One2many(comodel_name='club.department', inverse_name='subclub_id', string=_("Departments"), tracking=True)
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='subclub_id', string=_("Roles / Functions"), tracking=True)
    member_ids = fields.Many2many(string=_('Members'), comodel_name='club.member', relation='club_subclub_member_rel', column1='subclub_id', column2='member_id', tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids')
    active = fields.Boolean(default=True, tracking=True)

    boards_count = fields.Integer(string=_("No Boards"), compute="_compute_counts")
    departments_count = fields.Integer(string=_("No Departments"), compute="_compute_counts")
    roles_count = fields.Integer(string=_("No Roles"), compute="_compute_counts")
    members_count = fields.Integer(string=_("No Members"), compute="_compute_counts")

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

    def create(self, vals):
        if not vals.get('club_id'):
            raise ValidationError(_("Parent Club must be specified when creating a Sub-Club."))

        new_subclubs = super().create(vals)

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
