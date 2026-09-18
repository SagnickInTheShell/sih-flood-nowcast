import { Link } from "react-router-dom";
import { useFloodStore } from "../store/useFloodStore";
import SyntheticDataBadge from "./SyntheticDataBadge";

export default function Header() {
  const isSynthetic = useFloodStore((s) => s.simulateResult?.is_synthetic_ward ?? true);
  return (
    <header className="bg-navy text-white px-6 py-3.5 flex items-center justify-between flex-wrap gap-3 shadow-md relative z-10">
      <div>
        <div className="text-xs uppercase tracking-wider text-teal font-medium">Team Expecto Patronum &middot; SIH26085</div>
        <h1 className="text-lg font-semibold tracking-tight">Urban Flood Nowcasting System</h1>
      </div>
      <div className="flex items-center gap-4">
        <SyntheticDataBadge isSynthetic={isSynthetic} />
        <Link
          to="/citizen"
          className="text-sm text-sky/90 hover:text-white transition-colors border-b border-transparent hover:border-white"
        >
          Citizen view
        </Link>
      </div>
    </header>
  );
}
