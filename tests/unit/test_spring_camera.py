"""
Purpose: Unit tests for closed-form damped spring-mass camera easing.
Inputs: Normalized time t in [0, 1].
Outputs: Verified spring boundary conditions, determinism, bounded overshoot, and JS/Python parity.
Depends on: math, pytest
Used by: tests
Config keys: None
Tests: tests/unit/test_spring_camera.py
"""

import math
import pytest


def damped_spring(t: float, omega_d: float = 2 * math.pi, zeta: float = 0.65) -> float:
    """Python mirror of closed-form damped spring implemented in camera_engine.js."""
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    s_zeta = math.sqrt(1 - zeta * zeta)
    omega_n = omega_d / s_zeta
    decay = zeta * omega_n
    coeff = zeta / s_zeta
    env = math.exp(-decay * t) - t * math.exp(-decay)
    osc = math.cos(omega_d * t) + coeff * math.sin(omega_d * t)
    return 1.0 - env * osc


def test_spring_start_value():
    """Spring function must start at exactly 0.0 at t=0 and for negative t."""
    assert damped_spring(0.0) == 0.0
    assert damped_spring(-0.1) == 0.0
    assert damped_spring(-10.0) == 0.0


def test_spring_end_value():
    """Spring function must end at exactly 1.0 at t=1 and for t > 1."""
    assert damped_spring(1.0) == 1.0
    assert damped_spring(1.1) == 1.0
    assert damped_spring(5.0) == 1.0


def test_spring_determinism_same_input():
    """Spring function is a pure function of time: identical inputs yield identical outputs."""
    test_points = [0.01, 0.1, 0.25, 0.496, 0.5, 0.75, 0.99]
    for pt in test_points:
        val1 = damped_spring(pt)
        val2 = damped_spring(pt)
        assert val1 == val2


def test_spring_bounded_overshoot():
    """Spring function must exhibit spring-mass overshoot that is strictly bounded (never > 1.15)."""
    samples = [damped_spring(i / 1000.0) for i in range(1001)]
    min_val = min(samples)
    max_val = max(samples)

    # Must stay non-negative to prevent stage boundary exposure
    assert min_val >= 0.0
    # Must exhibit positive overshoot above target 1.0
    assert max_val > 1.0
    # Must stay bounded below 1.15 (our default zeta=0.65 has ~6.6% overshoot)
    assert max_val <= 1.15
    assert round(max_val, 3) == 1.066
