import { Link } from "react-router-dom";
import { useFloodStore } from "../store/useFloodStore";
import SyntheticDataBadge from "./SyntheticDataBadge";

export default function Header() {
  const isSynthetic = useFloodStore((s) => s.simulateResult?.is_synthetic_ward ?? true);
  return (
    <header className="bg-navy text-white px-6 py-3 flex items-center justify-between flex-wrap gap-2">
      <div>
        <div className="text-xs uppercase tracking-wide text-teal">Team Expecto Patronum &middot; SIH26085</div>
        <h1 className="text-lg font-semibold">Urban Flood Nowcasting System</h1>
      </div>
      <div className="flex items-center gap-4">
        <SyntheticDataBadge isSynthetic={isSynthetic} />
        <Link to="/citizen" className="text-sm underline text-sky hover:text-white">
          Citizen view
        </Link>
      </div>
    </header>
  );
}
