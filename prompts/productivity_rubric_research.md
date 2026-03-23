# Productivity Analysis Rubric — Research-Backed Time Estimates

## Overview

This document defines the scoring rubric used by AI Core's productivity analysis feature.
After each workflow completes, the system classifies the work performed into predefined
components and maps each component to a conservative time estimate representing how long
a human developer would take to perform the same task manually.

**Key design principle:** The LLM classifies *what* happened (observable facts from the
action log). The rubric maps those classifications to *pre-set* time values. The LLM
cannot inflate or modify the time values — they are hardcoded in the orchestrator.

---

## Component Rubric

### 1. Codebase Comprehension and Navigation

**System actions:** `get_repo_info`, `get_file_tree`, `get_file_content`

| Classification | Files read | Time value | Justification |
|---|---|---|---|
| Small | 1–3 files | 15 min | Focused task with known scope |
| Medium | 4–8 files | 30 min | Building mental model across multiple files, tracing dependencies |
| Large | 9+ files | 45 min | Deep exploration of unfamiliar codebase or complex dependency chain |

**Research backing:**
- Xia et al. (2017) field study of 79 professional developers across 3,244 working hours
  found developers spend approximately **58% of their time on program comprehension**.
- Ko et al. (2006) found developers spend about **35% of their time navigating** the codebase.
- Minelli et al. (2015) measured that programmers spend approximately **70% of their time
  reading and navigating code**, with only 15% dedicated to actively writing new code.
- Bob Martin (Clean Code): "The ratio of time spent reading versus writing is well over 10 to 1."

### 2. CI/CD Triage and Log Analysis

**System actions:** `get_build_info`, `get_test_results`, `get_console_output`, `get_coverage_report`

| Sub-component | Time value | Justification |
|---|---|---|
| Build status check | 10 min | Open CI dashboard, locate build, check status, understand context |
| Test result analysis | 20 min | Parse which tests failed, read error messages, understand failure patterns |
| Console log analysis | 30 min | Read raw build logs (often 10k–50k chars), locate relevant errors, understand context |
| Coverage analysis | 15 min | Interpret JaCoCo/coverage reports, compare against targets, identify gaps |

**Research backing:**
- Undo/CI Research Report: **26% of developer time** is spent reproducing and fixing
  failing tests — equivalent to 620 million developer hours annually across the industry.
- Gitar (2025): "Manually figuring out why CI builds fail takes too long and pulls developers
  away from their work. This process grows slower with larger teams and often leads to
  frustration. A quick fix can stretch into hours when you factor in mental fatigue from
  task switching."
- Build failures typically resolve within 24 hours but even that time adds up to major
  productivity losses across teams.

### 3. Root Cause Diagnosis

**System actions:** Claude's multi-step reasoning across tool calls (reading code + logs → hypothesis → verification)

| Classification | Time value | Justification |
|---|---|---|
| None (no failures) | 0 min | Only new tests were added; no diagnosis required |
| Simple | 20 min | Assertion format, import, typo — obvious once located |
| Moderate | 60 min | Logic error, wrong expectation — requires understanding both implementation and test |
| Complex | 120 min | Multi-file, concurrency, environment-dependent — may require multiple hypotheses |

**Research backing:**
- Undo/CI Research: Software engineers spend an average of **13 hours** to find and fix
  a single CI failure in their backlog. Our "complex" value of 120 min (2 hours) uses
  a fraction of this as a conservative lower bound.
- Same study: **41% of respondents** say getting the bug to reproduce is the biggest
  barrier to finding and fixing bugs faster.
- **56% of respondents** say they could release software 1–2 days faster if reproducing
  failures wasn't an issue.

### 4. Fix Implementation

**System actions:** `create_branch`, `create_or_update_file`

| Classification | Time value | Justification |
|---|---|---|
| None | 0 min | No code changes were made |
| Modify existing | 30 min | Editing known test files with existing patterns to follow |
| Create new | 60 min | Writing integration tests from scratch — fixtures, assertions, API understanding |
| Both | 75 min | Combination with some shared context reducing overlap |

