from odoo import models, fields

class ClubMemberMembership(models.Model):
    _name = 'club.member.membership'
    _description = 'Membership History for Members'

    member_id = fields.Many2one('club.member', required=True)
    membership_id = fields.Many2one('club.membership', required=True)
    start_date = fields.Date()
    end_date = fields.Date()
