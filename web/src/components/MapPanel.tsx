import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const BAND_COLORS: Record<string, string> = {
  green: "#22c55e",
  amber: "#f59e0b",
  red: "#ef4444",
};

const BAND_OPACITY = 0.6;
const LOW_CONF_OPACITY = 0.3;

interface Feature {
  geometry: { coordinates: number[][][] };
  properties: {
    risk: number;
    band: string;
    accumulated_dsv: number;
    criterion_alert: boolean;
    reason: string;
    confidence: number;
    confidence_label: string;
  };
}

interface GeoJSON {
  features: Feature[];
}

interface MapPanelProps {
  geojson: GeoJSON | null;
  onSelect: (feature: Feature | null) => void;
}

function Legend() {
  return (
    <div className="map-legend">
      <div className="legend-title">Risk Band</div>
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: BAND_COLORS.green }} />
        <span>Green — Low risk</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: BAND_COLORS.amber }} />
        <span>Amber — Monitor</span>
      </div>
      <div className="legend-item">
        <span className="legend-swatch" style={{ background: BAND_COLORS.red }} />
        <span>Red — High risk</span>
      </div>
      <div className="legend-divider" />
      <div className="legend-item">
        <span className="legend-swatch legend-swatch-hatched" />
        <span>Hatched = lower confidence</span>
      </div>
      <div className="legend-note">
        We're interpolating across disagreeing weather stations.
      </div>
    </div>
  );
}

export default function MapPanel({ geojson, onSelect }: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
      center: [78.4, 27.15],
      zoom: 10,
    });

    map.addControl(new maplibregl.NavigationControl());
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !geojson) return;

    const sourceId = "risk-cells";
    const fillId = "risk-fill";
    const hatchBorderId = "risk-hatch-border";

    // Clean up old layers
    for (const id of [hatchBorderId, fillId]) {
      if (map.getLayer(id)) map.removeLayer(id);
    }
    if (map.getSource(sourceId)) map.removeSource(sourceId);

    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: geojson.features.map((f) => ({
          type: "Feature" as const,
          geometry: f.geometry,
          properties: f.properties,
        })),
      },
    });

    // Fill layer — low-confidence cells get reduced opacity
    map.addLayer({
      id: fillId,
      type: "fill",
      source: sourceId,
      paint: {
        "fill-color": [
          "match",
          ["get", "band"],
          "green", BAND_COLORS.green,
          "amber", BAND_COLORS.amber,
          "red", BAND_COLORS.red,
          "#888888",
        ],
        "fill-opacity": [
          "case",
          ["==", ["get", "confidence_label"], "low"],
          LOW_CONF_OPACITY,
          BAND_OPACITY,
        ],
      },
    });

    // Dashed border for low-confidence cells
    map.addLayer({
      id: hatchBorderId,
      type: "line",
      source: sourceId,
      filter: ["==", ["get", "confidence_label"], "low"],
      paint: {
        "line-color": "#6b7280",
        "line-width": 1.5,
        "line-dasharray": [4, 3],
      },
    });

    // Click handler
    map.on("click", fillId, (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      const feature = e.features?.[0] as Feature | undefined;
      if (feature) {
        onSelect(feature);
      }
    });

    map.on("mouseenter", fillId, () => {
      map.getCanvas().style.cursor = "pointer";
    });

    map.on("mouseleave", fillId, () => {
      map.getCanvas().style.cursor = "";
    });
  }, [geojson, onSelect]);

  return (
    <div className="map-wrapper">
      <div ref={containerRef} className="map-container" />
      <Legend />
    </div>
  );
}
