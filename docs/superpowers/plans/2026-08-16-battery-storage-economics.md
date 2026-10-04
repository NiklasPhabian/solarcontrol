# Battery Storage Economics Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible notebook that reconstructs unmanaged heating demand, simulates an AC-coupled self-consumption battery, and evaluates observed-period and lifecycle economics from the Haslach database.

**Architecture:** Keep the analysis self-contained in one notebook, with pure pandas/NumPy helper functions defined before their use. Validate each transformation first with compact synthetic frames, then apply it to the read-only SQLite data and produce tables and matplotlib figures.

**Tech Stack:** Python 3, Jupyter, pandas, NumPy, matplotlib, sqlite3, unittest-style assertions

**Spec:** `docs/superpowers/specs/2026-08-16-battery-storage-economics-design.md`

**Checkpoint (2026-10-04):** Design and plan preserved; implementation has not
started and `notebooks/battery_storage_economics.ipynb` does not yet exist.
Continue in a local clone with a consistent, read-only Haslach database snapshot.
All tasks below remain pending.

## Global Constraints

- Create only `notebooks/battery_storage_economics.ipynb`; do not modify the database or runtime control code.
- Use only pandas, NumPy, matplotlib, sqlite3, pathlib, dataclasses, and Python standard-library functionality already available in the `solarcontrol` environment.
- Default to data beginning `2026-07-01`, configurable 15-minute intervals, 95% daily coverage, COP 4.0, and a 330-day lifecycle-economics threshold. Keep `RESAMPLE_FREQUENCY` editable; the wider default accommodates timestamp variation in the roughly five-minute source cadence.
- Positive `power_mains` is import and negative `power_mains` is export.
- Battery dispatch is self-consumption-only: no grid charging and no simultaneous charge/discharge.
- Partial-year annualization is disabled by default and, when enabled, must be visibly labeled provisional and seasonally biased.
- Every notebook cell must include `metadata.language`; the finished notebook must be valid JSON.

---

### Task 1: Data Loading And Heating Counterfactual

**Files:**
- Create: `notebooks/battery_storage_economics.ipynb`

**Interfaces:**
- Consumes: SQLite table `main` and the configuration constants in the notebook assumptions cell.
- Produces: `find_db_path() -> Path`, `load_source_data(db_path: Path) -> pd.DataFrame`, `prepare_intervals(source: pd.DataFrame, frequency: str, minimum_daily_coverage: float) -> tuple[pd.DataFrame, pd.DataFrame]`, and `build_heating_counterfactual(intervals: pd.DataFrame, cop: float, standby_threshold_w: float) -> tuple[pd.DataFrame, pd.DataFrame]`.

- [ ] **Step 1: Create the notebook introduction and assumptions cells**

Add markdown explaining the purpose, sign conventions, partial-year warning, and the managed-heating counterfactual. Add one code cell containing editable assumptions with these concrete defaults:

```python
ANALYSIS_START = "2026-07-01"
ANALYSIS_END = None
RESAMPLE_FREQUENCY = "15min"
MINIMUM_DAILY_COVERAGE = 0.95
HEAT_PUMP_COP = 4.0
HEAT_PUMP_STANDBY_THRESHOLD_W = 100.0

BATTERY_CAPACITY_KWH = 10.0
INITIAL_SOC_FRACTION = 0.5
MAX_CHARGE_POWER_KW = 5.0
MAX_DISCHARGE_POWER_KW = 5.0
CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95
ANNUAL_CAPACITY_DEGRADATION = 0.02

ELECTRICITY_PRICE_EUR_PER_KWH = 0.30
FEED_IN_TARIFF_EUR_PER_KWH = 0.08
INSTALLED_BATTERY_COST_EUR = 8000.0
ANNUAL_OM_COST_EUR = 50.0
PROJECT_LIFETIME_YEARS = 15
DISCOUNT_RATE = 0.04
MINIMUM_DAYS_FOR_LIFECYCLE = 330
ALLOW_PARTIAL_YEAR_ANNUALIZATION = False
SENSITIVITY_CAPACITIES_KWH = [0.0, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0]
```

