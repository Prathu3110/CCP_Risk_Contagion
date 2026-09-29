/**
 * A method's name, with its colour carried by a swatch rather than the text.
 *
 * Amber and two of the three baseline greys fall below 4.5:1 against paper, so
 * setting a method's name in its own colour fails WCAG 1.4.3. Darkening the
 * tokens would break the semantic palette the whole page depends on, so the
 * colour moves to a mark beside the label and the label itself is ink.
 */
export default function SeriesName({
  label,
  colour,
  className = "",
}: {
  label: string;
  colour: string;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span
        aria-hidden
        className="inline-block w-3 h-3 shrink-0 rounded-[1px]"
        style={{ backgroundColor: colour }}
      />
      <span>{label}</span>
    </span>
  );
}
