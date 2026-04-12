"""RPA execution package (contracts + local fake runner for product.update_price confirm phase)."""

from app.rpa.schema import RpaExecutionInput, RpaExecutionOutput, RpaRunner

__all__ = ["RpaExecutionInput", "RpaExecutionOutput", "RpaRunner"]
