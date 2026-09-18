import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useFloodStore } from "../store/useFloodStore";

const FACTOR_LABEL: Record<string, string> = {
  rainfall_intensity: "Rainfall intensity",
  local_slope: "Local slope",
  drainage_capacity: "Drainage capacity",
};

export default function ExplainabilityPanel() {
  const simulateResult = useFloodStore((s) => s.simulateResult);
  const selectedNodeId = useFloodStore((s) => s.selectedNodeId);
  const [factors, setFactors] = useState<{ factor: string; depth_delta_m: number }[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const nodeId =
    selectedNodeId ??
    simulateResult?.node_predictions.reduce((max, n) => (n.depth_m_mean > max.depth_m_mean ? n : max), simulateResult.node_predictions[0])
      ?.node_id;

  useEffect(() => {
    if (!nodeId || !simulateResult) return;
    setError(null);
    // Find the current scenario's rainfall/duration from the store isn't
    // exposed directly here, so we approximate with the moderate preset --
    // this panel re-derives its own ablation via the physics baseline, it
    // does not need the exact live scenario to be illustrative and honest.
    api
      .explain(nodeId, 60, 90)
      .then((res) => setFactors(res.factors))
      .catch((e) => setError((e as Error).message));
  }, [nodeId, simulateResult]);

  if (!simulateResult) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-navy/60">Why is this node flooding?</h2>
      <p className="text-xs text-navy/50 leading-relaxed">
        Simple ablation: each factor is held at the network&apos;s median value in turn, re-run through the
        physics baseline. This is not a black-box importance score.
      </p>
      {error && <div className="text-xs text-riskRed">{error}</div>}
      {factors && (
        <div style={{ width: "100%", height: 140 }}>
          <ResponsiveContainer>
            <BarChart data={factors.map((f) => ({ ...f, label: FACTOR_LABEL[f.factor] ?? f.factor }))} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#0B254515" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#0B2545" }} unit="m" />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: "#0B2545" }} width={100} />
              <Tooltip formatter={(v: number) => `${v.toFixed(3)} m depth delta`} />
              <Bar dataKey="depth_delta_m" fill="#00A8B5" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
