import { useFloodStore } from "../store/useFloodStore";

const LAYERS: { key: "roads" | "floodDepth" | "uncertainty" | "infra" | "route"; label: string }[] = [
  { key: "roads", label: "Road flood state" },
  { key: "floodDepth", label: "Flood depth heatmap" },
  { key: "uncertainty", label: "Uncertainty overlay" },
  { key: "infra", label: "Critical infrastructure" },
  { key: "route", label: "Active route" },
];

export default function LayerControls() {
  const layerVisibility = useFloodStore((s) => s.layerVisibility);
  const toggleLayer = useFloodStore((s) => s.toggleLayer);
  return (
    <div className="space-y-2">
      <h2 className="font-semibold text-navy">Layers</h2>
      {LAYERS.map((l) => (
        <label key={l.key} className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={layerVisibility[l.key]} onChange={() => toggleLayer(l.key)} />
          {l.label}
        </label>
      ))}
    </div>
  );
}
