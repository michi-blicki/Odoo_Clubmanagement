from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    pobox = fields.Char(string='P.O. Box', groups="base.group_user", copy=False, tracking=False)

    phone_fix_home = fields.Char(string='Home Phone', groups="base.group_user", copy=False, tracking=False)
    phone_fix_work = fields.Char(string='Work Phone', groups="base.group_user", copy=False, tracking=False)
    mobile2 = fields.Char(string='Mobile 2', groups="base.group_user", copy=False, tracking=False)
    mobile_work = fields.Char(string='Work Mobile', groups="base.group_user", copy=False, tracking=False)
    email2 = fields.Char(string='Secondary Email', groups="base.group_user", copy=False, tracking=False)
    email_work = fields.Char(string='Work Email', groups="base.group_user", copy=False, tracking=False)

    ssnid = fields.Char(string='SSN No', help='Social Security Number', groups="base.group_user", copy=False, tracking=True)

    club_member_id = fields.Many2one(string="Club Member", comodel_name="club.member", compute="_compute_club_member_id", store=True, search="_search_club_member_id")
    is_club_member = fields.Boolean(string="Is Club Member", compute="_compute_is_club_member", store=True, index=True)

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    def _compute_is_club_member(self):
        # Mapping aller partner_ids, die in club.member existieren
        member_partners = self.env["club.member"].sudo().search([]).mapped("partner_id.id")
        for rec in self:
            rec.is_club_member = rec.id in member_partners

    @api.depends('is_club_member')
    def _compute_club_member_id(self):
        for partner in self:
            member = self.env['club.member'].sudo().search([
                ('partner_id', '=', partner.id)
            ], limit=1)
            partner.club_member_id = member.id if member else False

    def _search_club_member_id(self, operator, value):
        if operator == '=':
            members = self.env['club.member'].search({
                ('id', '=', value)
            })
            return [('id', 'in', members.mapped('partner_id.id'))]
        return []

    def action_create_club_member(self):
        self.ensure_one()
        if self.is_club_member:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Information"),
                    'message': _("This contact is already a club member."),
                    'type': 'info',
                }
            }

        # Create club member
        club_member = self.env['club.member'].create({
            'partner_id': self.id,
            'is_club_member': True,
        })
        
        # Return action to open the new club member form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'club.member',
            'res_id': club_member.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_remove_club_member(self):
        self.ensure_one()
        club_member = self.env['club.member'].sudo().search([('partner_id', '=', self.id)], limit=1)
        if not club_member:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Information"),
                    'message': _("This contact is not a club member."),
                    'type': 'info',
                }
            }
        
        club_member.sudo().unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Success"),
                'message': _("Club member record has been removed."),
                'type': 'success',
            }
        }