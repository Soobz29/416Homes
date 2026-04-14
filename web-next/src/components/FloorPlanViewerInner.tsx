"use client";

import { useEffect, useState } from "react";
import { Viewer } from "@pascal-app/viewer";
import type { Listing } from "@/types";

interface Props {
  listing: Listing;
}

function WebGPUUnsupported() {
  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "12px",
      }}
    >
      <p
        style={{
          fontFamily: "DM Mono, monospace",
          fontSize: "0.8rem",
          color: "#e07060",
        }}
      >
        WebGPU is not supported in this browser.
      </p>
      <p
        style={{
          fontFamily: "DM Mono, monospace",
          fontSize: "0.7rem",
          color: "#6b6b60",
        }}
      >
        Use Chrome 113+ or Edge 113+ for the 3D viewer.
      </p>
    </div>
  );
}

export default function FloorPlanViewerInner({ listing }: Props) {
  const [gpuSupported, setGpuSupported] = useState<boolean | null>(null);

  useEffect(() => {
    setGpuSupported(
      typeof navigator !== "undefined" && "gpu" in navigator
    );
  }, []);

  // Still probing — avoid flash
  if (gpuSupported === null) return null;

  if (!gpuSupported) return <WebGPUUnsupported />;

  // Viewer manages its own Canvas + WebGPU renderer internally.
  // It reads scene state from its Zustand store — empty scene on first load.
  return (
    <div style={{ width: "100%", height: "100%" }}>
      <Viewer />
    </div>
  );
}
