# Battery Storage Economics Notebook Design

## Purpose

Create `notebooks/battery_storage_economics.ipynb` to estimate the technical and financial effect of adding an AC-coupled battery at the Haslach site. The notebook will use measured data from `database/haslach.db`, reconstruct a counterfactual without the existing managed resistance-heating loads, simulate battery dispatch, and report lifecycle economics.

The current dataset contains only a partial reliable year. The notebook must run on that data for development, but it must not present partial-year results as representative annual economics unless the user explicitly enables provisional annualization.

## Scope

The first version models PV self-consumption only:

- the battery charges only from site export;
- the battery discharges only to offset site import;
- grid charging and time-varying tariffs are out of scope;
- dispatch is deterministic and greedy rather than optimized;
- the battery is AC-coupled, with independent charge and discharge efficiencies and power limits.

The notebook will use pandas, NumPy, matplotlib, sqlite3, and Python standard-library functionality already available in the project environment. It will not add a runtime dependency.

## Source Data

Read these columns from the SQLite `main` table:

- `timestamp`
- `power_mains`
- `power_pv`
- `power_mypv`
- `power_bwwp`
- `power_wp`
- `controller_state`
- `fhs280_compressor`
- `fhs280_elpatron`

Timestamps will be parsed as timezone-aware values and converted to `Europe/Berlin`. The default analysis start is `2026-07-01`, with an optional end date.

Power sign conventions are:

- positive `power_mains`: grid import;
- negative `power_mains`: grid export;
- positive generation and load columns: produced or consumed power.

## Data Preparation And Quality

Resample power measurements to a configurable regular interval, defaulting to five minutes. Each interval uses the mean of its available samples.

The notebook will report:

- source and retained date ranges;
- source row count;
- missing values by required column;
- observed timestamp spacing;
- valid interval coverage per day;
- days excluded from analysis;
- days requiring a replacement-profile fallback.

A day is eligible for energy and economic aggregation only if its valid interval coverage meets a configurable threshold, defaulting to 95%. Missing spans will not be interpolated across merely to make a day appear complete. The battery simulation will operate on contiguous eligible intervals; state of charge will reset to the configured initial value after a data discontinuity so energy cannot be carried across an unknown period.

## Counterfactual Heating Demand

The measured site load is reconstructed as:

```text
observed_load = power_pv + power_mains
```

The existing managed heating does not disappear in the counterfactual. Its delivered thermal energy is instead supplied by the corresponding heat pump at a configurable coefficient of performance, defaulting to 4.0.

For each eligible day:

1. Calculate MyPV thermal energy from `power_mypv`.
2. Calculate BWWP EL thermal energy from `power_bwwp` while the electric-heater relay is active (`fhs280_elpatron == 1`).
3. Remove those electrical loads from `observed_load`.
4. Convert each daily thermal energy to replacement heat-pump electricity by dividing by COP.
5. Allocate MyPV replacement electricity over that day's observed main-heat-pump profile from positive `power_wp`.
6. Allocate BWWP EL replacement electricity over that day's observed BWWP compressor profile, primarily using `fhs280_compressor == 1` and excluding EL operation.

Allocation weights are proportional to the corresponding positive heat-pump power after a configurable standby threshold. This preserves each day's replacement electrical energy while following observed demand-driven run timing.

If no usable empirical profile exists for a source on a day with replacement demand, distribute that source's replacement electricity uniformly over the eligible intervals of that day and record the fallback in the quality report.

The resulting baseline is:

```text
counterfactual_load = observed_load
                    - power_mypv
                    - bwwp_el_power
                    + mypv_replacement_hp_power
                    + bwwp_replacement_hp_power

counterfactual_mains = counterfactual_load - power_pv
```

Small negative reconstructed loads caused by meter timing or noise will be clipped to zero and their frequency and energy impact reported.

## Battery Model

All primary assumptions will be grouped in one early configuration cell. Battery inputs include:

- usable capacity in kWh;
- initial state of charge as a fraction of usable capacity;
- maximum AC charge power in kW;
- maximum AC discharge power in kW;
- rectifier/charge efficiency;
- inverter/discharge efficiency;
- annual capacity degradation;
- no grid charging.

