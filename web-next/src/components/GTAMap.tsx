"use client";
import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Listing } from "@/types";

/* ── Neighbourhood coordinate fallback table ──────────────────────── */
const NBHD_COORDS: Record<string, [number, number]> = {
  "downtown":           [43.6476, -79.3830],
  "king west":          [43.6420, -79.4049],
  "king":               [43.6420, -79.4049],
  "yorkville":          [43.6703, -79.3935],
  "leslieville":        [43.6603, -79.3288],
  "the beaches":        [43.6674, -79.2956],
  "beaches":            [43.6674, -79.2956],
  "roncesvalles":       [43.6484, -79.4487],
  "annex":              [43.6688, -79.4001],
  "midtown":            [43.6977, -79.3900],
  "north york":         [43.7615, -79.4111],
  "scarborough":        [43.7731, -79.2577],
  "etobicoke":          [43.6368, -79.5614],
  "mississauga":        [43.5890, -79.6441],
  "port credit":        [43.5500, -79.5836],
  "brampton":           [43.6832, -79.7633],
  "vaughan":            [43.8361, -79.5085],
  "markham":            [43.8561, -79.3370],
  "richmond hill":      [43.8828, -79.4403],
  "oakville":           [43.4675, -79.6877],
  "burlington":         [43.3255, -79.7990],
  "ajax":               [43.8509, -79.0204],
  "pickering":          [43.8384, -79.0868],
  "whitby":             [43.8975, -78.9429],
  "oshawa":             [43.8971, -78.8658],
  "corktown":           [43.6505, -79.3613],
  "trinity bellwoods":  [43.6478, -79.4154],
  "liberty village":    [43.6383, -79.4202],
  "distillery":         [43.6503, -79.3593],
  "kensington":         [43.6553, -79.4003],
  "junction":           [43.6595, -79.4670],
  "parkdale":           [43.6424, -79.4408],
  "high park":          [43.6469, -79.4629],
  "mimico":             [43.6133, -79.5033],
  "east york":          [43.6918, -79.3251],
  "forest hill":        [43.6921, -79.4214],
  "leaside":            [43.7071, -79.3460],
  "riverdale":          [43.6656, -79.3480],
  "rosedale":           [43.6836, -79.3815],
  "davisville":         [43.6993, -79.3939],
  "don mills":          [43.7468, -79.3388],
  "agincourt":          [43.7861, -79.2783],
  "willowdale":         [43.7713, -79.4131],
  "thornhill":          [43.8097, -79.4338],
  "woodbridge":         [43.7773, -79.5830],
  "yonge eglinton":     [43.7046, -79.3979],
  "yonge":              [43.6532, -79.3832],
  "eglinton":           [43.7046, -79.3979],
  "toronto":            [43.6532, -79.3832],
  "gta":                [43.7000, -79.4200],
};

function getListingCoords(l: Listing): [number, number] | null {
  if (l.lat != null && l.lng != null) return [l.lat, l.lng];
  const needle = [l.neighbourhood, l.city, l.address]
    .filter(Boolean).join(" ").toLowerCase();
  const sortedEntries = Object.entries(NBHD_COORDS)
    .sort((a, b) => b[0].length - a[0].length);
  for (const [key, coords] of sortedEntries) {
    if (needle.includes(key)) return coords;
  }
  return null;
}

/* Flies map to selected listing when selectedId changes */
function MapFlyTo({ listing }: { listing: Listing | null }) {
  const map = useMap();
  useEffect(() => {
    if (!listing) return;
    const coords = getListingCoords(listing);
    if (coords) map.flyTo([coords[0], coords[1]], 15, { duration: 0.8 });
  }, [listing, map]);
  return null;
}

