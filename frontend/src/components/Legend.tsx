import { stateColor, stateLabel } from "../theme";

export default function Legend() {
  return (
    <div className="absolute bottom-4 left-4 bg-white/95 rounded shadow-md px-3 py-2 text-xs space-y-1 z-10">
      <div className="font-semibold text-navy mb-1">Road flood state</div>
      {Object.entries(stateColor).map(([key, [r, g, b]]) => (
        <div key={key} className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: `rgb(${r},${g},${b})` }} />
          {stateLabel[key]}
        </div>
      ))}
      <div className="flex items-center gap-2 pt-1 border-t border-navy/10 mt-1">
        <span className="inline-block w-3 h-3 rounded-full bg-navy" />
        Critical infrastructure
      </div>
    </div>
  );
}
