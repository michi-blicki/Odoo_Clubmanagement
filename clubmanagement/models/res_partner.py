from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ssnid = fields.Char(string=_('SSN No'), help='Social Security Number', groups="base.group_user", copy=False, tracking=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()