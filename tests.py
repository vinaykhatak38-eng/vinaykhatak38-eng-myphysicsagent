from quantum_states.self_check import run_self_check


if __name__ == "__main__":
    print("Running quantum state self-checks...")
    for message in run_self_check():
        print(f"- {message}")
