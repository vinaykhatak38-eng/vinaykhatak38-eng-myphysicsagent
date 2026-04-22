from __future__ import annotations

import math
from typing import Any

EARTH_MU = 3.986_004_418e14
DEFAULT_SCENARIO = "projectile"
VIEWBOX_WIDTH = 400
VIEWBOX_HEIGHT = 280
VIEWBOX_PADDING = 28

STYLE_LABELS = {
    "blueprint": "blueprint",
    "cinematic": "cinematic",
    "chalkboard": "chalkboard",
    "glass": "glass-lab",
}

AUDIENCE_LABELS = {
    "students": "students",
    "creators": "science creators",
    "research": "research teams",
}

SCENARIOS = {
    "projectile": {
        "label": "Projectile Arc",
        "solver": "Analytical ballistic solver",
        "equation": "x = v0 cos(theta)t, y = v0 sin(theta)t - 1/2 gt^2",
        "defaults": {"primary": 28.0, "secondary": 52.0, "tertiary": 9.81},
    },
    "pendulum": {
        "label": "Damped Pendulum",
        "solver": "Angular oscillator solver",
        "equation": "theta(t) ~ theta0 cos(2pi t / T) e^(-d t)",
        "defaults": {"primary": 1.8, "secondary": 28.0, "tertiary": 0.08},
    },
    "spring": {
        "label": "Spring Mass",
        "solver": "Simple harmonic motion solver",
        "equation": "x(t) = A sin(omega t), omega = sqrt(k / m)",
        "defaults": {"primary": 1.2, "secondary": 18.0, "tertiary": 0.35},
    },
    "orbit": {
        "label": "Orbital Pass",
        "solver": "Two-body orbital planner",
        "equation": "v_c = sqrt(mu / r), T = 2pi sqrt(r^3 / mu)",
        "defaults": {"primary": 6771.0, "secondary": 7.67, "tertiary": 0.16},
    },
}


