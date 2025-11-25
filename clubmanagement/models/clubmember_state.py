from odoo import models, fields

class ClubMemberState(models.Model):
    _name = 'club.member.state'
    _description = 'Member Status History'

    member_id = fields.Many2one('club.member', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('joining', 'Joining'),
        ('active', 'active'),
        ('inactive', 'inactive'),
        ('blocked_club', 'blocked_club'),
        ('blocked_official', 'blocked_official'),
        ('left', 'left')
    ], default='pending', required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date()
    reason = fields.Text(required=False)