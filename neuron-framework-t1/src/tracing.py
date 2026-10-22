"""
Optional Weights & Biases Weave tracing.

Modules import this as `from src import tracing as weave` and use
`@weave.op()`, `weave.init(...)` and `weave.log({...})`. When the `weave`
package is installed, `op` and `init` are Weave's own. Without it they do
nothing, so the agents and tests run without a W&B account.

Weave has no `log()` function (the agents used to call one and crashed), so
`log` writes structured events to the standard logger and, when a Weave call
is in progress, attaches them to that call's attributes.
"""

import json
import logging

logger = logging.getLogger("neuron_t1")

try:
    import weave as _weave
except ImportError:  # tracing is optional
    _weave = None


def op(*args, **kwargs):
    """weave.op when Weave is installed, otherwise a no-op decorator."""
    if _weave is None:
        return lambda fn: fn
    return _weave.op(*args, **kwargs)


def init(project_name: str):
    """Start Weave tracing for a project, if Weave is installed."""
    if _weave is None:
        logger.info("weave is not installed; tracing disabled")
        return None
    return _weave.init(project_name)


def log(event: dict) -> None:
    """Record a structured event in the log (and on the current Weave call)."""
    logger.info(json.dumps(event, default=str))
    if _weave is not None:
        try:
            call = _weave.get_current_call()
            if call is not None:
                call.attributes.setdefault("events", []).append(event)
        except Exception:
            # Tracing must never break the pipeline (e.g. frozen attributes)
            logger.debug("could not attach event to the current Weave call")
