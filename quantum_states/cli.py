from __future__ import annotations

import argparse

from quantum_states.core import GATE_NAMES, PRESET_NAMES, QuantumState, parse_complex_value
from quantum_states.self_check import run_self_check


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Explore single-qubit quantum states, gates, and measurement probabilities."
    )
    parser.add_argument(
        "--preset",
        default="zero",
        choices=PRESET_NAMES,
        help="Starting state preset. Ignored if both --alpha and --beta are provided.",
    )
    parser.add_argument("--alpha", help="Amplitude for |0>. Examples: 1, 0.5+0.5j, 1j")
    parser.add_argument("--beta", help="Amplitude for |1>. Examples: 0, -1, 0.5-0.5j")
    parser.add_argument(
        "--gates",
        nargs="*",
        default=[],
        help=f"Gate sequence to apply. Supported gates: {', '.join(GATE_NAMES)}.",
    )
    parser.add_argument("--shots", type=int, default=0, help="Optional number of measurement shots to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for measurement sampling.")
    parser.add_argument("--demo", action="store_true", help="Run a short built-in demonstration.")
    parser.add_argument("--self-check", action="store_true", help="Run lightweight built-in checks and exit.")
    return parser


def build_state(args: argparse.Namespace) -> QuantumState:
    if args.alpha is not None or args.beta is not None:
        if args.alpha is None or args.beta is None:
            raise ValueError("Provide both --alpha and --beta together.")
        return QuantumState(parse_complex_value(args.alpha), parse_complex_value(args.beta))
    return QuantumState.from_preset(args.preset)


def starting_label(args: argparse.Namespace) -> str:
    if args.alpha is not None and args.beta is not None:
        return "custom amplitudes"
    return args.preset


def demo_output() -> str:
    initial = QuantumState.from_preset("zero")
    final = initial.apply_gates(["H", "S", "H"])
    lines = [
        "Demo: start from |0>, then apply H, S, H.",
        "Initial state:",
        *[f"  {line}" for line in initial.summary_lines()],
        "",
        "Final state:",
        *[f"  {line}" for line in final.summary_lines()],
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.self_check:
            print("Self-check results:")
            for item in run_self_check():
                print(f"- {item}")
            return 0

        if args.demo:
            print(demo_output())
            return 0

        state = build_state(args)
        final_state = state.apply_gates(args.gates)

        print("Quantum State Summary")
        print("---------------------")
        print(f"Starting state  : {starting_label(args)}")
        print(f"Applied gates   : {' '.join(g.upper() for g in args.gates) if args.gates else '(none)'}")
        for line in final_state.summary_lines():
            print(line)

        if args.shots:
            counts = final_state.measure(args.shots, seed=args.seed)
            print(f"Measurement shots: {args.shots}")
            print(f"Counts           : |0>={counts['0']}, |1>={counts['1']}")
        return 0
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
