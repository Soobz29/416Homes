"use client";

import { useRef, useEffect, useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";

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
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const ref = useRef<HTMLDivElement>(null);
  const listId = useRef(`dropdown-list-${Math.random().toString(36).slice(2, 9)}`);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      if (ref.current && !ref.current.contains(target)) {
        const list = document.getElementById(listId.current);
        if (!list || !list.contains(target)) setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useLayoutEffect(() => {
    if (open && ref.current && typeof document !== "undefined") {
      const rect = ref.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
      });
    }
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const label = selected?.label ?? placeholder;

  const dropdownList =
    open && typeof document !== "undefined" ? (
      <div
        id={listId.current}
        role="listbox"
        className="fixed z-[9999] max-h-64 overflow-auto rounded border border-[rgba(200,169,110,0.3)] bg-[#ffffff] shadow-xl"
        style={{
          top: position.top,
          left: position.left,
          width: position.width,
          minWidth: 120,
        }}
      >
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            role="option"
            aria-selected={opt.value === value}
            onClick={() => {
              onChange(opt.value);
              setOpen(false);
            }}
            className="block w-full px-3 py-2 text-left font-['DM Mono',monospace] text-[0.82rem] text-[#0a0a08] hover:bg-[#f0efe8] focus:bg-[#f0efe8] focus:outline-none"
          >
            {opt.label}
          </button>
        ))}
      </div>
    ) : null;

  return (
    <>
      <div ref={ref} className={`relative ${className}`} id={id}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="fi w-full border border-[rgba(200,169,110,0.2)] bg-[rgba(10,10,8,0.8)] px-3 py-2 text-left font-['DM Mono',monospace] text-[0.82rem] text-[#f5f4ef] flex items-center justify-between gap-2"
        >
          <span>{label}</span>
          <span className="text-[0.6rem] opacity-70">{open ? "▲" : "▼"}</span>
        </button>
      </div>
      {dropdownList && createPortal(dropdownList, document.body)}
    </>
  );
}
