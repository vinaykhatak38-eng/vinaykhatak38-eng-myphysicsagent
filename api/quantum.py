from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

from quantum_states.core import GATE_NAMES, PRESET_NAMES, QuantumState, format_complex, parse_complex_value


def _coerce_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def _coerce_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer.") from exc


def _parse_gates(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("gates")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip().upper() for item in raw if str(item).strip()]
    text = str(raw).replace(",", " ")
    return [part.strip().upper() for part in text.split() if part.strip()]


def _build_state(payload: dict[str, Any]) -> tuple[QuantumState, str]:
    alpha = _coerce_string(payload, "alpha")
    beta = _coerce_string(payload, "beta")
    preset = _coerce_string(payload, "preset") or "zero"

    if alpha is not None or beta is not None:
        if alpha is None or beta is None:
            raise ValueError("Provide both alpha and beta together.")
        return QuantumState(parse_complex_value(alpha), parse_complex_value(beta)), "custom amplitudes"
    return QuantumState.from_preset(preset), preset


def _complex_payload(value: complex) -> dict[str, Any]:
    return {
        "real": round(value.real, 12),
        "imag": round(value.imag, 12),
        "text": format_complex(value),
    }


def evaluate_request(payload: dict[str, Any]) -> dict[str, Any]:
    state, starting_state = _build_state(payload)
    gates = _parse_gates(payload)
    shots = _coerce_int(payload, "shots")
    seed = _coerce_int(payload, "seed")

    if shots is not None and shots < 0:
        raise ValueError("shots must be zero or a positive integer.")

    final_state = state.apply_gates(gates)
    probabilities = final_state.probabilities()
    x, y, z = final_state.bloch_coordinates()

    response: dict[str, Any] = {
        "startingState": starting_state,
        "appliedGates": gates,
        "ket": final_state.ket_label(),
        "amplitudes": {
            "alpha": _complex_payload(final_state.alpha),
            "beta": _complex_payload(final_state.beta),
        },
        "probabilities": {
            "0": round(probabilities["0"], 12),
            "1": round(probabilities["1"], 12),
        },
        "blochVector": {
            "x": round(x, 12),
            "y": round(y, 12),
            "z": round(z, 12),
        },
        "supported": {
            "presets": list(PRESET_NAMES),
            "gates": list(GATE_NAMES),
        },
    }
    if shots:
        response["measurement"] = {
            "shots": shots,
            "counts": final_state.measure(shots, seed=seed),
            "seed": seed,
        }
    return response


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        payload = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
        self._handle_payload(payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Request body must be valid JSON."})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Request body must be a JSON object."})
            return
        self._handle_payload(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle_payload(self, payload: dict[str, Any]) -> None:
        try:
            response = evaluate_request(payload)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc), "supported": {"presets": list(PRESET_NAMES), "gates": list(GATE_NAMES)}})
            return
        self._send_json(200, response)

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
