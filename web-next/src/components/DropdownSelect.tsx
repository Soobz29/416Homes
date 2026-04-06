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
}: {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const label = selected?.label ?? placeholder;

  return (
    <div ref={ref} className={`relative ${className}`} id={id}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full border border-[rgba(212,175,55,0.2)] bg-[rgba(10,10,8,0.8)] px-3 py-2 text-left font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] flex items-center justify-between gap-2"
      >
        <span>{label}</span>
        <span className="text-[0.6rem] opacity-70">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 top-full z-50 mt-1 max-h-60 w-full overflow-y-auto rounded border border-[rgba(212,175,55,0.35)] bg-[#141410] shadow-2xl"
        >
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="option"
              aria-selected={opt.value === value}
              onMouseDown={(e) => {
                e.preventDefault(); // prevent blur on trigger before click registers
                onChange(opt.value);
                setOpen(false);
              }}
              className={`block w-full px-3 py-2 text-left font-['DM_Mono',monospace] text-[0.82rem] text-[#f5f4ef] hover:bg-[rgba(212,175,55,0.12)] focus:outline-none ${
                opt.value === value ? "bg-[rgba(212,175,55,0.18)] text-[#D4AF37]" : ""
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
