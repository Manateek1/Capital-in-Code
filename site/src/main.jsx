import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import "./styles.css";

const REPOSITORY = "https://github.com/Manateek1/Capital-in-Code";
const PROJECT_PATH = `${REPOSITORY}/tree/main/projects/cic-001-overnight-effect`;
const REPORT_PATH = `${REPOSITORY}/blob/main/projects/cic-001-overnight-effect/research-report.md`;

function Mark() {
  return <span className="mark" aria-hidden="true"><i /><b /></span>;
}

function ExternalArrow() {
  return <span aria-hidden="true">↗</span>;
}

function Header() {
  return (
    <header className="site-header">
      <Link className="wordmark" to="/">Capital in Code <Mark /></Link>
      <nav aria-label="Primary navigation">
        <NavLink to="/projects/cic-001-overnight-effect">Projects</NavLink>
        <NavLink to="/methods">Methods</NavLink>
        <NavLink to="/about">About</NavLink>
      </nav>
      <a className="github-link" href={REPOSITORY} target="_blank" rel="noreferrer">GitHub <ExternalArrow /></a>
    </header>
  );
}

function Footer() {
  return (
    <footer>
      <Link className="wordmark" to="/">Capital in Code <Mark /></Link>
      <p>Independent research in quantitative finance, investing, coding, and statistics.</p>
      <a href={REPOSITORY} target="_blank" rel="noreferrer">View the repository <ExternalArrow /></a>
    </footer>
  );
}

function Layout({ children }) {
  return <><Header /><main>{children}</main><Footer /></>;
}

function LinkArrow({ children, ...props }) {
  return <Link className="text-link" {...props}>{children} <span aria-hidden="true">→</span></Link>;
}

function Home() {
  return <Layout>
    <section className="hero">
      <div>
        <h1>Research at the intersection of markets and code.</h1>
        <p>I ask focused questions, test them carefully, and explain the results clearly. Capital in Code is an independent research portfolio for learning in public.</p>
        <LinkArrow to="/projects/cic-001-overnight-effect">Explore CIC-001</LinkArrow>
      </div>
      <div className="hero-figure" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><svg viewBox="0 0 620 260" role="presentation"><path d="M0 177 L34 168 L64 179 L94 148 L122 154 L151 137 L183 173 L213 165 L246 197 L279 184 L310 153 L339 164 L370 112 L403 141 L439 98 L465 109 L493 55 L522 82 L553 40 L584 56 L620 15" /></svg></div>
    </section>
    <section className="featured">
      <div className="section-label">Featured project</div>
      <div className="feature-grid">
        <div><h2>CIC-001 — The Overnight Effect</h2><p>SPY's return is separated into close-to-open and open-to-close components to examine where its historical adjusted growth occurred.</p><LinkArrow to="/projects/cic-001-overnight-effect">View project</LinkArrow></div>
        <img src="/images/cic-001/growth-of-one-dollar.png" alt="Growth of one dollar across the overnight, regular-hours, and buy-and-hold return components." />
      </div>
    </section>
    <section className="principles">
      <h2>Every project is designed to be inspected.</h2>
      <div><p><strong>Question</strong>A specific question and recorded hypothesis.</p><p><strong>Method</strong>Data, assumptions, validation, and statistical tests made explicit.</p><p><strong>Evidence</strong>Results, charts, limitations, and reproducible source code.</p></div>
    </section>
  </Layout>;
}

const Metric = ({ label, value }) => <div className="metric"><span>{label}</span><strong>{value}</strong><small>annualized</small></div>;

