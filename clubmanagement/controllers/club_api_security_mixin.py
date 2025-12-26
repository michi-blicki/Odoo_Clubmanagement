# -*- coding: utf-8 -*-
import json
import time
from collections import defaultdict
from odoo import _
from odoo.http import request, Response
import logging

_logger = logging.getLogger(__name__)


class ClubApiSecurityMixin:
    """Security / Rate-Limit / HTTPS Enforcer for Club API routes."""

    # memory-based rate tracking per IP
    RATE_LOG = defaultdict(list)

    def _enforce_rate_limit(self, api_conf=None):
        """Basic per-IP rate-limit check, returns (ok, msg)."""
        env = request.env
        ip = request.httprequest.remote_addr or "unknown"
        now = time.time()

        # --- Defaultwerte laden
        limit_enabled = False
        limit_count = 60
        limit_window = 60  # Sekundenfenster

        if api_conf:
            limit_enabled = getattr(api_conf, "rate_limit_enabled", False)
            limit_count = getattr(api_conf, "rate_limit_per_minute", limit_count)
        else:
            # Fallback aus globaler Konfiguration
            param_env = env["ir.config_parameter"].sudo()
            limit_enabled = param_env.get_param("club.api.rate_limit_enabled", "True") == "True"
            limit_count = int(param_env.get_param("club.api.rate_limit_count", 60))

        if not limit_enabled:
            return True, None

        # --- Prüflogik
        self.RATE_LOG[ip] = [t for t in self.RATE_LOG[ip] if now - t < limit_window]
        if len(self.RATE_LOG[ip]) >= limit_count:
            _logger.warning("Rate limit exceeded for IP %s", ip)
            return False, _("Rate limit exceeded for IP: %s") % ip

        self.RATE_LOG[ip].append(now)
        return True, None

    def _secure_json_response(self, payload, api_conf=None, status=200):
        """Build a JSON HTTP response with proper CORS + HTTPS headers."""
        headers = {
            "Content-Type": "application/json",
            # Basis-CORS: sicherer Fallback für alle öffentlichen Endpunkte
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

        if api_conf:
            # individuelle CORS-Konfiguration
            if getattr(api_conf, "cors_allow_origin", None):
                headers["Access-Control-Allow-Origin"] = api_conf.cors_allow_origin

            # optional HTTPS-Policy
            if getattr(api_conf, "enforce_https", False):
                headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        body = json.dumps(payload)
        # Response Objekt benutzen (besser für type='http')
        return Response(body, status=status, headers=headers)
