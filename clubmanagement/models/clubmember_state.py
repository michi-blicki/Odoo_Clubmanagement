from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class ClubMemberState(models.Model):
    _name = 'club.member.state'
    _description = 'Member Status'
    _order ='sequence, id'
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'State Code must be unique!')
    ]

    name        = fields.Char(string='State Name', required=True)
    code        = fields.Char(string='Code', required=True)
    sequence    = fields.Integer(string='Sequence', required=True, default=10)
    state_type  = fields.Selection([
                        ('registered', 'Registered'),
                        ('pending', 'Pending'),
                        ('active', 'Active'),
                        ('inactive', 'Inactive'),
                        ('blocked', 'Blocked'),
                        ('archived', 'Archived'),
                        ('deleted', 'Deleted')
                    ], required=True, default='registered', string="State Type")
    description = fields.Text(string="Description")
    color       = fields.Integer(string="Color")
    active      = fields.Boolean(default=True)

    member_ids  = fields.One2many(string="Members", comodel_name="club.member", inverse_name="current_state_id")

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()