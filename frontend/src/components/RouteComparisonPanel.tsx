import { useFloodStore } from "../store/useFloodStore";

export default function RouteComparisonPanel() {
  const route = useFloodStore((s) => s.route);

  if (!route) {
    return (
      <div className="space-y-2">
        <h2 className="font-semibold text-navy">Route comparison</h2>
        <p className="text-xs text-navy/60">
          Click anywhere on the map to compute an emergency route to the ward&apos;s hospital,
          comparing the flood-aware route against the naive baseline route.
        </p>
      </div>
    );
  }

  const deltaSeconds = route.eta_seconds - route.baseline_eta_seconds;

  return (
    <div className="space-y-2">
      <h2 className="font-semibold text-navy">Route comparison</h2>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="bg-safeGreen/10 border border-safeGreen rounded p-2">
          <div className="text-xs text-safeGreen font-semibold">Flood-aware route</div>
          <div className="text-lg font-bold text-navy">{Math.round(route.eta_seconds)}s</div>
        </div>
        <div className="bg-navy/5 border border-navy/20 rounded p-2">
          <div className="text-xs text-navy/60 font-semibold">Naive baseline</div>
          <div className="text-lg font-bold text-navy">{Math.round(route.baseline_eta_seconds)}s</div>
        </div>
      </div>
      <p className="text-xs text-navy/70">
        {deltaSeconds <= 0
          ? `${Math.abs(Math.round(deltaSeconds))}s faster than the baseline.`
          : `${Math.round(deltaSeconds)}s slower than the baseline -- the detour trades time for safety.`}
      </p>
      {route.avoided_flooded_segments.length > 0 && (
        <div className="text-xs text-riskRed font-medium">
          Avoided {route.avoided_flooded_segments.length} flooded/at-risk segment(s) the baseline route would
          have used.
        </div>
      )}
    </div>
  );
}
