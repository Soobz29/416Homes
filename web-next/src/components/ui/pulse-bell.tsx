"use client";

interface PulseBellProps {
  count?: number;
  animate?: boolean;
}

export function PulseBell({ count = 0, animate = true }: PulseBellProps) {
  return (
    <>
      <style>{`
        @keyframes bell-swing {
          0%,100% { transform: rotate(0deg); transform-origin: top center; }
          15%      { transform: rotate(14deg); transform-origin: top center; }
          45%      { transform: rotate(-10deg); transform-origin: top center; }
          65%      { transform: rotate(6deg); transform-origin: top center; }
          80%      { transform: rotate(-3deg); transform-origin: top center; }
        }
        @keyframes badge-pulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(200,169,110,0.5); }
          50%      { box-shadow: 0 0 0 4px rgba(200,169,110,0); }
        }
        .bell-icon { animation: bell-swing 2.4s ease-in-out infinite; }
        .bell-badge { animation: badge-pulse 2s ease-in-out infinite; }
      `}</style>
      <span className="relative inline-flex items-center">
        <svg
          className={`h-4 w-4 text-[#c8a96e] ${animate ? "bell-icon" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {count > 0 && (
          <span className="bell-badge absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full bg-[#c8a96e] font-['DM_Mono',monospace] text-[0.5rem] font-bold text-[#0a0a08]">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </span>
    </>
  );
}
