import { useState } from "react";
import { useFloodStore } from "../store/useFloodStore";

export default function ScenarioSlider() {
  const scenarios = useFloodStore((s) => s.scenarios);
  const activeScenarioId = useFloodStore((s) => s.activeScenarioId);
  const runScenario = useFloodStore((s) => s.runScenario);
  const runCustomRainfall = useFloodStore((s) => s.runCustomRainfall);
  const loading = useFloodStore((s) => s.loading);

  const [intensity, setIntensity] = useState(60);
  const [duration, setDuration] = useState(90);

  return (
    <div className="space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-navy/60">Scenario</h2>
      <div className="flex flex-col gap-2">
        {scenarios.map((s) => (
          <button
            key={s.scenario_id}
            onClick={() => runScenario(s.scenario_id)}
            className={`text-left text-sm px-3.5 py-2.5 rounded-lg border transition-colors ${
              activeScenarioId === s.scenario_id
                ? "bg-teal text-white border-teal shadow-sm"
                : "bg-white text-textDark border-navy/15 hover:border-teal hover:bg-teal/5"
            }`}
          >
            <div className="font-medium">{s.label}</div>
            <div className={`text-xs ${activeScenarioId === s.scenario_id ? "text-white/80" : "text-navy/50"}`}>
              {s.rainfall_intensity_mm_hr} mm/hr &middot; {s.duration_min} min
            </div>
          </button>
        ))}
      </div>

      <div className="pt-4 border-t border-navy/10 space-y-3">
        <div>
          <label className="text-xs font-medium text-navy/70">Live rainfall intensity: {intensity} mm/hr</label>
          <input
            type="range"
            min={5}
            max={150}
            step={5}
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            onMouseUp={() => runCustomRainfall(intensity, duration)}
            onTouchEnd={() => runCustomRainfall(intensity, duration)}
            className="w-full accent-teal mt-1"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-navy/70">Storm duration: {duration} min</label>
          <input
            type="range"
            min={15}
            max={180}
            step={15}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            onMouseUp={() => runCustomRainfall(intensity, duration)}
            onTouchEnd={() => runCustomRainfall(intensity, duration)}
            className="w-full accent-teal mt-1"
          />
        </div>
      </div>
      {loading && (
        <div className="text-xs text-teal font-medium flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-teal animate-pulse" />
          Computing...
        </div>
      )}
    </div>
  );
}
