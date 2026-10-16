import type { Machine, Status } from "../api";

const STATUS_LABEL: Record<Status, string> = {
  ok: "Normal",
  warning: "Warning",
  alarm: "Alarm",
  no_data: "No data",
};

function fmt(value: number | null | undefined, unit: string, digits = 1): string {
  return value === null || value === undefined ? "–" : `${value.toFixed(digits)} ${unit}`;
}

/** Replayed machines carry the dataset name; everything else is simulated. */
export function isReplayed(m: Machine): boolean {
  return m.data_source !== "simulated";
}

interface Props {
  machines: Machine[] | null;
  error: string | null;
  onAsk: (machine: Machine) => void;
}

export function MachineSidebar({ machines, error, onAsk }: Props) {
  const alarms = machines?.filter((m) => m.status === "alarm").length ?? 0;
  return (
    <aside className="sidebar" aria-label="Machine status">
      <div className="sidebar-head">
        <h2>Machines</h2>
        {machines && (
          <span className={`pill ${alarms ? "pill-alarm" : "pill-ok"}`}>
            {alarms ? `${alarms} in alarm` : "All normal"}
          </span>
        )}
      </div>
      {error && <p className="sidebar-error">Live data unavailable: {error}</p>}
      {!machines && !error && <p className="muted">Loading…</p>}
      <ul className="machine-list">
        {machines?.map((m) => (
          <li key={m.id}>
            <button
              type="button"
              className={`machine machine-${m.status}`}
              onClick={() => onAsk(m)}
              title={`Ask about ${m.id}`}
            >
              <div className="machine-row">
                <span className={`dot dot-${m.status}`} aria-hidden />
                <span className="machine-id">{m.id}</span>
                <span className="machine-name">{m.name}</span>
                <span className={`status status-${m.status}`}>{STATUS_LABEL[m.status]}</span>
              </div>
              <div className="machine-meta">
                {m.model} · {m.location}
              </div>
              {isReplayed(m) && (
                <div className="data-source" title="Readings replayed from a public dataset">
                  Real data · {m.data_source}
                </div>
              )}
              {m.latest && (
                <dl className="readings">
                  <div>
                    <dt>Vib</dt>
                    <dd>{fmt(m.latest.vibration_mm_s, "mm/s")}</dd>
                  </div>
                  <div>
                    <dt>Temp</dt>
                    <dd>{fmt(m.latest.temperature_c, "°C")}</dd>
                  </div>
                  <div>
                    <dt>Press</dt>
                    <dd>{fmt(m.latest.pressure_bar, "bar")}</dd>
                  </div>
                  <div>
                    <dt>Curr</dt>
                    <dd>{fmt(m.latest.current_a, "A")}</dd>
                  </div>
                  {m.latest.load_duty_pct != null && (
                    <div>
                      <dt>Duty</dt>
                      <dd>{fmt(m.latest.load_duty_pct, "%", 0)}</dd>
                    </div>
                  )}
                  {m.latest.bearing_accel_g != null && (
                    <div>
                      <dt>Brg acc</dt>
                      <dd>{fmt(m.latest.bearing_accel_g, "g", 2)}</dd>
                    </div>
                  )}
                </dl>
              )}
              {m.flags.map((f) => (
                <p key={f.metric} className={`flag flag-${f.level}`}>
                  {f.message}
                </p>
              ))}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
