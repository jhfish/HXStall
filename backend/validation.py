#!/usr/bin/env python3
"""
Input Validation and Engineering Guardrails

Implements strict validation rules for steam heat exchanger stall analysis.
Provides both hard errors (block calculation) and warnings (allow but inform).

Author: Implementation based on engineering requirements
Date: 2026-01-28
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationMessage:
    """Structured validation message"""
    severity: str  # 'error' or 'warning'
    field: str  # Input field name
    value: Optional[float]  # Invalid value
    message: str  # Engineer-friendly explanation
    reason: str  # Physics/engineering reason
    suggested_fix: str  # How to fix
    code: str  # Machine-readable error code


class InputValidator:
    """
    Comprehensive input validation for stall analysis.
    
    Implements requirements for:
    - Hard input requirements (blocking errors)
    - Engineering warnings (non-blocking)
    - Physics-based guardrails
    """
    
    # Physical constants and limits
    TEMP_MIN = -100.0  # °F
    TEMP_MAX = 700.0  # °F
    TEMP_CRITICAL = 705.5  # °F (approximate water critical point)
    TEMP_CRITICAL_MARGIN = 700.0  # °F (safe limit below critical)
    
    TEMP_SAT_MIN = 32.02  # °F (triple point)
    TEMP_SAT_MAX = 705.5  # °F (critical point)
    
    PRESSURE_MIN = 0.0  # psig
    PRESSURE_TYPICAL_MAX = 600.0  # psig (warning threshold)
    
    U_MIN_TYPICAL = 5.0  # BTU/(hr·ft²·°F)
    U_MAX_TYPICAL = 2000.0  # BTU/(hr·ft²·°F)
    
    AREA_MIN_TYPICAL = 1.0  # ft²
    AREA_MAX_TYPICAL = 20000.0  # ft²
    
    Z_CRITICAL = 0.999  # Z factor safety limit
    
    LOAD_LOW_THRESHOLD = 10.0  # % (warning for loads below this)
    
    def __init__(self):
        """Initialize validator"""
        self.errors: List[ValidationMessage] = []
        self.warnings: List[ValidationMessage] = []
    
    def clear(self):
        """Clear all messages"""
        self.errors.clear()
        self.warnings.clear()
    
    def add_error(self, field: str, value: Optional[float], message: str, 
                  reason: str, suggested_fix: str, code: str):
        """Add a blocking error"""
        self.errors.append(ValidationMessage(
            severity='error',
            field=field,
            value=value,
            message=message,
            reason=reason,
            suggested_fix=suggested_fix,
            code=code
        ))
    
    def add_warning(self, field: str, value: Optional[float], message: str, 
                    reason: str, suggested_fix: str, code: str):
        """Add a non-blocking warning"""
        self.warnings.append(ValidationMessage(
            severity='warning',
            field=field,
            value=value,
            message=message,
            reason=reason,
            suggested_fix=suggested_fix,
            code=code
        ))
    
    def validate_inputs(self, inputs: Dict) -> Tuple[List[ValidationMessage], List[ValidationMessage]]:
        """
        Validate all inputs and return errors and warnings.
        
        Args:
            inputs: Dictionary of input parameters
            
        Returns:
            Tuple of (errors, warnings)
        """
        self.clear()
        
        # Extract values
        duty = inputs.get('duty_100pct')
        area = inputs.get('surface_area')
        htc_clean = inputs.get('htc_clean')
        htc_service = inputs.get('htc_service')
        temp_in = inputs.get('process_inlet_temp')
        temp_out = inputs.get('process_outlet_temp')
        bp_max = inputs.get('backpressure_max')
        bp_min = inputs.get('backpressure_min', 0)
        load_percentages = inputs.get('load_percentages', [100, 90, 80, 70, 60, 50, 40, 30, 20, 10])
        
        # ========== A) HARD INPUT REQUIREMENTS (BLOCK) ==========
        
        # 1) Duty / Area / U must be positive
        if duty is not None and duty <= 0:
            self.add_error(
                field='duty_100pct',
                value=duty,
                message=f'Duty must be > 0 (entered: {duty})',
                reason='Heat duty represents energy transfer rate; zero or negative values are physically meaningless',
                suggested_fix='Enter heat duty at 100% load in BTU/hr (e.g., 1,257,060 BTU/hr)',
                code='DUTY_NONPOSITIVE'
            )
        
        if area is not None and area <= 0:
            self.add_error(
                field='surface_area',
                value=area,
                message=f'Heat-transfer area must be > 0 (entered: {area})',
                reason='Surface area is required for heat transfer; zero or negative values are invalid',
                suggested_fix='Enter heat exchanger surface area in ft² (e.g., 58.71 ft²)',
                code='AREA_NONPOSITIVE'
            )
        
        if htc_clean is not None and htc_clean <= 0:
            self.add_error(
                field='htc_clean',
                value=htc_clean,
                message=f'Overall heat-transfer coefficient (U clean) must be > 0 (entered: {htc_clean})',
                reason='U represents thermal conductance; zero or negative values prevent heat transfer',
                suggested_fix='Enter overall U in BTU/(hr·ft²·°F) for clean condition (typical: 100-200)',
                code='HTC_CLEAN_NONPOSITIVE'
            )
        
        if htc_service is not None and htc_service <= 0:
            self.add_error(
                field='htc_service',
                value=htc_service,
                message=f'Overall heat-transfer coefficient (U service) must be > 0 (entered: {htc_service})',
                reason='U represents thermal conductance; zero or negative values prevent heat transfer',
                suggested_fix='Enter overall U in BTU/(hr·ft²·°F) for fouled/service condition (typical: 80-150)',
                code='HTC_SERVICE_NONPOSITIVE'
            )
        
        # 2) Heating direction must be valid
        if temp_in is not None and temp_out is not None and temp_out <= temp_in:
            self.add_error(
                field='process_outlet_temp',
                value=temp_out,
                message=f'Outlet temperature ({temp_out}°F) must be greater than inlet temperature ({temp_in}°F)',
                reason='Steam heating increases process fluid temperature; outlet must exceed inlet (To > Ti)',
                suggested_fix='Verify temperatures: inlet is cold side, outlet is hot side. Check for reversed values.',
                code='TEMP_OUTLET_NOT_EXCEEDING_INLET'
            )
        
        # 3) Backpressure must be physically valid
        if bp_max is not None and bp_max < 0:
            self.add_error(
                field='backpressure_max',
                value=bp_max,
                message=f'Backpressure must be ≥ 0 psig (entered: {bp_max})',
                reason='Gauge pressure below atmospheric is vacuum; condensate systems operate at positive pressure',
                suggested_fix='Enter backpressure in psig (0 = atmospheric, typical range: 0-100 psig)',
                code='BACKPRESSURE_NEGATIVE'
            )
        
        if bp_min is not None and bp_min < 0:
            self.add_error(
                field='backpressure_min',
                value=bp_min,
                message=f'Backpressure (min) must be ≥ 0 psig (entered: {bp_min})',
                reason='Gauge pressure below atmospheric is vacuum; condensate systems operate at positive pressure',
                suggested_fix='Enter minimum backpressure in psig (typically 0 psig)',
                code='BACKPRESSURE_MIN_NEGATIVE'
            )
        
        if bp_max is not None and bp_min is not None and bp_max < bp_min:
            self.add_error(
                field='backpressure_max',
                value=bp_max,
                message=f'Backpressure max ({bp_max} psig) must be ≥ backpressure min ({bp_min} psig)',
                reason='Maximum backpressure cannot be less than minimum backpressure',
                suggested_fix='Verify backpressure values: max should be ≥ min',
                code='BACKPRESSURE_MAX_LESS_THAN_MIN'
            )
        
        # 4) Temperature ranges
        if temp_in is not None:
            if temp_in < self.TEMP_MIN or temp_in > self.TEMP_MAX:
                self.add_error(
                    field='process_inlet_temp',
                    value=temp_in,
                    message=f'Inlet temperature ({temp_in}°F) is outside supported bounds ({self.TEMP_MIN}°F to {self.TEMP_MAX}°F)',
                    reason='Temperature is outside validated range for this tool',
                    suggested_fix='Check units (°F vs °C) and re-enter. For extreme temperatures, verify IF-97 applicability.',
                    code='TEMP_INLET_OUT_OF_RANGE'
                )
        
        if temp_out is not None:
            if temp_out < self.TEMP_MIN or temp_out > self.TEMP_MAX:
                self.add_error(
                    field='process_outlet_temp',
                    value=temp_out,
                    message=f'Outlet temperature ({temp_out}°F) is outside supported bounds ({self.TEMP_MIN}°F to {self.TEMP_MAX}°F)',
                    reason='Temperature is outside validated range for this tool',
                    suggested_fix='Check units (°F vs °C) and re-enter. For extreme temperatures, verify IF-97 applicability.',
                    code='TEMP_OUTLET_OUT_OF_RANGE'
                )
            elif temp_out >= self.TEMP_CRITICAL_MARGIN:
                self.add_error(
                    field='process_outlet_temp',
                    value=temp_out,
                    message=f'Outlet temperature ({temp_out}°F) is too close to water critical point ({self.TEMP_CRITICAL}°F)',
                    reason='Saturation properties become ill-conditioned near critical point; results unreliable',
                    suggested_fix='Reduce outlet temperature below 700°F or confirm this is not supercritical service',
                    code='TEMP_OUTLET_NEAR_CRITICAL'
                )
        
        # ========== B) ENGINEERING WARNINGS (ALLOW BUT WARN) ==========
        
        # 1) U_service > U_clean
        if htc_clean is not None and htc_service is not None and htc_service > htc_clean:
            self.add_warning(
                field='htc_service',
                value=htc_service,
                message=f'Service (fouled) U ({htc_service}) is higher than clean U ({htc_clean})',
                reason='Fouling typically reduces heat transfer; service U should be ≤ clean U',
                suggested_fix='Verify U values. Service U should account for fouling resistance (typically 70-90% of clean U)',
                code='HTC_SERVICE_EXCEEDS_CLEAN'
            )
        
        # 2) Suspicious magnitudes - U
        if htc_clean is not None:
            if htc_clean < self.U_MIN_TYPICAL or htc_clean > self.U_MAX_TYPICAL:
                self.add_warning(
                    field='htc_clean',
                    value=htc_clean,
                    message=f'U clean ({htc_clean}) is outside typical range ({self.U_MIN_TYPICAL}-{self.U_MAX_TYPICAL} BTU/hr·ft²·°F) for condensing steam',
                    reason='Value is unusually low or high for steam-heated heat exchangers',
                    suggested_fix='Check units and verify U is overall coefficient (not film coefficient). Typical range: 100-200 for shell-and-tube',
                    code='HTC_CLEAN_UNUSUAL'
                )
        
        if htc_service is not None:
            if htc_service < self.U_MIN_TYPICAL or htc_service > self.U_MAX_TYPICAL:
                self.add_warning(
                    field='htc_service',
                    value=htc_service,
                    message=f'U service ({htc_service}) is outside typical range ({self.U_MIN_TYPICAL}-{self.U_MAX_TYPICAL} BTU/hr·ft²·°F) for condensing steam',
                    reason='Value is unusually low or high for steam-heated heat exchangers',
                    suggested_fix='Check units and verify U is overall coefficient (not film coefficient). Typical fouled range: 80-150 for shell-and-tube',
                    code='HTC_SERVICE_UNUSUAL'
                )
        
        # 3) Suspicious magnitudes - Area
        if area is not None:
            if area < self.AREA_MIN_TYPICAL or area > self.AREA_MAX_TYPICAL:
                self.add_warning(
                    field='surface_area',
                    value=area,
                    message=f'Area ({area} ft²) is outside typical range ({self.AREA_MIN_TYPICAL}-{self.AREA_MAX_TYPICAL} ft²)',
                    reason='Value is unusually small or large for industrial heat exchangers',
                    suggested_fix='Check units (ft² vs m²). Verify area is total heat transfer surface.',
                    code='AREA_UNUSUAL'
                )
        
        # 4) Suspicious magnitudes - Duty vs UA
        if duty is not None and area is not None and htc_clean is not None:
            UA = htc_clean * area
            if UA > 0:
                duty_per_UA = duty / UA
                if duty_per_UA < 10 or duty_per_UA > 1000:
                    self.add_warning(
                        field='duty_100pct',
                        value=duty,
                        message=f'Duty ({duty:,.0f} BTU/hr) appears inconsistent with UA ({UA:,.0f} BTU/hr·°F)',
                        reason=f'Duty/UA ratio ({duty_per_UA:.1f}) is unusual; may indicate numerical sensitivity or unit errors',
                        suggested_fix='Verify duty and UA are consistent. Typical ratio: 100-300°F for moderate temperature service',
                        code='DUTY_UA_INCONSISTENT'
                    )
        
        # 5) Backpressure unusually high
        if bp_max is not None and bp_max > self.PRESSURE_TYPICAL_MAX:
            self.add_warning(
                field='backpressure_max',
                value=bp_max,
                message=f'Backpressure ({bp_max} psig) is unusually high for condensate return service',
                reason='Typical condensate systems operate below 100 psig; high BP may indicate unusual service',
                suggested_fix='Verify backpressure in psig. Check if this is a special high-pressure condensate system.',
                code='BACKPRESSURE_HIGH'
            )
        
        # 6) Low-load sensitivity
        if load_percentages:
            min_load = min(load_percentages)
            if min_load < self.LOAD_LOW_THRESHOLD:
                self.add_warning(
                    field='load_percentages',
                    value=min_load,
                    message=f'Minimum load ({min_load}%) is below typical operating range',
                    reason='Very low loads can be numerically sensitive and may not represent stable operating conditions',
                    suggested_fix='Interpret results below 10% load with caution. Consider minimum practical turndown.',
                    code='LOAD_LOW'
                )
        
        return self.errors, self.warnings
    
    def validate_calculation_point(self, load_pct: float, Z: float, T_steam: float, 
                                   T_outlet: float) -> Optional[ValidationMessage]:
        """
        Validate a single calculation point during analysis.
        
        Args:
            load_pct: Load percentage
            Z: Z factor (dimensionless)
            T_steam: Required steam temperature, °F
            T_outlet: Process outlet temperature, °F
            
        Returns:
            ValidationMessage if guardrail violated, else None
        """
        # 1) Z must remain safely below 1
        if Z >= self.Z_CRITICAL:
            return ValidationMessage(
                severity='error',
                field='calculation',
                value=Z,
                message=f'Insufficient UA for required duty at {load_pct}% load (Z={Z:.4f} approaches 1)',
                reason='Z approaching 1 indicates pinch point violation; required steam temperature becomes unbounded (infinite LMTD)',
                suggested_fix='Increase area (A), increase U, reduce required duty, or limit turndown range. Cannot operate at this load.',
                code='Z_APPROACHING_ONE'
            )
        
        # 2) Required steam temperature must remain on saturation curve
        if T_steam < self.TEMP_SAT_MIN or T_steam > self.TEMP_SAT_MAX:
            return ValidationMessage(
                severity='error',
                field='calculation',
                value=T_steam,
                message=f'Calculated steam temperature at {load_pct}% load ({T_steam:.1f}°F) is outside physical saturation range ({self.TEMP_SAT_MIN}°F to {self.TEMP_SAT_MAX}°F)',
                reason='Steam temperature is near triple point or critical point where saturation properties are invalid',
                suggested_fix='Check UA, duty, and temperature inputs. Verify process outlet temperature is achievable with saturated steam.',
                code='TSTEAM_OUT_OF_SATURATION_RANGE'
            )
        
        # 3) Steam temperature must exceed outlet temperature
        if T_steam <= T_outlet:
            return ValidationMessage(
                severity='error',
                field='calculation',
                value=T_steam,
                message=f'Required steam temperature at {load_pct}% load ({T_steam:.1f}°F) is not greater than process outlet temperature ({T_outlet:.1f}°F)',
                reason='Steam must be hotter than process outlet for heat transfer; indicates insufficient driving force',
                suggested_fix='Increase U, increase area, reduce outlet temperature requirement, or reduce duty',
                code='TSTEAM_NOT_EXCEEDING_TOUTLET'
            )
        
        return None
    
    def format_messages(self, messages: List[ValidationMessage]) -> List[Dict]:
        """
        Format messages for API response.
        
        Args:
            messages: List of ValidationMessage objects
            
        Returns:
            List of dictionaries with message details
        """
        return [
            {
                'severity': msg.severity,
                'field': msg.field,
                'value': msg.value,
                'message': msg.message,
                'reason': msg.reason,
                'suggested_fix': msg.suggested_fix,
                'code': msg.code
            }
            for msg in messages
        ]
