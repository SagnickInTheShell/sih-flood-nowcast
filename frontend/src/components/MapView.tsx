import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { GeoJsonLayer, PathLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import { useFloodStore } from "../store/useFloodStore";
import { stateColor } from "../theme";

const ANCHOR = { lat: 12.9716, lng: 77.5946 };

// ASSUMPTION: CARTO's free "Positron" basemap style needs no API key and
// gives a real street-level look (roads, place labels, water) even though
// the synthetic ward's own road grid is a fictional overlay on top of it --
// swap for a production-licensed style (e.g. MapTiler, Stadia Maps) before
// real deployment. Demotiles (MapLibre's own placeholder style) rendered
// almost nothing at demo zoom levels, which read as a blank/abstract
// background; Positron actually looks like a map.
const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

export default function MapView() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const hasCenteredRef = useRef(false);

  const simulateResult = useFloodStore((s) => s.simulateResult);
  const criticalInfra = useFloodStore((s) => s.criticalInfra);
  const route = useFloodStore((s) => s.route);
  const layerVisibility = useFloodStore((s) => s.layerVisibility);
  const selectNode = useFloodStore((s) => s.selectNode);
  const computeRoute = useFloodStore((s) => s.computeRoute);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: [ANCHOR.lng, ANCHOR.lat],
      zoom: 14.5,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const overlay = new MapboxOverlay({ layers: [] });
    map.addControl(overlay as unknown as maplibregl.IControl);
    mapRef.current = map;
    overlayRef.current = overlay;

    // Demo affordance: click anywhere to route from that point to a
    // critical-infrastructure site that is ACTUALLY at risk under the
    // current scenario (zero access redundancy), falling back to the
    // first known site if nothing is at risk yet (e.g. light rain).
    // BUGFIX: this used to always target criticalInfra[0] -- fine for the
    // synthetic ward, where the hospital is deliberately sited to be
    // vulnerable, but in real mode (many facilities, no deliberate siting)
    // the first one in the list has no guaranteed relationship to which
    // facility is actually cut off right now.
    map.on("click", (e) => {
      const state = useFloodStore.getState();
      const atRiskIds = new Set(state.simulateResult?.at_risk_infra_ids ?? []);
      const infra = state.criticalInfra.find((i) => atRiskIds.has(i.infra_id)) ?? state.criticalInfra[0];
      if (infra) {
        computeRoute({ lat: e.lngLat.lat, lng: e.lngLat.lng }, { lat: infra.lat, lng: infra.lng });
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Real-mode wards (e.g. Bellandur) live nowhere near the synthetic
  // ward's placeholder anchor -- recentre once real data actually arrives,
  // instead of hardcoding a second location here.
  useEffect(() => {
    if (hasCenteredRef.current || !mapRef.current || criticalInfra.length === 0) return;
    const avgLat = criticalInfra.reduce((sum, i) => sum + i.lat, 0) / criticalInfra.length;
    const avgLng = criticalInfra.reduce((sum, i) => sum + i.lng, 0) / criticalInfra.length;
    mapRef.current.jumpTo({ center: [avgLng, avgLat], zoom: 15 });
    hasCenteredRef.current = true;
  }, [criticalInfra]);

  useEffect(() => {
    if (!overlayRef.current) return;
    const layers: any[] = [];

    if (simulateResult && layerVisibility.roads) {
      layers.push(
        new GeoJsonLayer({
          id: "road-segments",
          data: {
            type: "FeatureCollection",
            features: simulateResult.road_segments.map((seg) => ({
              type: "Feature",
              properties: { edge_id: seg.edge_id, state: seg.state },
              geometry: seg.geometry,
            })),
          },
          getLineColor: (f: any) => [...(stateColor[f.properties.state] ?? stateColor.clear), 255],
          getLineWidth: (f: any) => (f.properties.state === "flooded" ? 7 : 5),
          widthUnits: "pixels",
          lineWidthMinPixels: 4,
          capRounded: true,
          jointRounded: true,
          pickable: true,
        }),
      );
    }

    if (simulateResult && layerVisibility.floodDepth) {
      layers.push(
        new HeatmapLayer({
          id: "flood-depth-heatmap",
          data: simulateResult.node_predictions,
          getPosition: (d: any) => [d.lng, d.lat],
          getWeight: (d: any) => Math.max(d.depth_m_mean, 0.001),
          radiusPixels: 90,
          intensity: 1.5,
          threshold: 0.02,
          aggregation: "SUM",
          colorRange: [
            [234, 244, 250, 0],
            [187, 222, 217, 90],
            [232, 163, 61, 140],
            [232, 163, 61, 190],
            [192, 57, 43, 220],
            [140, 25, 18, 255],
          ],
        }),
      );
    }

    // Uncertainty is rendered as its own translucent overlay -- visible,
    // never hidden behind the mean-depth heatmap (§8.2).
    if (simulateResult && layerVisibility.uncertainty) {
      layers.push(
        new GeoJsonLayer({
          id: "uncertainty-band",
          data: {
            type: "FeatureCollection",
            features: simulateResult.node_predictions.map((n) => ({
              type: "Feature",
              properties: { std: n.depth_m_std, node_id: n.node_id },
              geometry: { type: "Point", coordinates: [n.lng, n.lat] },
            })),
          },
          pointType: "circle",
          getFillColor: [0, 168, 181, 70],
          getLineColor: [0, 168, 181, 160],
          lineWidthMinPixels: 1,
          getPointRadius: (f: any) => 8 + f.properties.std * 250,
          pointRadiusUnits: "pixels",
          pickable: true,
          onClick: (info: any) => selectNode(info.object?.properties?.node_id ?? null),
        }),
      );
    }

    if (layerVisibility.infra) {
      layers.push(
        new GeoJsonLayer({
          id: "critical-infra",
          data: {
            type: "FeatureCollection",
            features: criticalInfra.map((i) => ({
              type: "Feature",
              properties: { name: i.name, infra_type: i.infra_type },
              geometry: { type: "Point", coordinates: [i.lng, i.lat] },
            })),
          },
          pointType: "circle",
          getFillColor: [232, 163, 61, 255],
          getLineColor: [11, 37, 69, 255],
          getLineWidth: 2.5,
          lineWidthMinPixels: 2,
          getPointRadius: 11,
          pointRadiusUnits: "pixels",
          pickable: true,
        }),
      );
    }

    if (route && layerVisibility.route) {
      layers.push(
        new PathLayer({
          id: "baseline-route",
          data: [{ path: route.baseline_route_geometry.coordinates }],
          getPath: (d: any) => d.path,
          getColor: [148, 163, 184, 210],
          getWidth: 5,
          widthMinPixels: 4,
          capRounded: true,
        }),
        new PathLayer({
          id: "active-route",
          data: [{ path: route.route_geometry.coordinates }],
          getPath: (d: any) => d.path,
          getColor: [31, 107, 87, 255],
          getWidth: 6,
          widthMinPixels: 5,
          capRounded: true,
        }),
      );
    }

    overlayRef.current.setProps({ layers });
  }, [simulateResult, criticalInfra, route, layerVisibility, selectNode]);

  return <div ref={containerRef} className="absolute inset-0" />;
}
