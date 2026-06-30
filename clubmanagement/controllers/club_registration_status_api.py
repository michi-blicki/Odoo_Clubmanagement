# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

from odoo import http
from odoo.http import request

from .club_api_security_mixin import ClubApiSecurityMixin


class ClubRegistrationStatusAPIController(http.Controller, ClubApiSecurityMixin):
    _REGISTRATION_MODE_LABELS = {
        'open': 'Open',
        'restricted': 'Restricted (Waitlist)',
        'closed': 'Closed',
    }

    def _get_registration_mode_label(self, mode):
        return self._REGISTRATION_MODE_LABELS.get(mode, mode or '')

    def _can_register(self, effective_mode):
        return effective_mode != 'closed'

    def _extract_entity(self, model_name, record):
        effective_mode = record.effective_registration_mode or 'open'
        entity = {
            'id': record.id,
            'name': record.name,
            'effective_registration_mode': effective_mode,
            'effective_registration_mode_label': self._get_registration_mode_label(effective_mode),
            'can_register': self._can_register(effective_mode),
        }

        if model_name == 'club.department':
            entity['subclub_id'] = record.subclub_id.id if record.subclub_id else False
        elif model_name == 'club.pool':
            entity['subclub_id'] = record.subclub_id.id if record.subclub_id else False
            entity['department_id'] = record.department_id.id if record.department_id else False
        elif model_name == 'club.team':
            entity['department_id'] = record.department_id.id if record.department_id else False
            entity['pool_id'] = record.pool_id.id if record.pool_id else False

        return entity

    def _get_entities_by_level(self):
        levels = (
            ('club.subclub', 'Subclub'),
            ('club.department', 'Department'),
            ('club.pool', 'Pool'),
            ('club.team', 'Team'),
        )
        entities = {}
        metadata = {}

        for model_name, label in levels:
            records = request.env[model_name].sudo().search([('active', '=', True)], order='name asc')
            items = [self._extract_entity(model_name, record) for record in records]
            entities[model_name] = items
            metadata[model_name] = {
                'label': label,
                'count': len(items),
            }

        return entities, metadata

    def _build_registration_status_level(self, model_name, label):
        entities, metadata = self._get_entities_by_level()
        items = entities.get(model_name, [])
        counters = {
            'open': 0,
            'restricted': 0,
            'closed': 0,
        }

        for item in items:
            effective_mode = item['effective_registration_mode']
            if effective_mode in counters:
                counters[effective_mode] += 1

        return {
            'label': label,
            'count': metadata.get(model_name, {}).get('count', len(items)),
            'summary': counters,
            'items': items,
        }

    def _build_state(self, entities, metadata):
        levels = (
            ('club.subclub', 'Subclub'),
            ('club.department', 'Department'),
            ('club.pool', 'Pool'),
            ('club.team', 'Team'),
        )
        state = {}
        for model_name, label in levels:
            items = entities.get(model_name, [])
            counters = {
                'open': 0,
                'restricted': 0,
                'closed': 0,
            }
            for item in items:
                mode = item['effective_registration_mode']
                if mode in counters:
                    counters[mode] += 1

            state[model_name] = {
                'label': label,
                'count': metadata.get(model_name, {}).get('count', len(items)),
                'summary': counters,
                'items': items,
            }
        return state

    def _build_hierarchy(self, entities, max_level='club.team'):
        level_order = ['club.subclub', 'club.department', 'club.pool', 'club.team']
        if max_level not in level_order:
            max_level = 'club.team'
        max_index = level_order.index(max_level)

        departments_by_subclub = {}
        pools_by_department = {}
        teams_by_parent = {}

        for department in entities.get('club.department', []):
            subclub_id = department.get('subclub_id')
            if subclub_id:
                departments_by_subclub.setdefault(subclub_id, []).append(department)

        for pool in entities.get('club.pool', []):
            department_id = pool.get('department_id')
            if department_id:
                pools_by_department.setdefault(department_id, []).append(pool)

        for team in entities.get('club.team', []):
            pool_id = team.get('pool_id')
            department_id = team.get('department_id')
            key = ('pool', pool_id) if pool_id else ('department', department_id)
            if key[1]:
                teams_by_parent.setdefault(key, []).append(team)

        subclubs = []
        for subclub in entities.get('club.subclub', []):
            subclub_node = dict(subclub)

            if max_index >= 1:
                department_nodes = []
                for department in departments_by_subclub.get(subclub['id'], []):
                    department_node = dict(department)

                    if max_index >= 2:
                        pool_nodes = []
                        for pool in pools_by_department.get(department['id'], []):
                            pool_node = dict(pool)
                            if max_index >= 3:
                                pool_node['teams'] = [dict(team) for team in teams_by_parent.get(('pool', pool['id']), [])]
                            pool_nodes.append(pool_node)
                        department_node['pools'] = pool_nodes

                        if max_index >= 3:
                            department_node['teams_without_pool'] = [
                                dict(team) for team in teams_by_parent.get(('department', department['id']), [])
                            ]

                    department_nodes.append(department_node)

                subclub_node['departments'] = department_nodes

            subclubs.append(subclub_node)

        return {
            'root_level': 'club.subclub',
            'max_level': max_level,
            'subclubs': subclubs,
        }

    def _get_registration_status_payload(self, max_level='club.team'):
        entities, metadata = self._get_entities_by_level()
        return {
            'state': self._build_state(entities, metadata),
            'hierarchy': self._build_hierarchy(entities, max_level=max_level),
        }

    @http.route(
        '/club/member/registration_status',
        type='http',
        auth='public',
        website=False,
        sitemap=False,
        methods=['GET'],
        csrf=False,
    )
    def club_member_registration_status(self, **kwargs):
        max_level = kwargs.get('max_level') or 'club.team'

        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({'status': 'failed', 'error': msg}, None, status=429)

        return self._secure_json_response(self._get_registration_status_payload(max_level=max_level), None, status=200)