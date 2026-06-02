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

    def _close_previous_open_state(self):
        for record in self:
            if not record.member_id or not record.start_date or record.end_date:
                continue

            previous_open = self.search([
                ('member_id', '=', record.member_id.id),
                ('end_date', '=', False),
                ('id', '!=', record.id),
                ('start_date', '<=', record.start_date),
            ], order='start_date desc, id desc', limit=1)

            if previous_open:
                previous_open.write({'end_date': record.start_date})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._close_previous_open_state()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._close_previous_open_state()
        return result