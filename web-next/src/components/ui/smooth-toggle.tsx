"use client";

import { useCallback } from "react";

interface SmoothToggleProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

export function SmoothToggle({ checked, onChange, disabled }: SmoothToggleProps) {
  const toggle = useCallback(() => {
    if (!disabled) onChange(!checked);
  }, [checked, disabled, onChange]);

  return (
    <>
      <style>{`
        .smooth-toggle-track {
          position: relative;
          width: 40px;
          height: 22px;
          border-radius: 999px;
          cursor: pointer;
          transition: background 0.3s cubic-bezier(0.34,1.56,0.64,1);
          flex-shrink: 0;
        }
        .smooth-toggle-track.on  { background: rgba(200,169,110,0.35); border: 1px solid #c8a96e; }
        .smooth-toggle-track.off { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); }
        .smooth-toggle-track.disabled { opacity: 0.4; cursor: not-allowed; }
        .smooth-toggle-knob {
          position: absolute;
          top: 3px;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          transition: left 0.32s cubic-bezier(0.34,1.56,0.64,1),
                      background 0.3s ease;
        }
        .smooth-toggle-track.on  .smooth-toggle-knob { left: 21px; background: #c8a96e; }
        .smooth-toggle-track.off .smooth-toggle-knob { left: 3px;  background: rgba(255,255,255,0.35); }
      `}</style>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={toggle}
        disabled={disabled}
        title={checked ? "Disable alert" : "Enable alert"}
        className={`smooth-toggle-track ${checked ? "on" : "off"} ${disabled ? "disabled" : ""}`}
      >
        <span className="smooth-toggle-knob" />
      </button>
    </>
  );
}
