# Mode 3 Implementation Prompt - Optimized for HXStall Repository

## Current State Assessment

**IMPORTANT**: The current codebase in `/Users/jhsmacbook/Documents/HX Stall/HXStall/` only implements:
- **Mode 1**: Variable Load (Duty Turndown) - HARDCODED (no mode selection UI)
- **Mode 2**: Does NOT exist
- **Operating Mode Dropdown**: Does NOT exist

## Task: Add Mode 3 — Variable Outlet Temperature (Constant Inlet Temperature)

### Prerequisites

Before implementing Mode 3, you must:

1. **Create Operating Mode Selection Infrastructure**
   - Add dropdown to `frontend/index.html` with options:
     - "Variable Load (Duty Turndown)" - Mode 1 (existing)
     - "Variable Outlet Temperature" - Mode 3 (new)
   - Add JavaScript to show/hide appropriate input fields based on selection
   - Default to Mode 1 to preserve existing behavior

2. **Extend Backend API**
   - Add `operating_mode` field to `backend/main.py::AnalysisRequest`
   - Add conditional logic to handle Mode 3 parameters
   - Keep Mode 1 logic unchanged

3. **File Structure to Modify**
   ```
   HXStall/
   ├── frontend/index.html          [ADD mode dropdown + Mode 3 inputs]
   ├── backend/main.py              [ADD operating_mode parameter]
   ├── backend/validation.py        [ADD Mode 3 validation rules]
   ├── calculation_engine.py        [REUSE existing - no changes needed]
   └── MODE_3_IMPLEMENTATION.md     [DOCUMENT changes]
   ```

---

## 1. Conceptual Definition

Mode 3 represents the operating question:

> "My inlet temperature is stable, but my outlet temperature setpoint changes. How does changing the outlet temperature affect required steam pressure and stall risk?"

**Key Characteristics:**
- Process inlet temperature (Ti) is **constant**
- Process outlet temperature (To) is the **independent variable**
- Heat duty (Q) is **held constant** across the temperature sweep
- Condensing steam, constant UA (clean/service)
- Stall criterion **unchanged**

---

## 2. Core Constraint (Do NOT Change Physics)

Mode 3 must:
- ✅ Reuse `calculation_engine.py::StallCalculator.calculate_load_point()`
- ✅ Call existing calculation functions unchanged
- ❌ NOT introduce flow, cp, or dynamic duty recalculation
- ❌ NOT change the stall criterion
- ❌ NOT change the Z formulation
- ❌ NOT introduce new heat-transfer equations

**Only the independent variable changes from load_pct to To.**

---

## 3. User Inputs Required (Mode 3)

### Frontend UI Changes (`frontend/index.html`)

**Add Mode Selection Dropdown:**
```html
<div class="form-group">
    <label for="operating_mode">Operating Mode</label>
    <select id="operating_mode" onchange="updateInputsForMode()">
        <option value="mode1">Variable Load (Duty Turndown)</option>
        <option value="mode3">Variable Outlet Temperature</option>
    </select>
</div>
```

**Mode 3 Input Fields (show only when mode3 selected):**

| Input Field | Parameter | Units | Default | Description |
|-------------|-----------|-------|---------|-------------|
| `temp_in` | Process Inlet Temp (Ti) | °F | 0 | Constant inlet temperature |
| `temp_out_min` | Min Outlet Temp | °F | 100 | Minimum To to evaluate |
| `temp_out_max` | Max Outlet Temp | °F | 300 | Maximum To to evaluate |
| `duty_ref` | Reference Duty | BTU/hr | 1257060 | Constant duty across sweep |
| `area` | Surface Area | ft² | 58.71 | Heat transfer area |
| `htc_clean` | HTC (Clean) | BTU/(hr·ft²·°F) | 140 | Clean condition |
| `htc_service` | HTC (Service) | BTU/(hr·ft²·°F) | 110 | Fouled condition |
| `bp_max` | Backpressure (Max) | psig | 70 | Condensate backpressure |
| `num_points` | Number of Points | - | 25 | Evaluation points |

**Mode 1 Input Fields (hide when mode3 selected):**
- `temp_out` (single value) - replaced by range in Mode 3
- Load percentage controls - not applicable in Mode 3

---

## 4. Backend API Changes (`backend/main.py`)

### Extend `AnalysisRequest` Model:

