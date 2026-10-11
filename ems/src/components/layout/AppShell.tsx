import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Avatar } from '@/components/ui/Avatar';
import { roleLabel } from '@/lib/labels';
import { clearSession, getSession } from '@/lib/session';
import { crumbsFor, subtitleFor, useDocumentTitle } from './breadcrumbs';
import { SidebarBody } from './Sidebar';
import { BellIcon, ChevronDownIcon, CloseIcon, LogoutIcon, MenuIcon, SearchIcon } from './icons';

function TopBar({ onMenu }: { onMenu: () => void }) {
  const [query, setQuery] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const session = getSession();
  const navigate = useNavigate();
  // RequireAuth guarantees session is valid before AppShell renders.
  const userName = session?.user.name ?? '';

  function signOut() {
    clearSession();
    navigate('/login', { replace: true });
  }

  return (
    <header className="sticky top-0 z-30 border-b border-line-soft bg-card/95 backdrop-blur">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:h-[76px] lg:px-8">
        <button
          type="button"
          onClick={onMenu}
          aria-label="Open navigation"
          className="flex size-10 items-center justify-center rounded-xl text-ink transition-colors hover:bg-nav-active lg:hidden"
        >
          <MenuIcon className="size-6" />
        </button>

        <form
          role="search"
          className="relative hidden w-full max-w-[220px] md:block lg:ml-auto lg:max-w-[240px]"
          onSubmit={(event) => event.preventDefault()}
        >
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3.5 size-[18px] -translate-y-1/2 text-ink-muted" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search anything..."
            aria-label="Search anything"
            className="h-10 w-full rounded-xl border border-line bg-search-bg pr-3 pl-10 text-[13px] text-ink placeholder:text-placeholder focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent/15 focus:outline-none"
          />
        </form>

        <div className="ml-auto flex items-center gap-2 md:gap-3 lg:ml-0">
          <button
            type="button"
            aria-label="Notifications, 1 unread"
            className="relative flex size-10 items-center justify-center rounded-full border border-line-soft bg-white text-ink transition-colors hover:bg-panel-from"
          >
            <BellIcon className="size-5" />
            <span aria-hidden="true" className="absolute top-2 right-2.5 size-1.5 rounded-full bg-danger" />
          </button>
          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className="flex items-center gap-2 rounded-xl px-1.5 py-1 transition-colors hover:bg-panel-from"
            >
              <Avatar name={userName} size="sm" />
              <span className="hidden text-left sm:block">
                <span className="block max-w-[130px] truncate text-[13px] leading-4 font-bold text-ink">
                  {userName}
                </span>
                <span className="block text-[11px] leading-4 text-ink-muted">
                  {session?.user.role ? roleLabel(session.user.role) : ''}
                </span>
              </span>
              <ChevronDownIcon className="hidden size-4 text-ink-muted sm:block" />
            </button>
            {menuOpen && (
              <>
                <button
                  type="button"
                  aria-label="Close account menu"
                  className="fixed inset-0 z-10 cursor-default"
                  onClick={() => setMenuOpen(false)}
                />
                <div role="menu" className="absolute right-0 z-20 mt-2 w-48 rounded-xl border border-line-soft bg-white p-1.5 shadow-pop">
                  <Link
                    to="/app/settings"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                    className="block rounded-lg px-3 py-2 text-sm text-ink transition-colors hover:bg-panel-from"
                  >
                    Profile settings
                  </Link>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={signOut}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-danger transition-colors hover:bg-danger-soft"
                  >
                    <LogoutIcon className="size-4" />
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="px-4 pb-3 md:hidden">
        <form role="search" className="relative" onSubmit={(event) => event.preventDefault()}>
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3.5 size-[18px] -translate-y-1/2 text-ink-muted" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search anything..."
            aria-label="Search anything"
            className="h-10 w-full rounded-xl border border-line bg-search-bg pr-3 pl-10 text-[13px] text-ink placeholder:text-placeholder focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent/15 focus:outline-none"
          />
        </form>
      </div>
    </header>
  );
}

function PageHeading() {
  const { pathname } = useLocation();
  const crumbs = crumbsFor(pathname);
  // CTO and CFO dashboards render their own H1 and subtitle per reference screenshots
  const isCustomHeadingPage =
    pathname === '/app/cto-dashboard' ||
    pathname === '/app/cfo-dashboard' ||
    pathname === '/app/coo-dashboard' ||
    pathname === '/app/hr-dashboard' ||
    pathname === '/app/manager-dashboard' ||
    pathname === '/app/employee-dashboard';

  if (isCustomHeadingPage) {
    return (
      <div className="mb-2">
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-ink-muted">
            {crumbs.map((crumb, index) => (
              <li key={crumb.label} className="flex items-center gap-1.5">
                {index > 0 && (
                  <span aria-hidden="true" className="text-ink-muted/60">
                    /
                  </span>
                )}
                {crumb.to && index < crumbs.length - 1 ? (
                  <NavLink to={crumb.to} className="text-ink-muted transition-colors hover:text-primary">
                    {crumb.label}
                  </NavLink>
                ) : (
                  <span aria-current={index === crumbs.length - 1 ? 'page' : undefined} className={index === crumbs.length - 1 ? 'font-semibold text-ink' : 'text-ink-muted'}>
                    {crumb.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      </div>
    );
  }

  return (
    <div>
      <nav aria-label="Breadcrumb">
        <ol className="flex flex-wrap items-center gap-1 text-lg font-bold sm:text-xl">
          {crumbs.map((crumb, index) => (
            <li key={crumb.label} className="flex items-center gap-1">
              {index > 0 && (
                <span aria-hidden="true" className="text-ink-muted">
                  /
                </span>
              )}
              {crumb.to && index < crumbs.length - 1 ? (
                <NavLink to={crumb.to} className="text-ink transition-colors hover:text-primary">
                  {crumb.label}
                </NavLink>
              ) : (
                <span aria-current={index === crumbs.length - 1 ? 'page' : undefined} className={index === crumbs.length - 1 ? 'text-primary' : 'text-ink'}>
                  {crumb.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
      <p className="mt-0.5 text-xs text-ink-muted">{subtitleFor(pathname)}</p>
    </div>
  );
}

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { pathname } = useLocation();
  useDocumentTitle(pathname);

  return (
    <div className="min-h-screen bg-app-bg">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[228px] border-r border-line-soft bg-white lg:block">
        <SidebarBody />
      </aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div
            className="absolute inset-0 bg-ink/40"
            onClick={() => setDrawerOpen(false)}
            style={{ animation: 'ems-fade-in 150ms ease-out' }}
          />
          <div
            className="absolute inset-y-0 left-0 w-[280px] max-w-[85vw] bg-white shadow-pop"
            style={{ animation: 'ems-drawer-in 200ms ease-out' }}
          >
            <div className="flex h-16 items-center justify-end px-4">
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close navigation"
                className="flex size-10 items-center justify-center rounded-xl text-ink transition-colors hover:bg-nav-active"
              >
                <CloseIcon className="size-6" />
              </button>
            </div>
            <div className="h-[calc(100%-4rem)]">
              <SidebarBody onNavigate={() => setDrawerOpen(false)} />
            </div>
          </div>
        </div>
      )}

      <div className="lg:pl-[228px]">
        <TopBar onMenu={() => setDrawerOpen(true)} />
        <main className="px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
          <PageHeading />
          <div className="mt-4 lg:mt-5">
            <Outlet />
          </div>
          <footer className="mt-6 flex flex-col gap-2 pb-6 text-xs text-ink-muted sm:flex-row sm:items-center sm:justify-between">
            <p>@2026 EMS — Employee Management System</p>
            <p className="flex items-center gap-1.5">
              <span aria-hidden="true" className="size-1.5 rounded-full bg-success" />
              All systems operational
            </p>
          </footer>
        </main>
      </div>
    </div>
  );
}