- [ ] **Step 2: Add synthetic failing checks for preparation and replacement allocation**

Define a two-day synthetic source frame with one complete day, one incomplete day, positive PV/load signals, MyPV power, BWWP EL intervals, main heat-pump runtime, and BWWP compressor runtime. Before defining the implementation functions, add checks that document the required behavior:

```python
prepared, daily_quality = prepare_intervals(
    synthetic_source,
    frequency="5min",
    minimum_daily_coverage=0.95,
)
counterfactual, fallback_days = build_heating_counterfactual(
    prepared,
    cop=4.0,
    standby_threshold_w=100.0,
)

assert daily_quality.loc[daily_quality.index[0], "eligible"]
assert not daily_quality.loc[daily_quality.index[1], "eligible"]
assert np.isclose(
    counterfactual["mypv_replacement_hp_power"].sum(),
    counterfactual["power_mypv"].sum() / 4.0,
)
assert np.isclose(
    counterfactual["bwwp_replacement_hp_power"].sum(),
    counterfactual["bwwp_el_power"].sum() / 4.0,
)
```

- [ ] **Step 3: Run the synthetic check cell and verify the expected failure**

Run the cell after temporarily defining stubs that raise `NotImplementedError`. Expected: failure from `prepare_intervals`, proving the checks execute before implementation.

- [ ] **Step 4: Implement database loading and interval preparation**

Implement `find_db_path()` using repository-root and notebook-directory candidates, and load only the nine required columns with a parameterized date filter. Parse timestamps with `pd.to_datetime(..., utc=True)` and convert to `Europe/Berlin`.

In `prepare_intervals`, resample power columns by mean and relay/state columns by last observation. Calculate expected intervals per local calendar day, `valid_intervals`, `coverage`, and `eligible`. Mark an interval valid only when `power_mains` and `power_pv` are both present. Retain eligible days for simulation and add a `segment_id` that increments after a timestamp discontinuity greater than one resampling interval.

- [ ] **Step 5: Implement daily heating replacement allocation**

In `build_heating_counterfactual`:

```python
frame["observed_load"] = frame["power_pv"] + frame["power_mains"]
frame["bwwp_el_power"] = frame["power_bwwp"].where(frame["fhs280_elpatron"].eq(1), 0.0).clip(lower=0.0)
```

For each local day, integrate MyPV and BWWP EL energy using the fixed interval duration, divide each by COP, and convert replacement energy back to interval-average power. Weight MyPV replacement by positive `power_wp` above the standby threshold. Weight BWWP replacement by positive `power_bwwp` where `fhs280_compressor == 1` and `fhs280_elpatron != 1`. Use equal weights across eligible daily intervals when a required profile has zero total weight, and record source/date/reason in `fallback_days`.

Calculate `counterfactual_load_raw`, report negative-load count and Wh, clip it to `counterfactual_load`, and calculate `counterfactual_mains = counterfactual_load - power_pv`.

- [ ] **Step 6: Run the synthetic checks and apply the functions to SQLite data**

Run the synthetic cell again. Expected: all assertions pass. Then load `database/haslach.db`, prepare intervals, and display source range, retained range, row counts, missing counts, timestamp-spacing statistics, `daily_quality`, excluded days, fallback days, and clipped-load diagnostics.

### Task 2: AC-Coupled Battery Dispatch

**Files:**
- Modify: `notebooks/battery_storage_economics.ipynb`

**Interfaces:**
- Consumes: prepared counterfactual frame with `counterfactual_mains`, `segment_id`, and fixed interval frequency.
- Produces: `simulate_battery(frame: pd.DataFrame, capacity_kwh: float, initial_soc_fraction: float, max_charge_power_kw: float, max_discharge_power_kw: float, charge_efficiency: float, discharge_efficiency: float) -> pd.DataFrame`.

- [ ] **Step 1: Add deterministic dispatch checks using a four-interval synthetic frame**

Use `counterfactual_mains = [-4000, -4000, 3000, 3000]` W at one-hour intervals, capacity 5 kWh, empty initial SOC, 3 kW charge/discharge limits, and 90% efficiencies. Assert:

