from odoo import models, api, _
from odoo.exceptions import AccessError

import logging
_logger = logging.getLogger(__name__)

class ClubSecurityMixin(models.AbstractModel):
    _name = 'club.security.mixin'
    _description = 'Cascading need-to-know security mixing for clubmanagement'

    @api.model
    def _get_user_member(self, user=None):
        user = user or self.env.user
        return self.env['club.member'].sudo().with_context(club_security_internal=True).search(
            [('partner_id', '=', user.partner_id.id)], limit=1
        )

    @api.model
    def _get_user_roles(self, user=None):
        member = self._get_user_member(user)
        return member.role_ids if member else self.env['club.role']

    @api.model
    def _get_user_scope_entities(self, user=None):
        roles = self._get_user_roles(user)
        return {
            'club_ids': roles.filtered(lambda r: r.club_id).mapped('club_id'),
            'subclub_ids': roles.filtered(lambda r: r.subclub_id).mapped('subclub_id'),
            'department_ids': roles.filtered(lambda r: r.department_id).mapped('department_id'),
            'pool_ids': roles.filtered(lambda r: r.pool_id).mapped('pool_id'),
            'team_ids': roles.filtered(lambda r: r.team_id).mapped('team_id'),
        }

    @api.model
    def _get_visible_team_ids(self, user=None):
        scopes = self._get_user_scope_entities(user)
        Team = self.env['club.team']
        team_ids = scopes['team_ids']

        pool_teams = Team.search([('pool_id', 'in', scopes['pool_ids'].ids)])
        dept_teams = Team.search([('department_id', 'in', scopes['department_ids'].ids)])
        subclub_teams = Team.search([('department_id.subclub_id', 'in', scopes['subclub_ids'].ids)])
        club_teams = Team.search([('club_id', 'in', scopes['club_ids'].ids)])

        return team_ids | pool_teams | dept_teams | subclub_teams | club_teams

    @api.model
    def _get_visible_member_ids(self, user=None):
        Team = self.env['club.team']
        Department = self.env['club.department']
        Pool = self.env['club.pool']
        SubClub = self.env['club.subclub']
        Club = self.env['club.club']

        scopes = self._get_user_scope_entities(user)
        visible_teams = self._get_visible_team_ids(user)

        pool_members = Pool.search([('id', 'in', scopes['pool_ids'].ids)]).mapped('member_ids_display')
        dept_members = Department.search([('id', 'in', scopes['department_ids'].ids)]).mapped('member_ids_display')
        subclub_members = SubClub.search([('id', 'in', scopes['subclub_ids'].ids)]).mapped('member_ids_display')
        club_members = Club.search([('id', 'in', scopes['club_ids'].ids)]).mapped('member_ids_display')
        team_members = visible_teams.mapped('member_ids_display')

        all_members = pool_members | dept_members | subclub_members | club_members | team_members
        return all_members

    @api.model
    def _check_user_action_permissions(self, action: str, user=None, record=None):
        """Check if current user is allowed to perform a write/create/unlink action on given record."""
        user = user or self.env.user

        if (user.login == 'admin') or (user.login == '__system__'):
            return True

        if user.has_group('clubmanagement.group_clubmanagement_administrator'):
            return True

        member = self._get_user_member(user)
        if not member:
            raise AccessError(_("Action denied: No club.member record linked to user '%s'.") % user.name)

        permitted = False
        roles = self._get_user_roles(user)

        scopes = {
            'club':  'club_id',
            'subclub':  'subclub_id',
            'department': 'department_id',
            'pool':  'pool_id',
            'team':  'team_id',
        }

        # Map required permission flag to role field
        perm_field = {
            'write': 'perm_write',
            'create': 'perm_create',
            'unlink': 'perm_unlink',
            'read': 'perm_read',
        }.get(action)

        for role in roles.filtered(lambda r: getattr(r, perm_field)):
            for scope_type, scope_field in scopes.items():
                obj_field_val = getattr(record, scope_field, None)
                if scope_field in role._fields and getattr(role, scope_field, None):
                    if getattr(role, scope_field).id == getattr(record, scope_field, None).id:
                        permitted = True
                        break
            if permitted:
                break

        if not permitted and not user.has_group('clubmanagement.group_clubmanagement_administrator'):
            raise AccessError(_("You are not allowed to %(action)s %(model)s records!") %
                              {'action': action, 'model': record._description})

        return True