from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class HrEmployeePrivate(models.Model):
    _inherit = 'hr.employee'

    ssnid = fields.Char(string=_('SSN No'), related='address_id.ssnid', help=_('Social Security Number'), groups="hr.group_hr_user", store=True, readonly=False, tracking=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()
