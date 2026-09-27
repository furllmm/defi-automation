import argparse
from defi_manager.selftest import main as selftest

def main() -> int:
    parser = argparse.ArgumentParser(prog="defi-manager")
    parser.add_argument("command", choices=("selftest",))
    args = parser.parse_args()
    return selftest() if args.command == "selftest" else 1

