"use client";

import { useEffect, useState } from "react";
import { Viewer, useViewer } from "@pascal-app/viewer";
import { useScene, SlabNode, WallNode } from "@pascal-app/core";
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

  // Seed a default 8×6m room once WebGPU is confirmed available.
  useEffect(() => {
    if (!gpuSupported) return;

    const { loadScene, createNodes, nodes } = useScene.getState();

    // Creates Site → Building → Level hierarchy (no-op if already exists)
    loadScene();

    // Find the level node so we can parent geometry to it
    const allNodes = useScene.getState().nodes;
    const levelNode = Object.values(allNodes).find((n) => n.type === "level");
    if (!levelNode) return;

    // Only seed if the level has no geometry children yet
    const levelChildren = "children" in levelNode ? (levelNode as { children: string[] }).children : [];
    const hasGeometry = levelChildren.some((id) => {
      const child = allNodes[id as keyof typeof allNodes];
      return child && (child.type === "slab" || child.type === "wall");
    });
    if (hasGeometry) return;

    // 8m wide × 6m deep room (coordinates in metres, X/Z plane)
    const slab = SlabNode.parse({
      polygon: [[-4, -3], [4, -3], [4, 3], [-4, 3]],
      elevation: 0.05,
    });
    const wallSouth = WallNode.parse({ start: [-4, -3] as [number, number], end: [4, -3] as [number, number] });
    const wallEast  = WallNode.parse({ start: [4, -3]  as [number, number], end: [4, 3]  as [number, number] });
    const wallNorth = WallNode.parse({ start: [4, 3]   as [number, number], end: [-4, 3] as [number, number] });
    const wallWest  = WallNode.parse({ start: [-4, 3]  as [number, number], end: [-4, -3] as [number, number] });

    createNodes([
      { node: slab,      parentId: levelNode.id },
      { node: wallSouth, parentId: levelNode.id },
      { node: wallEast,  parentId: levelNode.id },
      { node: wallNorth, parentId: levelNode.id },
      { node: wallWest,  parentId: levelNode.id },
    ]);
  // `nodes` from destructure is intentionally not listed — we re-read via getState() after loadScene()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gpuSupported]);

  // Still probing — show dark placeholder to avoid white flash
  if (gpuSupported === null) {
    return <div style={{ width: "100%", height: "100%", background: "#1f2433" }} />;
  }

  if (!gpuSupported) return <WebGPUUnsupported />;

  // Viewer manages its own Canvas + WebGPU renderer internally.
  // Scene is pre-seeded with a default 8×6m room above.
  return (
    <div style={{ width: "100%", height: "100%" }}>
      <Viewer />
    </div>
  );
}
