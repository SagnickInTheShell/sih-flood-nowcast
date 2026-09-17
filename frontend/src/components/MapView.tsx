import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { GeoJsonLayer, PathLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import { useFloodStore } from "../store/useFloodStore";
import { stateColor } from "../theme";

const ANCHOR = { lat: 12.9716, lng: 77.5946 };

// ASSUMPTION: MapLibre's free "demotiles" style needs no API key and is used
// as a placeholder basemap for this prototype -- swap for a production-
// licensed style (e.g. MapTiler, Stadia Maps) before real deployment.
const BASEMAP_STYLE = "https://demotiles.maplibre.org/style.json";

export default function MapView() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

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
    });
    const overlay = new MapboxOverlay({ layers: [] });
    map.addControl(overlay as unknown as maplibregl.IControl);
    mapRef.current = map;
    overlayRef.current = overlay;

    // Demo affordance: click anywhere to route from that point to the
    // ward's first critical-infrastructure site (kept simple on purpose).
    map.on("click", (e) => {
      const infra = useFloodStore.getState().criticalInfra[0];
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
          getLineWidth: (f: any) => (f.properties.state === "flooded" ? 5 : 3),
          lineWidthMinPixels: 2,
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
          radiusPixels: 45,
          colorRange: [
            [234, 244, 250, 0],
            [232, 163, 61, 120],
            [232, 163, 61, 180],
            [192, 57, 43, 200],
            [192, 57, 43, 255],
            [120, 20, 15, 255],
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
          getFillColor: [11, 37, 69, 255],
          getLineColor: [255, 255, 255, 255],
          getLineWidth: 2,
          lineWidthMinPixels: 2,
          getPointRadius: 9,
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
          getColor: [148, 163, 184, 200],
          getWidth: 4,
          widthMinPixels: 3,
        }),
        new PathLayer({
          id: "active-route",
          data: [{ path: route.route_geometry.coordinates }],
          getPath: (d: any) => d.path,
          getColor: [31, 107, 87, 255],
          getWidth: 5,
          widthMinPixels: 4,
        }),
      );
    }

    overlayRef.current.setProps({ layers });
  }, [simulateResult, criticalInfra, route, layerVisibility, selectNode]);

  return <div ref={containerRef} className="absolute inset-0" />;
}
