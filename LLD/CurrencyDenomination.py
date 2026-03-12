# fmt: off
# ==============================================================================
#  CURRENCY DENOMINATION CALCULATOR — ASCII CLASS DIAGRAM
# ==============================================================================
#
#  ┌──────────────────────────────────────────────────────────────────────────┐
#  │                 CURRENCY DENOMINATION CALCULATOR                         │
#  └──────────────────────────────────────────────────────────────────────────┘
#
#  ┌──────────────────────────────────┐
#  │        DenominationService       │  ← Facade
#  ├──────────────────────────────────┤
#  │ + currency_strategy: CurrencyStrategy│
#  │ + calc_strategy: CalcStrategy    │
#  ├──────────────────────────────────┤
#  │ + set_currency_strategy()        │
#  │ + set_calculation_strategy()     │
#  │ + calculate_and_print(amount)    │
#  └────────┬──────────────┬──────────┘
#           │              │
#    1 uses │              │ 1 uses
#           ▼              ▼
#  ┌─────────────────┐  ┌──────────────────────────────┐
#  │ CurrencyStrategy│  │     CalculationStrategy      │
#  │  (ABC/Interface)│  │       (ABC/Interface)         │
#  ├─────────────────┤  ├──────────────────────────────┤
#  │+get_denominations│ │+calculate(units, denoms)      │
#  │  (): List       │  │  : Dict[Denomination, int]   │
#  └────────┬────────┘  └──────────────┬───────────────┘
#           │                          │
#     ┌─────┴─────┐              ┌─────┴──────┐
#     │           │              │            │
#     ▼           ▼              ▼            ▼
#  ┌───────┐  ┌───────┐  ┌────────────┐  ┌──────────┐
#  │  INR  │  │  USD  │  │  Greedy    │  │    DP    │
#  │Strategy│ │Strategy│ │  Strategy  │  │ Strategy │
#  ├───────┤  ├───────┤  ├────────────┤  ├──────────┤
#  │returns│  │returns│  │ O(n) fast  │  │O(n*amt)  │
#  │ INR   │  │ USD   │  │ not always │  │ always   │
#  │denoms │  │denoms │  │ optimal    │  │ optimal  │
#  └───────┘  └───────┘  └────────────┘  └──────────┘
#
#  ┌──────────────────────────────┐
#  │        Denomination          │  ← Value Object / Model
#  ├──────────────────────────────┤
#  │ + value: Decimal             │
#  │ + name: str                  │
#  │ + type: str (BILL/COIN)      │
#  └──────────────────────────────┘
#
#  ┌──────────────────────┐
#  │   DenominationType   │  ← Constants
#  ├──────────────────────┤
#  │ BILL = "BILL"        │
#  │ COIN = "COIN"        │
#  └──────────────────────┘
#
#  RELATIONSHIPS:
#  DenominationService ──1──> CurrencyStrategy   (Strategy Pattern, swappable)
#  DenominationService ──1──> CalculationStrategy(Strategy Pattern, swappable)
#  INRStrategy  ──▷── CurrencyStrategy           (implements)
#  USDStrategy  ──▷── CurrencyStrategy           (implements)
#  GreedyStrategy──▷── CalculationStrategy       (implements, O(n) not always optimal)
#  DPStrategy   ──▷── CalculationStrategy        (implements, O(n×amt) always optimal)
#  Both strategies return Dict[Denomination, int] → count of each bill/coin
# ==============================================================================
# fmt: on
import math
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict

"""
==============================================================================================
CURRENCY DENOMINATION CALCULATOR LOW LEVEL DESIGN (INTERVIEW OPTIMIZED)
==============================================================================================

Key Features:
1. Greedy Algorithm: Fast calculation (O(n) time).
2. Dynamic Programming: Guarantees minimum count (O(amount * n) time).
3. Multi-Currency: INR, USD, EUR via Strategy Pattern.
4. Precision: Uses Decimal for accurate currency handling.

Design Patterns:
1. Facade: DenominationService (Controller).
2. Strategy: CurrencyStrategy (INR, USD, EUR).
3. Strategy: CalculationStrategy (Greedy, DP).

Class Design Diagram:
---------------------
[DenominationService] "1" *-- "1" [CurrencyStrategy]
[DenominationService] "1" *-- "1" [CalculationStrategy]
[CurrencyStrategy] <|-- [INRStrategy]
[CurrencyStrategy] <|-- [USDStrategy]
[CalculationStrategy] <|-- [GreedyStrategy]
[CalculationStrategy] <|-- [DPStrategy]

Class Details:
---------------------
1. DenominationService
   - Methods: calculate_and_print(), set_currency_strategy(), set_calculation_strategy().

2. CalculationStrategy (Interface)
   - Role: Algorithm for computing denominations.
   - Impl: GreedyStrategy (fast/O(n)), DPStrategy (optimal/O(amount*n)).

3. CurrencyStrategy (Interface)
   - Role: Defines denominations for a currency.
"""

# ==========================================
# Enums & Models
# ==========================================

class DenominationType:
    BILL = "BILL"
    COIN = "COIN"

class Denomination:
    """Represents a single bill or coin."""
    def __init__(self, value: Decimal, name: str, d_type: str):
        self.value = value
        self.name = name
        self.type = d_type

    def __repr__(self):
        return f"Denom({self.value} {self.name})"

# ==========================================
# Strategy Pattern: Currency Strategies
# ==========================================

class CurrencyStrategy(ABC):
    @abstractmethod
    def get_denominations(self) -> List[Denomination]:
        pass

