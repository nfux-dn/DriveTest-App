// Maps any status/verdict string to a themed pill (spec section 33).

interface Props {
  value: string | null | undefined;
  label?: string;
}

export function StatusPill({ value, label }: Props) {
  const normalized = (value ?? "UNKNOWN").toLowerCase();
  return (
    <span className={`pill ${normalized}`}>
      <span className="dot" />
      {label ?? value ?? "—"}
    </span>
  );
}
