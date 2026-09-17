import { useFloodStore } from "../store/useFloodStore";

export default function CriticalAccessBanner() {
  const risk = useFloodStore((s) => s.route?.critical_access_risk);
  if (!risk) return null;

  return (
    <div className="bg-riskRed text-white px-6 py-3 flex items-center gap-3">
      <span className="text-2xl" aria-hidden="true">
        &#9888;
      </span>
      <div>
        <div className="font-bold text-base">Critical access risk: {risk.infra_name}</div>
        <div className="text-sm">
          {risk.message} (access redundancy score: {risk.access_redundancy_score})
        </div>
      </div>
    </div>
  );
}