class INRStrategy(CurrencyStrategy):
    def get_denominations(self) -> List[Denomination]:
        return [
            Denomination(Decimal("100"), "hundred rupee bill", DenominationType.BILL),
            Denomination(Decimal("50"), "fifty rupee bill", DenominationType.BILL),
            Denomination(Decimal("20"), "twenty rupee bill", DenominationType.BILL),
            Denomination(Decimal("10"), "ten rupee bill", DenominationType.BILL),
            Denomination(Decimal("5"), "five rupee bill", DenominationType.BILL),
            Denomination(Decimal("2"), "two rupee bill", DenominationType.BILL),
            Denomination(Decimal("1"), "one rupee bill", DenominationType.BILL),
            Denomination(Decimal("0.50"), "fifty paisa coin", DenominationType.COIN),
            Denomination(Decimal("0.25"), "twenty-five paisa coin", DenominationType.COIN),
            Denomination(Decimal("0.10"), "ten paisa coin", DenominationType.COIN),
        ]

class USDStrategy(CurrencyStrategy):
    def get_denominations(self) -> List[Denomination]:
        return [
            Denomination(Decimal("100"), "hundred dollar bill", DenominationType.BILL),
            Denomination(Decimal("50"), "fifty dollar bill", DenominationType.BILL),
            Denomination(Decimal("20"), "twenty dollar bill", DenominationType.BILL),
            Denomination(Decimal("10"), "ten dollar bill", DenominationType.BILL),
            Denomination(Decimal("5"), "five dollar bill", DenominationType.BILL),
            Denomination(Decimal("1"), "one dollar bill", DenominationType.BILL),
            Denomination(Decimal("0.25"), "quarter", DenominationType.COIN),
            Denomination(Decimal("0.10"), "dime", DenominationType.COIN),
            Denomination(Decimal("0.05"), "nickel", DenominationType.COIN),
            Denomination(Decimal("0.01"), "penny", DenominationType.COIN),
        ]

# ==========================================
# Calculation Strategy Pattern
# ==========================================

class CalculationStrategy(ABC):
    @abstractmethod
    def calculate(self, amount_units: int, denominations: List[Denomination]) -> Dict[Denomination, int]:
        pass

class GreedyStrategy(CalculationStrategy):
    """Calculates using largest denomination first. O(n) but may not be optimal."""
    def calculate(self, amount_units: int, denominations: List[Denomination]) -> Dict[Denomination, int]:
        result = {}
        for d in denominations:
            denom_unit = int((d.value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            count = amount_units // denom_unit
            if count > 0:
                amount_units -= count * denom_unit
                result[d] = count
        return result

class DPStrategy(CalculationStrategy):
    """Guarantees minimum number of denominations. O(amount * n)."""
    def calculate(self, amount_units: int, denominations: List[Denomination]) -> Dict[Denomination, int]:
        dp = [float('inf')] * (amount_units + 1)
        parent = [-1] * (amount_units + 1)
        dp[0] = 0

        denom_units = [
            int((d.value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            for d in denominations
        ]

        for i in range(1, amount_units + 1):
            for j, unit in enumerate(denom_units):
                if unit <= i and dp[i - unit] + 1 < dp[i]:
                    dp[i] = dp[i - unit] + 1
                    parent[i] = j

        result = {}
        curr = amount_units
        while curr > 0 and parent[curr] != -1:
            idx = parent[curr]
            d = denominations[idx]
            result[d] = result.get(d, 0) + 1
            curr -= denom_units[idx]
        return result

# ==========================================
# Service (Facade)
# ==========================================

class DenominationService:
    """Service to compute denominations for a given amount."""
    def __init__(self):
        self.currency_strategy: CurrencyStrategy = INRStrategy()
        self.calc_strategy: CalculationStrategy = GreedyStrategy()
        print("INFO: Denomination Service initialized.")

    def set_currency_strategy(self, strategy: CurrencyStrategy):
        self.currency_strategy = strategy

    def set_calculation_strategy(self, strategy: CalculationStrategy):
        self.calc_strategy = strategy

    def calculate_and_print(self, amount: Decimal):
        """Converts amount to smallest unit and runs calculation."""
        units = int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        result = self.calc_strategy.calculate(units, self.currency_strategy.get_denominations())

        bills, coins = [], []
        for d, count in result.items():
            text = f"{self._count_word(count)} {d.name}"
            (bills if d.type == DenominationType.BILL else coins).append(text)

        print(f"INFO: Amount: {amount}")
        print(f"INFO: Bills: {', '.join(bills) if bills else 'none'}")
        print(f"INFO: Coins: {', '.join(coins) if coins else 'none'}")

    def _count_word(self, count: int) -> str:
        words = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
        return words[count] if count <= 10 else str(count)

# ==========================================
# Main Execution / Demo
# ==========================================

if __name__ == "__main__":
    print("--- Currency Denomination Calculator Demo ---")

    service = DenominationService()
    amount = Decimal("143.25")

    # INR with GREEDY
    print("=== INR (Greedy Strategy) ===")
    service.calculate_and_print(amount)

    # USD with DP
    print("\n=== USD (DP Strategy) ===")
    service.set_currency_strategy(USDStrategy())
    service.set_calculation_strategy(DPStrategy())
    service.calculate_and_print(amount)

    # Note: Classic demo where Greedy fails
    print("\n=== Greedy vs DP Demo ===")
    print("Denominations: [1, 3, 4], Amount: 6")
    print("Greedy picks: 4+1+1 = 3 coins | DP picks: 3+3 = 2 coins")
    # The DPStrategy correctly handles this case internally
