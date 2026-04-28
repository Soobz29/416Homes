"use client"

import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type WheelEvent,
  type TouchEvent,
} from "react"
import { motion } from "framer-motion"
import { MeshGradientBg } from "@/components/ui/mesh-gradient-bg"

export interface ScrollExpandHeroProps {
  mediaSrc: string
  posterSrc?: string
  /** Title split into two words at first space — left word moves left, rest moves right */
  title?: string
  /** Smaller label shown below the expanding frame */
  date?: string
  scrollToExpand?: string
  children?: ReactNode
}

/**
 * Scroll-driven expanding video hero.
 * Background is always the animated MeshGradient (no static image needed).
 * Locks page scroll while expanding; releases once fully expanded.
 * Adapted for the 416Homes Terminal Broker palette (amber accent, no radius).
 */
export default function ScrollExpandHero({
  mediaSrc,
  posterSrc,
  title,
  date,
  scrollToExpand = "Scroll to expand preview",
  children,
}: ScrollExpandHeroProps) {
  const [scrollProgress, setScrollProgress] = useState(0)
  const [showContent, setShowContent] = useState(false)
  const [fullyExpanded, setFullyExpanded] = useState(false)
  const [touchStartY, setTouchStartY] = useState(0)
  const [isMobile, setIsMobile] = useState(false)
  const [isMuted, setIsMuted] = useState(true)
  const videoRef = useRef<HTMLVideoElement>(null)

  /* Reset state when key props change */
  useEffect(() => {
    setScrollProgress(0)
    setShowContent(false)
    setFullyExpanded(false)
    setIsMuted(true)
    if (videoRef.current) videoRef.current.muted = true
  }, [mediaSrc])

  /* Resize listener */
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener("resize", check)
    return () => window.removeEventListener("resize", check)
  }, [])

  /* Wheel / touch / scroll handlers */
  useEffect(() => {
    const onWheel = (e: Event) => {
      const we = e as unknown as WheelEvent
      if (fullyExpanded && we.deltaY < 0 && window.scrollY <= 5) {
        setFullyExpanded(false)
        we.preventDefault()
      } else if (!fullyExpanded) {
        we.preventDefault()
        const delta = we.deltaY * 0.0009
        const next = Math.min(Math.max(scrollProgress + delta, 0), 1)
        setScrollProgress(next)
        if (next >= 1) { setFullyExpanded(true); setShowContent(true) }
        else if (next < 0.75) setShowContent(false)
      }
    }

    const onTouchStart = (e: Event) => {
      const te = e as unknown as TouchEvent
      setTouchStartY(te.touches[0].clientY)
    }

    const onTouchMove = (e: Event) => {
      const te = e as unknown as TouchEvent
      if (!touchStartY) return
      const touchY = te.touches[0].clientY
      const deltaY = touchStartY - touchY
      if (fullyExpanded && deltaY < -20 && window.scrollY <= 5) {
        setFullyExpanded(false)
        te.preventDefault()
      } else if (!fullyExpanded) {
        te.preventDefault()
        const factor = deltaY < 0 ? 0.008 : 0.005
        const next = Math.min(Math.max(scrollProgress + deltaY * factor, 0), 1)
        setScrollProgress(next)
        if (next >= 1) { setFullyExpanded(true); setShowContent(true) }
        else if (next < 0.75) setShowContent(false)
        setTouchStartY(touchY)
      }
    }

    const onTouchEnd = () => setTouchStartY(0)
    const onScroll = () => { if (!fullyExpanded) window.scrollTo(0, 0) }

    window.addEventListener("wheel", onWheel, { passive: false })
    window.addEventListener("scroll", onScroll)
    window.addEventListener("touchstart", onTouchStart, { passive: false })
    window.addEventListener("touchmove", onTouchMove, { passive: false })
    window.addEventListener("touchend", onTouchEnd)

    return () => {
      window.removeEventListener("wheel", onWheel)
      window.removeEventListener("scroll", onScroll)
      window.removeEventListener("touchstart", onTouchStart)
      window.removeEventListener("touchmove", onTouchMove)
      window.removeEventListener("touchend", onTouchEnd)
    }
  }, [scrollProgress, fullyExpanded, touchStartY])

  const toggleMute = () => {
    if (!videoRef.current) return
    videoRef.current.muted = !videoRef.current.muted
    setIsMuted(videoRef.current.muted)
  }

  const mediaW = 300 + scrollProgress * (isMobile ? 650 : 1250)
  const mediaH = 400 + scrollProgress * (isMobile ? 200 : 400)
  const textShift = scrollProgress * (isMobile ? 180 : 150)

  const firstWord = title ? title.split(" ")[0] : ""
  const rest = title ? title.split(" ").slice(1).join(" ") : ""

  return (
    <div className="overflow-x-hidden" style={{ background: "var(--bg)" }}>
      <section
        className="relative flex flex-col items-center justify-start"
        style={{ minHeight: "100dvh" }}
      >
        <div className="relative w-full flex flex-col items-center" style={{ minHeight: "100dvh" }}>

          {/* ── Animated mesh gradient background — fades out as video expands ── */}
          <motion.div
            className="absolute inset-0 z-0 h-full"
            initial={{ opacity: 1 }}
            animate={{ opacity: 1 - scrollProgress * 0.8 }}
            transition={{ duration: 0.1 }}
          >
            <MeshGradientBg speed={0.3} />
            {/* Subtle dark vignette so title text stays readable */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "radial-gradient(ellipse at center, transparent 30%, rgba(5,6,10,0.55) 100%)",
              }}
            />
          </motion.div>

          <div className="container mx-auto flex flex-col items-center justify-start relative z-10">
            <div className="flex flex-col items-center justify-center w-full relative" style={{ height: "100dvh" }}>

              {/* ── Expanding video frame ── */}
              <div
                className="absolute z-0 top-1/2 left-1/2"
                style={{
                  transform: "translate(-50%, -50%)",
                  width: `${mediaW}px`,
                  height: `${mediaH}px`,
                  maxWidth: "95vw",
                  maxHeight: "85vh",
                  boxShadow: `0 0 80px rgba(255,176,0,${0.08 + scrollProgress * 0.25})`,
                }}
              >
                <div className="relative w-full h-full">
                  <video
                    ref={videoRef}
                    src={mediaSrc}
                    poster={posterSrc}
                    autoPlay
                    muted
                    loop
                    playsInline
                    preload="auto"
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />

                  {/* Veil that lifts as you scroll */}
                  <motion.div
                    className="absolute inset-0"
                    initial={{ opacity: 0.65 }}
                    animate={{ opacity: 0.45 - scrollProgress * 0.35 }}
                    transition={{ duration: 0.2 }}
                    style={{ background: "rgba(5,6,10,0.4)", pointerEvents: "none" }}
                  />

                  {/* Amber border that brightens while expanding */}
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      border: `1px solid rgba(255,176,0,${0.20 + scrollProgress * 0.55})`,
                      pointerEvents: "none",
                    }}
                  />

                  {/* ── Mute / unmute toggle — bottom-right corner ── */}
                  <button
                    onClick={toggleMute}
                    title={isMuted ? "Unmute" : "Mute"}
                    style={{
                      position: "absolute",
                      bottom: 12,
                      right: 12,
                      zIndex: 20,
                      width: 36,
                      height: 36,
                      background: "rgba(5,6,10,0.75)",
                      border: "1px solid rgba(255,176,0,0.40)",
                      color: "var(--accent)",
                      fontFamily: "var(--mono)",
                      fontSize: "0.85rem",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backdropFilter: "blur(6px)",
                      transition: "border-color 0.2s, background 0.2s",
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = "rgba(255,176,0,0.15)"
                      e.currentTarget.style.borderColor = "rgba(255,176,0,0.70)"
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = "rgba(5,6,10,0.75)"
                      e.currentTarget.style.borderColor = "rgba(255,176,0,0.40)"
                    }}
                  >
                    {isMuted ? "🔇" : "🔊"}
                  </button>
                </div>

                {/* Date / price label + scroll hint — below the frame */}
                <div
                  className="flex flex-col items-center text-center relative z-10 mt-3"
                  style={{ fontFamily: "var(--mono)" }}
                >
                  {date && (
                    <p
                      style={{
                        fontSize: "0.72rem",
                        letterSpacing: "0.18em",
                        textTransform: "uppercase",
                        color: "var(--accent)",
                        transform: `translateX(-${textShift}vw)`,
                        transition: "none",
                      }}
                    >
                      {date}
                    </p>
                  )}
                  {scrollProgress < 0.98 && (
                    <p
                      style={{
                        fontSize: "0.6rem",
                        letterSpacing: "0.14em",
                        textTransform: "uppercase",
                        color: "var(--text-mute)",
                        transform: `translateX(${textShift}vw)`,
                        transition: "none",
                        marginTop: 4,
                      }}
                    >
                      {scrollToExpand}
                    </p>
                  )}
                </div>
              </div>

              {/* ── Split title — words fly apart as media expands ── */}
              {title && (
                <div
                  className="flex items-center justify-center text-center gap-4 w-full relative z-10 flex-col"
                  style={{ pointerEvents: "none" }}
                >
                  <h2
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: "clamp(2.4rem, 4.5vw, 5.2rem)",
                      fontWeight: 700,
                      letterSpacing: "-0.02em",
                      color: "var(--text)",
                      transform: `translateX(-${textShift}vw)`,
                      transition: "none",
                      margin: 0,
                    }}
                  >
                    {firstWord}
                  </h2>
                  <h2
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: "clamp(2.4rem, 4.5vw, 5.2rem)",
                      fontWeight: 700,
                      letterSpacing: "-0.02em",
                      color: "var(--accent)",
                      transform: `translateX(${textShift}vw)`,
                      transition: "none",
                      margin: 0,
                    }}
                  >
                    {rest}
                  </h2>
                </div>
              )}
            </div>

            {/* Content revealed after full expansion */}
            <motion.section
              initial={{ opacity: 0 }}
              animate={{ opacity: showContent ? 1 : 0 }}
              transition={{ duration: 0.7 }}
              style={{ width: "100%" }}
            >
              {children}
            </motion.section>
          </div>
        </div>
      </section>
    </div>
  )
}
