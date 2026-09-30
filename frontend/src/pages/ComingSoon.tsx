export function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-300 py-24 text-center dark:border-slate-700">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="text-slate-500 dark:text-slate-400">Esta página todavía no está lista.</p>
    </div>
  )
}