export default function GTAMap({ listings, selectedId, onSelect }: {
  listings: Listing[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
}) {
  const listingsWithCoords = listings
    .map(l => ({ listing: l, coords: getListingCoords(l) }))
    .filter((x): x is { listing: Listing; coords: [number, number] } => x.coords !== null);

  const selected = selectedId ? (listings.find(l => l.id === selectedId) ?? null) : null;

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {/* Leaflet CSS overrides — Terminal Broker dark theme */}
      <style>{`
        .leaflet-container { background: #05060A !important; font-family: 'JetBrains Mono', monospace; }
        .leaflet-control-zoom a {
          background: #0A0D14 !important; border-color: rgba(255,191,0,0.25) !important;
          color: #FFB000 !important; font-family: monospace;
        }
        .leaflet-control-zoom a:hover { background: rgba(255,176,0,0.12) !important; }
        .leaflet-control-attribution {
          background: rgba(5,6,10,0.82) !important; color: #5A5848 !important;
          font-size: 9px !important; border-top: 1px solid rgba(255,191,0,0.12) !important;
        }
        .leaflet-control-attribution a { color: #8A8876 !important; }
        .leaflet-bar { border: 1px solid rgba(255,191,0,0.2) !important; border-radius: 0 !important; box-shadow: none !important; }
        .leaflet-bar a:first-child { border-radius: 0 !important; }
        .leaflet-bar a:last-child  { border-radius: 0 !important; }
      `}</style>

      <MapContainer
        center={[43.65, -79.42]}
        zoom={11}
        style={{ width: "100%", height: "100%" }}
        zoomControl={true}
        attributionControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />
        <MapFlyTo listing={selected} />
        {listingsWithCoords.map(({ listing: l, coords }) => {
          const isDeal = (l.fair_value ?? 0) >= 3;
          const isSelected = l.id === selectedId;
          return (
            <CircleMarker
              key={l.id}
              center={[coords[0], coords[1]]}
              radius={isSelected ? 12 : 7}
              pathOptions={{
                color: "#FFB000",
                weight: isSelected ? 2.5 : 1.5,
                fillColor: isDeal ? "#FFB000" : "transparent",
                fillOpacity: isDeal ? 0.9 : 0,
                opacity: 1,
              }}
              eventHandlers={{ click: () => onSelect?.(l.id) }}
            />
          );
        })}
      </MapContainer>

      {/* Legend — top left, above map tiles */}
      <div style={{
        position: "absolute", top: 20, left: 20, zIndex: 1000,
        background: "var(--bg)", border: "1px solid var(--border)",
        padding: "10px 14px",
        fontFamily: "var(--mono)", fontSize: "0.62rem",
        color: "var(--text-mute)", letterSpacing: "0.1em", textTransform: "uppercase",
        pointerEvents: "none",
      }}>
        <div style={{ color: "var(--accent)", marginBottom: 6, letterSpacing: "0.14em" }}>Legend</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", display: "inline-block", flexShrink: 0 }} />
          Under market
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", border: "1.5px solid var(--accent)", display: "inline-block", flexShrink: 0 }} />
          At market
        </div>
      </div>

      {/* Selected listing card — bottom right (or full-width on mobile via .map-selected-card CSS) */}
      {selected && (
        <div className="map-selected-card" style={{
          position: "absolute", bottom: 20, right: 20, width: 320, zIndex: 1000,
          background: "var(--bg)", border: "1px solid var(--border-strong)",
          overflow: "hidden",
          boxShadow: "0 12px 40px rgba(0,0,0,0.5)",
        }}>
          {selected.photos?.[0] && (
            <img src={selected.photos[0]} alt=""
              style={{ width: "100%", height: 140, objectFit: "cover", display: "block" }} />
          )}
          <div style={{ padding: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
              <div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "0.6rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-mute)" }}>
                  {selected.neighbourhood || selected.city}
                </div>
                <div style={{ fontFamily: "var(--mono)", fontSize: "1.3rem", fontWeight: 600, marginTop: 2 }}>
                  ${selected.price.toLocaleString("en-CA")}
                </div>
              </div>
              {selected.fair_value != null && (
                <span style={{
                  border: `1px solid ${selected.fair_value >= 3 ? "var(--border-strong)" : "var(--border)"}`,
                  padding: "3px 8px", fontFamily: "var(--mono)", fontSize: "0.56rem",
                  letterSpacing: "0.1em", textTransform: "uppercase",
                  color: selected.fair_value >= 3 ? "var(--accent)" : "var(--text-mute)",
                }}>
                  {selected.fair_value >= 3 ? "↓" : "="} {Math.abs(selected.fair_value).toFixed(1)}%
                </span>
              )}
            </div>
            <div style={{ fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text-mute)", marginTop: 6 }}>
              {selected.address}
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 6, fontFamily: "var(--mono)", fontSize: "0.68rem", color: "var(--text)" }}>
              {selected.beds  > 0 && <span>{selected.beds} BD</span>}
              {selected.baths > 0 && <><span style={{ opacity: 0.4 }}>·</span><span>{selected.baths} BA</span></>}
              {selected.sqft  > 0 && <><span style={{ opacity: 0.4 }}>·</span><span>{selected.sqft.toLocaleString()} SF</span></>}
            </div>
            <a href={selected.url} target="_blank" rel="noreferrer" style={{
              display: "block", width: "100%", marginTop: 10, padding: "8px",
              background: "var(--accent)", color: "var(--bg)",
              fontFamily: "var(--mono)", fontSize: "0.68rem",
              letterSpacing: "0.12em", textTransform: "uppercase",
              textDecoration: "none", textAlign: "center", fontWeight: 700,
              boxSizing: "border-box",
            }}>
              Open listing →
            </a>
          </div>
        </div>
      )}

      {/* Empty state */}
      {listingsWithCoords.length === 0 && (
        <div style={{
          position: "absolute", bottom: 20, left: "50%", transform: "translateX(-50%)", zIndex: 1000,
          background: "rgba(10,13,20,0.92)", border: "1px solid var(--border)",
          padding: "8px 16px",
          fontFamily: "var(--mono)", fontSize: "0.58rem",
          textTransform: "uppercase", letterSpacing: "0.12em",
          color: "var(--text-mute)", whiteSpace: "nowrap",
        }}>
          ◆ GTA · Load listings to see pins
        </div>
      )}
    </div>
  );
}