```python
class AnalysisRequest(BaseModel):
    # Add operating mode selector
    operating_mode: str = Field(default="mode1", description="Operating mode: 'mode1' or 'mode3'")
    
    # Mode 1 fields (existing)
    duty_100pct: Optional[float] = None
    process_outlet_temp: Optional[float] = None  # Single value for Mode 1
    load_percentages: Optional[List[float]] = None
    
    # Mode 3 fields (new)
    duty_ref: Optional[float] = None  # Constant duty for Mode 3
    temp_out_min: Optional[float] = None
    temp_out_max: Optional[float] = None
    num_points: Optional[int] = 25
    
    # Common fields (both modes)
    surface_area: float
    htc_clean: float
    htc_service: float
    process_inlet_temp: float
    backpressure_max: float
    backpressure_min: float = 0
    max_feed_rate: float = 1000
```

### Add Mode 3 Analysis Function:

```python
def run_mode3_analysis(request: AnalysisRequest):
    """
    Run Mode 3: Variable Outlet Temperature analysis
    
    For each To in [To_min, To_max]:
        - Hold Ti constant
        - Use Q_ref (constant duty)
        - Calculate required steam conditions
        - Check stall condition
    """
    # Generate outlet temperature points
    temps = np.linspace(request.temp_out_min, request.temp_out_max, request.num_points)
    
    results = []
    for To_i in temps:
        # Create StallInputs with this specific To
        inputs = StallInputs(
            duty_100pct=request.duty_ref,  # Use reference duty (100% basis)
            surface_area=request.surface_area,
            htc_clean=request.htc_clean,
            htc_service=request.htc_service,
            process_inlet_temp=request.process_inlet_temp,
            process_outlet_temp=To_i,  # Variable outlet temp
            backpressure_max=request.backpressure_max,
            backpressure_min=request.backpressure_min,
            max_feed_rate=request.max_feed_rate,
            load_percentages=[100]  # Fixed at 100% (constant duty)
        )
        
        # Run existing calculation engine
        result = run_stall_analysis(inputs)
        
        # Store result keyed by To
        results.append({
            'outlet_temp': To_i,
            'load_point': result.load_points[0]  # Only one load point (100%)
        })
    
    return results
```

---

## 5. Validation Rules (`backend/validation.py`)

Add Mode 3-specific validation to `InputValidator` class:

```python
def validate_mode3_inputs(self, inputs: dict) -> Tuple[List[ValidationMessage], List[ValidationMessage]]:
    """Validate Mode 3 specific inputs"""
    errors = []
    warnings = []
    
    Ti = inputs.get('process_inlet_temp')
    To_min = inputs.get('temp_out_min')
    To_max = inputs.get('temp_out_max')
    
    # Rule 1: To_min > Ti
    if To_min <= Ti:
        errors.append(ValidationMessage(
            message="Minimum outlet temperature must be greater than inlet temperature",
            field="temp_out_min",
            reason=f"To_min ({To_min}°F) ≤ Ti ({Ti}°F) - no heat transfer possible",
            suggested_fix=f"Set To_min > {Ti}°F (e.g., {Ti + 50}°F)",
            code="TO_MIN_TOO_LOW"
        ))
    
    # Rule 2: To_max > Ti
    if To_max <= Ti:
        errors.append(ValidationMessage(
            message="Maximum outlet temperature must be greater than inlet temperature",
            field="temp_out_max",
            reason=f"To_max ({To_max}°F) ≤ Ti ({Ti}°F) - no heat transfer possible",
            suggested_fix=f"Set To_max > {Ti}°F (e.g., {Ti + 100}°F)",
            code="TO_MAX_TOO_LOW"
        ))
    
    # Rule 3: To_max > To_min
    if To_max <= To_min:
        errors.append(ValidationMessage(
            message="Maximum outlet temperature must be greater than minimum",
            field="temp_out_max",
            reason=f"To_max ({To_max}°F) ≤ To_min ({To_min}°F) - invalid range",
            suggested_fix=f"Set To_max > {To_min}°F (e.g., {To_min + 50}°F)",
            code="TO_RANGE_INVALID"
        ))
    
    # Warning: Small temperature difference
    if To_min - Ti < 10:
        warnings.append(ValidationMessage(
            message="Small temperature difference between inlet and minimum outlet",
            field="temp_out_min",
            reason=f"ΔT = {To_min - Ti}°F is very small - may cause high steam requirements",
            suggested_fix="Consider increasing To_min for more realistic operation",
            code="SMALL_DELTA_T"
        ))
    
    return errors, warnings
```

