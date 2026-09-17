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
    <div className="space-y-2">
      <h2 className="font-semibold text-navy">Uncertainty &middot; node {node.node_id}</h2>
      <div style={{ width: "100%", height: 120 }}>
        <ResponsiveContainer>
          <AreaChart data={data}>
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} unit="m" width={40} />
            <Tooltip formatter={(v: number) => `${v.toFixed(2)} m`} />
            <Area type="monotone" dataKey="depth" stroke="#00A8B5" fill="#00A8B5" fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-navy/60 italic border-t border-navy/10 pt-2">{simulateResult.model_caveat}</p>
    </div>
  );
}
