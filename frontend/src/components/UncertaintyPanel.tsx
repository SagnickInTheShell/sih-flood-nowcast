import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFloodStore } from "../store/useFloodStore";

export default function UncertaintyPanel() {
  const simulateResult = useFloodStore((s) => s.simulateResult);
  const selectedNodeId = useFloodStore((s) => s.selectedNodeId);

  if (!simulateResult || simulateResult.node_predictions.length === 0) return null;

  const node =
    simulateResult.node_predictions.find((n) => n.node_id === selectedNodeId) ??
    simulateResult.node_predictions.reduce((max, n) => (n.depth_m_mean > max.depth_m_mean ? n : max));

  const data = [
    { label: "-1σ", depth: Math.max(node.depth_m_mean - node.depth_m_std, 0) },
    { label: "mean", depth: node.depth_m_mean },
    { label: "+1σ", depth: node.depth_m_mean + node.depth_m_std },
  ];

  return (
    <div className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-navy/60">
        Uncertainty &middot; node {node.node_id}
      </h2>
      <div style={{ width: "100%", height: 120 }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#0B2545" }} axisLine={{ stroke: "#0B254522" }} />
            <YAxis tick={{ fontSize: 11, fill: "#0B2545" }} unit="m" width={40} axisLine={{ stroke: "#0B254522" }} />
            <Tooltip formatter={(v: number) => `${v.toFixed(2)} m`} />
            <Area type="monotone" dataKey="depth" stroke="#00A8B5" strokeWidth={2} fill="#00A8B5" fillOpacity={0.25} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-navy/50 italic leading-relaxed border-t border-navy/10 pt-3">
        {simulateResult.model_caveat}
      </p>
    </div>
  );
}