```python
dispatch = simulate_battery(
    dispatch_fixture,
    capacity_kwh=5.0,
    initial_soc_fraction=0.0,
    max_charge_power_kw=3.0,
    max_discharge_power_kw=3.0,
    charge_efficiency=0.9,
    discharge_efficiency=0.9,
)

assert np.all(dispatch["battery_charge_power_w"] >= 0)
assert np.all(dispatch["battery_discharge_power_w"] >= 0)
assert not ((dispatch["battery_charge_power_w"] > 0) & (dispatch["battery_discharge_power_w"] > 0)).any()
assert dispatch["soc_kwh"].between(0.0, 5.0).all()
assert np.isclose(dispatch.iloc[0]["battery_charge_power_w"], 3000.0)
assert np.isclose(dispatch.iloc[0]["soc_kwh"], 2.7)
assert np.isclose(dispatch.iloc[2]["battery_discharge_power_w"], 3000.0)
```

- [ ] **Step 2: Run the dispatch checks and verify the expected failure**

Run with a temporary `simulate_battery` stub that raises `NotImplementedError`. Expected: failure from the stub.

- [ ] **Step 3: Implement interval dispatch**

Iterate chronologically. At each new `segment_id`, reset stored energy to `capacity_kwh * initial_soc_fraction` and set `soc_reset = True`. For export, limit AC charge energy by export, charge power, and remaining capacity divided by charge efficiency. For import, limit AC discharge energy by import, discharge power, and stored energy multiplied by discharge efficiency.

Return these columns appended to a copy of the frame:

```text
battery_charge_power_w
battery_discharge_power_w
soc_kwh
soc_reset
charge_loss_wh
discharge_loss_wh
post_battery_mains
residual_import_power_w
residual_export_power_w
charge_power_limited_w
charge_capacity_limited_w
discharge_power_limited_w
discharge_energy_limited_w
```

- [ ] **Step 4: Run dispatch checks and full-data invariants**

Expected: synthetic assertions pass. On the real frame, assert SOC bounds, no simultaneous charge/discharge, no battery charging while baseline mains is positive, and no discharging while baseline mains is negative. Assert the maximum absolute per-interval balance residual is below `1e-6` W for:

```python
post_battery_mains = (
    counterfactual_mains
    + battery_charge_power_w
    - battery_discharge_power_w
)
```

### Task 3: Technical Results And Financial Model

**Files:**
- Modify: `notebooks/battery_storage_economics.ipynb`

**Interfaces:**
- Consumes: battery dispatch frame and notebook assumptions.
- Produces: `summarize_energy(dispatch: pd.DataFrame) -> pd.Series`, `calculate_observed_savings(dispatch: pd.DataFrame, electricity_price: float, feed_in_tariff: float) -> pd.DataFrame`, and `build_lifecycle(counterfactual: pd.DataFrame, assumptions: dict[str, float], eligible_days: int, allow_partial_year: bool) -> tuple[pd.DataFrame | None, str]`.

- [ ] **Step 1: Add summary and financial checks**

Use the Task 2 fixture and assert that the energy summary reconciles baseline grid energy, post-battery grid energy, stored-energy change, and conversion losses. Add a one-year cash-flow fixture with EUR 400 gross savings, EUR 50 O&M, EUR 1000 capex, and 0% discount rate, asserting year-zero cash flow of EUR -1000 and year-one net cash flow of EUR 350.

- [ ] **Step 2: Run checks and verify the expected failure**

Use stubs raising `NotImplementedError`. Expected: first summary or financial helper call fails.

- [ ] **Step 3: Implement technical summaries**

Integrate W to kWh using the interval duration. Return baseline/post-battery import and export, PV generation, counterfactual demand, AC charge/discharge, charge/discharge losses, equivalent full cycles, peak powers, final SOC, reset count, PV self-consumption, and self-sufficiency.

Define:

```text
PV self-consumption = 1 - export / PV generation
self-sufficiency = 1 - import / counterfactual demand
equivalent full cycles = AC charge energy * charge efficiency / usable capacity
```

