"use client";

import { useEffect, useState } from "react";
import { Viewer, useViewer } from "@pascal-app/viewer";
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
        background: "#0f0f0b",
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

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function FloorPlanViewerInner({ listing: _listing }: Props) {
  const [gpuSupported, setGpuSupported] = useState<boolean | null>(null);
  const setTheme = useViewer((state) => state.setTheme);

  // Force dark theme to match 416Homes UI
  useEffect(() => {
    setTheme("dark");
  }, [setTheme]);

  useEffect(() => {
    // Must run client-side — navigator is not available during SSR.
    // Intentional setState-in-effect: this is a one-time capability probe.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setGpuSupported(typeof navigator !== "undefined" && "gpu" in navigator);
  }, []);

  // Still probing — show dark placeholder to avoid white flash
  if (gpuSupported === null) {
    return <div style={{ width: "100%", height: "100%", background: "#1f2433" }} />;
  }

  if (!gpuSupported) return <WebGPUUnsupported />;

  // Viewer manages its own Canvas + WebGPU renderer internally.
  // It reads scene state from its Zustand store — empty scene on first load.
  return (
    <div style={{ width: "100%", height: "100%" }}>
      <Viewer />
    </div>
  );
}