For each interval of duration `dt`, export is first available for charging and import is first available for discharging. Charge and discharge are constrained by AC power limits, available export/import, remaining usable capacity, and stored energy.

```text
stored_energy_added = ac_charge_energy * charge_efficiency
stored_energy_removed = ac_discharge_energy / discharge_efficiency
```

The battery cannot charge and discharge in the same interval. State of charge remains within zero and the current usable capacity. It carries continuously across valid adjacent intervals and resets only after excluded or missing spans.

The model records AC charge/discharge power, state of charge, conversion losses, residual import/export, curtailed charging opportunity due to power or capacity limits, and unmet import due to power or energy limits.

## Energy And Operational Results

The selected battery scenario will report:

- baseline and post-battery grid import and export;
- PV generation and counterfactual consumption;
- battery charge, discharge, and conversion losses;
- change in PV self-consumption and site self-sufficiency;
- equivalent full cycles;
- observed charge/discharge peaks;
- final and reset-boundary state of charge;
- energy-balance residuals.

Visuals will include:

- daily data coverage;
- a representative multi-day dispatch plot with PV, load, grid flow, battery power, and state of charge;
- monthly energy-flow comparison;
- monthly or cumulative bill savings;
- battery-capacity sensitivity.

## Financial Model

Editable financial inputs include:

- retail electricity price in EUR/kWh;
- feed-in tariff in EUR/kWh;
- installed battery cost in EUR;
- annual operating and maintenance cost in EUR;
- project lifetime in years;
- discount rate;
- annual battery capacity degradation.

Per-interval battery value is the avoided retail purchase minus the feed-in revenue forgone by energy diverted into the battery. Annual bill savings are calculated from baseline versus post-battery import and export, so conversion losses are naturally included.

For each lifecycle year, repeat the measured-year simulation with degraded usable capacity and otherwise unchanged load/PV data. Report:

- annual gross and net savings;
- cumulative undiscounted cash flow;
- cumulative discounted cash flow;
- simple payback year, when reached;
- discounted payback year, when reached;
- net present value at the configured discount rate.

The model assumes the measured year repeats and labels that assumption explicitly. Replacement costs, residual value, electricity-price escalation, battery calendar degradation beyond the configured annual capacity loss, taxes, financing, and demand charges are out of scope in the first version.

## Partial-Year Guard

Lifecycle economics require a configurable minimum number of eligible days, defaulting to 330. With fewer eligible days:

- observed-period technical and savings results remain available;
- lifecycle tables and payback/NPV are withheld by default;
- the notebook explains that seasonal coverage is insufficient;
- an `ALLOW_PARTIAL_YEAR_ANNUALIZATION` switch may enable explicitly provisional scaling by eligible-day count.

Any provisional result must be labeled as seasonal-biased and unsuitable for an investment decision.

## Capacity Sensitivity

Run the same dispatch model over an editable list of usable capacities. Unless overridden, charge/discharge power and installed cost remain fixed at the selected scenario values; the chart therefore describes energy-value sensitivity, not a vendor price curve. A separate optional EUR/kWh installed-cost assumption may be used to show NPV by capacity when the user intentionally enables it.

The sensitivity output will compare annual savings, equivalent full cycles, marginal savings per added kWh, and NPV where annual economics are permitted.

## Validation And Acceptance

The notebook is complete when it:

1. Opens `database/haslach.db` whether launched from the repository root or `notebooks/`.
2. Executes top to bottom in the existing `solarcontrol` conda environment.
3. Handles the current partial dataset without presenting unlabeled annual investment results.
4. Preserves daily replacement heat-pump energy within floating-point tolerance.
5. Keeps battery state of charge within bounds and forbids simultaneous charge/discharge.
6. Reconciles baseline and post-battery energy balances within a documented numerical tolerance.
7. Shows all assumptions together near the top of the notebook.
8. Produces interpretable tables and plots without modifying the database.

Small assertion cells will enforce the replacement-energy, state-of-charge, dispatch, and energy-balance invariants. Validation will execute all code cells against the current database and inspect the resulting errors and key summaries.