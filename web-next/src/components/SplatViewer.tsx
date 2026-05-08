"use client";

import { useEffect, useRef } from "react";

interface SplatViewerProps {
  splatUrl: string;
}

/**
 * 3D Gaussian Splat viewer using @mkkellogg/gaussian-splats-3d.
 * Dynamically imported (ssr: false) in tours/[id]/page.tsx to avoid SSR crash.
 * Renders .splat / .ply / .ksplat files with orbit + WASD controls.
 */
export default function SplatViewer({ splatUrl }: SplatViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let viewer: InstanceType<typeof import("@mkkellogg/gaussian-splats-3d").Viewer> | undefined;
    let cancelled = false;

    (async () => {
      try {
        const { Viewer } = await import("@mkkellogg/gaussian-splats-3d");
        if (cancelled || !containerRef.current) return;

        viewer = new Viewer({
          cameraUp: [0, -1, 0],
          initialCameraPosition: [-1, -4, 6],
          initialCameraLookAt: [0, 4, 0],
          rootElement: containerRef.current,
          selfDrivenMode: true,
          useBuiltInControls: true,
          useWorker: true,
        });

        await viewer.addSplatScene(splatUrl, {
          streamView: true,
          showLoadingUI: true,
        });

        if (!cancelled) {
          viewer.start();
        }
      } catch (err) {
        console.error("SplatViewer error:", err);
      }
    })();

    return () => {
      cancelled = true;
      try {
        viewer?.dispose();
      } catch {}
    };
  }, [splatUrl]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        background: "#0a0a08",
        position: "relative",
      }}
    />
  );
}
