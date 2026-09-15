/** Restates the page's one colour rule wherever two series share a chart. */
export default function Legend({
  observed,
  generated,
}: {
  observed: string;
  generated: string;
}) {
  return (
    <p className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink/70">
      <span className="flex items-center gap-2">
        <span aria-hidden className="inline-block w-5 h-0.5 bg-observed" />
        {observed}
      </span>
      <span className="flex items-center gap-2">
        <span aria-hidden className="inline-block w-5 h-0.5 bg-generated" />
        {generated}
      </span>
    </p>
  );
}
