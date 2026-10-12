const STEPS = ["Create account", "Company setup", "Invite team"];

/** The 3-step onboarding indicator from screens 05 and 06. */
export function Steps({ current }: { current: 1 | 2 | 3 }) {
  return (
    <div className="steps" aria-label={`Step ${current} of 3`}>
      {STEPS.map((s, i) => (
        <div key={s} className={`step ${i + 1 < current ? "done" : i + 1 === current ? "current" : ""}`}>
          <i>{i + 1 < current ? "✓" : i + 1}</i>
          {s}
        </div>
      ))}
    </div>
  );
}
