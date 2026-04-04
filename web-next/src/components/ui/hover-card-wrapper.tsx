"use client";

import { ReactNode } from "react";

interface HoverCardWrapperProps {
  children: ReactNode;
  className?: string;
}

export function HoverCardWrapper({ children, className = "" }: HoverCardWrapperProps) {
  return (
    <>
      <style>{`
        .hover-card-lift {
          transition: transform 0.28s cubic-bezier(0.34,1.56,0.64,1),
                      box-shadow 0.28s ease;
          will-change: transform;
        }
        .hover-card-lift:hover {
          transform: translateY(-6px) scale(1.012);
          box-shadow: 0 16px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(200,169,110,0.35);
        }
      `}</style>
      <div className={`hover-card-lift ${className}`}>{children}</div>
    </>
  );
}
