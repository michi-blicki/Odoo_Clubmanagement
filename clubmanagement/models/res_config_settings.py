from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    club_age_of_majority        = fields.Integer(string='Age of Majority', config_parameter="clubmanagement.age_of_majority")
    force_guardian_requirement  = fields.Boolean(string='Force Requirement for Guardian Contact', config_parameter='clubmanagement.force_guardian_requirement')
    start_member_id             = fields.Integer(string='Start Member ID', config_parameter="clubmanagement.start_member_id")
    start_member_id_set         = fields.Boolean(string='Start Member ID set', compute='_compute_start_member_id_set')

    club_api_rate_limit_enabled = fields.Boolean(
        string="Enable API Rate Limit",
        config_parameter="club.api.rate_limit_enabled",
        help="Activate basic per-IP rate limiting for public and JSON API routes"
    )

    club_api_rate_limit_count = fields.Integer(
        string="Limit per IP per Minute",
        config_parameter="club.api.rate_limit_count",
        default=60,
        help="Maximum number of allowed requests per IP address per minute"
    )

    club_invoice_grouping_mode = fields.Selection(
        selection=[
            ('single', 'Single Invoice'),
            ('by_payer', 'Group by Payer'),
        ],
        string='Default Invoice Grouping Mode',
        config_parameter='clubmanagement.default_invoice_grouping_mode',
        default='single',
    )

    club_minor_invoice_source = fields.Selection(
        selection=[
            ('primary_guardian', 'Primary Guardian'),
            ('manual', 'Manual'),
        ],
        string='Default Minor Debtor Source',
        config_parameter='clubmanagement.default_minor_invoice_source',
        default='primary_guardian',
    )

    membership_billing_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Membership Billing Journal',
        config_parameter='clubmanagement.membership_billing_journal_id',
        domain="[('type', '=', 'sale')]",
    )

    member_default_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Member Receivable Account',
        config_parameter='clubmanagement.member_default_receivable_account_id',
        domain="[('deprecated', '=', False), ('account_type', '=', 'asset_receivable')]",
        help='Default receivable account used when creating a member contact.',
    )

    member_default_payable_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Member Payable Account',
        config_parameter='clubmanagement.member_default_payable_account_id',
        domain="[('deprecated', '=', False), ('account_type', '=', 'liability_payable')]",
        help='Default payable account used when creating a member contact.',
    )

    registration_success_mail_enabled = fields.Boolean(
        string='Send Registration Success Mail',
        config_parameter='clubmanagement.registration_success_mail_enabled',
        default=True,
        help='When enabled, a registration success mail is queued after a successful registration event.',
    )

    registration_success_on_manual_create = fields.Boolean(
        string='Trigger Registration Success on Manual Member Create',
        config_parameter='clubmanagement.registration_success_on_manual_create',
        default=False,
        help='When enabled, manually created members also trigger the registration success event.',
    )


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

    def action_rebuild_team_menu_structure(self):
        self.ensure_one()

        menu_model = self.env['ir.ui.menu'].sudo()
        action_model = self.env['ir.actions.act_window'].sudo()
        root_menu = self.env.ref('clubmanagement.club_teams_root_menu', raise_if_not_found=False)
        user_group = self.env.ref('clubmanagement.group_clubmanagement_user', raise_if_not_found=False)
        team_form_view = self.env.ref('clubmanagement.club_team_overview_form_view', raise_if_not_found=False)

        if not root_menu:
            raise ValidationError(_("Root menu 'Teams' was not found (clubmanagement.club_teams_root_menu)."))
        if not user_group:
            raise ValidationError(_("User group was not found (clubmanagement.group_clubmanagement_user)."))
        if not team_form_view:
            raise ValidationError(_("Team form view was not found (clubmanagement.club_team_overview_form_view)."))

        child_menus = menu_model.search([
            ('id', 'child_of', root_menu.id),
            ('id', '!=', root_menu.id),
        ])
        if child_menus:
            child_menus.unlink()

        auto_actions = action_model.search([('name', 'like', '[Teams Menu]%')])
        if auto_actions:
            auto_actions.unlink()

        subclubs = self.env['club.subclub'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')
        departments = self.env['club.department'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')
        pools = self.env['club.pool'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')
        teams = self.env['club.team'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')

        departments_by_subclub = {}
        for department in departments:
            subclub_key = department.subclub_id.id or False
            departments_by_subclub.setdefault(subclub_key, self.env['club.department'])
            departments_by_subclub[subclub_key] |= department

        pools_by_department = {}
        for pool in pools:
            pools_by_department.setdefault(pool.department_id.id, self.env['club.pool'])
            pools_by_department[pool.department_id.id] |= pool

        pooled_teams_by_pool = {}
        unpooled_teams_by_department = {}
        for team in teams:
            if team.pool_id:
                pooled_teams_by_pool.setdefault(team.pool_id.id, self.env['club.team'])
                pooled_teams_by_pool[team.pool_id.id] |= team
            else:
                unpooled_teams_by_department.setdefault(team.department_id.id, self.env['club.team'])
                unpooled_teams_by_department[team.department_id.id] |= team

        subclub_items = []
        for subclub in subclubs:
            subclub_items.append((subclub.id, subclub.name, subclub.sequence or 10))

        has_orphan_departments = bool(departments_by_subclub.get(False))
        if has_orphan_departments or not subclub_items:
            subclub_items.append((False, _('No Subclub'), 9999))

        for subclub_id, subclub_name, subclub_sequence in subclub_items:
            subclub_menu = menu_model.create({
                'name': subclub_name,
                'parent_id': root_menu.id,
                'sequence': subclub_sequence,
                'groups_id': [(6, 0, [user_group.id])],
            })

            subclub_departments = departments_by_subclub.get(subclub_id, self.env['club.department']).sorted(
                key=lambda record: (record.sequence, record.name)
            )

            for department in subclub_departments:
                department_menu = menu_model.create({
                    'name': department.name,
                    'parent_id': subclub_menu.id,
                    'sequence': department.sequence or 10,
                    'groups_id': [(6, 0, [user_group.id])],
                })

                department_pools = pools_by_department.get(department.id, self.env['club.pool']).sorted(
                    key=lambda record: (record.sequence, record.name)
                )
                for pool in department_pools:
                    pool_menu = menu_model.create({
                        'name': pool.name,
                        'parent_id': department_menu.id,
                        'sequence': pool.sequence or 10,
                        'groups_id': [(6, 0, [user_group.id])],
                    })

                    pool_teams = pooled_teams_by_pool.get(pool.id, self.env['club.team']).sorted(
                        key=lambda record: (record.sequence, record.name)
                    )
                    for team in pool_teams:
                        team_action = action_model.create({
                            'name': _('[Teams Menu] Team: %s') % team.name,
                            'res_model': 'club.team',
                            'view_mode': 'form',
                            'view_id': team_form_view.id,
                            'res_id': team.id,
                            'target': 'current',
                        })

                        menu_model.create({
                            'name': team.name,
                            'parent_id': pool_menu.id,
                            'sequence': team.sequence or 10,
                            'groups_id': [(6, 0, [user_group.id])],
                            'action': 'ir.actions.act_window,%s' % team_action.id,
                        })

                department_teams = unpooled_teams_by_department.get(department.id, self.env['club.team']).sorted(
                    key=lambda record: (record.sequence, record.name)
                )
                for team in department_teams:
                    team_action = action_model.create({
                        'name': _('[Teams Menu] Team: %s') % team.name,
                        'res_model': 'club.team',
                        'view_mode': 'form',
                        'view_id': team_form_view.id,
                        'res_id': team.id,
                        'target': 'current',
                    })

                    menu_model.create({
                        'name': team.name,
                        'parent_id': department_menu.id,
                        'sequence': team.sequence or 10,
                        'groups_id': [(6, 0, [user_group.id])],
                        'action': 'ir.actions.act_window,%s' % team_action.id,
                    })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Menu structure rebuilt'),
                'message': _('The Teams menu hierarchy was rebuilt from Subclub, Department, Pool, and Team data.'),
                'type': 'success',
                'sticky': False,
            },
        }

    # Backward-compatible alias for potential typo-based calls
    def action_rebuild_team_menu_structur(self):
        self.ensure_one()
        return self.action_rebuild_team_menu_structure()

    def action_rebuild_pool_menu_structure(self):
        self.ensure_one()

        menu_model = self.env['ir.ui.menu'].sudo()
        action_model = self.env['ir.actions.act_window'].sudo()
        root_menu = self.env.ref('clubmanagement.club_pools_root_menu', raise_if_not_found=False)
        user_group = self.env.ref('clubmanagement.group_clubmanagement_user', raise_if_not_found=False)
        pool_form_view = self.env.ref('clubmanagement.club_pool_overview_form_view', raise_if_not_found=False)

        if not root_menu:
            raise ValidationError(_("Root menu 'Pools' was not found (clubmanagement.club_pools_root_menu)."))
        if not user_group:
            raise ValidationError(_("User group was not found (clubmanagement.group_clubmanagement_user)."))
        if not pool_form_view:
            raise ValidationError(_("Pool form view was not found (clubmanagement.club_pool_overview_form_view)."))

        child_menus = menu_model.search([
            ('id', 'child_of', root_menu.id),
            ('id', '!=', root_menu.id),
        ])
        if child_menus:
            child_menus.unlink()

        auto_actions = action_model.search([('name', 'like', '[Pools Menu]%')])
        if auto_actions:
            auto_actions.unlink()

        subclubs = self.env['club.subclub'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')
        departments = self.env['club.department'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')
        pools = self.env['club.pool'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')

        departments_by_subclub = {}
        for department in departments:
            subclub_key = department.subclub_id.id or False
            departments_by_subclub.setdefault(subclub_key, self.env['club.department'])
            departments_by_subclub[subclub_key] |= department

        pools_by_department = {}
        for pool in pools:
            pools_by_department.setdefault(pool.department_id.id, self.env['club.pool'])
            pools_by_department[pool.department_id.id] |= pool

        subclub_items = []
        for subclub in subclubs:
            subclub_items.append((subclub.id, subclub.name, subclub.sequence or 10))

        has_orphan_departments = bool(departments_by_subclub.get(False))
        if has_orphan_departments or not subclub_items:
            subclub_items.append((False, _('No Subclub'), 9999))

        for subclub_id, subclub_name, subclub_sequence in subclub_items:
            subclub_menu = menu_model.create({
                'name': subclub_name,
                'parent_id': root_menu.id,
                'sequence': subclub_sequence,
                'groups_id': [(6, 0, [user_group.id])],
            })

            subclub_departments = departments_by_subclub.get(subclub_id, self.env['club.department']).sorted(
                key=lambda record: (record.sequence, record.name)
            )
            for department in subclub_departments:
                department_menu = menu_model.create({
                    'name': department.name,
                    'parent_id': subclub_menu.id,
                    'sequence': department.sequence or 10,
                    'groups_id': [(6, 0, [user_group.id])],
                })

                department_pools = pools_by_department.get(department.id, self.env['club.pool']).sorted(
                    key=lambda record: (record.sequence, record.name)
                )
                for pool in department_pools:
                    pool_action = action_model.create({
                        'name': _('[Pools Menu] Pool: %s') % pool.name,
                        'res_model': 'club.pool',
                        'view_mode': 'form',
                        'view_id': pool_form_view.id,
                        'res_id': pool.id,
                        'target': 'current',
                    })

                    menu_model.create({
                        'name': pool.name,
                        'parent_id': department_menu.id,
                        'sequence': pool.sequence or 10,
                        'groups_id': [(6, 0, [user_group.id])],
                        'action': 'ir.actions.act_window,%s' % pool_action.id,
                    })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Menu structure rebuilt'),
                'message': _('The Pools menu hierarchy was rebuilt from Subclub, Department, and Pool data.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_rebuild_department_menu_structure(self):
        self.ensure_one()

        menu_model = self.env['ir.ui.menu'].sudo()
        action_model = self.env['ir.actions.act_window'].sudo()
        root_menu = self.env.ref('clubmanagement.club_departments_root_menu', raise_if_not_found=False)
        user_group = self.env.ref('clubmanagement.group_clubmanagement_user', raise_if_not_found=False)
        department_form_view = self.env.ref('clubmanagement.club_department_overview_form_view', raise_if_not_found=False)

        if not root_menu:
            raise ValidationError(_("Root menu 'Departments' was not found (clubmanagement.club_departments_root_menu)."))
        if not user_group:
            raise ValidationError(_("User group was not found (clubmanagement.group_clubmanagement_user)."))
        if not department_form_view:
            raise ValidationError(_("Department form view was not found (clubmanagement.club_department_overview_form_view)."))

        child_menus = menu_model.search([
            ('id', 'child_of', root_menu.id),
            ('id', '!=', root_menu.id),
        ])
        if child_menus:
            child_menus.unlink()

        auto_actions = action_model.search([('name', 'like', '[Departments Menu]%')])
        if auto_actions:
            auto_actions.unlink()

        subclubs = self.env['club.subclub'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')
        departments = self.env['club.department'].sudo().search([
            ('active', '=', True),
        ], order='sequence, name')

        departments_by_subclub = {}
        for department in departments:
            subclub_key = department.subclub_id.id or False
            departments_by_subclub.setdefault(subclub_key, self.env['club.department'])
            departments_by_subclub[subclub_key] |= department

        subclub_items = []
        for subclub in subclubs:
            subclub_items.append((subclub.id, subclub.name, subclub.sequence or 10))

        has_orphan_departments = bool(departments_by_subclub.get(False))
        if has_orphan_departments or not subclub_items:
            subclub_items.append((False, _('No Subclub'), 9999))

        for subclub_id, subclub_name, subclub_sequence in subclub_items:
            subclub_menu = menu_model.create({
                'name': subclub_name,
                'parent_id': root_menu.id,
                'sequence': subclub_sequence,
                'groups_id': [(6, 0, [user_group.id])],
            })

            subclub_departments = departments_by_subclub.get(subclub_id, self.env['club.department']).sorted(
                key=lambda record: (record.sequence, record.name)
            )
            for department in subclub_departments:
                department_action = action_model.create({
                    'name': _('[Departments Menu] Department: %s') % department.name,
                    'res_model': 'club.department',
                    'view_mode': 'form',
                    'view_id': department_form_view.id,
                    'res_id': department.id,
                    'target': 'current',
                })

                menu_model.create({
                    'name': department.name,
                    'parent_id': subclub_menu.id,
                    'sequence': department.sequence or 10,
                    'groups_id': [(6, 0, [user_group.id])],
                    'action': 'ir.actions.act_window,%s' % department_action.id,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Menu structure rebuilt'),
                'message': _('The Departments menu hierarchy was rebuilt from Subclub and Department data.'),
                'type': 'success',
                'sticky': False,
            },
        }