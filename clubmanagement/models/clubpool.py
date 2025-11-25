from odoo import models, fields

class ClubPool(models.Model):
    _name = 'club.pool'
    _description = 'Pool'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]

    name = fields.Char(required=True)
    department_id = fields.Many2one('club.department', required=True)
    hr_department_id = fields.Many2one('hr.department', string="HR Department", help="Optional HR department mapping for HR processes")
    team_ids = fields.One2many('club.team', 'pool_id', string='Teams')
    active = fields.Boolean(default=True)
    