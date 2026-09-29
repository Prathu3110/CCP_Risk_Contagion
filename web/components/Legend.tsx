/** Restates the page's colour rule wherever several series share a chart. */
export default function Legend({
  series,
}: {
  series: { key: string; label: string; colour: string }[];
}) {
  return (
    <p className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink/80">
      {series.map((entry) => (
        <span key={entry.key} className="flex items-center gap-2">
          <span
            aria-hidden
            className="inline-block w-4 h-3 rounded-[1px]"
            style={{ backgroundColor: entry.colour }}
          />
          {entry.label}
        </span>
      ))}
    </p>
  );
}
