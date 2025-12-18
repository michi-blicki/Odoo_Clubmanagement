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

    name = fields.Char(string=_("State Name"), required=True)
    code = fields.Char(string=_("Code"), required=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    state_type = fields.Selection([
        ('registered', _('Registered')),
        ('pending', _('Pending')),
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('blocked', _('Blocked')),
        ('archived', _('Archived')),
        ('deleted', _('Deleted'))
    ], required=True, default='registered', string=_("State Type"))
    description = fields.Text(string=_("Description"))
    color = fields.Integer(string=_("Color"))
    active = fields.Boolean(default=True)

    member_ids = fields.One2many(string=_("Members"), comodel_name="club.member", inverse_name="current_state_id")

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()