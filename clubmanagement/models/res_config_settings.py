from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    club_age_of_majority    = fields.Integer(string='Age of Majority', config_parameter="clubmanagement.age_of_majority")
    start_member_id         = fields.Integer(string='Start Member ID', config_parameter="clubmanagement.start_member_id")
    start_member_id_set     = fields.Boolean(string='Start Member ID set', compute='_compute_start_member_id_set')

    @api.depends('start_member_id')
    def _compute_start_member_id_set(self):
        param = self.env['ir.config_parameter'].sudo().get_param('clubmanagement.start_member_id')
        for record in self:
            record.start_member_id_set = bool(param)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo().get_param('clubmanagement.start_member_id')
        if not param and self.start_member_id:
            self.env['ir.config_parameter'].sudo().set_param('clubmanagement.start_member_id', self.start_member_id)
        elif param and self.start_member_id != int(param):
            raise ValidationError(_("Start Member ID cannot be changed once set."))