**Research backing:**
- Tidelift/New Stack survey (2019): Developers spend less than **one-third (32%) of their
  time writing new code**. The remainder goes to maintenance (19%), testing (12%), and
  security (4%).
- Apriorit testing estimation guide: Creating one test case typically takes about **10 minutes**.
  A new test file with 3–5 integration test methods = 30–50 min of writing plus setup time.
- IDC "How Do Software Developers Spend Their Time?" (2024): Application development
  accounted for only **16% of developers' time**, with the majority spent on operational
  and supportive tasks.

### 5. Build-Verify Cycles

**System actions:** `trigger_build` + `wait_for_build_completion` + result analysis (per cycle)

| Classification | Time value | Justification |
|---|---|---|
| Per cycle | 30 min | Build wait + context switch recovery + result analysis |

**Research backing:**
- Incredibuild "Big Dev Build Times" survey: Developers spend an average of **57 minutes
  per day** waiting for builds to finish.
- Gloria Mark, UC Irvine (cited by GitHub Engineering): It takes an average of **23 minutes
  and 15 seconds** to get back to the original task after context switching.
- GitHub blog (2022): "Labor is much, much more expensive than compute resources." Even at
  $75/hr developer cost, a 30-minute build cycle costs $37.50 in developer time alone.
- Real-world case studies report CI pipelines of 30–120 minutes being common, with teams
  losing 6+ developer-hours per day waiting for feedback.

### 6. PR Creation and Documentation

**System actions:** `create_pull_request` (with AI-generated summary body)

| Classification | Time value | Justification |
|---|---|---|
| PR created | 20 min | Writing title, description, listing changes, linking context |

**Research backing:**
- Graphite "State of Code Review 2024": The median engineer at a large company takes around
  **13 hours to merge a pull request**. The creation portion (title, summary, change list)
  is a subset — 20 min is conservative for a well-documented PR.
- LinearB engineering benchmarks: Elite teams maintain coding times under 1 hour from first
  commit to PR creation.

### 7. Change Verification and Review Preparation

**System actions:** Post-edit `get_file_content` calls, `get_commit_diff`, `get_pr_details`, `get_pr_diff`

| Sub-component | Time value | Justification |
|---|---|---|
| Per file verified | 5 min | Re-read of a file you just edited to confirm correctness |
| Per diff inspection | 10 min | Reviewing a commit diff or PR diff for unintended changes |

**Research backing:**
- LinearB (2024): Elite teams complete code reviews in under **3 hours**. Self-review
  before requesting peer review is a standard best practice — 5 min per file and 10 min
  per diff are conservative estimates for a quick once-over.
- Research shows interrupted tasks contain **twice as many errors** — self-verification
  catches issues that would otherwise require a full review cycle.

---

## Default Cost Assumptions

| Parameter | Default value | Source |
|---|---|---|
| Developer hourly rate (loaded) | $75 USD | US average ~$55/hr base (ZipRecruiter 2025) × 1.35 for benefits/overhead |
| Working hours per year | 2,080 | Standard (52 weeks × 40 hours) |

These values are configurable and clearly labeled as assumptions in the dashboard widget.

---

## Anti-Bias Design

The productivity analysis is designed to prevent the LLM from inflating its own value:

1. **Rubric-based classification:** The LLM reports *what it did* (observable facts),
   not *how hard it was*. Time values are pre-set, not LLM-generated.
2. **Conservative lower bounds:** Every time value uses the low end of the research range.
   The research says 13 hours average per CI failure — we use 20 minutes to 2 hours
   depending on complexity.
3. **Full transparency:** Every estimate shows a line-item breakdown traceable to specific
   actions in the workflow log. No black-box numbers.
4. **Separate API call:** The analysis runs as a distinct, lightweight Claude call after
   the workflow — it does not consume workflow interactions or bias the main agent.
