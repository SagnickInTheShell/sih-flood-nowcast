"""Historical backtest hook (§6.6).

Ships with ZERO pre-filled events -- no historical flood is invented
here. One stub event with every field null/"TODO..." exercises the
schema and the run_backtest() mechanism end-to-end. GET
/api/backtest/{event_id} returns 501 until a real, sourced event is
added -- see docs/DATA_SOURCES.md for how.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HistoricalEvent:
    event_id: str
    date: str | None = None
    location_note: str | None = None
    rainfall_timeseries_mm_hr: list[float] | None = None
    reported_flooded_streets: list[str] | None = None
    source_url: str | None = None


@dataclass
class BacktestResult:
    event_id: str
    predicted_flooded_edge_ids: list[str]
    reported_flooded_streets: list[str]
    matched_streets: list[str]
    missed_streets: list[str]
    note: str


STUB_EVENT = HistoricalEvent(
    event_id="TODO_real_event_needed",
    date=None,
    location_note="TODO: fill with a real documented event (date, ward/locality, source)",
    rainfall_timeseries_mm_hr=None,
    reported_flooded_streets=None,
    source_url=None,
)

EVENTS: dict[str, HistoricalEvent] = {STUB_EVENT.event_id: STUB_EVENT}


def run_backtest(event: HistoricalEvent, provider, drainage_graph, static, model) -> BacktestResult:
    if not event.rainfall_timeseries_mm_hr or not event.reported_flooded_streets:
        raise ValueError(
            f"Event '{event.event_id}' has no rainfall/observed-flooding data yet -- "
            "cannot run a backtest against it. See docs/DATA_SOURCES.md."
        )
    from app.ml.infer import predict_scenario

    dt_min_assumption = 5
    duration_min = len(event.rainfall_timeseries_mm_hr) * dt_min_assumption
    avg_intensity = sum(event.rainfall_timeseries_mm_hr) / len(event.rainfall_timeseries_mm_hr)
    predict_scenario(provider, drainage_graph, static, model, avg_intensity, duration_min)

    # NOTE: mapping predicted flooded *nodes* to human-readable street names
    # requires the road graph's street-name tags, which the synthetic ward
    # does not carry. This stays a documented TODO until a real event (with
    # a real, named road network) is wired in.
    predicted_edge_ids: list[str] = []
    matched = [s for s in event.reported_flooded_streets if s in predicted_edge_ids]
    missed = [s for s in event.reported_flooded_streets if s not in predicted_edge_ids]

    return BacktestResult(
        event_id=event.event_id,
        predicted_flooded_edge_ids=predicted_edge_ids,
        reported_flooded_streets=event.reported_flooded_streets,
        matched_streets=matched,
        missed_streets=missed,
        note="Backtest mechanism is wired end-to-end; street-name matching needs a real event with named roads.",
    )
