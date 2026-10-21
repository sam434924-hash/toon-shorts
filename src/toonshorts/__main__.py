"""
Purpose: Executable entry point for module invocation.
Inputs: Command line arguments from sys.argv.
Outputs: Execution of ToonShorts CLI.
Depends on: cli, sys
Used by: None
Config keys: None
Tests: tests/smoke/test_smoke_pipeline.py
"""

from .cli import main

if __name__ == "__main__":
    main()
