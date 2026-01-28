# Excel Workbook Mapping - Stall Chart.xlsm

## Overview
This document maps the cell addresses, formulas, and calculation logic from the Excel workbook `Stall Chart.xlsm` to support accurate replication in the web application.

---

## Workbook Structure

### Sheets
1. **STALL CHART** - Main calculation and display sheet
2. **Properties** - X-Steam property lookup examples
3. **Functions** - X-Steam function documentation

### Named Ranges
- `Stall`: `'STALL CHART'!$AI$14:$AI$15` - Stall indicator flags

---

## INPUT CELLS (STALL CHART Sheet)

| Cell | Parameter | Value (Example) | Units | Description |
|------|-----------|-----------------|-------|-------------|
| D7 | Duty (100% load) | 1,257,060 | BTU/hr | Heat duty at maximum load |
| D8 | Surface Area | 58.71 | ft² | Heat exchanger surface area |
| D9 | HTC (Clean) | 140 | BTU/(hr·ft²·°F) | Overall heat transfer coefficient (clean) |
| D10 | HTC (Service) | 110 | BTU/(hr·ft²·°F) | Overall heat transfer coefficient (fouled/service) |
| D11 | Process (Ti) | 0 | °F | Process fluid inlet temperature |
| D12 | Process (To) | 300 | °F | Process fluid outlet temperature |
| D13 | Backpressure (Max) | 70 | psig | Maximum condensate return backpressure |
| D14 | Backpressure (Min) | 0 | psig | Minimum condensate return backpressure |
| D15 | Max Feed Rate | 1,057 | lb/hr | Maximum process feed rate |
| C20:C30 | Load % | 100, 90, 80... 0 | % | Load percentages for turndown analysis |

---

## CALCULATION FORMULAS

### 1. Z Factor Calculation (Dimensionless)

**Clean condition (Column Z):**
```excel
Z20 = EXP((($D$11-$D$12)*$D$9*$D$8)/D20)
```

**Service/Fouled condition (Column AA):**
```excel
AA20 = EXP((($D$11-$D$12)*$D$10*$D$8)/D20)
```

**Python equivalent:**
```python
Z_clean = exp(((T_i - T_o) * U_clean * A) / Q)
Z_service = exp(((T_i - T_o) * U_service * A) / Q)
```

**Where:**
- Ti = D11 (Process inlet temperature, °F)
- To = D12 (Process outlet temperature, °F)
- U_clean = D9 (Clean HTC, BTU/(hr·ft²·°F))
- U_service = D10 (Service HTC, BTU/(hr·ft²·°F))
- A = D8 (Surface area, ft²)
- Q = D20 (Duty at current load, BTU/hr)

---

### 2. Load Scaling

**Capacity (Column B):**
```excel
B21 = $B$20*C21/100
```

**Duty (Column D):**
```excel
D21 = ($D$20/100)*C21
```

**Python equivalent:**
```python
capacity = max_feed_rate * (load_pct / 100)
duty = duty_100pct * (load_pct / 100)
```

---

### 3. Required Steam Temperature (°F)

**Clean condition (Column E):**
```excel
E20 = ($D$12-(Z20*$D$11))/(1-Z20)
```

**Service condition (Column H):**
```excel
H20 = ($D$12-(AA20*$D$11))/(1-AA20)
```

**Python equivalent:**
```python
T_s_clean = (T_o - Z_clean * T_i) / (1 - Z_clean)
T_s_service = (T_o - Z_service * T_i) / (1 - Z_service)
```

**Derivation:** From LMTD equation for condensing steam:
```
Z = exp((Ti - To) * U * A / Q)
T_s = (T_o - Z * T_i) / (1 - Z)
```

---

### 4. Required Steam Pressure (psig)

**Clean condition (Column F):**
```excel
F20 = (psat_t(E20))-14.5
```

**Service condition (Column I):**
```excel
I20 = (psat_t(H20))-14.5
```

**Python equivalent:**
```python
# Convert to absolute pressure for steam tables
P_abs_psia = psat_t(T_s_degF)  # Returns psia
P_gauge_psig = P_abs_psia - 14.5  # Convert to psig
```

**Note:** The Excel uses `-14.5` instead of `-14.7` (standard atmospheric) - preserve this for parity.

---

### 5. Steam/Condensate Flow Rate (lb/hr)

**Clean condition (Column G):**
```excel
G20 = D20/(hV_p(F20+14.7)-hL_p(F20+14.7))
```

**Service condition (Column J):**
```excel
J20 = D20/(hV_p(I20+14.7)-hL_p(I20+14.7))
```

**Python equivalent:**
```python
# Convert psig to psia for steam tables
P_abs = P_gauge + 14.7

# Get enthalpy of vaporization
h_vapor = hV_p(P_abs)  # BTU/lb
h_liquid = hL_p(P_abs)  # BTU/lb
h_fg = h_vapor - h_liquid  # Latent heat

# Steam flow rate
mdot_steam = Q / h_fg  # lb/hr
```

