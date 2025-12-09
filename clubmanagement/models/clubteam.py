from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ClubTeam(models.Model):
    _name = 'club.team'
    _description = 'Team'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'club.log.mixin',
    ]

    name = fields.Char(required=True, tracking=True)
    shortname = fields.Char(string=_("Short Name"), required=False, size=5, help=_("Short code, max 5 characters"), tracking=True)
    club_id = fields.Many2one(string=_('Club'), comodel_name='club.club', ondelete='restrict', required=True, readonly=True)
    department_id = fields.Many2one(string=_('Department'), comodel_name='club.department', required=True, tracking=True)
    pool_id = fields.Many2one(string=_('Pool'), comodel_name='club.pool', required=False, tracking=True)
    hr_department_id = fields.Many2one(comodel_name='hr.department', string=_("HR Department"), help=_("Optional HR department mapping for HR processes"), tracking=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    role_ids = fields.One2many(comodel_name='club.role', inverse_name='team_id', string=_("Roles / Functions"))
    member_ids = fields.Many2many(string=_('Members'), comodel_name='club.member', relation='club_team_member_rel', column1='team_id', column2='member_id', tracking=True)
    member_ids_display = fields.Many2many(string=_('All Members'), comodel_name='club.member', compute='_compute_member_ids', store=True)
    members_count = fields.Integer(string=_("Member Cound"), compute="_compute_member_ids", store=True)
    active = fields.Boolean(default=True, tracking=True)

    @api.depends('shortname')
    def _check_shortname_length(self):
        for record in self:
            if record.shortname and len(record.shortname) > 5:
                raise ValidationError(_("Short NAme must be at most 5 characters"))


    @api.depends('member_ids')
    def _compute_member_ids(self):
        for team in self:
            team.member_ids_display = [(6, 0, team.member_ids.ids)]
            team.member_count = len(team.member_ids)

    ########################
    # CREATE HOOK
    ########################
    def create(self, vals):
        teams = super(ClubTeam, self).create(vals)

        for team in teams:

            self.env['club.log'].log_event(
                scope_type='team',
                activity_type='create',
                model=self._name,
                res_id=team.id,
                res_name=team.name,
                description=_("Team created: %s") % team.name,
            )

        return team

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
