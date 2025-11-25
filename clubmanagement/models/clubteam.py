from odoo import models, fields

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
    member_ids = fields.Many2many('club.team.member', string='Members')
    active = fields.Boolean(default=True)