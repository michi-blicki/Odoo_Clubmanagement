from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class HrEmployeePrivate(models.Model):
    _inherit = 'hr.employee'

    ssnid = fields.Char(string='SSN No', related='address_id.ssnid', help='Social Security Number', groups='hr.group_hr_user', store=True, readonly=False, tracking=True)
    private_address_id = fields.Many2one(string="Private Address Partner", comodel_name='res.partner', groups='hr.group_hr_user,group_clubmanagement_key_user', store=True, readonly=False, tracking=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.onchange('private_address_id')
    def _onchange_private_address_id(self):
        if self.private_address_id:
            if self.private_address_id.ssnid:
                self.ssnid = self.private_address_id.ssnid
            elif self.ssnid:
                self.private_address_id.ssnid = self.ssnid

            self.private_city = self.private_address_id.city
            self.private_country_id = self.private_address_id.country_id
            self.private_email = self.private_address_id.email
            self.private_phone = self.private_address_id.phone
            self.private_state_id = self.private_address_id.state_id
            self.private_street = self.private_address_id.street
            self.private_street2 = self.private_address_id.street2
            self.private_zip = self.private_address_id.zip