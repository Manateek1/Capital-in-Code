# Capital in Code — Project Context

> This is the living memory for the Capital in Code project. It was initialized
> from the user-provided `Capital_in_Code_Context.md` on 2026-07-29 and should
> evolve as durable decisions and milestones emerge. It is working context, not
> a substitute for the user's latest explicit instructions.

## High-Level Goal

Capital in Code is a software-focused project centered on finance, investing,
and programming. The goal is to build substantial work that demonstrates
technical ability while providing real value.

The current repository direction describes Capital in Code more specifically as
Dillon Nagar's public portfolio of coding and investing experiments. Each
project should explore a clear market or investing question using code,
financial data, models, charts, and a concise written analysis.

## Desired Characteristics

- Useful to real people.
- Portfolio-quality code.
- Strong enough to discuss in college applications and interviews.
- An opportunity to learn modern software engineering practices.
- Focused, reproducible research explained in plain language.

## Core Themes

- Finance and investing
- Software engineering
- Data analysis and statistics
- APIs and automation
- Financial modeling
- AI-assisted development

## Project Identity and Boundaries

- Capital in Code is a portfolio, not currently a startup, fund, nonprofit, or
  formal academic journal.
- It is separate from RentMax AI.
- It is separate from Voices United.
- It is focused on coding, finance, and long-term technical growth.
- Public work must include an educational/informational disclaimer and must not
  present itself as financial, investment, tax, or legal advice.

## Project Structure

- Projects receive permanent sequential identifiers: `CIC-001`, `CIC-002`, and
  so on.
- Each project should include a focused question, testable hypothesis, source
  code, data/method notes, charts, a written analysis, limitations, and
  reproducibility instructions.
- The public website should remain simple, fast, readable, and consistent with
  the repository's branding direction.

## Current Status

### Current completion status — 2026-08-08

- `CIC-001`, **The Overnight Effect**, is complete on `main`, including its
  tested Python research pipeline, verified results, formal research report,
  concise technical summary, charts, and reproducibility instructions.
- The public Capital in Code site is a React/Vite application in `site/` with
  Home, CIC-001, Methods, and About routes. It is connected to GitHub for
  deployments from `main`; its Vercel project uses `site` as the root directory
  and `dist` as the build output.
- The site identifies Dillon Nagar as its creator, links to the public GitHub
  repository and the CIC-001 research materials, and includes a site-wide
  educational disclaimer. It is intended as a public admissions-oriented
  research portfolio, not investment advice.

### Dated branding decision — 2026-08-08

- The public site now uses a primary, text-free mark: a navy circular orbit
  with an ascending signal path. It is used alongside the Capital in Code
  wordmark in the header and footer, and as the website favicon.
- The mark supports the existing minimalist, geometric, circle-based identity
  and is explicitly not a promise of financial performance.

### Historical repository snapshot — 2026-07-29

- GitHub repository: `Manateek1/Capital-in-Code`.
- The repository foundation is present on `main`.
- The local working branch was `codex/repository-foundation` and was
  synchronized with its remote tracking branch.
- `CIC-001`, **The Overnight Effect**, is the selected first research project.
- A substantial implementation and verified analysis existed on the downloaded
  remote branch `origin/codex/cic-001-overnight-effect`; it had not yet been
  merged into `main` as of this snapshot.
- The public website was still a future placeholder; no website framework had
  yet been added as of this snapshot.

## Direction History

The initial conversation context described the project as early-stage and in
planning/discovery, with no finalized product direction. It identified the
immediate priority as choosing a clear MVP instead of brainstorming
indefinitely. The repository foundation subsequently narrowed the direction to
a public portfolio of reproducible coding-and-investing experiments and selected
The Overnight Effect as `CIC-001`.

## Possible Future Areas

- Investment research tools
- Portfolio analytics
- Financial dashboards
- Market-data integrations
- Quantitative analysis
- Educational finance software
- Developer-focused finance tools

These are possibilities, not committed roadmap items.

## Current Near-Term Priority

Review, integrate, and present `CIC-001` as the first complete portfolio piece,
then use what is learned from it to choose the next project deliberately.

## Context Maintenance

Add only durable, project-level information here. Date meaningful status
snapshots and record major decisions or reversals so future work has both the
current direction and the relevant history.
