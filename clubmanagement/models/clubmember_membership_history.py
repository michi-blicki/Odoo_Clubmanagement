from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubMemberMembershipHistory(models.Model):
    _name = 'club.member.membership.history'
    _description = 'Club Member Membership History'
    _order = 'date_start DESC, id DESC'

    member_id = fields.Many2one(string=_("Member"), comodel_name="club.member", required=True, ondelete='cascade')
    membership_id = fields.Many2one(string=_("Membership"), comodel_name="club.member.membership", required=True, ondelete='restrict')
    date_start = fields.Date(string=_("Start Date"), required=True, default=fields.Date.context_today)
    date_end = fields.Date(string=_("End Date"), required=False)
    active = fields.Boolean(default=True)
    notes = fields.Text(string=_('Notes'))

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end and record.date_start > record.date_end:
                raise ValidationError(_("End Date must be after start date."))
                