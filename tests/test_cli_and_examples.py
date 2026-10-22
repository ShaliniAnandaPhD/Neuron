"""Run the CLI and the examples the way a user would: as separate processes."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd, seed="0"):
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("seed", ["0", "1", "2", "3"])
def test_quickstart_example(tmp_path, seed):
    result = run([str(ROOT / "examples" / "quickstart.py")], cwd=tmp_path, seed=seed)
    assert result.returncode == 0, result.stderr
    assert (
        result.stdout.strip()
        == "responder: Sounds like you like it but it isn't working. Repair or refund?"
    )


def test_cli_help(tmp_path):
    result = run(["-m", "neuron.cli", "--help"], cwd=tmp_path)
    assert result.returncode == 0
    assert "circuit" in result.stdout


@pytest.mark.parametrize(
    "args, expected",
    [
        (["init"], "Initialized Neuron framework"),
        (["agent", "list"], "ReflexAgent"),
        (["circuit", "list"], "sequential_pipeline"),
    ],
)
def test_cli_commands(tmp_path, args, expected):
    result = run(["-m", "neuron.cli", "--log-level", "warning", *args], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


def test_build_your_first_circuit_tutorial(tmp_path):
    module = (
        "neuron.build_your_first_agentic_circuit.examples.basic_circuit.simple_demo"
    )
    result = run(["-m", module], cwd=tmp_path)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Demo completed successfully" in result.stdout + result.stderr
