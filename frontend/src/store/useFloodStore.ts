import { create } from "zustand";
import {
  api,
  CriticalInfraItem,
  LatLng,
  RouteResponse,
  ScenarioSummary,
  SimulateResponse,
} from "../api/client";

interface LayerVisibility {
  roads: boolean;
  floodDepth: boolean;
  uncertainty: boolean;
  infra: boolean;
  route: boolean;
}

interface FloodStore {
  scenarios: ScenarioSummary[];
  activeScenarioId: string | null;
  simulateResult: SimulateResponse | null;
  criticalInfra: CriticalInfraItem[];
  route: RouteResponse | null;
  selectedNodeId: string | null;
  layerVisibility: LayerVisibility;
  loading: boolean;
  error: string | null;

  loadInitial: () => Promise<void>;
  runScenario: (scenarioId: string) => Promise<void>;
  runCustomRainfall: (intensity: number, duration: number) => Promise<void>;
  computeRoute: (start: LatLng, end: LatLng) => Promise<void>;
  selectNode: (nodeId: string | null) => void;
  toggleLayer: (key: keyof LayerVisibility) => void;
}

export const useFloodStore = create<FloodStore>((set, get) => ({
  scenarios: [],
  activeScenarioId: null,
  simulateResult: null,
  criticalInfra: [],
  route: null,
  selectedNodeId: null,
  layerVisibility: { roads: true, floodDepth: true, uncertainty: true, infra: true, route: true },
  loading: false,
  error: null,

  loadInitial: async () => {
    set({ loading: true, error: null });
    try {
      const [scenarios, infra] = await Promise.all([
        api.getScenarios(),
        api.getCriticalInfrastructure(),
      ]);
      set({ scenarios, criticalInfra: infra });
      if (scenarios.length > 0) {
        await get().runScenario(scenarios[1]?.scenario_id ?? scenarios[0].scenario_id);
      }
    } catch (e) {
      set({ error: (e as Error).message });
    } finally {
      set({ loading: false });
    }
  },

  runScenario: async (scenarioId: string) => {
    const scenario = get().scenarios.find((s) => s.scenario_id === scenarioId);
    if (!scenario) return;
    await get().runCustomRainfall(scenario.rainfall_intensity_mm_hr, scenario.duration_min);
  },

  runCustomRainfall: async (intensity: number, duration: number) => {
    set({ loading: true, error: null });
    try {
      const result = await api.simulate(intensity, duration);
      set({ simulateResult: result, activeScenarioId: result.scenario_id, route: null });
    } catch (e) {
      set({ error: (e as Error).message });
    } finally {
      set({ loading: false });
    }
  },

  computeRoute: async (start: LatLng, end: LatLng) => {
    const scenarioId = get().activeScenarioId;
    if (!scenarioId) return;
    set({ loading: true, error: null });
    try {
      const route = await api.route(start, end, scenarioId);
      set({ route });
    } catch (e) {
      set({ error: (e as Error).message });
    } finally {
      set({ loading: false });
    }
  },

  selectNode: (nodeId: string | null) => set({ selectedNodeId: nodeId }),
  toggleLayer: (key: keyof LayerVisibility) =>
    set((state) => ({ layerVisibility: { ...state.layerVisibility, [key]: !state.layerVisibility[key] } })),
}));
