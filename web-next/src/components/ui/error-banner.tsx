interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 border border-[rgba(192,57,43,0.4)] bg-[rgba(192,57,43,0.08)] px-4 py-3 font-['DM_Mono',monospace] text-[0.75rem] text-[#e07060]"
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="shrink-0 leading-none text-[#6b6b60] transition-colors hover:text-[#f5f4ef]"
          aria-label="Dismiss error"
        >
          ×
        </button>
      )}
    </div>
  );
}
