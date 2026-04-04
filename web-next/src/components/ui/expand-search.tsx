"use client";

import { useState, useRef } from "react";

interface ExpandSearchProps {
  value: string;
  onChange: (v: string) => void;
  onSearch?: (v: string) => void;
  placeholder?: string;
}

export function ExpandSearch({ value, onChange, onSearch, placeholder = "Search listings…" }: ExpandSearchProps) {
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const expanded = focused || value.length > 0;

  return (
    <>
      <style>{`
        .expand-search-wrap {
          display: flex;
          align-items: center;
          border: 1px solid rgba(200,169,110,0.25);
          border-radius: 6px;
          background: rgba(255,255,255,0.03);
          overflow: hidden;
          transition: width 0.35s cubic-bezier(0.34,1.56,0.64,1),
                      border-color 0.2s ease,
                      background 0.2s ease;
          width: 38px;
          cursor: pointer;
        }
        .expand-search-wrap.open {
          width: 200px;
          border-color: rgba(200,169,110,0.6);
          background: rgba(200,169,110,0.06);
          cursor: text;
        }
        .expand-search-icon {
          flex-shrink: 0;
          padding: 0 10px;
          color: #c8a96e;
          display: flex;
          align-items: center;
        }
        .expand-search-input {
          background: transparent;
          border: none;
          outline: none;
          color: #f5f4ef;
          font-family: 'DM Mono', monospace;
          font-size: 0.72rem;
          width: 100%;
          padding: 7px 8px 7px 0;
          opacity: 0;
          transition: opacity 0.2s ease;
        }
        .expand-search-wrap.open .expand-search-input { opacity: 1; }
      `}</style>
      <div
        className={`expand-search-wrap ${expanded ? "open" : ""}`}
        onClick={() => { setFocused(true); inputRef.current?.focus(); }}
      >
        <span className="expand-search-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          ref={inputRef}
          className="expand-search-input"
          type="text"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => { if (e.key === "Enter" && onSearch) onSearch(value); }}
        />
      </div>
    </>
  );
}
