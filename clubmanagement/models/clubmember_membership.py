from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ClubMemberMembership(models.Model):
    _name = 'club.member.membership'
    _description = 'Club Member Membership'
    _order = 'sequence, id'
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', _('Membership Code must be unique!'))
    ]

    name = fields.Char(string=_("Membership Name"), required=True)
    code = fields.Char(string=_("Membership Code"), required=True)
    company_id = fields.Many2one(string=_("Company"), comodel_name='res.company', required=True, default=lambda self: self.env.company)
    price = fields.Monetary(string=_("Price"), compute="_compute_price", store=True, currency_field='currency_id')
    currency_id = fields.Many2one(string=_("Currency"), comodel_name='res.currency', related='company_id.currency_id', readonly=True)
    sequence = fields.Integer(string=_("Sequence"), required=True, default=10)
    member_ids = fields.Many2many(string=_("Current Members"), comodel_name="club.member", compute="_compute_member_ids", store=False, readonly=True)
    member_count = fields.Integer(string=_("Member Count"), compute="_compute_member_ids", store=False, readonly=True)
    description = fields.Html(string=_("Description"), help="Description of Membership - can be HTML or Markdown Code")

    membership_history_ids = fields.One2many(string=_("Membership History"), comodel_name="club.member.membership.history", inverse_name="membership_id")
    
    active = fields.Boolean(default=True)

    main_product_id = fields.Many2one(string=_("Main Product"), comodel_name="product.product", required=True)
    main_product_price = fields.Monetary(string=_("Main Product Price"), compute="_compute_main_product_price", store=False, currency_field='currency_id')

    additional_product_ids = fields.One2many(string=_("Additional Products"), comodel_name='club.member.membership.additional.product', inverse_name='membership_id')

    @api.model
    def init(self):
        _logger.info('Initializing model: %s', self._name)
        super().init()

    @api.depends('member_ids')
    def _compute_member_ids(self):
        for membership in self:
            members = self.env['club.member'].search([
                ('current_membership_id', '=', membership.id),
                ('active', '=', True)
            ])
            membership.member_ids = members
            membership.member_count = len(members)

    @api.depends('main_product_id')
    def _compute_main_product_price(self):
        for record in self:
            record.main_product_price = record.main_product_id.list_price if record.main_product_id else 0.0


    @api.depends('main_product_id', 'additional_product_ids', 'additional_product_ids.product_id')
    def _compute_price(self):
        for membership in self:
            total_price = 0.0
            if membership.main_product_id:
                total_price += membership.main_product_id.list_price
            if membership.additional_product_ids:
                total_price += sum(additional.product_id.list_price for additional in membership.additional_product_ids)
            membership.price = total_price


    def action_show_members(self):
        self.ensure_one()
        return {
            'name': _("Members"),
            'type': 'ir.actions.act_window',
            'res_model': 'club.member',
            'view_mode': 'list,form',
            'view_id': 'club_member_list_view_for_membership',
            'domain': [('current_membership_id', '=', self.id)],
            'context': {
                'default_current_membership_id': self.id,
            }
        }

    ################################
    # CREATE HOOK
    ################################
    @api.model_create_multi
    def create(self, vals):
        memberships = super(ClubMemberMembership, self).create(vals)

        for membership in memberships:
            # 1. Get root menu for membership lists
            menu_root = self.env.ref('clubmanagement.club_memberships_root_menu', raise_if_not_found=True)
            
            # 2. Create action with domain to current memberhip.id
            action = self.env['ir.actions.act_window'].create({
                'name': _(membership.name),
                'res_model': 'club.member',
                'view_mode': 'list,form',
                'view_id': self.env.ref('clubmanagement.club_member_active_list_view').id,
                'domain': [('current_membership_id', '=', membership.id)],
                'context': {},
                'type': 'ir.actions.act_window',
            })
            
            # 3. Create menu with action and parent to membership root menu
            menu = self.env['ir.ui.menu'].create({
                'name': membership.name,
                'parent_id': menu_root.id,
                'action': "ir.actions.act_window,%d" % action.id,
                'sequence': 10,
            })

            # 4. Add to helper table used by unlink hook
            self.env['club.member.membership.menu'].create({
                'membership_id': membership.id,
                'menu_id': menu.id,
                'action_id': action.id,
            })

        return memberships

    ################################
    # WRITE HOOK
    ################################
    def write(self, vals):
        result = super().write(vals)
        for membership in self:
            # Membership AKTIVIERT -> Menü ggf. anlegen (sofern nicht vorhanden)
            if 'active' in vals and vals['active']:
                if not self.env['club.member.membership.menu'].search([
                    ('membership_id', '=', membership.id)
                ], limit=1):
                    menu_root = self.env.ref('your_module.club_memberships_root_menu', raise_if_not_found=True)
                    action = self.env['ir.actions.act_window'].create({
                        'name': _(membership.name),
                        'res_model': 'club.member',
                        'view_mode': 'tree,form',
                        'view_id': self.env.ref('your_module.club_member_active_list_view').id,
                        'domain': [('current_membership_id', '=', membership.id)],
                        'context': {},
                        'type': 'ir.actions.act_window',
                    })
                    menu = self.env['ir.ui.menu'].create({
                        'name': membership.name,
                        'parent_id': menu_root.id,
                        'action': "ir.actions.act_window,%d" % action.id,
                        'sequence': 10,
                    })
                    self.env['club.member.membership.menu'].create({
                        'membership_id': membership.id,
                        'menu_id': menu.id,
                        'action_id': action.id,
                    })
            # Membership DEAKTIVIERT -> Menü entfernen
            elif 'active' in vals and not vals['active']:
                menu_entries = self.env['club.member.membership.menu'].search([
                    ('membership_id', '=', membership.id)
                ])
                # Auch dazugehörige ir.ui.menu & ir.actions.act_window entfernen
                for menu_entry in menu_entries:
                    if menu_entry.menu_id:
                        menu_entry.menu_id.unlink()
                    if menu_entry.action_id:
                        menu_entry.action_id.unlink()
                menu_entries.unlink()
        return result


    ################################
    # UNLINK HOOK
    ################################
    def unlink(self):
        for membership in self:
            # Prüfen, ob History-Objekte existieren
            history_count = self.env['club.member.membership.history'].search_count([
                ('membership_id', '=', membership.id)
            ])
            if history_count > 0:
                # Membership stattdessen deaktivieren, löschen verhindern
                if membership.active:
                    membership.active = False
                raise ValidationError(
                    _("This membership is present in the history of at least one member. "
                      "It has been deactivated instead of deleted.")
                )
            # Hilfstabellen-Menüs löschen
            menu_entries = self.env['club.member.membership.menu'].search([
                ('membership_id', '=', membership.id)
            ])
            menu_entries.unlink()
        # Wenn keine History existiert, löschen!
        return super(ClubMemberMembership, self).unlink()

class ClubMemberMembershipMenu(models.Model):
    _name = 'club.member.membership.menu'
    _description = 'Membership Menu Entry Helper'

    membership_id = fields.Many2one('club.member.membership', required=True, ondelete="cascade")
    menu_id = fields.Many2one('ir.ui.menu', required=True, ondelete="cascade")
    action_id = fields.Many2one('ir.actions.act_window', required=True, ondelete="cascade")
