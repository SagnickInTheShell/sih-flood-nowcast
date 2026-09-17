import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useFloodStore } from "../store/useFloodStore";
import SyntheticDataBadge from "./SyntheticDataBadge";

function riskLevel(depth: number): { label: string; colorClass: string } {
  if (depth >= 0.3) return { label: "Flooded", colorClass: "bg-riskRed" };
  if (depth >= 0.15) return { label: "At risk", colorClass: "bg-riskAmber" };
  return { label: "Clear", colorClass: "bg-safeGreen" };
}

export default function CitizenAlertView() {
  const simulateResult = useFloodStore((s) => s.simulateResult);
  const loadInitial = useFloodStore((s) => s.loadInitial);
  const [address, setAddress] = useState("");
  const [result, setResult] = useState<{ label: string; colorClass: string; depth: number } | null>(null);

  useEffect(() => {
    if (!simulateResult) loadInitial();
  }, [simulateResult, loadInitial]);

  function checkRisk() {
    if (!simulateResult || simulateResult.node_predictions.length === 0 || !address.trim()) return;
    // ASSUMPTION: no geocoder is wired up for this prototype -- the "nearest
    // node" is picked deterministically from the address text so the demo
    // is repeatable without needing a real geocoding API key.
    const idx = address.length % simulateResult.node_predictions.length;
    const node = simulateResult.node_predictions[idx];
    setResult({ ...riskLevel(node.depth_m_mean), depth: node.depth_m_mean });
  }

  return (
    <div className="min-h-screen bg-sky flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex justify-between items-center">
          <h1 className="text-lg font-bold text-navy">Flood risk near you</h1>
          <SyntheticDataBadge isSynthetic={simulateResult?.is_synthetic_ward ?? true} />
        </div>

        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Enter your street / locality"
          className="w-full border border-navy/20 rounded px-3 py-2 text-sm"
        />
        <button
          onClick={checkRisk}
          className="w-full bg-teal text-white rounded px-3 py-2 text-sm font-semibold disabled:opacity-50"
          disabled={!simulateResult}
        >
          Check flood risk
        </button>

        {result && (
          <div className={`rounded p-4 text-white ${result.colorClass}`}>
            <div className="text-2xl font-bold">{result.label}</div>
            <div className="text-sm opacity-90">Predicted depth: {result.depth.toFixed(2)} m</div>
          </div>
        )}

        <p className="text-xs text-navy/60">
          This prototype demonstrates the citizen alert flow using the same nowcast pipeline as the operator
          dashboard. It does not yet use a real address geocoder.
        </p>
        <Link to="/" className="text-xs underline text-navySoft">
          Back to operator dashboard
        </Link>
      </div>
    </div>
  );
}
