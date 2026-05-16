"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { createPortal } from "react-dom";

export type DropdownOption = { value: string; label: string };

/**
 * Accessible dropdown with portaled menu.
 *
 * The option list is rendered via React Portal to <body> so it escapes any
 * parent `backdrop-filter`, `transform`, or `overflow` that would otherwise
 * create a stacking context / clip the menu. Previously the dashboard's
 * sticky filter bar (which uses `backdrop-filter: blur(16px)`) trapped the
 * dropdown inside its own stacking context — making the "All GTA" menu
 * paint behind the "My Alerts" card below. The portal fixes that.
 */
export function DropdownSelect({
  options,
  value,
  onChange,
  placeholder = "Select…",
  className = "",
  id,
  ariaLabel,
}: {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  id?: string;
  ariaLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [menuRect, setMenuRect] = useState<{ top: number; left: number; width: number } | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);

  // Compute menu position from the trigger's viewport rect.
  const positionMenu = useCallback(() => {
    if (!triggerRef.current) return;
    const r = triggerRef.current.getBoundingClientRect();
    setMenuRect({ top: r.bottom + 4, left: r.left, width: r.width });
  }, []);

  // Reposition on open, on scroll, on resize. Use capture for scroll so
  // ancestors (sticky filter bar, page scroll) all trigger updates.
  useEffect(() => {
    if (!open) return;
    positionMenu();
    const handler = () => positionMenu();
    window.addEventListener("scroll", handler, true);
    window.addEventListener("resize", handler);
    return () => {
      window.removeEventListener("scroll", handler, true);
      window.removeEventListener("resize", handler);
    };
  }, [open, positionMenu]);

  // Click-outside + Escape close. Uses capture-phase listeners so the menu
  // isn't accidentally closed by its own option-click.
  useEffect(() => {
    if (!open) return;
    function handlePointerOutside(e: MouseEvent | TouchEvent) {
      const target = e.target as Node;
      const insideWrapper = wrapperRef.current?.contains(target);
      const insideMenu = menuRef.current?.contains(target);
      if (!insideWrapper && !insideMenu) setOpen(false);
    }
    function handleEsc(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", handlePointerOutside);
    document.addEventListener("touchstart", handlePointerOutside);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handlePointerOutside);
      document.removeEventListener("touchstart", handlePointerOutside);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const label = selected?.label ?? placeholder;

  const menu = open && menuRect && typeof document !== "undefined"
    ? createPortal(
        <ul
          ref={menuRef}
          role="listbox"
          aria-label={ariaLabel || label}
          style={{
            position: "fixed",
            top: menuRect.top,
            left: menuRect.left,
            width: menuRect.width,
            maxHeight: 240,
            overflowY: "auto",
            zIndex: 9999,
            background: "#141410",
            border: "1px solid rgba(212,175,55,0.35)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
            borderRadius: 4,
            margin: 0,
            padding: 0,
            listStyle: "none",
          }}
        >
          {options.map((opt) => (
            <li key={opt.value} role="option" aria-selected={opt.value === value}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(opt.value);
                  setOpen(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onChange(opt.value);
                    setOpen(false);
                    triggerRef.current?.focus();
                  }
                }}
                className={`block w-full min-h-[40px] px-3 py-2 text-left font-['DM_Mono',monospace] text-[0.92rem] text-[#f5f4ef] hover:bg-[rgba(212,175,55,0.12)] cursor-pointer ${
                  opt.value === value ? "bg-[rgba(212,175,55,0.18)] text-[#D4AF37]" : ""
                }`}
              >
                {opt.label}
              </button>
            </li>
          ))}
        </ul>,
        document.body,
      )
    : null;

  return (
    <div ref={wrapperRef} className={className} id={id} style={{ position: "relative" }}>
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel || label}
        onClick={() => setOpen((o) => !o)}
        className="w-full min-h-[40px] border border-[rgba(212,175,55,0.2)] bg-[rgba(10,10,8,0.8)] px-3 py-2 text-left font-['DM_Mono',monospace] text-[0.92rem] text-[#f5f4ef] flex items-center justify-between gap-2 cursor-pointer"
      >
        <span>{label}</span>
        <span aria-hidden="true" className="text-[0.6rem] opacity-70">{open ? "▲" : "▼"}</span>
      </button>
      {menu}
    </div>
  );
}