function Project() {
  return <Layout>
    <section className="project-intro">
      <p className="project-code">CIC-001</p>
      <div className="intro-grid"><div><h1>The Overnight Effect in SPY</h1><p>This study decomposes SPY returns into the previous close to next open interval and the open to close interval. It tests where adjusted close-to-close growth historically occurred, with validation, paired statistical tests, robustness checks, and an explicit discussion of limits.</p></div><div className="project-orbits" aria-hidden="true"><i /><b /></div></div>
      <div className="metrics"><Metric label="Overnight" value="9.86%" /><Metric label="Regular hours" value="0.79%" /><Metric label="Buy and hold" value="10.73%" /></div>
    </section>
    <section className="chart-section"><h2>Growth of $1 by return component</h2><img src="/images/cic-001/growth-of-one-dollar.png" alt="Logarithmic growth chart comparing overnight, regular-hours, and buy-and-hold returns for SPY." /><p className="caption">Adjusted SPY data from Yahoo Finance via yfinance; 8,053 aligned return observations from 1994-01-04 through 2025-12-31. The logarithmic axis preserves proportional changes.</p></section>
    <section className="finding"><div><p className="section-label">What the test found</p><h2>Historical growth was concentrated in the close-to-next-open interval.</h2></div><div><p>The average overnight-minus-regular-hours difference was 3.18 basis points per trading day. The result was statistically detectable in the paired tests, but statistical significance does not establish a realistic or superior trading strategy.</p><LinkArrow to="/methods">How the analysis was designed</LinkArrow></div></section>
    <section className="project-links"><a href={REPORT_PATH} target="_blank" rel="noreferrer">Read the research report <ExternalArrow /></a><a href={PROJECT_PATH} target="_blank" rel="noreferrer">View source code <ExternalArrow /></a><a href={`${PROJECT_PATH}#run-the-analysis`} target="_blank" rel="noreferrer">Reproduce the analysis <ExternalArrow /></a><p><strong>Limitations</strong>Results are historical, adjusted-price evidence for one ETF and one sample. They are not a forecast or investment recommendation.</p></section>
    <section className="two-charts"><img src="/images/cic-001/yearly-return-comparison.png" alt="Annual comparison of overnight and regular-hours compounded returns." /><img src="/images/cic-001/drawdown-comparison.png" alt="Drawdown comparison for the three return components." /></section>
  </Layout>;
}

function Methods() {
  const steps = [["01", "Question", "Define a precise question and a testable hypothesis."], ["02", "Data", "Use documented sources and a fixed study window."], ["03", "Validation", "Check dates, inputs, alignment, and return identities."], ["04", "Analysis", "Apply descriptive statistics, paired tests, and robustness checks."], ["05", "Reproducibility", "Publish code, assumptions, and instructions for rerunning the work."]];
  return <Layout><section className="methods-hero"><div><h1>Methods that make the work inspectable.</h1><p>The goal is not to make results look cleaner than they are. It is to document the question, data, choices, and limitations clearly enough for a reader to follow.</p></div><div className="method-circle" aria-hidden="true" /></section><section className="steps">{steps.map(([number, title, text]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{text}</p></article>)}</section><section className="method-detail"><div><h2>Transparent assumptions. Meaningful limitations.</h2><p>Each project explains the adjustments, tests, and simplifications behind its findings. Limitations are part of the research design, not a footnote after the conclusion.</p></div><div><img src="/images/cic-001/cumulative-log-return-contribution.png" alt="Cumulative log-return contribution chart for CIC-001." /><p className="caption">CIC-001 uses a simple-return identity and an equivalent log-return decomposition as separate checks on the analysis.</p></div></section></Layout>;
}

function About() {
  return <Layout><section className="about-hero"><div><h1>A place to make the work visible.</h1><p>Capital in Code was created by Dillon Nagar as an independent portfolio at the intersection of quantitative finance, investing, coding, and statistics.</p><p>The projects are a record of the process: carefully framed questions, transparent methods, reproducible code, and conclusions that state their limits.</p></div><div className="about-orbits" aria-hidden="true"><i /><i /><i /></div></section><section className="about-facts"><div><h2>Focus</h2><p>Quantitative finance, investing, coding, and statistics.</p></div><div><h2>Format</h2><p>Open projects, documented methods, research reports, and source code.</p></div><div><h2>Principle</h2><p>Clarity over complexity; evidence over opinion; reproducibility over polish.</p></div></section><section className="explore"><h2>Explore the work</h2><LinkArrow to="/projects/cic-001-overnight-effect">CIC-001 — The Overnight Effect</LinkArrow><LinkArrow to="/methods">Research methods</LinkArrow><a className="text-link" href={REPOSITORY} target="_blank" rel="noreferrer">GitHub repository <ExternalArrow /></a></section></Layout>;
}

function NotFound() { return <Layout><section className="not-found"><h1>Page not found.</h1><LinkArrow to="/">Return home</LinkArrow></section></Layout>; }

function App() { return <Routes><Route path="/" element={<Home />} /><Route path="/projects/cic-001-overnight-effect" element={<Project />} /><Route path="/methods" element={<Methods />} /><Route path="/about" element={<About />} /><Route path="*" element={<NotFound />} /></Routes>; }

createRoot(document.getElementById("root")).render(<React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>);
