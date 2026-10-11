import logoMark from '../../design-reference/loggo.jpeg';

export function BrandLogo({ showTagline = true }: { showTagline?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <img src={logoMark} alt="EMS" className="size-11 rounded-xl object-contain shadow-xs" />
      <div>
        <p className="text-[28px] leading-none font-extrabold tracking-[-0.02em] text-ink">EMS</p>
        {showTagline && (
          <p className="mt-1 text-[13px] font-medium leading-tight text-ink-muted">
            Employee Management System
          </p>
        )}
      </div>
    </div>
  );
}
