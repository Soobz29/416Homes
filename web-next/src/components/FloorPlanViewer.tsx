"use client";

import dynamic from "next/dynamic";
import type { Listing } from "@/types";

// Dynamically imported with ssr:false so that all R3F / Three.js / WebGPU
// code is kept out of the server bundle entirely.
const Inner = dynamic(() => import("@/components/FloorPlanViewerInner"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        display: "flex",
        height: "100%",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <span
        style={{
          fontFamily: "DM Mono, monospace",
          fontSize: "0.72rem",
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#6b6b60",
        }}
      >
        Loading 3D viewer…
      </span>
    </div>
  ),
});

export function FloorPlanViewer({ listing }: { listing: Listing }) {
  return <Inner listing={listing} />;
}
