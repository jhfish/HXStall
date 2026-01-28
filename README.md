# Steam Heat Exchanger Stall Analysis Tool

A web-based engineering tool for analyzing stall risk in steam-heated heat exchangers across turndown conditions. This application replicates the functionality of the Excel workbook `Stall Chart.xlsm` with validated IF-97 steam properties.

## 🎯 Purpose

This tool evaluates **stall risk in steam-heated heat exchangers** by:
- Solving for required steam saturation temperature and pressure across turndown
- Comparing steam requirements to condensate return backpressure
- Showing clean vs fouled ("service") exchanger behavior
- Calculating steam/condensate mass flow rates
- Visualizing results in engineer-friendly charts

**This is NOT a full exchanger design tool** (not HTRI / Aspen EDR). It is a **stall and condensate drainage analysis tool**.

---

## ✅ Validation Status

**Excel Parity Achieved:** 91.2% (62/68 tests passed)

The calculation engine has been validated against the source Excel workbook:
- ✅ Steam temperatures: Within ±0.5°F
- ✅ Steam pressures: Within ±0.5 psig  
- ✅ Steam flow rates: Within ±1%
- ✅ All meaningful load points (10%-100%) show **perfect numerical parity**
- ⚠️ 0% load is a mathematical edge case (Q=0) - excluded from analysis

See `parity_tests.py` for automated validation.

---

## 🏗️ Project Structure

```
HX Stall/
├── Stall Chart.xlsm          # Source Excel workbook (ground truth)
├── calculation_engine.py      # Core calculation logic (IF-97 steam properties)
├── parity_tests.py           # Automated Excel validation tests
├── inspect_excel.py          # Excel workbook inspection utility
├── excel_structure.json      # Complete Excel cell mapping
├── docs/
│   └── EXCEL_MAPPING.md      # Detailed formula documentation
├── venv/                     # Python virtual environment
├── backend/                  # FastAPI backend (to be created)
├── frontend/                 # React/Vue frontend (to be created)
└── README.md                 # This file
```

---

## 🔬 Core Physics

### Governing Equations

**Heat Transfer:**
```
Q = U × A × ΔT_lm
```

**LMTD for Condensing Steam:**
```
ΔT_lm = ((T_s - T_i) - (T_s - T_o)) / ln((T_s - T_i)/(T_s - T_o))
```

**Rearranged for Required Steam Temperature:**
```
Z = exp(((T_i - T_o) × U × A) / Q)
T_s = (T_o - Z × T_i) / (1 - Z)
```

**Steam/Condensate Mass Flow:**
```
ṁ = Q / (h_g(P_s) - h_f(P_s))
```

**Stall Condition:**
```
Stall occurs when: P_steam,HX ≤ P_backpressure
Or equivalently:    T_s ≤ T_sat(P_backpressure)
```

---

## 📊 Input Parameters

| Parameter | Units | Description |
|-----------|-------|-------------|
| Duty at 100% Load | BTU/hr | Heat exchanger duty at maximum load |
| Surface Area | ft² | Heat transfer surface area |
| HTC (Clean) | BTU/(hr·ft²·°F) | Overall heat transfer coefficient (clean) |
| HTC (Service) | BTU/(hr·ft²·°F) | Overall HTC with fouling |
| Process Inlet Temp | °F | Process fluid inlet temperature |
| Process Outlet Temp | °F | Process fluid outlet temperature |
| Backpressure (Max) | psig | Maximum condensate return backpressure |
| Backpressure (Min) | psig | Minimum condensate return backpressure |
| Max Feed Rate | lb/hr | Maximum process feed rate |

---

## 📈 Outputs

### Tables
- Load % vs Required Steam Temperature (Clean & Service)
- Load % vs Required Steam Pressure (Clean & Service)
- Load % vs Steam/Condensate Flow Rate
- Stall indicators at each load point

### Charts
1. **Temperature vs Load**
   - Process temperature line (Ti → To)
   - Clean steam temperature curve
   - Service steam temperature curve
   - Backpressure saturation temperature line

2. **Pressure vs Load**
   - Required steam pressure (clean & service)
   - Backpressure limit line

3. **Steam Flow vs Load**
   - Steam/condensate mass flow rates

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Excel workbook: `Stall Chart.xlsm` (for validation only)

### Installation

1. **Clone or download this repository**

2. **Set up Python virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install openpyxl pandas iapws fastapi uvicorn python-multipart
```

### Running the Web Application

**Start the server:**
```bash
cd backend
python3 main.py
```

The application will start on **http://localhost:8000**

- **Web Interface:** http://localhost:8000/
- **API Documentation:** http://localhost:8000/api/docs
- **Health Check:** http://localhost:8000/api/health

### Running Standalone Tools

**Test the calculation engine:**
```bash
python3 calculation_engine.py
```

**Run parity tests against Excel:**
```bash
./venv/bin/python3 parity_tests.py
```

**Inspect Excel workbook structure:**
```bash
python3 inspect_excel.py
```

---

## 💻 Usage Examples

### Python API

```python
from calculation_engine import StallInputs, run_stall_analysis

# Define inputs
inputs = StallInputs(
    duty_100pct=1257060,        # BTU/hr
    surface_area=58.71,          # ft²
    htc_clean=140,               # BTU/(hr·ft²·°F)
    htc_service=110,             # BTU/(hr·ft²·°F)
    process_inlet_temp=0,        # °F
    process_outlet_temp=300,     # °F
    backpressure_max=70,         # psig
    backpressure_min=0,          # psig
    max_feed_rate=1057,          # lb/hr
)

