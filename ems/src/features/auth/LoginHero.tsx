import chipInsights from '@/assets/icons/chip-insights.svg';
import chipPeople from '@/assets/icons/chip-people.svg';
import chipProjects from '@/assets/icons/chip-projects.svg';
import illustration from '@/assets/images/login-illustration.svg';
import { BrandLogo } from '@/components/BrandLogo';

const highlights = [
  { label: 'People & HR', icon: chipPeople },
  { label: 'Projects', icon: chipProjects },
  { label: 'Insights', icon: chipInsights },
] as const;

/** Left brand panel of the login screen (hidden on small screens). */
export function LoginHero() {
  return (
    <aside className="relative hidden overflow-hidden bg-linear-to-b from-panel-from via-panel-via to-panel-to lg:block">
      {/* soft decorative circles from the design */}
      <div
        aria-hidden="true"
        className="absolute -top-[115px] -left-[115px] size-[230px] rounded-full bg-accent-soft"
      />
      <div
        aria-hidden="true"
        className="absolute -bottom-[150px] -left-[60px] size-[300px] rounded-full bg-mint/70"
      />

      <div className="relative flex h-full flex-col px-12 pt-16 pb-8 xl:px-[73px]">
        <BrandLogo />

        <p className="mt-14 text-[11px] font-semibold tracking-[0.06em] text-accent uppercase">
          One workspace. Every team.
        </p>
        <h1 className="mt-3 text-[44px] leading-[1.15] font-bold tracking-[-0.02em] text-ink">
          Work better,
          <br />
          <span className="text-accent">together.</span>
        </h1>
        <p className="mt-2.5 max-w-[330px] text-base leading-6 text-ink-body">
          Bring your people, projects and leads into one clear view of the work that matters.
        </p>

        <ul className="mt-7 flex flex-wrap gap-3">
          {highlights.map((item) => (
            <li
              key={item.label}
              className="flex h-11 w-[165px] items-center gap-3 rounded-2xl border border-line-soft bg-white px-3 shadow-chip"
            >
              <img src={item.icon} alt="" aria-hidden="true" className="size-7" />
              <span className="text-[13px] font-semibold text-ink">{item.label}</span>
            </li>
          ))}
        </ul>

        <img
          src={illustration}
          alt="A team member working at a desk beside a team overview card and a project pulse board"
          className="mt-12 w-full max-w-[553px] xl:mt-14"
        />
      </div>
    </aside>
  );
}
