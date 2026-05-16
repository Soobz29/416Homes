"use client";

import { useRef, useEffect, useState } from "react";

export type DropdownOption = { value: string; label: string };

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
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function handlePointerOutside(e: MouseEvent | TouchEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEsc(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    if (open) {
      document.addEventListener("mousedown", handlePointerOutside);
      document.addEventListener("touchstart", handlePointerOutside);
      document.addEventListener("keydown", handleEsc);
    }
    return () => {
      document.removeEventListener("mousedown", handlePointerOutside);
      document.removeEventListener("touchstart", handlePointerOutside);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const label = selected?.label ?? placeholder;

  return (
    <div ref={ref} className={`relative ${className}`} id={id}>
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

      {open && (
        <ul
          role="listbox"
          aria-label={ariaLabel || label}
          className="absolute left-0 top-full z-50 mt-1 max-h-60 w-full overflow-y-auto rounded border border-[rgba(212,175,55,0.35)] bg-[#141410] shadow-2xl list-none m-0 p-0"
        >
          {options.map((opt) => (
            <li key={opt.value} role="option" aria-selected={opt.value === value}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault(); // prevent blur on trigger before click registers
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
        </ul>
      )}
    </div>
  );
}