Return `NaN` when a denominator is zero.

- [ ] **Step 4: Implement observed savings and lifecycle economics**

Calculate interval baseline and post-battery cost as import cost minus export revenue, then aggregate by month. `build_lifecycle` must return `None` plus an explanatory message when `eligible_days < MINIMUM_DAYS_FOR_LIFECYCLE` and partial-year annualization is disabled.

When lifecycle analysis is allowed, calculate the scaling factor as `365.2425 / eligible_days` only for explicit partial-year annualization; otherwise use 1.0. For years 1 through project lifetime, degrade usable capacity by `(1 - annual_capacity_degradation) ** (year - 1)`, rerun dispatch, calculate gross savings, subtract O&M, and discount net cash flow by `(1 + discount_rate) ** year`. Include year zero with installed cost as a negative cash flow. Calculate cumulative cash flow, cumulative discounted cash flow, first simple/discounted payback years, and NPV.

- [ ] **Step 5: Run helper checks and display real-data tables**

Expected: all fixture assertions pass. Display an assumptions table, selected-scenario technical summary, monthly energy/cost table, and either the lifecycle table plus payback/NPV or the partial-year guard message. When provisional annualization is enabled, print `PROVISIONAL: seasonally biased partial-year annualization; not suitable for an investment decision.` immediately above lifecycle results.

### Task 4: Visuals, Sensitivity, And End-To-End Validation

**Files:**
- Modify: `notebooks/battery_storage_economics.ipynb`

**Interfaces:**
- Consumes: quality, counterfactual, dispatch, monthly, and lifecycle frames from Tasks 1-3.
- Produces: final figures, sensitivity table, and a notebook that executes top to bottom.

- [ ] **Step 1: Add data-quality and representative-dispatch figures**

Plot daily coverage with the eligibility threshold. Select the eligible three-day window with the largest PV energy and plot PV, counterfactual load, baseline/post-battery mains, battery charge/discharge, and SOC on aligned axes. Label all units and sign conventions.

- [ ] **Step 2: Add monthly and cumulative-value figures**

Plot monthly baseline versus post-battery import/export as grouped bars. Plot monthly savings and cumulative observed savings. If lifecycle results exist, add cumulative undiscounted and discounted cash-flow lines with a zero reference.

- [ ] **Step 3: Add capacity sensitivity**

For every value in `SENSITIVITY_CAPACITIES_KWH`, rerun dispatch and summarize annual or observed-period savings, equivalent full cycles, and marginal savings per added kWh. Include NPV only when lifecycle economics are allowed. Plot savings versus capacity and, where available, NPV on a second panel. Clearly state that fixed installed cost and fixed power limits do not form a vendor cost curve.

- [ ] **Step 4: Add a final validation cell**

The final code cell must assert:

```python
assert replacement_energy_checks_pass
assert dispatch["soc_kwh"].between(-1e-9, BATTERY_CAPACITY_KWH + 1e-9).all()
assert not ((dispatch["battery_charge_power_w"] > 1e-9) & (dispatch["battery_discharge_power_w"] > 1e-9)).any()
assert maximum_dispatch_balance_residual_w < 1e-6
assert db_path.name == "haslach.db"
print("All notebook validation checks passed.")
```

- [ ] **Step 5: Validate notebook JSON and execute every code cell**

Run:

```bash
conda run -n solarcontrol python -m json.tool notebooks/battery_storage_economics.ipynb >/dev/null
conda run -n solarcontrol jupyter nbconvert --to notebook --execute notebooks/battery_storage_economics.ipynb --output /tmp/battery_storage_economics.executed.ipynb --ExecutePreprocessor.timeout=300
```

Expected: both commands exit 0, the final output contains `All notebook validation checks passed.`, and the partial-year guard is shown for the current database.

- [ ] **Step 6: Review the final diff**

Run `git diff --check` and inspect `git diff --stat`. Confirm only the approved spec, implementation plan, and new notebook are changed by this task; leave any unrelated pre-existing worktree changes untouched.