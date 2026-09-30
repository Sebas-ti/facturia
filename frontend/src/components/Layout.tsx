import { NavLink, Outlet } from 'react-router-dom'

import { ThemeToggle } from './ThemeToggle'

const NAV_LINKS = [
  { to: '/', label: 'Inicio', end: true },
  { to: '/upload', label: 'Subir' },
  { to: '/invoices', label: 'Bandeja' },
  { to: '/review', label: 'Revisión' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/evals', label: 'Evals' },
]

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-4 py-4">
          <NavLink to="/" className="text-lg font-semibold tracking-tight">
            Factur<span className="text-brand-600 dark:text-brand-400">IA</span>
          </NavLink>

          <nav className="hidden items-center gap-1 text-sm font-medium sm:flex">
            {NAV_LINKS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 transition ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-900'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <Outlet />
      </main>
    </div>
  )
}