---

## 6. X-Axis Definition

**For Mode 3:**
- X-axis variable = **Process Outlet Temperature (To)**
- Units = °F (or °C based on global setting)
- Axis range = To_min → To_max
- Evaluation points = N (default 25, configurable)
- **Do NOT use 0-100% load axis**

**Chart Updates Required:**
- X-axis label: `"Process Outlet Temperature (°F)"`
- Chart title: `"Mode 3: Variable Outlet Temperature Analysis"`
- Subtitle: `"Inlet temperature held constant at ${Ti}°F"`

---

## 7. Chart and Table Updates (`frontend/index.html`)

### Chart Updates:

```javascript
function createMode3Chart(data, Ti) {
    const outletTemps = data.map(d => d.outlet_temp);
    const steamTempClean = data.map(d => d.load_point.steam_temp_clean);
    const steamTempService = data.map(d => d.load_point.steam_temp_service);
    
    // Update chart configuration
    chart.data.labels = outletTemps;  // X-axis: outlet temps
    chart.options.scales.x.title.text = 'Process Outlet Temperature (°F)';
    chart.options.plugins.subtitle.text = `Inlet temperature held constant at ${Ti}°F`;
    
    // Update datasets
    chart.data.datasets[0].data = steamTempClean;
    chart.data.datasets[1].data = steamTempService;
    
    chart.update();
}
```

### Table Updates:

| Column | Mode 1 | Mode 3 |
|--------|--------|--------|
| Independent Variable | Load % | Outlet Temp (°F) |
| Duty | Variable | Constant |
| T_steam Clean | ✓ | ✓ |
| P_steam Clean | ✓ | ✓ |
| Flow Clean | ✓ | ✓ |
| T_steam Service | ✓ | ✓ |
| P_steam Service | ✓ | ✓ |
| Flow Service | ✓ | ✓ |
| Stall Status | ✓ | ✓ |

---

## 8. Physical Behavior Validation

**Expected Results for Mode 3:**

1. **Higher To → Higher Ts**: As outlet temperature increases, required steam temperature increases
2. **Higher To → Higher Ps**: As outlet temperature increases, required steam pressure increases
3. **Higher To → Higher Stall Risk**: Stall risk increases at higher outlet temperatures
4. **Service vs Clean**: Service (fouled) condition requires higher steam pressure than clean

**Why?**
- Higher To reduces temperature driving force (ΔT_lm decreases)
- Smaller ΔT requires higher steam temperature to maintain Q
- Higher steam temperature means higher steam pressure (saturation)

---

## 9. Implementation Checklist

### Phase 1: Frontend (HTML/JS)
- [ ] Add operating mode dropdown
- [ ] Add Mode 3 input fields (with visibility toggle)
- [ ] Hide Mode 1-specific fields when Mode 3 selected
- [ ] Add JavaScript function `updateInputsForMode()`
- [ ] Update `runAnalysis()` to send operating_mode parameter
- [ ] Update chart rendering for variable x-axis
- [ ] Update table rendering for Mode 3 columns

### Phase 2: Backend (API)
- [ ] Add `operating_mode` to `AnalysisRequest`
- [ ] Add Mode 3 parameters to request model
- [ ] Create `run_mode3_analysis()` function
- [ ] Add conditional routing in `/api/analyze` endpoint
- [ ] Update response model to handle both modes

### Phase 3: Validation
- [ ] Add `validate_mode3_inputs()` to `validation.py`
- [ ] Implement To_min > Ti check
- [ ] Implement To_max > To_min check
- [ ] Add meaningful error messages

### Phase 4: Testing
- [ ] Test Mode 1 unchanged (regression test)
- [ ] Test Mode 3 with various inputs
- [ ] Verify physical behavior (higher To → higher Ps)
- [ ] Test validation rules (invalid ranges)
- [ ] Test chart/table rendering

---

## 10. Acceptance Criteria

✅ Task complete when:

1. **Mode Selection Works**
   - Dropdown shows "Variable Load" and "Variable Outlet Temperature"
   - Input fields update dynamically based on selection
   - Default behavior (Mode 1) unchanged

