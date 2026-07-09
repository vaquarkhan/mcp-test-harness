"""Run resiliency experiments via the harness scheduler."""

from __future__ import annotations

from mcp_test_harness.config import HarnessConfig
from mcp_test_harness.experiments.compiler import compile_experiments
from mcp_test_harness.experiments.loader import get_experiment, load_catalog, resolve_suite_members
from mcp_test_harness.experiments.models import ExperimentCatalog, ExperimentTemplate
from mcp_test_harness.experiments.scorecard import build_experiment_scorecard, collect_abort_reasons
from mcp_test_harness.models import SessionResults
from mcp_test_harness.scheduler import HarnessScheduler
from mcp_test_harness.unified_report import build_unified_summary


def resolve_experiment_ids(
    *,
    experiment_id: str | None = None,
    suite: str | None = None,
    catalog: ExperimentCatalog | None = None,
) -> list[str]:
    """Resolve ids from a single experiment or suite name."""
    if experiment_id and suite:
        raise ValueError("Specify either an experiment id or --suite, not both")
    cat = catalog or load_catalog()
    if suite:
        return resolve_suite_members(suite, cat)
    if experiment_id:
        get_experiment(experiment_id, cat)
        return [experiment_id]
    raise ValueError("Specify an experiment id or --suite")


def templates_for_ids(
    ids: list[str],
    catalog: ExperimentCatalog | None = None,
) -> list[ExperimentTemplate]:
    """Load templates for experiment ids."""
    cat = catalog or load_catalog()
    return [get_experiment(exp_id, cat) for exp_id in ids]


async def run_experiments(
    config: HarnessConfig,
    experiment_ids: list[str],
    *,
    catalog: ExperimentCatalog | None = None,
) -> SessionResults:
    """Compile and run experiment templates; attach scorecard to results."""
    cat = catalog or load_catalog()
    templates = templates_for_ids(experiment_ids, cat)
    cases = compile_experiments(templates)
    scheduler = HarnessScheduler()
    results = await scheduler.run_sequential(cases, config)

    template_map = {t.id: t for t in templates}
    abort_reasons = collect_abort_reasons(results, template_map)
    scorecard = build_experiment_scorecard(results, template_map, aborted_reasons=abort_reasons)

    cov = results.coverage or None
    results.unified_summary = build_unified_summary(results, cov)
    results.unified_summary["experiments"] = scorecard
    return results