---

### 6. Backpressure Saturation Temperature

**Max backpressure (Cell E13):**
```excel
E13 = Tsat_p((D13)+14.7)
```

**Min backpressure (Cell E14):**
```excel
E14 = Tsat_p((D14)+14.7)
```

**Python equivalent:**
```python
T_sat_max_bp = Tsat_p(P_max_psig + 14.7)
T_sat_min_bp = Tsat_p(P_min_psig + 14.7)
```

---

## X-STEAM / VBA FUNCTIONS USED

The Excel workbook uses the X-Steam library (Magnus Holmgren, IF-97 implementation) with the following functions:

### Temperature Functions
- `Tsat_p(P)` - Saturation temperature from pressure (psia) → °F
- `psat_t(T)` - Saturation pressure from temperature (°F) → psia

### Enthalpy Functions  
- `hV_p(P)` - Saturated vapor enthalpy from pressure (psia) → BTU/lb
- `hL_p(P)` - Saturated liquid enthalpy from pressure (psia) → BTU/lb
- `hV_T(T)` - Saturated vapor enthalpy from temperature (°F) → BTU/lb
- `hL_T(T)` - Saturated liquid enthalpy from temperature (°F) → BTU/lb

### Other Properties (not used in main calculations)
- `rhoV_p(P)`, `rhoL_p(P)` - Density
- `sV_p(P)`, `sL_p(P)` - Entropy
- `uV_p(P)`, `uL_p(P)` - Internal energy
- `Cp_pT(P,T)`, `Cv_pT(P,T)` - Heat capacities
- `w_pT(P,T)` - Speed of sound
- `my_pT(P,T)` - Dynamic viscosity
- `tc_pT(P,T)` - Thermal conductivity

---

## UNIT CONVERSIONS

### Pressure
- Excel uses **psig** (gauge) for backpressure inputs
- Excel uses **psia** (absolute) for steam property functions
- Conversion: `psia = psig + 14.7` (Excel uses 14.5 in formula F20/I20 for psig output)

### Temperature
- All temperatures in **°F** (Fahrenheit)

### Enthalpy
- **BTU/lb** (British Thermal Units per pound)

### Heat Transfer Coefficient
- **BTU/(hr·ft²·°F)**

### Duty
- **BTU/hr**

### Mass Flow
- **lb/hr** (pounds per hour)

---

## STALL CONDITION LOGIC

**Stall occurs when:**
```
P_steam_required ≤ P_backpressure
```

**Or equivalently:**
```
T_steam_required ≤ T_sat(P_backpressure)
```

**Excel implementation:** The STALL CHART sheet includes conditional logic in cells E33-H36 to calculate stall points, though the formulas reference cell C34 which controls stall chart display (value: "No" or "Yes").

---

## OUTPUT CELL RANGES

### Main Calculation Table (Rows 20-30)

| Column | Parameter | Units |
|--------|-----------|-------|
| B | Capacity | lb/hr |
| C | % Load | % |
| D | Duty | BTU/hr |
| E | Steam Temp (Clean) | °F |
| F | Steam Pressure (Clean) | psig |
| G | Steam Flow (Clean) | lb/hr |
| H | Steam Temp (Service) | °F |
| I | Steam Pressure (Service) | psig |
| J | Steam Flow (Service) | lb/hr |
| Z | Z factor (Clean) | dimensionless |
| AA | Z factor (Service) | dimensionless |

---

## CHART DATA PREPARATION

The workbook includes chart data in rows 39-50 (columns C-G) for plotting:
- Process temperature line (constant at To)
- Backpressure saturation temperatures
- BP Range

This data feeds the embedded charts showing:
1. Temperature vs Load
2. Pressure vs Load
3. Stall regions

---

## VALIDATION NOTES

### Critical Implementation Requirements

1. **Pressure convention consistency:**
   - Use `-14.5` (not `-14.7`) when converting psia to psig for output (cells F20, I20)
   - Use `+14.7` when converting psig to psia for property lookups

2. **Formula order:**
   - Calculate Z first
   - Then calculate T_s from Z
   - Then calculate P_s from T_s
   - Then calculate mdot from Q and P_s

3. **Edge cases:**
   - When Z ≥ 1: Physically impossible (pinch point violation)
   - When T_s ≤ T_o: Physically impossible (steam colder than outlet)
   - Division by zero when h_fg = 0

4. **Numerical precision:**
   - Steam properties should match IF-97 standard
   - Temperature tolerance: ±0.5 °F
   - Pressure tolerance: ±0.5 psig
   - Flow tolerance: ±1%

---

## FILES GENERATED FROM THIS MAPPING

1. `excel_structure.json` - Complete cell-by-cell structure
2. `calculation_engine.py` - Python implementation
3. `parity_tests.py` - Automated validation against Excel
4. `EXCEL_MAPPING.md` - This document

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-27  
**Source Workbook:** Stall Chart.xlsm  
**Author:** Automated extraction via openpyxl
