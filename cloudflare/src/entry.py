from __future__ import annotations

import hashlib
import json
import time
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from scripts.decision_service import build_decision
from scripts.intake_contract import (
    IntakeValidationError,
    extraction_messages,
    extraction_schema,
    fallback_incident_extraction,
    merge_extraction_results,
    normalize_model_extraction,
    validate_incident_text,
)
from scripts.scenario_contract import ScenarioValidationError

try:
    from .runtime_bundle import RUNTIME_POLICY_BUNDLE
    from .ui import DECISION_DESK_HTML
except ImportError:
    from runtime_bundle import RUNTIME_POLICY_BUNDLE
    from ui import DECISION_DESK_HTML


_RATE_BUCKETS: dict[str, list[float]] = {}


def _as_python(value):
    return value.to_py() if hasattr(value, "to_py") else value


def _header(request, name: str) -> str:
    value = request.headers.get(name)
    return str(value or "")


def _client_key(request, route: str) -> str:
    address = _header(request, "CF-Connecting-IP") or "local"
    return hashlib.sha256(f"{route}:{address}".encode("utf-8")).hexdigest()


def _within_rate_limit(request, route: str, maximum: int, window_seconds: int) -> bool:
    now = time.time()
    key = _client_key(request, route)
    recent = [value for value in _RATE_BUCKETS.get(key, []) if value > now - window_seconds]
    if len(recent) >= maximum:
        _RATE_BUCKETS[key] = recent
        return False
    recent.append(now)
    _RATE_BUCKETS[key] = recent
    return True


def _cors_origin(request, env) -> str:
    origin = _header(request, "Origin")
    allowed = str(getattr(env, "ALLOWED_ORIGIN", ""))
    request_origin = f"{urlparse(str(request.url)).scheme}://{urlparse(str(request.url)).netloc}"
    if not origin or origin == request_origin:
        return request_origin
    if origin == allowed:
        return origin
    return ""


def _headers(request, env, content_type: str) -> dict[str, str]:
    headers = {
        "Content-Type": content_type,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        ),
    }
    origin = _cors_origin(request, env)
    if origin:
        headers.update(
            {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Vary": "Origin",
            }
        )
    return headers


def _json_response(request, env, payload: dict, status: int = 200) -> Response:
    return Response(
        json.dumps(payload, sort_keys=True),
        status=status,
        headers=_headers(request, env, "application/json; charset=utf-8"),
    )


async def _request_json(request) -> dict:
    value = _as_python(await request.json())
    if not isinstance(value, dict):
        raise ValueError("JSON body must be an object.")
    return value


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(str(request.url)).path
        method = str(request.method).upper()

        if method == "POST" and _header(request, "Origin") and not _cors_origin(request, self.env):
            return _json_response(request, self.env, {"error": "origin_not_allowed"}, 403)

        if method == "OPTIONS":
            if not _cors_origin(request, self.env):
                return _json_response(request, self.env, {"error": "origin_not_allowed"}, 403)
            return Response("", status=204, headers=_headers(request, self.env, "text/plain; charset=utf-8"))

        if path == "/healthz" and method == "GET":
            return _json_response(
                request,
                self.env,
                {
                    "status": "ok",
                    "bundle_version": RUNTIME_POLICY_BUNDLE["bundle_version"],
                    "bundle_checksum": RUNTIME_POLICY_BUNDLE["bundle_checksum"],
                    "evidence_class": RUNTIME_POLICY_BUNDLE["evidence_class"],
                    "persistence": "disabled_public_demo",
                },
            )

        if path in {"/", "/index.html"} and method == "GET":
            return Response(
                DECISION_DESK_HTML,
                status=200,
                headers=_headers(request, self.env, "text/html; charset=utf-8"),
            )

        if path == "/v1/intake/parse" and method == "POST":
            if not _within_rate_limit(request, path, maximum=10, window_seconds=600):
                return _json_response(
                    request,
                    self.env,
                    {
                        "error": "rate_limited",
                        "message": "Narrative suggestions are temporarily rate-limited. Try again in a few minutes.",
                    },
                    429,
                )
            try:
                body = await _request_json(request)
                if body.get("scenario_mode") != "public_synthetic_demo":
                    return _json_response(
                        request,
                        self.env,
                        {"error": "synthetic_demo_only", "message": "The public endpoint accepts synthetic scenarios only."},
                        422,
                    )
                incident = validate_incident_text(body.get("incident_summary"))
            except IntakeValidationError as exc:
                return _json_response(request, self.env, {"error": exc.code, "message": str(exc)}, 422)
            except (ValueError, json.JSONDecodeError):
                return _json_response(
                    request,
                    self.env,
                    {"error": "invalid_request", "message": "Submit a valid JSON incident summary."},
                    400,
                )

            try:
                model = str(getattr(self.env, "INTAKE_MODEL", "@cf/meta/llama-3.1-8b-instruct-fast"))
                raw = await self.env.AI.run(
                    model,
                    {
                        "messages": extraction_messages(incident),
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": extraction_schema(),
                        },
                    },
                )
                model_result = normalize_model_extraction(raw)
                deterministic_result = fallback_incident_extraction(incident)
                return _json_response(
                    request,
                    self.env,
                    merge_extraction_results(model_result, deterministic_result),
                )
            except Exception as exc:
                print(f"intake_structured_ai_fallback:{type(exc).__name__}")
                return _json_response(request, self.env, fallback_incident_extraction(incident))

        if path == "/v1/recommend" and method == "POST":
            if not _within_rate_limit(request, path, maximum=40, window_seconds=600):
                return _json_response(request, self.env, {"error": "rate_limited"}, 429)
            try:
                body = await _request_json(request)
                scenario = body.get("scenario", body)
                if not isinstance(scenario, dict):
                    raise ValueError("scenario must be an object")
                scenario_mode = body.get("scenario_mode", scenario.get("scenario_mode"))
                if scenario_mode != "public_synthetic_demo":
                    return _json_response(
                        request,
                        self.env,
                        {"error": "synthetic_demo_only", "message": "The public endpoint accepts synthetic scenarios only."},
                        422,
                    )
                confirmed_scenario = {**scenario, "scenario_mode": scenario_mode}
                return _json_response(
                    request,
                    self.env,
                    build_decision(confirmed_scenario, RUNTIME_POLICY_BUNDLE).as_dict(),
                )
            except ScenarioValidationError as exc:
                return _json_response(
                    request,
                    self.env,
                    {"error": "invalid_scenario", "fields": exc.errors, "message": str(exc)},
                    422,
                )
            except ValueError as exc:
                return _json_response(request, self.env, {"error": "invalid_request", "message": str(exc)}, 400)

        return _json_response(request, self.env, {"error": "not_found"}, 404)
