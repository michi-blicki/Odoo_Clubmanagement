from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ClubMemberStateHistory(models.Model):
    _name = 'club.member.state.history'
    _description = 'Member State History'
    _order = 'date desc, id desc'

    member_id = fields.Many2one(string=_("Member"), comodel_name='club.member', required=True, ondelete='cascade')
    state_id = fields.Many2one(string=_("State"), comodel_name='club.member.state', required=True)
    start_date = fields.Datetime(string=_("Start Date"), required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string=_("End Date"), required=False)
    reason = fields.Text(string=_("Reason"), required=False)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("End Date must be after Start Date."))