from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ClubTeam(models.Model):
    _name = 'club.team'
    _description = 'Team'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True)
    pool_id = fields.Many2one('club.pool', required=True)
    hr_department_id = fields.Many2one('hr.department', string="HR Department", help="Optional HR department mapping for HR processes")
    member_ids = fields.Many2many('club.member', string='Members')
    active = fields.Boolean(default=True)

    def unlink(self):
        for team in self:
            if team.member_ids:
                raise ValidationError(
                    "Team members assigned. Team cannot be deleted! Deactivate team instead."
                )
        return super(ClubTeam, self).unlink()