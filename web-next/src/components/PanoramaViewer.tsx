"use client";

/**
 * PanoramaViewer — interactive 360° equirectangular sphere viewer.
 * Ported from text-to-360 (https://github.com/ilkerzg/text-to-360).
 *
 * Usage:
 *   const PanoramaViewer = dynamic(() => import("@/components/PanoramaViewer"), { ssr: false });
 *   <PanoramaViewer url="https://..." style={{ position:"absolute", inset:0, width:"100%", height:"100%" }} />
 */

import { useEffect, useRef } from "react";
import * as THREE from "three";

interface Props {
  url: string;
  style?: React.CSSProperties;
}

export default function PanoramaViewer({ url, style }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer;
    material: THREE.MeshBasicMaterial;
    camera: THREE.PerspectiveCamera;
    scene: THREE.Scene;
    geometry: THREE.SphereGeometry;
    rafId: number;
    lon: number;
    lat: number;
  } | null>(null);
  const loadingRef = useRef<HTMLDivElement>(null);

  // ── One-time scene setup ────────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const w = container.clientWidth || 800;
    const h = container.clientHeight || 500;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h);
    renderer.setClearColor(0x050505, 1);
    container.appendChild(renderer.domElement);
    renderer.domElement.style.display = "block";

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, w / h, 0.1, 1100);

    // Inverted sphere so camera looks at inner surface
    const geometry = new THREE.SphereGeometry(500, 96, 64);
    const material = new THREE.MeshBasicMaterial({ side: THREE.BackSide });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // ── Drag state ──
    let lon = 0, lat = 0;
    let lonStart = 0, latStart = 0;
    let startX = 0, startY = 0;
    let dragging = false;

    const onPointerDown = (e: PointerEvent) => {
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      lonStart = lon;
      latStart = lat;
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    };
    const onPointerMove = (e: PointerEvent) => {
      if (!dragging) return;
      lon = lonStart - (e.clientX - startX) * 0.2;
      lat = Math.max(-85, Math.min(85, latStart + (e.clientY - startY) * 0.2));
    };
    const onPointerUp = () => { dragging = false; };

    // ── Zoom ──
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      camera.fov = Math.max(30, Math.min(110, camera.fov + e.deltaY * 0.05));
      camera.updateProjectionMatrix();
    };

    container.addEventListener("pointerdown", onPointerDown);
    container.addEventListener("pointermove", onPointerMove);
    container.addEventListener("pointerup", onPointerUp);
    container.addEventListener("pointerleave", onPointerUp);
    container.addEventListener("wheel", onWheel, { passive: false });

    // ── Resize ──
    const ro = new ResizeObserver(() => {
      const rw = container.clientWidth;
      const rh = container.clientHeight;
      if (rw > 0 && rh > 0) {
        renderer.setSize(rw, rh);
        camera.aspect = rw / rh;
        camera.updateProjectionMatrix();
      }
    });
    ro.observe(container);

    // ── Animation loop ──
    let rafId = 0;
    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const phi = THREE.MathUtils.degToRad(90 - lat);
      const theta = THREE.MathUtils.degToRad(lon);
      camera.lookAt(
        500 * Math.sin(phi) * Math.cos(theta),
        500 * Math.cos(phi),
        500 * Math.sin(phi) * Math.sin(theta),
      );
      renderer.render(scene, camera);
    };
    animate();

    stateRef.current = { renderer, material, camera, scene, geometry, rafId, lon, lat };
    // Expose lon/lat as mutable via closure; store refs for cleanup
    Object.defineProperty(stateRef.current, "lon", {
      get: () => lon, set: (v) => { lon = v; }, configurable: true,
    });
    Object.defineProperty(stateRef.current, "lat", {
      get: () => lat, set: (v) => { lat = v; }, configurable: true,
    });

    return () => {
      cancelAnimationFrame(rafId);
      ro.disconnect();
      container.removeEventListener("pointerdown", onPointerDown);
      container.removeEventListener("pointermove", onPointerMove);
      container.removeEventListener("pointerup", onPointerUp);
      container.removeEventListener("pointerleave", onPointerUp);
      container.removeEventListener("wheel", onWheel);
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
      geometry.dispose();
      material.map?.dispose();
      material.dispose();
      renderer.dispose();
      stateRef.current = null;
    };
  }, []); // run once

  // ── Texture swap when url changes ───────────────────────────────────
  useEffect(() => {
    if (!url) return;
    // Show loading overlay
    if (loadingRef.current) loadingRef.current.style.display = "flex";

    const loader = new THREE.TextureLoader();
    loader.crossOrigin = "anonymous";
    let cancelled = false;

    loader.load(
      url,
      (texture) => {
        if (cancelled) { texture.dispose(); return; }
        texture.colorSpace = THREE.SRGBColorSpace;
        const state = stateRef.current;
        if (state) {
          const old = state.material.map;
          state.material.map = texture;
          state.material.needsUpdate = true;
          if (old) old.dispose();
        }
        if (loadingRef.current) loadingRef.current.style.display = "none";
      },
      undefined,
      (err) => {
        console.warn("[PanoramaViewer] texture load error:", err);
        if (loadingRef.current) loadingRef.current.style.display = "none";
      },
    );

    return () => { cancelled = true; };
  }, [url]);

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", cursor: "grab", background: "#050505", overflow: "hidden", ...style }}
    >
      {/* Loading overlay */}
      <div
        ref={loadingRef}
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "rgba(5,5,5,0.85)",
          zIndex: 10,
          pointerEvents: "none",
        }}
      >
        <div style={{
          width: 32,
          height: 32,
          border: "2px solid rgba(200,169,110,0.3)",
          borderTopColor: "#c8a96e",
          borderRadius: "50%",
          animation: "panorama-spin 0.8s linear infinite",
        }} />
        <style>{`@keyframes panorama-spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );
}
