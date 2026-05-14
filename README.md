# speculast

`speculast` is an installable Python framework for semantic code analysis,
automatic pytest generation, infrastructure detection, and visual reporting.

speculast parses Python projects through AST analysis, tracks semantic changes,
detects external dependencies, prepares test suites, can orchestrate Docker-backed
integration runs, and produces a self-contained HTML report.

## What speculast Does

- analyzes Python modules and projects at the semantic level;
- extracts functions, methods, imports, and external calls;
- detects infrastructure requirements such as PostgreSQL and Redis;
- generates production-style pytest suites;
- runs a full cycle with Docker, pytest, coverage, and JSON reports;
- builds timestamped HTML dashboards grouped by day under `reports/`.

## Installation

Use Python `3.12+`. The project is packaged through `pyproject.toml`.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install .
```

Linux / macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

After installation, the CLI command `speculast` becomes available in the active environment.

## CLI Quick Reference

```bash
speculast [PATH] [--no-tests] [--no-viz] [--no-real-db] [--no-cleanup] [--lang ru|en] [--cleanup-reports] [--report-retention-days N]
```

Examples:

```bash
speculast
speculast path/to/module.py
speculast . --cleanup-reports --report-retention-days 7
speculast . --no-tests
speculast . --no-viz --lang en
```

By default, `speculast` runs in Full Auto mode:

- uses the current directory when `PATH` is omitted;
- cleans temporary root-level technical noise automatically;
- enables real DB mode by default;
- runs generated tests;
- builds the HTML report;
- opens the fresh report in the browser automatically.

`--cleanup-reports` additionally prunes aged HTML reports from `reports/`.

The default full cycle performs:

1. semantic analysis;
2. test generation;
3. infrastructure planning;
4. `docker compose up -d` when services are required;
5. pytest execution with coverage and JSON reports;
6. HTML report generation;
7. `docker compose down --remove-orphans`.

## Template and Report Portability

speculast resolves Jinja and HTML templates through `importlib.resources`.
This means the package can locate bundled templates correctly after `pip install .`,
even when `speculast` is started from an unrelated working directory.

Bundled resources include:

- `engine/generator/templates/*.jinja2`
- `engine/visualizer/templates/report.html`

## Scenario A: Quick Start on Any OS

Install the package and run the full autonomous cycle against the current project:

```bash
python -m pip install .
speculast
```

Expected outputs:

- generated test suite under `tests/`;
- `docker-compose.yaml` when infrastructure is required;
- date-grouped reports such as `reports/2026-05-14/report_131530.html`.

If you also want to keep raw pytest and coverage JSON artifacts:

```bash
speculast . --no-cleanup
```

If you only need the report without pytest execution:

```bash
speculast . --no-tests
```

## Scenario B: Windows + Docker Desktop

Recommended stack:

- Python `3.12+`
- Docker Desktop
- PowerShell or Windows Terminal

Typical workflow:

```powershell
.venv\Scripts\activate
python -m pip install .
speculast
```

Notes for Windows:

- `speculast` can start and stop Docker-backed infrastructure for integration scenarios.
- If PostgreSQL-backed tests are generated, make sure Docker Desktop is installed and available in PATH.
- speculast writes final diagnostics into timestamped files inside `reports/`, while terminal output stays compact.

## Scenario C: Linux / macOS Server Mode

speculast does not require a desktop UI. The report is generated as a plain HTML file
that can be opened locally or archived as a build artifact.

Typical workflow:

```bash
source .venv/bin/activate
python -m pip install .
speculast /opt/projects/my-service --lang en
```

Recommended environment preparation:

- install Docker Engine or Docker Desktop for container-backed tests;
- ensure the current user can run `docker compose`;
- run inside a CI worker, VM, or server shell without GUI if needed.

For analysis-only mode on a server:

```bash
speculast /opt/projects/my-service --no-tests --no-viz
```

## Scenario D: CI/CD Integration

The CLI is designed to be called directly from automated validation pipelines.

Minimal pipeline step:

```bash
python -m pip install .
speculast . --lang en
```

Recommended artifacts to publish from the job:

- `reports/`
- generated `tests/` directory if you want to inspect emitted suites

If the pipeline should also retain raw pytest and coverage JSON files, run with `--no-cleanup` and publish:

- `.speculast/pytest-report.json`
- `.speculast/coverage.json`

Example GitHub Actions step:

```yaml
- name: Install framework
  run: python -m pip install .

- name: Run semantic analysis and tests
  run: speculast . --lang en
```

Example GitLab CI job:

```yaml
speculast:
  stage: test
  script:
    - python -m pip install .
    - speculast . --lang en
  artifacts:
    when: always
    paths:
      - reports/
```

## Project Layout

```text
engine/
  analyzer/    Semantic analysis and AST visitors
  core/        Pydantic models, i18n, protocols
  generator/   Jinja-based pytest generation templates and engine
  infra/       Infrastructure detection and Docker Compose helpers
  visualizer/  HTML dashboard rendering
main.py        CLI entry module
pyproject.toml Packaging metadata and script entry points
```

## Installed CLI Entry Point

The package registers:

```toml
[project.scripts]
speculast = "main:main"
```

So after installation, `speculast` runs the same autonomous CLI cycle exposed by `main.py`.

## Output Artifacts

Depending on the mode, the framework can generate:

- `tests/`
- `docker-compose.yaml`
- `reports/`

Temporary technical artifacts such as `.speculast/`, cache folders, and browser-check profiles are removed automatically unless `--no-cleanup` is used.

## Development Notes

Runtime dependencies are declared in `pyproject.toml` and include:

- `pydantic`
- `jinja2`
- `sqlalchemy`
- `asyncpg`
- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-json-report`
- `rich`

Optional development extras:

```bash
python -m pip install .[dev]
```