2. **Mode 3 Calculations Correct**
   - X-axis shows outlet temperature range
   - Higher To produces higher Ts and Ps
   - Stall detection works correctly
   - Service condition shows higher pressure than clean

3. **Charts and Tables Update**
   - X-axis label changes to "Process Outlet Temperature"
   - Chart subtitle shows inlet temperature
   - Table columns appropriate for Mode 3

4. **Validation Works**
   - Blocks To_min ≤ Ti
   - Blocks To_max ≤ To_min
   - Provides clear error messages

5. **No Regression**
   - Mode 1 still works identically
   - Excel parity unchanged for Mode 1
   - No breaking changes to existing functionality

---

## 11. Explicit Non-Goals

❌ Do NOT:
- Recalculate duty from flow or specific heat
- Allow multiple independent variables
- Introduce exchanger rating logic
- Change Z factor formulation
- Modify stall criterion
- Change existing calculation engine functions
- Add Mode 2 (out of scope)

---

## 12. Key Implementation Notes

### Reusing Existing Calculation Engine

The beauty of Mode 3 is that it **reuses** `calculation_engine.py` without modification:

```python
# Mode 3 just calls the existing engine multiple times
for To_i in outlet_temps:
    inputs = StallInputs(
        duty_100pct=Q_ref,           # Constant
        process_inlet_temp=Ti,        # Constant  
        process_outlet_temp=To_i,     # Variable ← Only this changes
        surface_area=A,               # Constant
        htc_clean=U_clean,            # Constant
        htc_service=U_service,        # Constant
        backpressure_max=BP,          # Constant
        load_percentages=[100]        # Always 100% (constant duty)
    )
    
    # Existing function, unchanged
    result = run_stall_analysis(inputs)
```

This demonstrates the **elegance of the duty-driven approach** - the same physics engine handles both modes.

---

## 13. Example Inputs for Testing

### Test Case 1: Moderate Temperature Range
```json
{
  "operating_mode": "mode3",
  "process_inlet_temp": 50,
  "temp_out_min": 100,
  "temp_out_max": 300,
  "duty_ref": 1257060,
  "surface_area": 58.71,
  "htc_clean": 140,
  "htc_service": 110,
  "backpressure_max": 70,
  "num_points": 25
}
```

**Expected**: Smooth increase in required steam pressure from To=100°F to To=300°F

### Test Case 2: High Outlet Temperature (Stall Risk)
```json
{
  "operating_mode": "mode3",
  "process_inlet_temp": 100,
  "temp_out_min": 250,
  "temp_out_max": 350,
  "duty_ref": 1500000,
  "surface_area": 50,
  "htc_clean": 120,
  "htc_service": 90,
  "backpressure_max": 80,
  "num_points": 20
}
```

**Expected**: Stall at higher outlet temperatures (reduced ΔT_lm → higher Ps → exceeds backpressure)

---

## Files to Create/Modify

### Create:
1. `/Users/jhsmacbook/Documents/HX Stall/HXStall/MODE_3_IMPLEMENTATION.md` - Implementation documentation
2. `/Users/jhsmacbook/Documents/HX Stall/HXStall/tests/test_mode3.py` - Unit tests (optional)

### Modify:
1. `/Users/jhsmacbook/Documents/HX Stall/HXStall/frontend/index.html` - Add UI elements
2. `/Users/jhsmacbook/Documents/HX Stall/HXStall/backend/main.py` - Add API logic
3. `/Users/jhsmacbook/Documents/HX Stall/HXStall/backend/validation.py` - Add validation

### Do NOT Modify:
1. `/Users/jhsmacbook/Documents/HX Stall/HXStall/calculation_engine.py` - Reuse as-is
2. `/Users/jhsmacbook/Documents/HX Stall/HXStall/parity_tests.py` - Mode 1 tests unchanged

---

## Summary

This optimized prompt accounts for:
- ✅ Current codebase state (Mode 1 only, no dropdown)
- ✅ Exact file paths in HXStall repository
- ✅ Reuse of existing calculation engine
- ✅ Clear validation rules and error handling
- ✅ Specific implementation steps
- ✅ Testing guidance
- ✅ No regression to Mode 1

**Key Insight**: Mode 3 is just Mode 1 with a different independent variable (To instead of load%). The physics engine remains unchanged - we just iterate over outlet temperatures instead of load percentages.