"use client";

/**
 * Terminal Broker design-system primitives.
 *
 * One source of truth for the buttons, eyebrows, and section wrappers used
 * across the marketing pages. Replaces the inline copies that previously
 * lived in `page.tsx`, `video/page.tsx`, `tours/page.tsx`, etc.
 *
 * All colours come from CSS variables in `globals.css` — no hex literals.
 */

import Link from "next/link";
import * as React from "react";

/* ─── Button ───────────────────────────────────────────────────────── */

type BtnSize = "default" | "sm";
type BtnVariant = "primary" | "ghost";

interface BtnBaseProps {
  children: React.ReactNode;
  variant?: BtnVariant;
  size?: BtnSize;
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  fullWidth?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

function buttonStyle({ variant = "primary", size = "default", fullWidth, disabled }: BtnBaseProps): React.CSSProperties {
  const small = size === "sm";
  const base: React.CSSProperties = {
    display: "inline-block",
    padding: small ? "10px 18px" : "14px 28px",
    fontFamily: "var(--mono)",
    fontWeight: variant === "primary" ? 700 : 400,
    fontSize: small ? "0.68rem" : variant === "primary" ? "0.82rem" : "0.72rem",
    letterSpacing: variant === "primary" ? "0.08em" : "0.12em",
    textTransform: "uppercase",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.55 : 1,
    textDecoration: "none",
    whiteSpace: "nowrap",
    transition: "background 0.2s ease, border-color 0.2s ease, color 0.2s ease",
    border: variant === "ghost" ? "1px solid var(--border-strong)" : "none",
    width: fullWidth ? "100%" : undefined,
    textAlign: fullWidth ? "center" : undefined,
  };
  if (variant === "primary") {
    base.background = "var(--accent)";
    base.color = "var(--bg)";
    base.boxShadow = "0 0 22px rgba(255,176,0,0.30), inset 0 1px 0 rgba(255,255,255,0.14)";
  } else {
    base.background = "transparent";
    base.color = "var(--text)";
  }
  return base;
}

/**
 * Single button primitive for the Terminal Broker theme.
 *
 * Usage:
 *   <TerminalButton href="/dashboard">Browse listings →</TerminalButton>
 *   <TerminalButton variant="ghost" onClick={...}>Reset filters</TerminalButton>
 *   <TerminalButton size="sm" href="/#alert">Set my alert</TerminalButton>
 */
export function TerminalButton(props: BtnBaseProps) {
  const { children, href, onClick, disabled, type = "button", className, style } = props;
  const merged: React.CSSProperties = { ...buttonStyle(props), ...(style || {}) };
  if (href && !disabled) {
    return (
      <Link href={href} className={className} style={merged}>
        {children}
      </Link>
    );
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={className}
      style={merged}
    >
      {children}
    </button>
  );
}

/* ─── Eyebrow ──────────────────────────────────────────────────────── */

interface EyebrowProps {
  children: React.ReactNode;
  /** Show the short amber line to the left of the label. */
  line?: boolean;
}

export function Eyebrow({ children, line }: EyebrowProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontFamily: "var(--mono)",
        fontSize: "0.62rem",
        textTransform: "uppercase",
        letterSpacing: "0.18em",
        color: "var(--accent)",
      }}
    >
      {line && (
        <span
          style={{
            height: 1,
            width: 28,
            background: "var(--accent)",
            flexShrink: 0,
          }}
        />
      )}
      {children}
    </div>
  );
}

/* ─── Section ──────────────────────────────────────────────────────── */

interface SectionProps {
  /** Optional anchor id for in-page links. */
  id?: string;
  /** Eyebrow text shown above the headline. */
  eyebrow?: string;
  /** Section headline — rendered as `h2`. */
  title?: React.ReactNode;
  /** Optional sub-headline / lede paragraph. */
  sub?: React.ReactNode;
  /** Section body content. */
  children: React.ReactNode;
  /** Drop the bottom 1px border (used by the last section). */
  hideBorder?: boolean;
}

/**
 * Consistent section wrapper used by the marketing pages.
 *
 * Provides a 1320px max-width container, generous vertical rhythm, an optional
 * eyebrow + headline + sub, and a bottom border. Always picks up `var(--border)`
 * and `var(--mono)` so it stays in sync with the global theme.
 */
export function Section({ id, eyebrow, title, sub, children, hideBorder }: SectionProps) {
  return (
    <section
      id={id}
      className="sec-wrap sec-pad-lg"
      style={{
        maxWidth: 1320,
        margin: "0 auto",
        padding: "96px 56px",
        borderBottom: hideBorder ? "none" : "1px solid var(--border)",
      }}
    >
      {(eyebrow || title || sub) && (
        <div style={{ marginBottom: 48 }}>
          {eyebrow && <Eyebrow line>{eyebrow}</Eyebrow>}
          {title && (
            <h2
              style={{
                fontFamily: "var(--mono)",
                fontSize: "clamp(2rem, 3.2vw, 3.4rem)",
                fontWeight: 700,
                lineHeight: 1.02,
                letterSpacing: "-0.015em",
                margin: eyebrow ? "20px 0 0" : "0",
                maxWidth: "28ch",
              }}
            >
              {title}
            </h2>
          )}
          {sub && (
            <p
              style={{
                fontFamily: "var(--mono)",
                fontSize: "0.85rem",
                lineHeight: 1.8,
                color: "var(--text-mute)",
                maxWidth: "62ch",
                marginTop: 20,
                marginBottom: 0,
              }}
            >
              {sub}
            </p>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
