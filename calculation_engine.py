#!/usr/bin/env python3
"""
Steam Heat Exchanger Stall Analysis - Calculation Engine

Implements the exact calculation logic from Stall Chart.xlsm using IF-97 steam properties.
This module replicates the Excel formulas documented in docs/EXCEL_MAPPING.md.

Author: Automated extraction and implementation
Date: 2026-01-27
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional
from iapws import IAPWS97


# ============================================================================
# UNIT CONVERSION CONSTANTS
# ============================================================================

# Pressure conversions
PSI_TO_MPA = 0.00689476  # psi to MPa
MPA_TO_PSI = 145.038  # MPa to psi
PSIG_TO_PSIA_EXCEL = 14.7  # Excel uses this for property lookups
PSIA_TO_PSIG_EXCEL = 14.5  # Excel uses this for output conversion (NOT 14.7!)

# Temperature conversions
def fahrenheit_to_kelvin(temp_f: float) -> float:
    """Convert Fahrenheit to Kelvin for IAPWS97"""
    return (temp_f + 459.67) * 5.0 / 9.0

def kelvin_to_fahrenheit(temp_k: float) -> float:
    """Convert Kelvin to Fahrenheit"""
    return temp_k * 9.0 / 5.0 - 459.67

# Enthalpy conversions
KJ_KG_TO_BTU_LB = 0.429923  # kJ/kg to BTU/lb
BTU_LB_TO_KJ_KG = 2.326  # BTU/lb to kJ/kg


# ============================================================================
# STEAM PROPERTY FUNCTIONS (IF-97 / IAPWS97)
# ============================================================================

class SteamProperties:
    """
    Steam property functions matching X-Steam VBA functions.
    Uses IAPWS97 (IF-97 standard implementation).
    """
    
    @staticmethod
    def Tsat_p(P_psia: float) -> float:
        """
        Saturation temperature from pressure.
        
        Args:
            P_psia: Absolute pressure in psia
            
        Returns:
            Saturation temperature in °F
        """
        try:
            P_MPa = P_psia * PSI_TO_MPA
            steam = IAPWS97(P=P_MPa, x=0)  # Saturated liquid point
            T_K = steam.T
            return kelvin_to_fahrenheit(T_K)
        except Exception as e:
            raise ValueError(f"Error in Tsat_p({P_psia} psia): {e}")
    
    @staticmethod
    def psat_t(T_degF: float) -> float:
        """
        Saturation pressure from temperature.
        
        Args:
            T_degF: Temperature in °F
            
        Returns:
            Saturation pressure in psia
        """
        try:
            T_K = fahrenheit_to_kelvin(T_degF)
            steam = IAPWS97(T=T_K, x=0)  # Saturated liquid point
            P_MPa = steam.P
            return P_MPa * MPA_TO_PSI
        except Exception as e:
            raise ValueError(f"Error in psat_t({T_degF} °F): {e}")
    
    @staticmethod
    def hV_p(P_psia: float) -> float:
        """
        Saturated vapor enthalpy from pressure.
        
        Args:
            P_psia: Absolute pressure in psia
            
        Returns:
            Saturated vapor enthalpy in BTU/lb
        """
        try:
            P_MPa = P_psia * PSI_TO_MPA
            steam = IAPWS97(P=P_MPa, x=1)  # Saturated vapor
            h_kJ_kg = steam.h
            return h_kJ_kg * KJ_KG_TO_BTU_LB
        except Exception as e:
            raise ValueError(f"Error in hV_p({P_psia} psia): {e}")
    
    @staticmethod
    def hL_p(P_psia: float) -> float:
        """
        Saturated liquid enthalpy from pressure.
        
        Args:
            P_psia: Absolute pressure in psia
            
        Returns:
            Saturated liquid enthalpy in BTU/lb
        """
        try:
            P_MPa = P_psia * PSI_TO_MPA
            steam = IAPWS97(P=P_MPa, x=0)  # Saturated liquid
            h_kJ_kg = steam.h
            return h_kJ_kg * KJ_KG_TO_BTU_LB
        except Exception as e:
            raise ValueError(f"Error in hL_p({P_psia} psia): {e}")


# ============================================================================
# INPUT DATA STRUCTURE
# ============================================================================

@dataclass
class StallInputs:
    """Input parameters for stall analysis (matches Excel input cells)"""
    
    # Heat exchanger design parameters
    duty_100pct: float  # BTU/hr - Cell D7
    surface_area: float  # ft² - Cell D8
    htc_clean: float  # BTU/(hr·ft²·°F) - Cell D9
    htc_service: float  # BTU/(hr·ft²·°F) - Cell D10
    
    # Process conditions
    process_inlet_temp: float  # °F - Cell D11
    process_outlet_temp: float  # °F - Cell D12
    
    # Condensate system backpressure
    backpressure_max: float  # psig - Cell D13
    backpressure_min: float  # psig - Cell D14
    
    # Operating parameters
    max_feed_rate: float  # lb/hr - Cell D15
    
    # Load range for analysis
    load_percentages: List[float] = None  # Cells C20:C30
    
    def __post_init__(self):
        """Set default load percentages if not provided"""
        if self.load_percentages is None:
            self.load_percentages = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0]
    
    def validate(self) -> List[str]:
        """Validate inputs and return list of warnings/errors"""
        warnings = []
        
        if self.duty_100pct <= 0:
            warnings.append("Duty must be positive")
        
        if self.surface_area <= 0:
            warnings.append("Surface area must be positive")
        
        if self.htc_clean <= 0 or self.htc_service <= 0:
            warnings.append("Heat transfer coefficients must be positive")
        
        if self.htc_service > self.htc_clean:
            warnings.append("Service HTC should not exceed clean HTC (fouling expected)")
        
        if self.process_outlet_temp <= self.process_inlet_temp:
            warnings.append("Outlet temperature must exceed inlet temperature")
        
        if self.backpressure_min < 0:
            warnings.append("Minimum backpressure cannot be negative")
        
        if self.backpressure_max < self.backpressure_min:
            warnings.append("Maximum backpressure must be >= minimum backpressure")
        
        if self.max_feed_rate <= 0:
            warnings.append("Maximum feed rate must be positive")
        
        return warnings


# ============================================================================
# OUTPUT DATA STRUCTURE
# ============================================================================

@dataclass
class LoadPoint:
    """Results for a single load point (one row of Excel table)"""
    
    load_pct: float  # %
    capacity: float  # lb/hr
    duty: float  # BTU/hr
    
    # Clean condition
    z_clean: float  # dimensionless
    steam_temp_clean: float  # °F
    steam_pressure_clean: float  # psig
    steam_flow_clean: float  # lb/hr
    
    # Service/fouled condition
    z_service: float  # dimensionless
    steam_temp_service: float  # °F
    steam_pressure_service: float  # psig
    steam_flow_service: float  # lb/hr
    
    # Stall flags
    stall_clean: bool
    stall_service: bool
    
    # Warnings for this load point
    warnings: List[str]


@dataclass
class StallResults:
    """Complete stall analysis results"""
    
    inputs: StallInputs
    load_points: List[LoadPoint]
    
    # Backpressure saturation temperatures
    t_sat_bp_max: float  # °F
    t_sat_bp_min: float  # °F
    
    # Summary statistics
    min_load_no_stall_clean: Optional[float] = None  # Minimum load % without stall (clean)
    min_load_no_stall_service: Optional[float] = None  # Minimum load % without stall (service)
    
    def __post_init__(self):
        """Calculate summary statistics with interpolation for more accurate results"""
        # Find minimum load without stall using interpolation
        self.min_load_no_stall_clean = self._interpolate_min_safe_load('clean')
        self.min_load_no_stall_service = self._interpolate_min_safe_load('service')
    
    def _interpolate_min_safe_load(self, condition: str) -> Optional[float]:
        """
        Interpolate to find the exact load percentage where stall begins.
        
        Args:
            condition: 'clean' or 'service'
            
        Returns:
            Interpolated minimum safe load percentage, or None if stall at all loads
        """
        # Sort load points from high to low
        sorted_points = sorted(self.load_points, key=lambda x: x.load_pct, reverse=True)
        
        # Find the transition point where stall changes from False to True
        prev_point = None
        for point in sorted_points:
            is_stalled = point.stall_clean if condition == 'clean' else point.stall_service
            
            if prev_point is not None:
                prev_stalled = prev_point.stall_clean if condition == 'clean' else prev_point.stall_service
                
                # Found transition: prev was OK, current is stalled
                if not prev_stalled and is_stalled:
                    # Get steam temperatures for interpolation
                    if condition == 'clean':
                        temp_high = prev_point.steam_temp_clean
                        temp_low = point.steam_temp_clean
                    else:
                        temp_high = prev_point.steam_temp_service
                        temp_low = point.steam_temp_service
                    
                    load_high = prev_point.load_pct
                    load_low = point.load_pct
                    
                    # Linear interpolation to find where T_steam = T_sat_backpressure
                    t_sat_bp = self.t_sat_bp_max
                    
                    # Interpolate: load = load_low + (load_high - load_low) * (t_sat_bp - temp_low) / (temp_high - temp_low)
                    if abs(temp_high - temp_low) > 0.01:  # Avoid division by zero
                        interpolated_load = load_low + (load_high - load_low) * (t_sat_bp - temp_low) / (temp_high - temp_low)
                        return round(interpolated_load, 1)  # Round to 1 decimal place
                    else:
                        # If temps are nearly identical, use midpoint
                        return round((load_high + load_low) / 2, 1)
            
            prev_point = point
        
        # If we get here, check if no stall at all or stall at all loads
        if sorted_points and not (sorted_points[-1].stall_clean if condition == 'clean' else sorted_points[-1].stall_service):
            # No stall even at lowest load
            return sorted_points[-1].load_pct
        
        return None  # Stall at all loads


# ============================================================================
# CALCULATION ENGINE
# ============================================================================

class StallCalculator:
    """
    Main calculation engine for stall analysis.
    Implements formulas from Excel workbook exactly.
    """
    
    def __init__(self, inputs: StallInputs):
        """Initialize calculator with input parameters"""
        self.inputs = inputs
        self.steam = SteamProperties()
    
    def calculate_z_factor(self, U: float, A: float, Q: float, 
                          T_i: float, T_o: float) -> float:
        """
        Calculate Z factor (dimensionless LMTD parameter).
        
        Excel formula: Z = EXP(((T_i - T_o) * U * A) / Q)
        
        Args:
            U: Overall heat transfer coefficient, BTU/(hr·ft²·°F)
            A: Surface area, ft²
            Q: Duty, BTU/hr
            T_i: Process inlet temperature, °F
            T_o: Process outlet temperature, °F
            
        Returns:
            Z factor (dimensionless)
        """
        if Q == 0:
            return float('inf')
        
        exponent = ((T_i - T_o) * U * A) / Q
        return math.exp(exponent)
    
    def calculate_steam_temperature(self, Z: float, T_i: float, T_o: float) -> float:
        """
        Calculate required steam saturation temperature.
        
        Excel formula: T_s = (T_o - Z * T_i) / (1 - Z)
        
        Args:
            Z: Z factor (dimensionless)
            T_i: Process inlet temperature, °F
            T_o: Process outlet temperature, °F
            
        Returns:
            Required steam temperature, °F
        """
        if Z >= 1.0:
            return float('inf')  # Physically impossible
        
        T_s = (T_o - Z * T_i) / (1.0 - Z)
        return T_s
    
    def calculate_steam_pressure(self, T_s: float) -> float:
        """
        Calculate required steam pressure from saturation temperature.
        
        Excel formula: P_psig = psat_t(T_s) - 14.5
        
        Args:
            T_s: Steam saturation temperature, °F
            
        Returns:
            Required steam pressure, psig
        """
        P_psia = self.steam.psat_t(T_s)
        P_psig = P_psia - PSIA_TO_PSIG_EXCEL  # Excel uses 14.5, not 14.7!
        return P_psig
    
    def calculate_steam_flow(self, Q: float, P_psig: float) -> float:
        """
        Calculate steam/condensate mass flow rate.
        
        Excel formula: mdot = Q / (hV_p(P_psia) - hL_p(P_psia))
        
        Args:
            Q: Duty, BTU/hr
            P_psig: Steam pressure, psig
            
        Returns:
            Steam flow rate, lb/hr
        """
        # Convert to absolute pressure for steam tables
        P_psia = P_psig + PSIG_TO_PSIA_EXCEL
        
        # Get latent heat of vaporization
        h_vapor = self.steam.hV_p(P_psia)
        h_liquid = self.steam.hL_p(P_psia)
        h_fg = h_vapor - h_liquid
        
        if h_fg <= 0:
            return float('inf')
        
        mdot = Q / h_fg
        return mdot
    
    def check_stall(self, T_steam: float, T_sat_bp: float) -> bool:
        """
        Check if stall condition exists.
        
        Stall occurs when: T_steam <= T_sat_backpressure
        
        Args:
            T_steam: Required steam temperature, °F
            T_sat_bp: Backpressure saturation temperature, °F
            
        Returns:
            True if stall condition exists
        """
        return T_steam <= T_sat_bp
    
    def calculate_load_point(self, load_pct: float, 
                            t_sat_bp_max: float, 
                            t_sat_bp_min: float) -> LoadPoint:
        """
        Calculate all parameters for a single load point.
        
        Args:
            load_pct: Load percentage (0-100)
            t_sat_bp_max: Max backpressure saturation temperature, °F
            t_sat_bp_min: Min backpressure saturation temperature, °F
            
        Returns:
            LoadPoint with all calculated values
        """
        warnings = []
        
        # Scale capacity and duty
        capacity = self.inputs.max_feed_rate * (load_pct / 100.0)
        duty = self.inputs.duty_100pct * (load_pct / 100.0)
        
        # Shorthand for inputs
        A = self.inputs.surface_area
        T_i = self.inputs.process_inlet_temp
        T_o = self.inputs.process_outlet_temp
        U_clean = self.inputs.htc_clean
        U_service = self.inputs.htc_service
        
        # ========== CLEAN CONDITION ==========
        try:
            z_clean = self.calculate_z_factor(U_clean, A, duty, T_i, T_o)
            
            if z_clean >= 1.0:
                warnings.append(f"Clean: Z >= 1 (pinch point violation) at {load_pct}% load")
                steam_temp_clean = float('inf')
                steam_pressure_clean = float('inf')
                steam_flow_clean = float('inf')
                stall_clean = True
            else:
                steam_temp_clean = self.calculate_steam_temperature(z_clean, T_i, T_o)
                
                if steam_temp_clean <= T_o:
                    warnings.append(f"Clean: Steam temp <= outlet temp at {load_pct}% load")
                
                steam_pressure_clean = self.calculate_steam_pressure(steam_temp_clean)
                steam_flow_clean = self.calculate_steam_flow(duty, steam_pressure_clean)
                
                # Check stall against max backpressure (worst case)
                stall_clean = self.check_stall(steam_temp_clean, t_sat_bp_max)
        
        except Exception as e:
            warnings.append(f"Clean calculation error at {load_pct}% load: {e}")
            z_clean = float('nan')
            steam_temp_clean = float('nan')
            steam_pressure_clean = float('nan')
            steam_flow_clean = float('nan')
            stall_clean = True
        
        # ========== SERVICE/FOULED CONDITION ==========
        try:
            z_service = self.calculate_z_factor(U_service, A, duty, T_i, T_o)
            
            if z_service >= 1.0:
                warnings.append(f"Service: Z >= 1 (pinch point violation) at {load_pct}% load")
                steam_temp_service = float('inf')
                steam_pressure_service = float('inf')
                steam_flow_service = float('inf')
                stall_service = True
            else:
                steam_temp_service = self.calculate_steam_temperature(z_service, T_i, T_o)
                
                if steam_temp_service <= T_o:
                    warnings.append(f"Service: Steam temp <= outlet temp at {load_pct}% load")
                
                steam_pressure_service = self.calculate_steam_pressure(steam_temp_service)
                steam_flow_service = self.calculate_steam_flow(duty, steam_pressure_service)
                
                # Check stall against max backpressure (worst case)
                stall_service = self.check_stall(steam_temp_service, t_sat_bp_max)
        
        except Exception as e:
            warnings.append(f"Service calculation error at {load_pct}% load: {e}")
            z_service = float('nan')
            steam_temp_service = float('nan')
            steam_pressure_service = float('nan')
            steam_flow_service = float('nan')
            stall_service = True
        
        return LoadPoint(
            load_pct=load_pct,
            capacity=capacity,
            duty=duty,
            z_clean=z_clean,
            steam_temp_clean=steam_temp_clean,
            steam_pressure_clean=steam_pressure_clean,
            steam_flow_clean=steam_flow_clean,
            z_service=z_service,
            steam_temp_service=steam_temp_service,
            steam_pressure_service=steam_pressure_service,
            steam_flow_service=steam_flow_service,
            stall_clean=stall_clean,
            stall_service=stall_service,
            warnings=warnings
        )
    
    def run_analysis(self) -> StallResults:
        """
        Run complete stall analysis across all load points.
        
        Returns:
            StallResults with all calculated data
        """
        # Validate inputs first
        validation_warnings = self.inputs.validate()
        if validation_warnings:
            print("⚠️  Input validation warnings:")
            for w in validation_warnings:
                print(f"  - {w}")
        
        # Calculate backpressure saturation temperatures
        bp_max_psia = self.inputs.backpressure_max + PSIG_TO_PSIA_EXCEL
        bp_min_psia = self.inputs.backpressure_min + PSIG_TO_PSIA_EXCEL
        
        t_sat_bp_max = self.steam.Tsat_p(bp_max_psia)
        t_sat_bp_min = self.steam.Tsat_p(bp_min_psia)
        
        # Calculate all load points
        load_points = []
        for load_pct in self.inputs.load_percentages:
            lp = self.calculate_load_point(load_pct, t_sat_bp_max, t_sat_bp_min)
            load_points.append(lp)
        
        # Create results object (summary stats calculated in __post_init__)
        results = StallResults(
            inputs=self.inputs,
            load_points=load_points,
            t_sat_bp_max=t_sat_bp_max,
            t_sat_bp_min=t_sat_bp_min
        )
        
        return results


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def run_stall_analysis(inputs: StallInputs) -> StallResults:
    """
    Convenience function to run complete stall analysis.
    
    Args:
        inputs: StallInputs object with all parameters
        
    Returns:
        StallResults object with complete analysis
    """
    calculator = StallCalculator(inputs)
    return calculator.run_analysis()


# ============================================================================
# EXAMPLE USAGE / TESTING
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("Steam Heat Exchanger Stall Analysis - Calculation Engine Test")
    print("=" * 70)
    
    # Create inputs matching Excel example
    inputs = StallInputs(
        duty_100pct=1257060,  # BTU/hr
        surface_area=58.71,  # ft²
        htc_clean=140,  # BTU/(hr·ft²·°F)
        htc_service=110,  # BTU/(hr·ft²·°F)
        process_inlet_temp=0,  # °F
        process_outlet_temp=300,  # °F
        backpressure_max=70,  # psig
        backpressure_min=0,  # psig
        max_feed_rate=1057,  # lb/hr
    )
    
    print("\n📊 INPUTS:")
    print(f"  Duty (100%): {inputs.duty_100pct:,.0f} BTU/hr")
    print(f"  Surface Area: {inputs.surface_area:.2f} ft²")
    print(f"  HTC Clean: {inputs.htc_clean} BTU/(hr·ft²·°F)")
    print(f"  HTC Service: {inputs.htc_service} BTU/(hr·ft²·°F)")
    print(f"  Process Ti: {inputs.process_inlet_temp}°F")
    print(f"  Process To: {inputs.process_outlet_temp}°F")
    print(f"  Backpressure Max: {inputs.backpressure_max} psig")
    print(f"  Backpressure Min: {inputs.backpressure_min} psig")
    
    # Run analysis
    print("\n⚙️  Running analysis...")
    results = run_stall_analysis(inputs)
    
    print(f"\n🌡️  BACKPRESSURE SATURATION TEMPERATURES:")
    print(f"  Max BP ({inputs.backpressure_max} psig): {results.t_sat_bp_max:.2f}°F")
    print(f"  Min BP ({inputs.backpressure_min} psig): {results.t_sat_bp_min:.2f}°F")
    
    print("\n📈 RESULTS TABLE:")
    print(f"{'Load':<6} {'Duty':<10} {'T_s(C)':<8} {'P_s(C)':<8} {'Flow(C)':<10} {'T_s(S)':<8} {'P_s(S)':<8} {'Flow(S)':<10} {'Stall':<8}")
    print(f"{'%':<6} {'BTU/hr':<10} {'°F':<8} {'psig':<8} {'lb/hr':<10} {'°F':<8} {'psig':<8} {'lb/hr':<10} {'?':<8}")
    print("-" * 100)
    
    for lp in results.load_points:
        stall_flag = ""
        if lp.stall_clean and lp.stall_service:
            stall_flag = "BOTH"
        elif lp.stall_service:
            stall_flag = "Service"
        elif lp.stall_clean:
            stall_flag = "Clean"
        else:
            stall_flag = "No"
        
        print(f"{lp.load_pct:<6.0f} {lp.duty:<10,.0f} {lp.steam_temp_clean:<8.1f} {lp.steam_pressure_clean:<8.1f} "
              f"{lp.steam_flow_clean:<10,.0f} {lp.steam_temp_service:<8.1f} {lp.steam_pressure_service:<8.1f} "
              f"{lp.steam_flow_service:<10,.0f} {stall_flag:<8}")
    
    print("\n📊 SUMMARY:")
    if results.min_load_no_stall_clean is not None:
        print(f"  Minimum load without stall (clean): {results.min_load_no_stall_clean}%")
    else:
        print(f"  Stall exists at ALL loads (clean)")
    
    if results.min_load_no_stall_service is not None:
        print(f"  Minimum load without stall (service): {results.min_load_no_stall_service}%")
    else:
        print(f"  Stall exists at ALL loads (service)")
    
    print("\n✅ Calculation engine test complete!")
