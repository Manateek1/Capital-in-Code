import summary from "./summary.json";
import "./yield-curve.css";

const REPOSITORY = "https://github.com/Manateek1/Capital-in-Code";
const PROJECT_PATH = `${REPOSITORY}/tree/main/projects/cic-003-yield-curve`;
const REPORT_PATH = `${REPOSITORY}/blob/main/projects/cic-003-yield-curve/research-report.md`;

function Metric({ label, value, note }) {
  return <div className="cic003-metric">
    <span>{label}</span>
    <strong>{value}</strong>
    <small>{note}</small>
  </div>;
}

function ThresholdTable() {
  return <div className="cic003-table-wrap" role="region" aria-label="Threshold sensitivity results" tabIndex="0">
    <table className="cic003-table">
      <caption>One row per spread threshold; these episodes are not independent trials.</caption>
      <thead><tr><th scope="col">Threshold</th><th scope="col">Confirmed episodes</th><th scope="col">Hits</th><th scope="col">False alarms</th><th scope="col">Recession starts covered</th><th scope="col">Right-censored</th></tr></thead>
      <tbody>{summary.threshold_sensitivity.map((row) => <tr key={row.threshold_percent}>
        <th scope="row">{row.threshold_percent > 0 ? "+" : ""}{row.threshold_percent.toFixed(2)} pp</th>
        <td>{row.confirmed_episodes}</td>
        <td>{row.hit_episodes}</td>
        <td>{row.false_alarm_episodes}</td>
        <td>{row.covered_recession_onsets} of {row.recession_onsets}</td>
        <td>{row.right_censored_episodes}</td>
      </tr>)}</tbody>
    </table>
  </div>;
}

function EpisodeTable() {
  return <div className="cic003-table-wrap" role="region" aria-label="Primary inversion episode results" tabIndex="0">
    <table className="cic003-table cic003-episode-table">
      <caption>Primary rule: three consecutive monthly means at or below 0.00 pp.</caption>
      <thead><tr><th scope="col">Inversion episode</th><th scope="col">Confirmed</th><th scope="col">NBER-based start in window</th><th scope="col">Months from confirmation</th><th scope="col">Result</th></tr></thead>
      <tbody>{summary.primary.episodes.map((episode) => <tr key={episode.episode}>
        <th scope="row">{episode.inversion_start}–{episode.inversion_end} <small>{episode.duration_months} months</small></th>
        <td>{episode.confirmation_month}</td>
        <td>{episode.recession_onsets_in_window.join(", ") || "None"}</td>
        <td>{episode.months_from_confirmation_to_first_onset ?? "—"}</td>
        <td><span className={`cic003-status cic003-status-${episode.status}`}>{episode.status.replace("-", " ")}</span></td>
      </tr>)}</tbody>
    </table>
  </div>;
}

