from odoo import http, fields
from odoo.http import request, Response
import logging
import json
import re
_logger = logging.getLogger(__name__)

from .club_api_security_mixin import ClubApiSecurityMixin


class ClubMemberWebController(http.Controller, ClubApiSecurityMixin):
    """Simple web controller for club member registration.

    Routes:
    - GET  /club/member/            -> info / placeholder page
    - POST /club/member/register    -> JSON endpoint to create a member

    The POST endpoint expects JSON with at least `firstname` and `lastname`.
    It will create a `club.member` using `sudo()` (public registration flow).
    """

    @http.route('/club/member/', type='http', auth='public', methods=['GET'], csrf=False)
    def index(self, **kw):
        # Enforce global rate limit for this public endpoint
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({'error': msg}, status=429)

        return request.make_response(
            "<html><body><h2>Club Member Registration</h2>"
            "<p>Use POST /club/member/register with JSON payload to register a member.</p>"
            "</body></html>",
            headers=[('Content-Type', 'text/html')]
        )

    @http.route('/club/member/register', type='http', auth='public', methods=['POST'], csrf=False)
    def register_member(self, **kw):

        # Enforce global rate limit for this public endpoint
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({'error': msg}, status=429)

        # Expect JSON body
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
        except Exception:
            return Response(json.dumps({'error': 'Invalid JSON payload'}), status=400, mimetype='application/json')

        # Lookup API config via X-API-Key header
        api_key = request.httprequest.headers.get('X-API-Key') or request.httprequest.environ.get('HTTP_X_API_KEY')
        config = None
        if api_key:
            config = request.env['club.api.config'].sudo().search([
                ('api_key', '=', api_key),
                ('api_name', '=', 'register_member'),
                ('active', '=', True),
            ], limit=1)

        # If no config found, reject (company must be derived from API config)
        if not config:
            return Response(json.dumps({'error': 'API key required or invalid for register_member'}), status=401, mimetype='application/json')

        # Build allowed and required technical names
        allowed_mixins = config.allowed_fields.sudo()
        required_mixins = config.required_fields.sudo() or request.env['club.field.mixin']

        allowed_names = {}
        for m in allowed_mixins:
            if m.field_type == 'system' and m.ir_field_id:
                irf = m.ir_field_id
                technical = irf.name
                label = irf.field_description or technical
                ttype = irf.ttype
                selection = None
                relation = None
                if ttype == 'selection':
                    selection = set()
                    for item in (irf.selection or []):
                        if isinstance(item, (list, tuple)) and item:
                            selection.add(item[0])
                if ttype in ('many2one', 'one2many', 'many2many'):
                    relation = irf.relation
            elif m.field_type == 'custom' and m.custom_field_id:
                cf = m.custom_field_id
                technical = cf.technical_name
                label = cf.label or technical
                # best-effort type mapping for custom fields
                ttype = getattr(cf, 'field_type', 'char')
                selection = getattr(cf, 'selection_values', None)
                relation = getattr(cf, 'relation_model', None)
            else:
                continue
            allowed_names[technical] = {
                'label': label,
                'mixin': m,
                'ttype': ttype,
                'selection': selection,
                'relation': relation,
                'ir_field': getattr(m, 'ir_field_id', False),
            }

        required_names = set()
        for m in required_mixins:
            if m.field_type == 'system' and m.ir_field_id:
                required_names.add(m.ir_field_id.name)
            elif m.field_type == 'custom' and m.custom_field_id:
                required_names.add(m.custom_field_id.technical_name)

        # Validation: presence, basic type checks, selection membership, uniqueness
        missing = []
        messages = []

        # Presence
        for req in required_names:
            val = payload.get(req)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(req)
                messages.append({'field': req, 'message': 'Missing required field', 'label': allowed_names.get(req, {}).get('label')})

        # Per-field validation
        email_field = 'email'
        for key, meta in allowed_names.items():
            if key not in payload:
                continue
            val = payload.get(key)
            ttype = meta.get('ttype')

            # Skip empty strings if not required
            if isinstance(val, str) and not val.strip() and key not in required_names:
                continue

            # Selection check
            if meta.get('selection'):
                if val not in meta['selection']:
                    messages.append({'field': key, 'message': f'Invalid selection value: {val}', 'label': meta.get('label')})
                    continue

            # Numeric checks
            if ttype in ('integer', 'biginteger'):
                try:
                    int(val)
                except Exception:
                    messages.append({'field': key, 'message': 'Invalid integer value', 'label': meta.get('label')})
                    continue
            if ttype in ('float', 'monetary'):
                try:
                    float(val)
                except Exception:
                    messages.append({'field': key, 'message': 'Invalid numeric value', 'label': meta.get('label')})
                    continue

            # Date / Datetime
            if ttype == 'date':
                try:
                    if val:
                        fields.Date.from_string(val)
                except Exception:
                    messages.append({'field': key, 'message': 'Invalid date format (expected YYYY-MM-DD)', 'label': meta.get('label')})
                    continue
            if ttype == 'datetime':
                try:
                    if val:
                        fields.Datetime.from_string(val)
                except Exception:
                    messages.append({'field': key, 'message': 'Invalid datetime format (ISO expected)', 'label': meta.get('label')})
                    continue

            # Email regexp
            if key == email_field and val:
                # simple RFC5322-lite regex
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", val):
                    messages.append({'field': key, 'message': 'Invalid email format', 'label': meta.get('label')})
                else:
                    existing = request.env['res.partner'].sudo().search_count([('email', '=ilike', val)])
                    if existing:
                        messages.append({'field': key, 'message': 'Email already used by another contact', 'label': meta.get('label')})

            # Many2one existence check (if numeric id provided)
            if ttype == 'many2one' and val:
                try:
                    rid = int(val)
                    rel = meta.get('relation')
                    if rel:
                        exists = request.env[rel].sudo().search_count([('id', '=', rid)])
                        if not exists:
                            messages.append({'field': key, 'message': f'Related record not found: {rid}', 'label': meta.get('label')})
                except Exception:
                    # allow xmlid or other forms for now
                    pass

        if missing or messages:
            body = {
                'missing_required_fields': missing,
                'messages': messages,
            }
            return Response(json.dumps(body), status=400, mimetype='application/json')

        # Build creation vals, only include allowed fields
        create_vals = {}
        for key, meta in allowed_names.items():
            if key in payload:
                val = payload.get(key)
                # Basic type coercion for dates
                if meta['mixin'].field_type == 'system' and meta['mixin'].ir_field_id and meta['mixin'].ir_field_id.ttype in ('date', 'datetime'):
                    try:
                        if val:
                            create_vals[key] = fields.Date.from_string(val) if meta['mixin'].ir_field_id.ttype == 'date' else fields.Datetime.from_string(val)
                    except Exception:
                        create_vals[key] = val
                else:
                    create_vals[key] = val

        # Ensure company context from config (use first company)
        company_id = config.company_ids and config.company_ids[0].id or False
        if company_id:
            create_vals['company_id'] = company_id

        try:
            Member = request.env['club.member'].sudo()
            member = Member.create(create_vals)
            body = {'member_id': member.id, 'member_ref': member.member_id}
            return Response(json.dumps(body), status=200, mimetype='application/json')
        except Exception as e:
            _logger.exception('Error creating member via API')
            return Response(json.dumps({'error': str(e)}), status=500, mimetype='application/json')

    @http.route('/club/member/age_of_majority', type='http', auth='public', methods=['GET'], csrf=False)
    def age_of_majority(self, **kw):
        """Return the configured age of majority as JSON.

        This reads the `clubmanagement.age_of_majority` config parameter.
        Returning public info — no sensitive data exposed.
        """
        # Enforce global rate limit for this public endpoint
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({'error': msg}, status=429)

        try:
            val = request.env['ir.config_parameter'].sudo().get_param('clubmanagement.age_of_majority')
            age = int(val) if val not in (None, '') else None
        except Exception:
            age = None
        return self._secure_json_response({'age_of_majority': age}, status=200)
