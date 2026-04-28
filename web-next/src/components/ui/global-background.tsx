"use client"

import { MeshGradientBg } from "@/components/ui/mesh-gradient-bg"

/**
 * Renders the animated mesh gradient as a full-viewport fixed background.
 * Mounted once in layout.tsx so every page shares a single canvas.
 * z-index: -1 — sits behind all page content.
 */
export function GlobalBackground() {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: -1,
        pointerEvents: "none",
      }}
    >
      <MeshGradientBg speed={0.2} />
    </div>
  )
}
