from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime

import json

_logger = logging.getLogger(__name__)

from .club_api_security_mixin import ClubApiSecurityMixin

class ClubMemberAPIController(http.Controller, ClubApiSecurityMixin):

    # --------------------------------------------------
    #  CORS: OPTIONS – Preflight‑Antwort
    # --------------------------------------------------
    @http.route('/api/club/member/register', type='http', auth='none', methods=['OPTIONS'], csrf=False)
    def cors_preflight(self, **kwargs):
        """
        Beantwortet CORS‑Preflight‑Requests von Browsern.
        Nutzt die Konfiguration aus club.api.config, falls vorhanden.
        """
        api_key = request.httprequest.headers.get("api_key") or kwargs.get("api_key")
        allowed_origin = "*"
        if api_key:
            conf = request.env["club.api.config"].sudo().search([
                ("api_name", "=", "register_member"),
                ("api_key", "=", api_key),
            ], limit=1)
            if conf and conf.cors_allow_origin:
                allowed_origin = conf.cors_allow_origin

        headers = {
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, api_key",
        }
        return request.make_response("", headers=headers)

    # --------------------------------------------------
    #  POST – Haupt‑Endpoint
    # --------------------------------------------------
    @http.route('/api/club/member/register', type='http', auth='none', methods=['POST'], csrf=False)
    def register_member(self, **kwargs):
        """
        Registriert einen neuen Club-Member über JSON-API.
        Führt Typkonvertierung, Validierung und Speicherung durch,
        basierend auf den erlaubten Feldern aus club.api.config.
        Legt nur 'club.member' an – kein separater res.partner.
        """
        env = request.env
        api_conf = None

        try:
            # 1️⃣ Request Body lesen
            raw_body = request.httprequest.get_data()
            data = json.loads(raw_body.decode("utf-8") or "{}")

            api_key = data.get("api_key")
            payload = data.get("data") or {}

            if not api_key:
                return self._secure_json_response(
                    {"status": "failed", "error": "Missing 'api_key'"},
                    None, status=400,
                )
            if not payload:
                return self._secure_json_response(
                    {"status": "failed", "error": "Missing 'data' section"},
                    None, status=400,
                )

            # 2️⃣ API-Konfiguration laden
            api_conf = env["club.api.config"].sudo().search([
                ("api_name", "=", "register_member"),
                ("api_key", "=", api_key),
                ("active", "=", True),
            ], limit=1)

            if not api_conf:
                return self._secure_json_response(
                    {"status": "failed", "error": "Invalid or inactive API key"},
                    None, status=401,
                )

            # 3️⃣ Rate-Limit prüfen
            ok, msg = self._enforce_rate_limit(api_conf)
            if not ok:
                return self._secure_json_response(
                    {"status": "failed", "error": msg}, api_conf, status=429
                )

            # 4️⃣ Felddefinitionen holen
            field_recs = api_conf.allowed_fields.sudo()
            member_fields = field_recs.filtered(lambda f: f.model == "club.member")

            required_fields = {"firstname", "lastname", "gender", "company_id"}
            all_member_fields = required_fields | set(member_fields.mapped("technical_name"))

            # 5️⃣ Typkonvertierung
            payload = self._convert_payload_types(payload, field_recs)

            # 6️⃣ Pflichtfelder prüfen
            missing = [f for f in required_fields if not payload.get(f)]
            if missing:
                msg = "Missing required fields: " + ", ".join(missing)
                return self._secure_json_response(
                    {"status": "failed", "error": msg}, api_conf, status=400,
                )

            # 7️⃣ Company prüfen
            company_id_val = int(payload.get("company_id")) if payload.get("company_id") else 0
            company = env["res.company"].sudo().browse(company_id_val)
            if not company.exists():
                return self._secure_json_response(
                    {"status": "failed", "error": f"Invalid Company {company_id_val}"},
                    api_conf, status=400,
                )

            # 8️⃣ Detailvalidierung
            validated_member, member_errors = self._validate_via_mixin(
                payload, member_fields, all_member_fields
            )
            if member_errors:
                return self._secure_json_response(
                    {"status": "failed", "error": str(member_errors)}, api_conf, status=422
                )

            # 9️⃣ Transaktion starten
            env.cr.execute("SAVEPOINT api_register_member")

            # ➓ Zusatzfelder setzen – Partner wird automatisch via _inherits erzeugt
            validated_member.update({
                "company_id": company.id,
                "club_id": api_conf.club_id.id,
            })

            # Name-Fallback falls partner_firstname aus irgendeinem Grund nicht greift
            if not validated_member.get("name"):
                fn = validated_member.get("firstname", "").strip()
                ln = validated_member.get("lastname", "").strip()
                validated_member["name"] = (fn + " " + ln).strip()

            # 👉 Nur noch club.member.create() – Partner wird implizit erzeugt
            api_user = api_conf.user_id or env.ref("base.user_admin")
            member = (
                env["club.member"]
                .with_user(api_user)
                .with_company(company)
                .with_context(mail_create_nolog=True, mail_create_nosubscribe=True)
                .create(validated_member)
            )

            env.cr.execute("RELEASE SAVEPOINT api_register_member")

            # 🔟 Antwort aufbauen
            result = {
                "status": "success",
                "member_id": member.member_id,
                "partner_id": member.partner_id.id,
                "member_name": member.partner_id.name,
                "company": {"id": company.id, "name": company.name},
                "current_state": {
                    "name": member.current_state_id.name if member.current_state_id else None,
                    "code": member.current_state_id.code if member.current_state_id else None,
                    "state_type": member.current_state_id.state_type if member.current_state_id else None,
                },
            }
            return self._secure_json_response(result, api_conf, status=200)

        # ⚠️ Fehlerbehandlung
        except (ValidationError, UserError) as e:
            env.cr.rollback()
            resp = {"status": "failed", "error": str(e)}
            return self._secure_json_response(resp, api_conf, status=500)
        except Exception as e:
            env.cr.rollback()
            _logger.exception("Unhandled exception in register_member(): %s", e)
            resp = {"status": "failed", "error": str(e)}
            return self._secure_json_response(resp, api_conf, status=500)


    # ===================================================
    # validate / check helpers wie gehabt
    # ===================================================

    def _validate_via_mixin(self, data, field_recs, allowed_names):
        validated, errors = {}, {}
        for f in field_recs:
            fname = f.technical_name
            if fname not in allowed_names or fname not in data:
                continue
            value = data[fname]
            expected_type = None
            if f.field_type == "system" and f.ir_field_id:
                expected_type = f.ir_field_id.ttype
            elif f.field_type == "custom" and f.custom_field_id:
                expected_type = f.custom_field_id.field_type
            msg = self._check_type(expected_type, value)
            if msg:
                errors[fname] = msg
            else:
                validated[fname] = value
        for f in field_recs.filtered(lambda r: r.required):
            if f.technical_name not in data:
                errors[f.technical_name] = "Required field missing"
        return validated, errors



    # ===================================================
    # Type Converting / check helpers wie gehabt
    # ===================================================
    def _check_type(self, expected, value):
        if not expected:
            return None
        try:
            if expected in ("char", "text", "selection"):
                if not isinstance(value, str):
                    return f"Expected string, got {type(value).__name__}"
            elif expected == "integer":
                int(value)
            elif expected in ("float", "monetary"):
                float(value)
            elif expected == "boolean":
                if not isinstance(value, bool):
                    return "Expected boolean"
            elif expected == "date":
                from datetime import date
                if isinstance(value, (date, datetime)):
                    return None
                try:
                    datetime.strptime(str(value), "%Y-%m-%d")
                except ValueError:
                    try:
                        datetime.fromisoformat(str(value))
                    except Exception:
                        try:
                            datetime.strptime(str(value), "%d.%m.%Y")
                        except Exception:
                            return f"Invalid value for type '{expected}'"
            elif expected == "many2one":
                if not isinstance(value, int):
                    return "Expected integer ID for many2one"
        except Exception:
            return f"Invalid value for type '{expected}'"
        return None


    def _convert_payload_types(self, payload, field_recs):
        """
        Konvertiert einfache JSON-Strings aus dem Frontend in korrekte
        Python-Typen gemäß Felddefinitionen (system/custom).
        Wird Enterprise-weit auch von anderen API-Endpunkten genutzt.
        """
        if not payload:
            return {}

        converted = {}
        for f in field_recs:
            name = f.technical_name
            if name not in payload:
                continue

            raw_val = payload[name]

            # Feldtyp bestimmen
            field_type = None
            if f.field_type == "system" and f.ir_field_id:
                field_type = f.ir_field_id.ttype
            elif f.field_type == "custom" and f.custom_field_id:
                field_type = f.custom_field_id.field_type

            # --- Leere Werte behandeln ------------------------------------------
            if raw_val in ("", None, "null"):
                # Differenzierte Behandlung nach Feldtyp
                if field_type in ("char", "text", "selection"):
                    converted[name] = ""
                elif field_type in ("integer", "float", "monetary", "many2one"):
                    converted[name] = False
                elif field_type == "boolean":
                    converted[name] = False
                elif field_type in ("date", "datetime"):
                    converted[name] = False
                else:
                    converted[name] = False
                continue

            # --- Nicht-leere Werte konvertieren ---------------------------------
            try:
                if field_type in ("integer", "many2one"):
                    converted[name] = int(raw_val)
                elif field_type in ("float", "monetary"):
                    converted[name] = float(str(raw_val).replace(",", "."))
                elif field_type == "boolean":
                    # akzeptiere Bool, Int oder String
                    if isinstance(raw_val, bool):
                        converted[name] = raw_val
                    else:
                        converted[name] = str(raw_val).strip().lower() in ("1", "true", "yes", "x", "on")
                elif field_type == "date":
                    val = str(raw_val)
                    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                        try:
                            converted[name] = datetime.strptime(val, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        _logger.info("Date conversion fallback for %s=%r", name, raw_val)
                        converted[name] = val
                elif field_type == "datetime":
                    val = str(raw_val)
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
                        try:
                            converted[name] = datetime.strptime(val, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        _logger.info("Datetime conversion fallback for %s=%r", name, raw_val)
                        converted[name] = val
                elif field_type == "many2many":
                    if isinstance(raw_val, list):
                        converted[name] = [int(i) for i in raw_val if str(i).isdigit()]
                    elif isinstance(raw_val, str):
                        converted[name] = [int(i.strip()) for i in raw_val.split(",") if i.strip().isdigit()]
                    else:
                        converted[name] = []
                else:
                    converted[name] = str(raw_val).strip()

            except Exception as e:
                _logger.warning(
                    "⚠️  Type conversion for field '%s' (expected %s) failed, using raw value %r; reason=%s",
                    name, field_type, raw_val, e
                )
                converted[name] = raw_val

        # Felder übernehmen, die nicht in allowed_fields definiert sind
        for k, v in payload.items():
            if k not in converted:
                converted[k] = v

        _logger.debug("🧭 Converted payload: %s", converted)
        return converted