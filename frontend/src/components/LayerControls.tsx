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
    <div className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-navy/60">Layers</h2>
      <div className="space-y-2">
        {LAYERS.map((l) => (
          <label key={l.key} className="flex items-center gap-2.5 text-sm text-textDark cursor-pointer">
            <input
              type="checkbox"
              checked={layerVisibility[l.key]}
              onChange={() => toggleLayer(l.key)}
              className="w-4 h-4 accent-teal cursor-pointer"
            />
            {l.label}
          </label>
        ))}
      </div>
    </div>
  );
}
