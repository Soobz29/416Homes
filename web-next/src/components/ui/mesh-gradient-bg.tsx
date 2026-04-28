"use client"

import { MeshGradient } from "@paper-design/shaders-react"
import type React from "react"

interface MeshGradientBgProps {
  speed?: number
  className?: string
  style?: React.CSSProperties
}

/**
 * Animated mesh-gradient background using 416Homes brand palette.
 * Drop inside any position:relative container and it fills it absolutely.
 *
 * Usage:
 *   <div style={{ position: "relative" }}>
 *     <MeshGradientBg />
 *     {children}
 *   </div>
 */
export function MeshGradientBg({ speed = 0.35, className = "", style }: MeshGradientBgProps) {
  return (
    <MeshGradient
      // Four stops: deep void → elevated dark → dark amber → pure accent
      colors={["#05060A", "#0A0D14", "#1a1200", "#FFB000"]}
      speed={speed}
      distortion={0.6}
      className={`absolute inset-0 w-full h-full ${className}`}
      style={style}
    />
  )
}
