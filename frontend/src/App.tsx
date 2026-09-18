import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import CitizenAlertView from "./components/CitizenAlertView";
import CriticalAccessBanner from "./components/CriticalAccessBanner";
import ExplainabilityPanel from "./components/ExplainabilityPanel";
import Header from "./components/Header";
import LayerControls from "./components/LayerControls";
import Legend from "./components/Legend";
import MapView from "./components/MapView";
import RouteComparisonPanel from "./components/RouteComparisonPanel";
import ScenarioSlider from "./components/ScenarioSlider";
import UncertaintyPanel from "./components/UncertaintyPanel";
import { useFloodStore } from "./store/useFloodStore";

function Dashboard() {
  const loadInitial = useFloodStore((s) => s.loadInitial);
  const error = useFloodStore((s) => s.error);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  return (
    <div className="h-screen bg-sky text-textDark flex flex-col">
      <Header />
      <CriticalAccessBanner />
      {error && <div className="bg-riskRed text-white text-sm px-4 py-2">{error}</div>}
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-96 flex-shrink-0 overflow-y-auto border-r border-navy/10 bg-white divide-y divide-navy/10">
          <div className="p-5"><ScenarioSlider /></div>
          <div className="p-5"><LayerControls /></div>
          <div className="p-5"><RouteComparisonPanel /></div>
          <div className="p-5"><UncertaintyPanel /></div>
          <div className="p-5"><ExplainabilityPanel /></div>
        </aside>
        <main className="flex-1 relative">
          <MapView />
          <Legend />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/citizen" element={<CitizenAlertView />} />
    </Routes>
  );
}
