from __future__ import annotations

import math

from quantum_states.core import QuantumState


def _close(left: complex | float, right: complex | float, tol: float = 1e-9) -> bool:
    return abs(left - right) <= tol


def run_self_check() -> list[str]:
    results: list[str] = []

    zero = QuantumState.from_preset("zero")
    flipped = zero.apply_gate("X")
    assert _close(flipped.alpha, 0.0)
    assert _close(flipped.beta, 1.0)
    results.append("X gate maps |0> to |1>.")

    plus = zero.apply_gate("H")
    assert _close(abs(plus.alpha) ** 2, 0.5)
    assert _close(abs(plus.beta) ** 2, 0.5)
    results.append("Hadamard creates an equal superposition from |0>.")

    plus_i = QuantumState.from_preset("plus_i")
    x, y, z = plus_i.bloch_coordinates()
    assert _close(x, 0.0)
    assert _close(y, 1.0)
    assert _close(z, 0.0)
    results.append("Bloch coordinates for |+i> lie on the +Y axis.")

    normalized = QuantumState(1 + 0j, 1 + 0j)
    assert _close(abs(normalized.alpha) ** 2 + abs(normalized.beta) ** 2, 1.0)
    results.append("Arbitrary amplitudes are normalized automatically.")

    phase_state = QuantumState.from_preset("one").apply_gate("T")
    expected = complex(math.cos(math.pi / 4), math.sin(math.pi / 4))
    assert _close(phase_state.beta, expected)
    results.append("T gate adds a pi/4 phase to |1>.")

    return results
