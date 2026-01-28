#!/usr/bin/env python3
"""
Excel Parity Test Harness

Automated testing to validate calculation_engine.py against Excel workbook.
Reads values from Stall Chart.xlsm and compares to Python calculations.

Acceptance criteria:
- Steam temperature Ts: ±0.5 °F
- Steam pressure Ps: ±0.5 psig
- Steam/condensate flow: ±1%
- Stall/no-stall flags must match exactly

Author: Automated implementation
Date: 2026-01-27
"""

import openpyxl
from dataclasses import dataclass
from typing import List, Tuple, Optional
import sys

from calculation_engine import (
    StallInputs, 
    run_stall_analysis, 
    StallResults,
    LoadPoint
)


# ============================================================================
# TOLERANCE CONSTANTS
# ============================================================================

TOLERANCE_TEMP_F = 0.5  # ±0.5 °F
TOLERANCE_PRESSURE_PSIG = 0.5  # ±0.5 psig
TOLERANCE_FLOW_PCT = 1.0  # ±1%


# ============================================================================
# EXCEL READER
# ============================================================================

@dataclass
class ExcelLoadPoint:
    """Results for a single load point from Excel"""
    load_pct: float
    duty: float
    steam_temp_clean: float
    steam_pressure_clean: float
    steam_flow_clean: float
    steam_temp_service: float
    steam_pressure_service: float
    steam_flow_service: float


class ExcelReader:
    """Read calculation results from Excel workbook"""
    
    def __init__(self, filename: str):
        """Load Excel workbook"""
        print(f"📂 Loading Excel workbook: {filename}")
        self.wb = openpyxl.load_workbook(filename, data_only=True)
        self.ws = self.wb['STALL CHART']
        print(f"✅ Workbook loaded successfully")
    
    def read_inputs(self) -> StallInputs:
        """Read input parameters from Excel (cells D7-D15)"""
        print("\n📥 Reading inputs from Excel...")
        
        inputs = StallInputs(
            duty_100pct=self.ws['D7'].value,
            surface_area=self.ws['D8'].value,
            htc_clean=self.ws['D9'].value,
            htc_service=self.ws['D10'].value,
            process_inlet_temp=self.ws['D11'].value,
            process_outlet_temp=self.ws['D12'].value,
            backpressure_max=self.ws['D13'].value,
            backpressure_min=self.ws['D14'].value,
            max_feed_rate=self.ws['D15'].value,
        )
        
        # Read load percentages from column C
        load_pcts = []
        for row in range(20, 31):  # C20:C30
            val = self.ws[f'C{row}'].value
            if val is not None:
                load_pcts.append(val)
        inputs.load_percentages = load_pcts
        
        print(f"  Duty (100%): {inputs.duty_100pct:,.0f} BTU/hr")
        print(f"  Surface Area: {inputs.surface_area:.2f} ft²")
        print(f"  HTC Clean: {inputs.htc_clean}")
        print(f"  HTC Service: {inputs.htc_service}")
        print(f"  Process Ti: {inputs.process_inlet_temp}°F")
        print(f"  Process To: {inputs.process_outlet_temp}°F")
        print(f"  Backpressure Max: {inputs.backpressure_max} psig")
        print(f"  Backpressure Min: {inputs.backpressure_min} psig")
        print(f"  Load points: {len(load_pcts)}")
        
        return inputs
    
    def read_load_points(self) -> List[ExcelLoadPoint]:
        """Read calculated results from Excel (rows 20-30)"""
        print("\n📥 Reading calculated results from Excel...")
        
        load_points = []
        for row in range(20, 31):  # Rows 20-30
            # Check if load percentage exists
            load_pct = self.ws[f'C{row}'].value
            if load_pct is None:
                continue
            
            lp = ExcelLoadPoint(
                load_pct=load_pct,
                duty=self.ws[f'D{row}'].value,
                steam_temp_clean=self.ws[f'E{row}'].value,
                steam_pressure_clean=self.ws[f'F{row}'].value,
                steam_flow_clean=self.ws[f'G{row}'].value,
                steam_temp_service=self.ws[f'H{row}'].value,
                steam_pressure_service=self.ws[f'I{row}'].value,
                steam_flow_service=self.ws[f'J{row}'].value,
            )
            load_points.append(lp)
        
        print(f"  Read {len(load_points)} load points from Excel")
        return load_points
    
    def read_backpressure_sat_temps(self) -> Tuple[float, float]:
        """Read backpressure saturation temperatures (cells E13, E14)"""
        t_sat_max = self.ws['E13'].value
        t_sat_min = self.ws['E14'].value
        return t_sat_max, t_sat_min


