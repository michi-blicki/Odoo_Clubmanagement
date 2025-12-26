# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

from .club_api_security_mixin import ClubApiSecurityMixin


class ClubLookupAPIController(http.Controller, ClubApiSecurityMixin):
    """
        REST-like Lookup Controller for external Forms
        Returns pure JSON responses over GET requests
        Uses ClubApiSecurityMixin for HTTPS, CORS and Rate-Limit enforcement
    """

    @http.route('/api/club/lookup/companies', type='http', auth='none', methods=['GET'], csrf=False)
    def list_companies(self, **kwargs):
        """Return list of companies for external clients."""
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({"status": "failed", "error": msg}, None, status=429)

        try:
            companies = request.env['res.company'].sudo().search([], order='name asc')
            data = [{"id": c.id, "name": c.name} for c in companies]
            _logger.info("Lookup request /companies served %d entries", len(data))
            return self._secure_json_response({"status": "success", "companies": data}, None, status=200)
        except Exception as e:
            _logger.exception("Error fetching company list: %s", e)
            return self._secure_json_response({
                "status": "failed",
                "error": _("Failed to fetch company list."),
                "details": str(e)
            }, None, status=500)

    @http.route('/api/club/lookup/countries', type='http', auth='none', methods=['GET'], csrf=False)
    def list_countries(self, **kwargs):
        """Return list of countries."""
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({"status": "failed", "error": msg}, None, status=429)

        try:
            countries = request.env['res.country'].sudo().search([], order="name asc")
            data = [{"id": c.id, "code": c.code, "name": c.name} for c in countries]
            _logger.info("Lookup request /countries served %d entries", len(data))
            return self._secure_json_response({"status": "success", "countries": data}, None, status=200)
        except Exception as e:
            _logger.exception("Error fetching countries: %s", e)
            return self._secure_json_response({
                "status": "failed",
                "error": _("Failed to fetch countries."),
                "details": str(e)
            }, None, status=500)

    @http.route('/api/club/lookup/states', type='http', auth='none', methods=['GET'], csrf=False)
    def list_states(self, country_id=None, **kwargs):
        """Return states filtered by country_id (optional)."""
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({"status": "failed", "error": msg}, None, status=429)

        try:
            domain = []
            if country_id:
                try:
                    domain = [("country_id", "=", int(country_id))]
                except ValueError:
                    return self._secure_json_response({
                        "status": "failed",
                        "error": _("Invalid country_id parameter")
                    }, None, status=400)

            states = request.env['res.country.state'].sudo().search(domain, order="name asc")
            data = [{
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "country_id": s.country_id.id if s.country_id else None,
                "country_name": s.country_id.name if s.country_id else None,
            } for s in states]

            _logger.info("Lookup request /states (country_id=%s) served %d entries", country_id, len(data))
            return self._secure_json_response({"status": "success", "states": data}, None, status=200)
        except Exception as e:
            _logger.exception("Error fetching states: %s", e)
            return self._secure_json_response({
                "status": "failed",
                "error": _("Failed to fetch states."),
                "details": str(e)
            }, None, status=500)

    @http.route('/api/club/lookup/api_fields', type='http', auth='none', methods=['GET'], csrf=False)
    def list_api_fields(self, company_id=None, api_name=None, **kwargs):
        """
        Return allowed API fields for the active ClubApiConfig linked to a given company and api_name.
        Used by external forms for dynamic field generation.
        Example:
            GET /api/club/lookup/api_fields?company_id=3&api_name=register_member
        """

        # --- Rate Limit prüfen
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({"status": "failed", "error": msg}, None, status=429)

        # --- Parameter validieren
        if not company_id:
            return self._secure_json_response({
                "status": "failed",
                "error": _("Missing company_id query parameter.")
            }, None, status=400)

        if not api_name:
            return self._secure_json_response({
                "status": "failed",
                "error": _("Missing api_name query parameter.")
            }, None, status=400)

        try:
            cid = int(company_id)
        except (ValueError, TypeError):
            return self._secure_json_response({
                "status": "failed",
                "error": _("Invalid company_id parameter.")
            }, None, status=400)

        try:
            # --- Suche Config mit passender Company und API
            api_config = request.env['club.api.config'].sudo().search([
                ('company_ids', 'in', [cid]),
                ('active', '=', True),
                ('api_name', '=', api_name),
            ], limit=1)

            if not api_config:
                return self._secure_json_response({
                    "status": "failed",
                    "error": _("No API configuration found for this company or API type.")
                }, None, status=404)

            # --- Feldliste lesen
            fields_qs = api_config.allowed_fields.sudo().sorted(key=lambda f: f.sequence or f.id)

            data = []
            for f in fields_qs.sudo():
                data.append({
                    "id": f.id,
                    "sequence": f.sequence or 0,
                    "name": f.technical_name or "",
                    "label": f.label or f.technical_name or "",
                    "type": f.field_type or "system",
                    "model": f.model or "",
                    "required": bool(f.required),
                    "readonly": False,   # readonly ist im Mixin nicht definiert
                    "custom": f.field_type == "custom",
                })

            result = {
                "status": "success",
                "company_id": cid,
                "api_name": api_name,
                "api_config_id": api_config.id,
                "count": len(data),
                "fields": data,
            }

            _logger.info(
                "Lookup /api_fields company_id=%s api_name=%s -> %s fields",
                cid, api_name, len(data)
            )

            return self._secure_json_response(result, api_config, status=200)

        except Exception as e:
            _logger.exception("Error fetching field list for company_id=%s, api_name=%s: %s", company_id, api_name, e)
            return self._secure_json_response({
                "status": "failed",
                "error": _("Failed to load API field list."),
                "details": str(e)
            }, None, status=500)

    @http.route("/api/club/lookup/languages", type="http", auth="none", methods=["GET"], csrf=False)
    def list_languages(self, **kwargs):
        """
        Return list of available languages (res.lang).
        Includes id, name, code and iso_code.
        """
        # --- Rate Limit prüfen
        ok, msg = self._enforce_rate_limit(None)
        if not ok:
            return self._secure_json_response({"status": "failed", "error": msg}, None, status=429)

        try:
            # --- Daten abholen
            langs = request.env["res.lang"].sudo().search([], order="name asc")
            data = [{
                "id": lang.id,
                "name": lang.name,
                "code": lang.code,
                "iso_code": lang.iso_code or "",
            } for lang in langs]

            _logger.info("Lookup request /languages served %d entries", len(data))

            # --- Erfolgs-Antwort
            return self._secure_json_response({
                "status": "success",
                "languages": data,
                "count": len(data)
            }, None, status=200)

        except Exception as e:
            _logger.exception("Error fetching languages: %s", e)
            return self._secure_json_response({
                "status": "failed",
                "error": _("Failed to fetch language list."),
                "details": str(e)
            }, None, status=500)