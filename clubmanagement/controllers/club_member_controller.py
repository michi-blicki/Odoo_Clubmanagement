# -*- coding: utf-8 -*-
# Copyright (C) 2026 by Michael Blickenstorfer; licensed under OPL-1.0 or later; see LICENSE file for details.

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