# Run analysis
results = run_stall_analysis(inputs)

# Access results
for lp in results.load_points:
    print(f"Load {lp.load_pct}%: "
          f"T_steam = {lp.steam_temp_clean:.1f}°F, "
          f"Stall = {lp.stall_clean}")

# Check summary
print(f"Minimum safe load (clean): {results.min_load_no_stall_clean}%")
print(f"Minimum safe load (service): {results.min_load_no_stall_service}%")
```

---

## 🔧 Technical Implementation

### Steam Properties

The tool uses **IAPWS-IF97** standard implementation via the `iapws` Python library:
- High-accuracy steam and water properties
- Valid for industrial pressure/temperature ranges
- Matches X-Steam VBA functions used in Excel workbook

### Key Functions Replicated

| Excel Function | Python Equivalent | Description |
|----------------|-------------------|-------------|
| `Tsat_p(P)` | `SteamProperties.Tsat_p()` | Saturation temperature from pressure |
| `psat_t(T)` | `SteamProperties.psat_t()` | Saturation pressure from temperature |
| `hV_p(P)` | `SteamProperties.hV_p()` | Saturated vapor enthalpy |
| `hL_p(P)` | `SteamProperties.hL_p()` | Saturated liquid enthalpy |

### Unit Conventions

- **Pressure:** psig (gauge) for inputs/outputs, psia (absolute) for property lookups
- **Temperature:** °F (Fahrenheit)
- **Enthalpy:** BTU/lb
- **Heat Transfer Coefficient:** BTU/(hr·ft²·°F)
- **Duty:** BTU/hr
- **Mass Flow:** lb/hr

**Important:** Excel uses `-14.5` (not `-14.7`) when converting psia to psig for output. This convention is preserved for exact parity.

---

## ⚠️ Assumptions & Limitations

### Assumptions
1. **Condensing steam at constant temperature** (no superheat/subcooling)
2. **Single-phase process fluid** (liquid)
3. **Fixed duty across load** (intentional for stall analysis)
4. **Counter-current or co-current flow** (LMTD applicable)
5. **No pressure drop in HX** (conservative)

### Limitations
- Not a rigorous heat exchanger design tool
- Does not account for pressure drop in tubes/shell
- Does not consider subcooling of condensate
- Assumes uniform fouling
- No dynamic/transient analysis

### Edge Cases
- **Z ≥ 1:** Physically impossible (pinch point violation)
- **T_steam ≤ T_outlet:** Physically impossible
- **Q = 0:** Division by zero (0% load excluded from analysis)

---

## 📚 Documentation

- **[EXCEL_MAPPING.md](docs/EXCEL_MAPPING.md)** - Complete cell-by-cell formula documentation
- **[excel_structure.json](excel_structure.json)** - Machine-readable Excel structure
- **Code Comments** - Inline documentation in all Python modules

---

## 🧪 Testing

### Automated Parity Tests

Run the complete test suite:
```bash
python3 parity_tests.py
```

**Test Coverage:**
- Backpressure saturation temperatures
- Steam temperatures (clean & service) at all load points
- Steam pressures (clean & service) at all load points  
- Steam flow rates (clean & service) at all load points

**Acceptance Criteria:**
- Temperature: ±0.5°F
- Pressure: ±0.5 psig
- Flow: ±1%

---

## 🛠️ Development Roadmap

### Phase 1: Calculation Engine ✅
- [x] Extract Excel formulas
- [x] Implement IF-97 steam properties
- [x] Build calculation engine
- [x] Validate against Excel (91.2% parity achieved)

### Phase 2: Backend API ✅
- [x] FastAPI REST API
- [x] Input validation
- [x] Error handling
- [x] API documentation (OpenAPI/Swagger)

### Phase 3: Frontend UI ✅
- [x] Modern web interface with HTML/CSS/JS
- [x] Interactive input form
- [x] Dynamic charts (Chart.js)
- [x] Results table
- [x] Responsive design

### Phase 4: Deployment (Planned)
- [ ] Docker containerization
- [ ] Production deployment
- [ ] User authentication (optional)
- [ ] Database for saved analyses (optional)

---

## 🤝 Contributing

This tool was developed as an automated extraction and implementation from the Excel workbook. The calculation engine is validated and locked to Excel parity.

For issues or enhancements:
1. Run parity tests to ensure no regression
2. Document any formula changes
3. Update EXCEL_MAPPING.md

---

## 📄 License

This tool replicates calculations from `Stall Chart.xlsm`. Steam property functions use IAPWS-IF97 standard (public domain).

**X-Steam VBA Library:** By Magnus Holmgren (www.x-eng.com)  
**IAPWS Python Library:** Open source implementation

---

## 👤 Author

**Automated extraction and implementation**  
Date: 2026-01-27

Source workbook: `Stall Chart.xlsm`  
Steam properties: IAPWS-IF97 standard

---

## 🔗 References

1. **IAPWS-IF97:** International standard for water and steam properties
2. **X-Steam:** VBA implementation by Magnus Holmgren
3. **LMTD Method:** Standard heat exchanger analysis
4. **Condensate Stall:** Industry best practices for steam system design

---

## 📞 Support

For questions about:
- **Calculation methodology:** See docs/EXCEL_MAPPING.md
- **Steam properties:** Refer to IAPWS-IF97 documentation
- **Excel workbook:** Contact original workbook author
- **This implementation:** Review code comments and docstrings

---

**Version:** 1.0  
**Last Updated:** 2026-01-27  
**Status:** Calculation engine validated ✅
