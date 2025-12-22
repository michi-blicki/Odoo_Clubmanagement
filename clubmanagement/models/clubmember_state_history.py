from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)

class ClubMemberStateHistory(models.Model):
    _name = 'club.member.state.history'
    _description = 'Member State History'
    _order = 'start_date desc, end_date desc, id desc'

    member_id   = fields.Many2one(string='Member', comodel_name='club.member', required=True, ondelete='cascade')
    state_id    = fields.Many2one(string='State', comodel_name='club.member.state', required=True)
    start_date  = fields.Datetime(string='Start Date', required=True, default=fields.Datetime.now)
    end_date    = fields.Datetime(string='End Date', required=False)
    reason      = fields.Text(string='Reason', required=False)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("End Date must be after Start Date."))