export default function YieldCurvePage() {
  const primary = summary.primary;
  const lowerThreshold = summary.threshold_sensitivity.find(
    (row) => row.threshold_percent === -0.25,
  );
  const higherThreshold = summary.threshold_sensitivity.find(
    (row) => row.threshold_percent === 0.25,
  );
  return <div className="cic003-page">
    <section className="project-intro">
      <p className="project-code">CIC-003</p>
      <div className="intro-grid cic003-intro-grid">
        <div>
          <h1>The Yield Curve’s Warning Window</h1>
          <p>Does a confirmed inversion of the 10-year/3-month Treasury spread precede or overlap later U.S. recession starts? This study counts distinct inversion episodes, missed recession starts, and false alarms using an explicit follow-up window.</p>
        </div>
        <div className="cic003-orbit" aria-hidden="true"><i /><b /></div>
      </div>
      <div className="cic003-metrics">
        <Metric label="Recession starts covered" value={`${primary.covered_recession_onsets} of ${primary.recession_onsets}`} note="NBER-based starts in the sample" />
        <Metric label="Confirmed episodes" value={primary.confirmed_episodes} note="3 consecutive monthly means ≤ 0.00 pp" />
        <Metric label="False alarms" value={primary.false_alarm_episodes} note="No onset in the defined warning window" />
      </div>
      <p className="cic003-sample-note">Monthly sample: {summary.sample_start} through {summary.sample_end} · {summary.monthly_observations} observations · both source files refreshed (UTC) {summary.metadata.data_retrieved_at_utc.slice(0, 10)}</p>
    </section>

    <section className="chart-section cic003-chart-section">
      <h2>Treasury spread and NBER-based recession months</h2>
      <figure>
        <img src="/images/cic-003/spread-and-recessions.svg" alt="Monthly average 10-year minus 3-month Treasury spread from January 1982 to October 2026. A dashed zero line marks inversion; NBER-based recession months are shaded." />
        <figcaption>Daily FRED T10Y3M values are averaged within each calendar month. The zero line marks equal 10-year and 3-month yields; shaded periods use the monthly FRED USREC indicator.</figcaption>
      </figure>
    </section>

    <section className="finding cic003-finding">
      <div><p className="section-label">What the historical rule found</p><h2>{primary.covered_recession_onsets} of {primary.recession_onsets} recession starts fell inside a confirmed inversion’s warning window.</h2></div>
      <div>
        <p>The zero-threshold rule produced {primary.confirmed_episodes} confirmed episodes from {summary.sample_start} through {summary.sample_end}. {primary.hit_episodes} covered a recession start; {primary.false_alarm_episodes} ended without one in their follow-up window.</p>
        <p>The median confirmation-to-recession interval was {primary.median_confirmation_lead_months} months. These are a handful of historical events, not an estimated probability or a forecast.</p>
        <a className="text-link" href="/methods">How the research is framed <span aria-hidden="true">→</span></a>
      </div>
    </section>

    <section className="chart-section cic003-chart-section">
      <h2>What counted as a warning episode</h2>
      <figure>
        <img src="/images/cic-003/inversion-episode-timeline.svg" alt="Timeline of confirmed inversion episodes. Solid navy bars mark months below the zero threshold, dashed gray segments show up to twelve months of follow-up, and outlined circles mark covered NBER-based recession starts." />
        <figcaption>A signal becomes confirmed at the end of its third consecutive inverted month. It remains active while the monthly mean is inverted, then receives twelve months of follow-up.</figcaption>
      </figure>
    </section>

    <section className="cic003-results">
      <p className="section-label">Episode results</p>
      <h2>Primary rule: at or below 0.00 percentage points</h2>
      <EpisodeTable />
    </section>

    <section className="cic003-results cic003-sensitivity">
      <p className="section-label">Threshold sensitivity</p>
      <h2>Changing the cutoff changed the trade-off</h2>
      <ThresholdTable />
      <p className="caption">The −0.25 pp rule covered {lowerThreshold.covered_recession_onsets} of {lowerThreshold.recession_onsets} starts. The +0.25 pp rule covered {higherThreshold.covered_recession_onsets} of {higherThreshold.recession_onsets} and has {higherThreshold.right_censored_episodes} right-censored episode(s). This check is descriptive and does not select a threshold for future use.</p>
    </section>

    <section className="project-links cic003-links">
      <a href={REPORT_PATH} target="_blank" rel="noreferrer">Read the full research report <span aria-hidden="true">↗</span></a>
      <a href={PROJECT_PATH} target="_blank" rel="noreferrer">View the source code <span aria-hidden="true">↗</span></a>
      <a href={`${PROJECT_PATH}#reproduce-the-analysis`} target="_blank" rel="noreferrer">Reproduce the analysis <span aria-hidden="true">↗</span></a>
      <p><strong>Limitations</strong>FRED’s NBER-based monthly labels are retrospective. Historical coverage does not establish real-time forecasting skill or causation.</p>
    </section>
    <p className="cic003-disclaimer">Educational research only. Not investment, tax, or legal advice, and not a recommendation to buy or sell any security.</p>
  </div>;
}