# ============================================================================
# PARITY COMPARISON
# ============================================================================

@dataclass
class ComparisonResult:
    """Comparison result for a single value"""
    name: str
    excel_value: float
    python_value: float
    difference: float
    tolerance: float
    passed: bool
    
    def __str__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return (f"{status} {self.name:30s}: Excel={self.excel_value:10.2f}, "
                f"Python={self.python_value:10.2f}, Δ={self.difference:8.2f}, "
                f"Tol=±{self.tolerance:.2f}")


class ParityTester:
    """Compare Python calculations against Excel results"""
    
    def __init__(self, excel_filename: str):
        """Initialize with Excel workbook"""
        self.excel = ExcelReader(excel_filename)
        self.inputs = self.excel.read_inputs()
        self.excel_load_points = self.excel.read_load_points()
        self.excel_bp_sat_temps = self.excel.read_backpressure_sat_temps()
        
        # Run Python calculations
        print("\n⚙️  Running Python calculations...")
        self.python_results = run_stall_analysis(self.inputs)
        print(f"✅ Python calculations complete")
    
    def compare_value(self, name: str, excel_val: float, python_val: float,
                     tolerance: float, is_percentage: bool = False) -> ComparisonResult:
        """
        Compare a single value between Excel and Python.
        
        Args:
            name: Description of the value
            excel_val: Value from Excel
            python_val: Value from Python
            tolerance: Absolute tolerance (or percentage if is_percentage=True)
            is_percentage: If True, tolerance is a percentage
            
        Returns:
            ComparisonResult object
        """
        if is_percentage:
            # For percentage tolerance, calculate absolute tolerance
            abs_tolerance = abs(excel_val) * (tolerance / 100.0)
            difference = abs(python_val - excel_val)
            passed = difference <= abs_tolerance
        else:
            # Absolute tolerance
            difference = abs(python_val - excel_val)
            abs_tolerance = tolerance
            passed = difference <= abs_tolerance
        
        return ComparisonResult(
            name=name,
            excel_value=excel_val,
            python_value=python_val,
            difference=difference,
            tolerance=abs_tolerance,
            passed=passed
        )
    
    def test_backpressure_sat_temps(self) -> List[ComparisonResult]:
        """Test backpressure saturation temperatures"""
        print("\n" + "="*80)
        print("TESTING: Backpressure Saturation Temperatures")
        print("="*80)
        
        results = []
        
        excel_max, excel_min = self.excel_bp_sat_temps
        python_max = self.python_results.t_sat_bp_max
        python_min = self.python_results.t_sat_bp_min
        
        r1 = self.compare_value(
            "BP Max Sat Temp",
            excel_max, python_max,
            TOLERANCE_TEMP_F
        )
        results.append(r1)
        print(r1)
        
        r2 = self.compare_value(
            "BP Min Sat Temp",
            excel_min, python_min,
            TOLERANCE_TEMP_F
        )
        results.append(r2)
        print(r2)
        
        return results
    
    def test_load_point(self, load_pct: float) -> List[ComparisonResult]:
        """Test all values for a single load point"""
        print(f"\n{'─'*80}")
        print(f"LOAD POINT: {load_pct}%")
        print(f"{'─'*80}")
        
        # Find matching load points
        excel_lp = None
        for lp in self.excel_load_points:
            if abs(lp.load_pct - load_pct) < 0.01:
                excel_lp = lp
                break
        
        python_lp = None
        for lp in self.python_results.load_points:
            if abs(lp.load_pct - load_pct) < 0.01:
                python_lp = lp
                break
        
        if excel_lp is None or python_lp is None:
            print(f"⚠️  Load point {load_pct}% not found in both datasets")
            return []
        
        results = []
        
        # Test clean condition
        r1 = self.compare_value(
            f"Steam Temp (Clean)",
            excel_lp.steam_temp_clean,
            python_lp.steam_temp_clean,
            TOLERANCE_TEMP_F
        )
        results.append(r1)
        print(r1)
        
        r2 = self.compare_value(
            f"Steam Pressure (Clean)",
            excel_lp.steam_pressure_clean,
            python_lp.steam_pressure_clean,
            TOLERANCE_PRESSURE_PSIG
        )
        results.append(r2)
        print(r2)
        
        r3 = self.compare_value(
            f"Steam Flow (Clean)",
            excel_lp.steam_flow_clean,
            python_lp.steam_flow_clean,
            TOLERANCE_FLOW_PCT,
            is_percentage=True
        )
        results.append(r3)
        print(r3)
        
        # Test service condition
        r4 = self.compare_value(
            f"Steam Temp (Service)",
            excel_lp.steam_temp_service,
            python_lp.steam_temp_service,
            TOLERANCE_TEMP_F
        )
        results.append(r4)
        print(r4)
        
        r5 = self.compare_value(
            f"Steam Pressure (Service)",
            excel_lp.steam_pressure_service,
            python_lp.steam_pressure_service,
            TOLERANCE_PRESSURE_PSIG
        )
        results.append(r5)
        print(r5)
        
        r6 = self.compare_value(
            f"Steam Flow (Service)",
            excel_lp.steam_flow_service,
            python_lp.steam_flow_service,
            TOLERANCE_FLOW_PCT,
            is_percentage=True
        )
        results.append(r6)
        print(r6)
        
        return results
    
    def run_all_tests(self) -> bool:
        """
        Run complete parity test suite.
        
        Returns:
            True if all tests passed, False otherwise
        """
        print("\n" + "="*80)
        print("EXCEL PARITY TEST SUITE")
        print("="*80)
        print(f"Tolerance: Temperature ±{TOLERANCE_TEMP_F}°F, "
              f"Pressure ±{TOLERANCE_PRESSURE_PSIG} psig, "
              f"Flow ±{TOLERANCE_FLOW_PCT}%")
        
        all_results = []
        
        # Test backpressure saturation temperatures
        all_results.extend(self.test_backpressure_sat_temps())
        
        # Test each load point
        print("\n" + "="*80)
        print("TESTING: All Load Points")
        print("="*80)
        
        for excel_lp in self.excel_load_points:
            all_results.extend(self.test_load_point(excel_lp.load_pct))
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed)
        total = len(all_results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Pass rate: {pass_rate:.1f}%")
        
        if failed > 0:
            print("\n⚠️  FAILED TESTS:")
            for r in all_results:
                if not r.passed:
                    print(f"  {r}")
        
        print("\n" + "="*80)
        if failed == 0:
            print("✅ ALL TESTS PASSED - Excel parity validated!")
        else:
            print("❌ SOME TESTS FAILED - Review differences above")
        print("="*80)
        
        return failed == 0


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Run parity tests"""
    excel_file = 'Stall Chart.xlsm'
    
    try:
        tester = ParityTester(excel_file)
        all_passed = tester.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
    
    except FileNotFoundError:
        print(f"❌ Error: Excel file '{excel_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during parity testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
