# Quantum States Project

This is a small educational Python project for exploring **single-qubit quantum states**. It lets you start from a common state, apply quantum gates, inspect amplitudes and probabilities, view Bloch-sphere coordinates, and simulate measurements.

## Features

- Dependency-free Python code
- Common presets such as `|0>`, `|1>`, `|+>`, `|->`, `|+i>`, and `|-i>`
- Single-qubit gates: `I`, `X`, `Y`, `Z`, `H`, `S`, `T`
- Automatic normalization for custom amplitudes
- Bloch-vector output for pure states
- Optional measurement-shot simulation
- Built-in self-checks

## Project Layout

- `main.py`: run the project from the command line
- `quantum_states/core.py`: core state math and gate logic
- `quantum_states/cli.py`: command-line interface
- `quantum_states/self_check.py`: lightweight verification helpers
- `tests.py`: simple script wrapper for the self-checks

## Usage

Show the default `|0>` state:

```bash
python main.py
```

Start from `|0>`, apply a Hadamard gate, and simulate 1000 measurements:

```bash
python main.py --preset zero --gates H --shots 1000 --seed 7
```

Build a custom state from amplitudes and apply two gates:

```bash
python main.py --alpha 1 --beta 1j --gates Z H
```

Run the built-in demonstration:

```bash
python main.py --demo
```

Run lightweight self-checks:

```bash
python main.py --self-check
```

## Notes

- The project focuses on **single-qubit** states to keep the code readable.
- If `python` is not available on your `PATH`, run these files with whichever Python launcher is installed on your machine.
