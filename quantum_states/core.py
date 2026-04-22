from __future__ import annotations

from dataclasses import dataclass
import math
import random
from collections import Counter

SQRT_HALF = 1 / math.sqrt(2)

PRESET_STATES = {
    "zero": (1 + 0j, 0 + 0j),
    "one": (0 + 0j, 1 + 0j),
    "plus": (SQRT_HALF + 0j, SQRT_HALF + 0j),
    "minus": (SQRT_HALF + 0j, -SQRT_HALF + 0j),
    "plus_i": (SQRT_HALF + 0j, 1j * SQRT_HALF),
    "minus_i": (SQRT_HALF + 0j, -1j * SQRT_HALF),
}

PRESET_NAMES = tuple(PRESET_STATES)

GATE_MATRICES = {
    "I": ((1 + 0j, 0 + 0j), (0 + 0j, 1 + 0j)),
    "X": ((0 + 0j, 1 + 0j), (1 + 0j, 0 + 0j)),
    "Y": ((0 + 0j, -1j), (1j, 0 + 0j)),
    "Z": ((1 + 0j, 0 + 0j), (0 + 0j, -1 + 0j)),
    "H": ((SQRT_HALF + 0j, SQRT_HALF + 0j), (SQRT_HALF + 0j, -SQRT_HALF + 0j)),
    "S": ((1 + 0j, 0 + 0j), (0 + 0j, 1j)),
    "T": ((1 + 0j, 0 + 0j), (0 + 0j, complex(math.cos(math.pi / 4), math.sin(math.pi / 4)))),
}

GATE_NAMES = tuple(GATE_MATRICES)


def parse_complex_value(raw: str) -> complex:
    normalized = raw.strip().replace("i", "j")
    try:
        return complex(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Could not parse complex value {raw!r}. Examples: 1, -0.5, 0.5+0.5j, 1j."
        ) from exc


def _format_real(value: float) -> str:
    if math.isclose(value, 0.0, abs_tol=1e-12):
        return "0"
    rounded = round(value, 6)
    text = f"{rounded:.6f}".rstrip("0").rstrip(".")
    return text if text != "-0" else "0"


def format_complex(value: complex) -> str:
    real = 0.0 if math.isclose(value.real, 0.0, abs_tol=1e-12) else value.real
    imag = 0.0 if math.isclose(value.imag, 0.0, abs_tol=1e-12) else value.imag

    if imag == 0.0:
        return _format_real(real)
    if real == 0.0:
        return f"{_format_real(imag)}j"

    sign = "+" if imag >= 0 else "-"
    return f"{_format_real(real)} {sign} {_format_real(abs(imag))}j"


@dataclass(frozen=True)
class QuantumState:
    alpha: complex
    beta: complex

    def __post_init__(self) -> None:
        norm = abs(self.alpha) ** 2 + abs(self.beta) ** 2
        if math.isclose(norm, 0.0, abs_tol=1e-15):
            raise ValueError("The zero vector is not a valid quantum state.")

        scale = math.sqrt(norm)
        object.__setattr__(self, "alpha", self.alpha / scale)
        object.__setattr__(self, "beta", self.beta / scale)

    @classmethod
    def from_preset(cls, name: str) -> "QuantumState":
        try:
            alpha, beta = PRESET_STATES[name.lower()]
        except KeyError as exc:
            valid = ", ".join(PRESET_NAMES)
            raise ValueError(f"Unknown preset {name!r}. Choose one of: {valid}.") from exc
        return cls(alpha, beta)

    def amplitudes(self) -> tuple[complex, complex]:
        return self.alpha, self.beta

    def probabilities(self) -> dict[str, float]:
        return {"0": abs(self.alpha) ** 2, "1": abs(self.beta) ** 2}

    def bloch_coordinates(self) -> tuple[float, float, float]:
        overlap = self.alpha.conjugate() * self.beta
        x = 2 * overlap.real
        y = 2 * overlap.imag
        z = abs(self.alpha) ** 2 - abs(self.beta) ** 2
        return x, y, z

    def ket_label(self) -> str:
        return f"({format_complex(self.alpha)})|0> + ({format_complex(self.beta)})|1>"

    def apply_matrix(self, matrix: tuple[tuple[complex, complex], tuple[complex, complex]]) -> "QuantumState":
        a = matrix[0][0] * self.alpha + matrix[0][1] * self.beta
        b = matrix[1][0] * self.alpha + matrix[1][1] * self.beta
        return QuantumState(a, b)

    def apply_gate(self, gate_name: str) -> "QuantumState":
        upper = gate_name.upper()
        try:
            matrix = GATE_MATRICES[upper]
        except KeyError as exc:
            valid = ", ".join(GATE_NAMES)
            raise ValueError(f"Unknown gate {gate_name!r}. Choose from: {valid}.") from exc
        return self.apply_matrix(matrix)

    def apply_gates(self, gate_names: list[str]) -> "QuantumState":
        state = self
        for gate_name in gate_names:
            state = state.apply_gate(gate_name)
        return state

    def measure(self, shots: int, seed: int | None = None) -> dict[str, int]:
        if shots <= 0:
            raise ValueError("shots must be a positive integer.")
        probabilities = self.probabilities()
        generator = random.Random(seed)
        samples = generator.choices(
            population=["0", "1"],
            weights=[probabilities["0"], probabilities["1"]],
            k=shots,
        )
        counts = Counter(samples)
        return {"0": counts.get("0", 0), "1": counts.get("1", 0)}

    def summary_lines(self) -> list[str]:
        probabilities = self.probabilities()
        x, y, z = self.bloch_coordinates()
        return [
            f"State vector: {self.ket_label()}",
            f"Amplitude alpha: {format_complex(self.alpha)}",
            f"Amplitude beta : {format_complex(self.beta)}",
            f"Probability |0>: {probabilities['0']:.6f}",
            f"Probability |1>: {probabilities['1']:.6f}",
            f"Bloch vector   : ({x:.6f}, {y:.6f}, {z:.6f})",
        ]
