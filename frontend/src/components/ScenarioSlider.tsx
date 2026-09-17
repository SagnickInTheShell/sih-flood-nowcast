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
    <div className="space-y-3">
      <h2 className="font-semibold text-navy">Scenario</h2>
      <div className="flex flex-col gap-1">
        {scenarios.map((s) => (
          <button
            key={s.scenario_id}
            onClick={() => runScenario(s.scenario_id)}
            className={`text-left text-sm px-3 py-2 rounded border transition-colors ${
              activeScenarioId === s.scenario_id
                ? "bg-teal text-white border-teal"
                : "bg-white border-navy/20 hover:border-teal"
            }`}
          >
            {s.label} &mdash; {s.rainfall_intensity_mm_hr} mm/hr, {s.duration_min} min
          </button>
        ))}
      </div>

      <div className="pt-2 border-t border-navy/10 space-y-2">
        <div>
          <label className="text-xs text-navy/70">Live rainfall intensity: {intensity} mm/hr</label>
          <input
            type="range"
            min={5}
            max={150}
            step={5}
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            onMouseUp={() => runCustomRainfall(intensity, duration)}
            onTouchEnd={() => runCustomRainfall(intensity, duration)}
            className="w-full accent-teal"
          />
        </div>
        <div>
          <label className="text-xs text-navy/70">Storm duration: {duration} min</label>
          <input
            type="range"
            min={15}
            max={180}
            step={15}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            onMouseUp={() => runCustomRainfall(intensity, duration)}
            onTouchEnd={() => runCustomRainfall(intensity, duration)}
            className="w-full accent-teal"
          />
        </div>
      </div>
      {loading && <div className="text-xs text-teal">Computing...</div>}
    </div>
  );
}
