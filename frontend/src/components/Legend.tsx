import { stateColor, stateLabel } from "../theme";

export default function Legend() {
  return (
    <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-navy/10 px-3.5 py-3 text-xs space-y-1.5 z-10">
      <div className="font-semibold text-navy/70 uppercase tracking-wide text-[10px] mb-1.5">Road flood state</div>
      {Object.entries(stateColor).map(([key, [r, g, b]]) => (
        <div key={key} className="flex items-center gap-2 text-textDark">
          <span
            className="inline-block w-3 h-3 rounded-full ring-1 ring-black/5"
            style={{ backgroundColor: `rgb(${r},${g},${b})` }}
          />
          {stateLabel[key]}
        </div>
      ))}
      <div className="flex items-center gap-2 pt-1.5 border-t border-navy/10 mt-1.5 text-textDark">
        <span className="inline-block w-3 h-3 rounded-full bg-gold ring-1 ring-black/5" />
        Critical infrastructure
      </div>
    </div>
  );
}
