"""
Purpose: Exception hierarchy for core pipeline and plugin errors.
Inputs: Error messages and exception arguments.
Outputs: Exception classes for caps, plugins, and pipeline execution.
Depends on: None
Used by: client, core, core.caps, core.client, core.registry
Config keys: None
Tests: tests/unit/test_spend_cap.py, tests/unit/test_registry.py
"""


class SpendCapExceededError(RuntimeError):
    """Raised when hard caps on API calls or image generations are reached."""
    pass


class PluginNotFoundError(KeyError):
    """Raised when a requested plugin name is not found in the registry."""
    pass


class PipelineError(RuntimeError):
    """Raised when an unrecoverable error occurs during pipeline execution."""
    pass
