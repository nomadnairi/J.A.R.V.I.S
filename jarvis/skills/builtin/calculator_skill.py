"""
A calculator skill — safe arithmetic evaluation.

Demonstrates a parameterised tool the LLM can call ("what's 12.5% of 320?"),
while also handling explicit "calc ..." fast-path requests. Evaluation uses a
restricted AST walker, so no arbitrary code can run.
"""

from __future__ import annotations

import ast
import operator

from jarvis.skills.base import BaseSkill, SkillResult

# Allowed binary / unary operators.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    """Recursively evaluate a parsed arithmetic expression."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric literals are allowed.")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression.")


def evaluate(expression: str) -> float:
    """Safely evaluate an arithmetic ``expression`` and return the result."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Could not parse expression: {expression!r}") from exc
    return _safe_eval(tree)


class CalculatorSkill(BaseSkill):
    """Evaluate arithmetic expressions (fast-path + LLM tool)."""

    name = "calculator"
    description = (
        "Evaluate an arithmetic expression. Supports + - * / // % ** and "
        "parentheses. Example expression: '(12.5/100)*320'."
    )
    priority = 45
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression to evaluate.",
            }
        },
        "required": ["expression"],
    }

    def can_handle(self, text: str) -> bool:
        lowered = text.strip().lower()
        return lowered.startswith(("calc ", "calculate "))

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        expr = text.split(" ", 1)[1] if " " in text else ""
        return await self.execute(expression=expr)

    async def execute(self, expression: str = "", **_: object) -> SkillResult:
        expr = (expression or "").strip()
        if not expr:
            return SkillResult(text="I need an expression to evaluate.", handled=True)
        try:
            result = evaluate(expr)
        except (ValueError, ZeroDivisionError) as exc:
            return SkillResult(text=f"I couldn't compute that: {exc}", handled=True)
        # Present whole numbers without a trailing ".0".
        pretty = int(result) if float(result).is_integer() else round(result, 6)
        return SkillResult(text=f"{expr} = {pretty}", metadata={"result": result})