def _coerce_string(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    return str(value).strip() or default


def _coerce_float(payload: dict[str, Any], key: str, default: float) -> float:
    value = payload.get(key, default)
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number.") from exc


def _coerce_int(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    if value in ("", None):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer.") from exc


def _coerce_bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _round(value: float, digits: int = 3) -> float:
    return round(value, digits)


def _metric(label: str, value: str, note: str) -> dict[str, str]:
    return {"label": label, "value": value, "note": note}


def _time_windows(duration_seconds: int, beats: list[tuple[str, str]]) -> list[dict[str, Any]]:
    segment = duration_seconds / max(len(beats), 1)
    storyboard = []
    for index, (title, beat) in enumerate(beats):
        start = round(index * segment, 1)
        end = round(duration_seconds if index == len(beats) - 1 else (index + 1) * segment, 1)
        storyboard.append(
            {
                "startSeconds": start,
                "endSeconds": end,
                "time": f"{start:.1f}-{end:.1f}s",
                "title": title,
                "beat": beat,
            }
        )
    return storyboard


def _scale_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    usable_width = VIEWBOX_WIDTH - (VIEWBOX_PADDING * 2)
    usable_height = VIEWBOX_HEIGHT - (VIEWBOX_PADDING * 2)

    scaled = []
    for x_value, y_value in points:
        x_ratio = 0.5 if span_x <= 1e-9 else (x_value - min_x) / span_x
        y_ratio = 0.5 if span_y <= 1e-9 else (y_value - min_y) / span_y
        scaled_x = VIEWBOX_PADDING + (x_ratio * usable_width)
        scaled_y = VIEWBOX_HEIGHT - VIEWBOX_PADDING - (y_ratio * usable_height)
        scaled.append((_round(scaled_x, 2), _round(scaled_y, 2)))
    return scaled


def _path_from_points(points: list[tuple[float, float]], closed: bool = False) -> str:
    if not points:
        return ""
    commands = [f"M {points[0][0]} {points[0][1]}"]
    commands.extend(f"L {x_value} {y_value}" for x_value, y_value in points[1:])
    if closed:
        commands.append("Z")
    return " ".join(commands)


def _preview(points: list[tuple[float, float]], labels: list[str], closed: bool = False) -> dict[str, Any]:
    scaled = _scale_points(points)
    marker_indexes = [0, len(scaled) // 2, len(scaled) - 1]
    markers = []
    for index, label in zip(marker_indexes, labels):
        x_value, y_value = scaled[index]
        markers.append({"x": x_value, "y": y_value, "label": label})
    return {
        "viewBox": f"0 0 {VIEWBOX_WIDTH} {VIEWBOX_HEIGHT}",
        "path": _path_from_points(scaled, closed=closed),
        "markers": markers,
        "motionSeconds": _round(_clamp(len(points) / 14, 2.6, 6.0), 2),
    }


def _style_label(style: str) -> str:
    return STYLE_LABELS.get(style, STYLE_LABELS["blueprint"])


def _audience_label(audience: str) -> str:
    return AUDIENCE_LABELS.get(audience, AUDIENCE_LABELS["students"])


def _build_projectile(inputs: dict[str, Any]) -> dict[str, Any]:
    speed = _clamp(inputs["primary"], 1.0, 140.0)
    angle_degrees = _clamp(inputs["secondary"], 5.0, 85.0)
    gravity = _clamp(inputs["tertiary"], 1.0, 30.0)

    angle = math.radians(angle_degrees)
    horizontal_velocity = speed * math.cos(angle)
    vertical_velocity = speed * math.sin(angle)
    time_to_apex = vertical_velocity / gravity
    total_time = max(0.4, 2 * time_to_apex)
    horizontal_range = (speed**2 * math.sin(2 * angle)) / gravity
    apex_height = (vertical_velocity**2) / (2 * gravity)

    points = []
    for step in range(40):
        moment = total_time * step / 39
        x_value = horizontal_velocity * moment
        y_value = max(0.0, (vertical_velocity * moment) - (0.5 * gravity * moment * moment))
        points.append((x_value, y_value))

    return {
        "metrics": [
            _metric("Flight time", f"{total_time:.2f}s", "Full visible motion before impact."),
            _metric("Horizontal range", f"{horizontal_range:.1f}m", "Idealized landing distance from the launch point."),
            _metric("Apex height", f"{apex_height:.1f}m", "Highest point in the reconstructed arc."),
            _metric("Launch vector", f"{speed:.1f}m/s @ {angle_degrees:.0f}deg", "Seed used for the camera-follow path."),
        ],
        "storyboard": _time_windows(
            inputs["durationSeconds"],
            [
                ("Parse the sketch", "Identify the launcher, axes, and launch vector from the original diagram."),
                ("Solve the trajectory", "Project the ballistic path and fade in the governing equation beside the arc."),
                ("Track the apex", "Switch to a follow-cam at the peak to show velocity changing direction."),
                ("Impact replay", "Replay the full path with range and height callouts for the audience."),
            ],
        ),
        "preview": _preview(points, ["Launch", "Apex", "Impact"]),
        "assumptions": [
            "2D motion with no drag.",
            "Point-mass approximation.",
            "Constant gravitational acceleration.",
        ],
        "insight": "Best for whiteboard shots, cannon problems, or sports diagrams where the arc itself tells the story.",
        "equationNote": "The agent overlays horizontal and vertical components separately so the motion feels explainable, not magical.",
    }


def _build_pendulum(inputs: dict[str, Any]) -> dict[str, Any]:
    length = _clamp(inputs["primary"], 0.2, 10.0)
    angle_degrees = _clamp(inputs["secondary"], 3.0, 80.0)
    damping = _clamp(inputs["tertiary"], 0.0, 0.95)

    angle = math.radians(angle_degrees)
    period = 2 * math.pi * math.sqrt(length / 9.81) * (1 + (angle * angle) / 16)
    arc_length = length * angle
    max_speed = math.sqrt(max(0.0, 2 * 9.81 * length * (1 - math.cos(angle))))

    points = []
    cycles = 1.5
    for step in range(54):
        time_value = (period * cycles) * step / 53
        displacement = angle * math.cos((2 * math.pi * time_value) / period) * math.exp(-damping * time_value / 2)
        bob_x = length * math.sin(displacement)
        bob_y = -length * math.cos(displacement)
        points.append((bob_x, bob_y))

    return {
        "metrics": [
            _metric("Swing period", f"{period:.2f}s", "Small-angle corrected period for the primary swing."),
            _metric("Arc length", f"{arc_length:.2f}m", "Distance traced from centerline to release point."),
            _metric("Peak bob speed", f"{max_speed:.2f}m/s", "Maximum speed at the bottom of the swing."),
            _metric("Damping ratio", f"{damping:.2f}", "Controls how fast the motion settles in the video."),
        ],
        "storyboard": _time_windows(
            inputs["durationSeconds"],
            [
                ("Lock the pivot", "Anchor the ceiling point and rebuild the string length from the source sketch."),
                ("Reveal the swing", "Animate the bob through its first sweep with a ghosted trail."),
                ("Explain the forces", "Overlay restoring force and velocity vectors near the centerline."),
                ("Settle the motion", "Ease into the damped response so the loop feels physically grounded."),
            ],
        ),
        "preview": _preview(points, ["Release", "Centerline", "Return"]),
        "assumptions": [
            "Planar motion around a fixed pivot.",
            "Small-angle approximation with a light damping envelope.",
            "Uniform gravity and negligible string mass.",
        ],
        "insight": "Great for classroom explanations where you want force vectors and timing to stay visually legible.",
        "equationNote": "The agent uses a damped cosine motion to keep the loop readable and elegant for explainers.",
    }


def _build_spring(inputs: dict[str, Any]) -> dict[str, Any]:
    mass = _clamp(inputs["primary"], 0.1, 20.0)
    spring_constant = _clamp(inputs["secondary"], 1.0, 240.0)
    amplitude = _clamp(inputs["tertiary"], 0.05, 2.5)

    omega = math.sqrt(spring_constant / mass)
    period = 2 * math.pi / omega
    max_speed = omega * amplitude
    max_acceleration = (omega**2) * amplitude

    points = []
    cycles = 2.5
    for step in range(64):
        time_value = (period * cycles) * step / 63
        displacement = amplitude * math.sin(omega * time_value)
        points.append((time_value, displacement))

    return {
        "metrics": [
            _metric("Oscillation period", f"{period:.2f}s", "Time required for one complete cycle."),
            _metric("Angular frequency", f"{omega:.2f}rad/s", "Controls the pace of the loop and overlays."),
            _metric("Max speed", f"{max_speed:.2f}m/s", "Center-pass speed for the mass block."),
            _metric("Max acceleration", f"{max_acceleration:.2f}m/s^2", "Peak restoring acceleration at the endpoints."),
        ],
        "storyboard": _time_windows(
            inputs["durationSeconds"],
            [
                ("Rebuild equilibrium", "Extract the anchor, spring axis, and rest length from the source diagram."),
                ("Drive the motion", "Animate compression and extension with synced displacement markers."),
                ("Show energy exchange", "Fade between kinetic and potential energy labels over each half-cycle."),
                ("Loop for export", "Finish on a clean center pass so the clip can loop on social or in class."),
            ],
        ),
        "preview": _preview(points, ["Phase start", "Equilibrium", "Phase end"]),
        "assumptions": [
            "Linear spring response obeying Hooke's law.",
            "No friction unless added in post.",
            "Motion constrained to one axis for readability.",
        ],
        "insight": "Useful for hooke-law sketches, oscillator reels, and side-view dynamics explainers.",
        "equationNote": "The motion is staged around the equilibrium line so viewers instantly understand compression versus extension.",
    }


def _build_orbit(inputs: dict[str, Any]) -> dict[str, Any]:
    orbital_radius_km = _clamp(inputs["primary"], 6571.0, 120000.0)
    injected_velocity_kms = _clamp(inputs["secondary"], 1.0, 15.0)
    eccentricity = _clamp(inputs["tertiary"], 0.0, 0.82)

    orbital_radius_m = orbital_radius_km * 1000
    circular_velocity = math.sqrt(EARTH_MU / orbital_radius_m) / 1000
    escape_velocity = math.sqrt(2 * EARTH_MU / orbital_radius_m) / 1000
    orbital_period_minutes = (2 * math.pi * math.sqrt((orbital_radius_m**3) / EARTH_MU)) / 60

    semi_major = orbital_radius_km
    semi_minor = semi_major * math.sqrt(max(0.01, 1 - (eccentricity**2)))
    points = []
    for step in range(72):
        angle = (2 * math.pi * step) / 71
        points.append((semi_major * math.cos(angle), semi_minor * math.sin(angle)))

    return {
        "metrics": [
            _metric("Circular speed", f"{circular_velocity:.2f}km/s", "Reference velocity at the chosen orbital radius."),
            _metric("Injected speed", f"{injected_velocity_kms:.2f}km/s", "Velocity the animation will highlight on entry."),
            _metric("Orbital period", f"{orbital_period_minutes:.1f}min", "Approximate loop duration for a near-circular pass."),
            _metric("Escape margin", f"{(injected_velocity_kms / escape_velocity):.2f}x", "How close the chosen speed is to local escape velocity."),
        ],
        "storyboard": _time_windows(
            inputs["durationSeconds"],
            [
                ("Interpret the diagram", "Detect the planet center, orbital ring, and the injected path from the sketch."),
                ("Frame the transfer", "Show velocity and curvature while the camera drifts into a clean orbital view."),
                ("Annotate the numbers", "Overlay orbital speed, period, and radius as the body completes the pass."),
                ("Export the loop", "End on a stabilized path that works as a hero background or teaching clip."),
            ],
        ),
        "preview": _preview(points, ["Insertion", "Apoapsis", "Return"], closed=True),
        "assumptions": [
            "Two-body model around an Earth-like central mass.",
            "No atmospheric drag or thrust after insertion.",
            "2D orbital plane chosen for diagram clarity.",
        ],
        "insight": "A strong fit for orbital mechanics explainers, transfer visuals, or sci-tech landing pages.",
        "equationNote": "The agent treats the diagram as a planar orbital brief, which keeps the visuals elegant while preserving believable numbers.",
    }


def build_simulation_blueprint(payload: dict[str, Any]) -> dict[str, Any]:
    scenario = _coerce_string(payload, "scenario", DEFAULT_SCENARIO).lower()
    if scenario not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unknown scenario {scenario!r}. Choose one of: {valid}.")

    style = _coerce_string(payload, "style", "blueprint").lower()
    if style not in STYLE_LABELS:
        style = "blueprint"

    audience = _coerce_string(payload, "audience", "students").lower()
    if audience not in AUDIENCE_LABELS:
        audience = "students"

    duration_seconds = _coerce_int(payload, "durationSeconds", 12)
    fps = _coerce_int(payload, "fps", 24)

    inputs = {
        "scenario": scenario,
        "style": style,
        "audience": audience,
        "prompt": _coerce_string(payload, "prompt", "Clean up the diagram and turn it into a narrated simulation video."),
        "durationSeconds": _clamp(duration_seconds, 6, 40),
        "fps": _clamp(fps, 12, 60),
        "primary": _coerce_float(payload, "primary", SCENARIOS[scenario]["defaults"]["primary"]),
        "secondary": _coerce_float(payload, "secondary", SCENARIOS[scenario]["defaults"]["secondary"]),
        "tertiary": _coerce_float(payload, "tertiary", SCENARIOS[scenario]["defaults"]["tertiary"]),
        "equations": _coerce_bool(payload, "equations", True),
    }

    builders = {
        "projectile": _build_projectile,
        "pendulum": _build_pendulum,
        "spring": _build_spring,
        "orbit": _build_orbit,
    }
    scenario_payload = builders[scenario](inputs)
    scenario_meta = SCENARIOS[scenario]

    pipeline = [
        "Read the source sketch and isolate bodies, labels, and arrows.",
        f"Fit a {scenario_meta['solver'].lower()} to the extracted geometry.",
        f"Build a {_style_label(style)} render with timing tuned for {_audience_label(audience)}.",
        "Export the clip with motion cues, labels, and reusable timing beats.",
    ]

    equation_overlay = (
        f"Equation overlays enabled: {scenario_meta['equation']}"
        if inputs["equations"]
        else "Equation overlays disabled: the agent will keep the render visually cleaner."
    )

    headline = f"{scenario_meta['label']} blueprint ready"
    summary = (
        f"Converted the {scenario_meta['label'].lower()} sketch into a {int(inputs['durationSeconds'])}s "
        f"{_style_label(style)} explainer for {_audience_label(audience)}."
    )

    return {
        "agentName": "VectorMotion Agent",
        "headline": headline,
        "summary": summary,
        "prompt": inputs["prompt"],
        "scenario": {
            "id": scenario,
            "label": scenario_meta["label"],
            "solver": scenario_meta["solver"],
        },
        "videoSpec": {
            "durationSeconds": int(inputs["durationSeconds"]),
            "fps": int(inputs["fps"]),
            "style": style,
            "audience": audience,
        },
        "simulation": {
            "equation": scenario_meta["equation"],
            "equationOverlay": equation_overlay,
            "insight": scenario_payload["insight"],
            "equationNote": scenario_payload["equationNote"],
        },
        "metrics": scenario_payload["metrics"],
        "storyboard": scenario_payload["storyboard"],
        "pipeline": pipeline,
        "assumptions": scenario_payload["assumptions"],
        "preview": scenario_payload["preview"],
        "supported": {
            "scenarios": list(SCENARIOS),
            "styles": list(STYLE_LABELS),
            "audiences": list(AUDIENCE_LABELS),
        },
    }
