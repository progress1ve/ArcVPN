"""Partner-only HTTP surface. Partner cookies never authorize customer/admin APIs."""
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, jsonify, request
from database import db_partners as db

COOKIE = "__Host-arcvpn_partner"


def register_partner_api(app, admin_authorized, admin_context, bot_username):
    bp = Blueprint("partners", __name__)

    def error(message, status=400):
        return jsonify(ok=False, error=message), status

    def same_origin():
        origin = request.headers.get("Origin", "")
        try:
            parsed = urlsplit(origin)
        except ValueError:
            return False
        return (parsed.scheme == "https" and parsed.netloc == request.host
                and not parsed.username and not parsed.password and not parsed.path
                and not parsed.query and not parsed.fragment)

    @bp.after_request
    def no_store(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    def gate(admin=False):
        def decorate(fn):
            @wraps(fn)
            def guarded(*args, **kwargs):
                if request.method != "GET" and not same_origin():
                    return error("invalid_origin", 403)
                if admin:
                    if not admin_authorized("partners.manage"):
                        return error("forbidden", 403)
                    identity = (admin_context() or {}).get("actor_id", "")
                else:
                    identity = db.session_partner(request.cookies.get(COOKIE, ""))
                    if not identity:
                        return error("unauthorized", 401)
                try:
                    return fn(identity, *args, **kwargs)
                except ValueError as exc:
                    return error(str(exc), 409 if str(exc) in {
                        "insufficient_balance", "operation_conflict", "source_already_assigned", "preview_changed"
                    } else 400)
                except __import__("sqlite3").IntegrityError:
                    return error("record_conflict", 409)
            return guarded
        return decorate

    @bp.route("/api/partners/login", methods=["POST"])
    def login():
        if not same_origin():
            return error("invalid_origin", 403)
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return error("invalid_payload")
        try:
            token = db.authenticate(body.get("login"), body.get("password"),
                                    request.headers.get("X-Real-IP") or request.remote_addr or "")
        except ValueError:
            return error("login_rate_limited", 429)
        if not token:
            return error("invalid_credentials", 401)
        response = jsonify(ok=True)
        response.set_cookie(COOKIE, token, secure=True, httponly=True, samesite="Strict", max_age=12 * 3600, path="/")
        return response

    @bp.route("/api/partners/logout", methods=["POST"])
    @gate()
    def logout(identity):
        db.logout(request.cookies.get(COOKIE, ""))
        response = jsonify(ok=True)
        response.delete_cookie(COOKIE, secure=True, httponly=True, samesite="Strict", path="/")
        return response

    @bp.route("/api/partners/cabinet")
    @gate()
    def cabinet(identity):
        return jsonify(ok=True, **db.report(identity["id"], bot_username(), request.args))

    @bp.route("/api/admin/partners", methods=["GET", "POST"])
    @gate(admin=True)
    def partners(actor):
        if request.method == "POST":
            body = payload()
            return jsonify(ok=True, partner=db.create_partner(body.get("name"), body.get("login"), body.get("password"), actor))
        return jsonify(ok=True, partners=db.list_partners(), sources=db.source_options())

    @bp.route("/api/admin/partners/<int:partner_id>", methods=["GET", "PATCH"])
    @gate(admin=True)
    def partner(actor, partner_id):
        if request.method == "PATCH":
            return jsonify(ok=True, partner=db.update_partner(partner_id, payload(), actor))
        return jsonify(ok=True, **db.report(partner_id, bot_username(), request.args, admin=True))

    @bp.route("/api/admin/partners/<int:partner_id>/sources", methods=["POST"])
    @gate(admin=True)
    def source(actor, partner_id):
        body = payload()
        return jsonify(ok=True, source_id=db.assign_source(partner_id, body.get("kind"), body.get("target_id"), actor))

    @bp.route("/api/admin/partners/<int:partner_id>/sources/<int:source_id>", methods=["DELETE"])
    @gate(admin=True)
    def remove_source(actor, partner_id, source_id):
        db.disable_source(partner_id, source_id, actor)
        return jsonify(ok=True)

    @bp.route("/api/admin/partners/<int:partner_id>/import-preview", methods=["POST"])
    @gate(admin=True)
    def preview(actor, partner_id):
        return jsonify(ok=True, **db.preview_import(partner_id, payload().get("source_id"), actor))

    @bp.route("/api/admin/partners/<int:partner_id>/import-confirm", methods=["POST"])
    @gate(admin=True)
    def confirm(actor, partner_id):
        body = payload()
        if body.get("confirmed") is not True or not isinstance(body.get("token"), str):
            return error("confirmation_required")
        return jsonify(ok=True, **db.confirm_import(partner_id, body["token"], actor))

    @bp.route("/api/admin/partners/<int:partner_id>/ledger", methods=["POST"])
    @gate(admin=True)
    def ledger(actor, partner_id):
        return jsonify(ok=True, entry=db.post_entry(partner_id, payload(), actor))

    def payload():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValueError("invalid_payload")
        return body

    app.register_blueprint(bp)
