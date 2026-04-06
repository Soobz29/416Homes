"use client";

interface BouncingDotsProps {
  size?: "sm" | "md";
  color?: string;
}

export function BouncingDots({ size = "md", color = "#D4AF37" }: BouncingDotsProps) {
  const dim = size === "sm" ? 6 : 9;
  const gap = size === "sm" ? "gap-1" : "gap-[6px]";

  return (
    <>
      <style>{`
        @keyframes dot-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-${dim + 3}px); opacity: 1; }
        }
        .dot-bounce-1 { animation: dot-bounce 1.2s ease-in-out infinite 0s; }
        .dot-bounce-2 { animation: dot-bounce 1.2s ease-in-out infinite 0.2s; }
        .dot-bounce-3 { animation: dot-bounce 1.2s ease-in-out infinite 0.4s; }
      `}</style>
      <div className={`flex items-center ${gap}`} aria-label="Loading">
        {[1, 2, 3].map((n) => (
          <span
            key={n}
            className={`dot-bounce-${n} inline-block rounded-full`}
            style={{ width: dim, height: dim, background: color }}
          />
        ))}
      </div>
    </>
  );
}
