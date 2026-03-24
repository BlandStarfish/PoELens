"""
Crafting module — cheat sheets + task queue, unified.

The task queue is the actionable side of the cheat sheets:
- Cheat sheets define crafting methods (alteration spam, essence, fossil, etc.)
- Task queue holds your specific goals, each referencing a method
- Each task shows current cost, where to get each material, and next action

TOS-safe: display-only overlay, no game interaction.
"""

import json
import os
from typing import Callable, Optional

_SHEETS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "crafting", "methods.json")


class CraftingModule:
    def __init__(self, state, poe_ninja):
        self._state = state
        self._ninja = poe_ninja
        self._methods = self._load_methods()
        self._on_update: list[Callable] = []

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def _load_methods(self) -> dict:
        if os.path.exists(_SHEETS_PATH):
            with open(_SHEETS_PATH, "r") as f:
                return json.load(f)
        return {}

    # ------------------------------------------------------------------
    # Cheat sheets
    # ------------------------------------------------------------------

    def get_method(self, method_id: str) -> Optional[dict]:
        return self._methods.get(method_id)

    def list_methods(self) -> list[dict]:
        return [{"id": k, **v} for k, v in self._methods.items()]

    def get_method_cost(self, method_id: str, quantity: int = 1) -> dict:
        """
        Returns the current chaos cost of running a crafting method once
        (or N times), based on live poe.ninja prices.
        """
        method = self._methods.get(method_id)
        if not method:
            return {}

        total_chaos = 0.0
        line_items = []
        for mat in method.get("materials", []):
            name = mat["name"]
            qty = mat["qty_per_craft"] * quantity
            cat = mat.get("category", "Currency")
            price = self._ninja.get_price(name, cat) or 0.0
            cost = price * qty
            total_chaos += cost
            line_items.append({
                "name": name,
                "qty": qty,
                "chaos_each": round(price, 2),
                "chaos_total": round(cost, 2),
                "acquire_via": mat.get("acquire_via", []),
            })

        return {
            "method_id": method_id,
            "method_name": method.get("name", method_id),
            "quantity": quantity,
            "total_chaos": round(total_chaos, 2),
            "line_items": line_items,
        }

    # ------------------------------------------------------------------
    # Task queue
    # ------------------------------------------------------------------

    def get_queue(self) -> list[dict]:
        """Returns the crafting task queue with live cost data attached."""
        tasks = self._state.get_crafting_queue()
        enriched = []
        for task in tasks:
            cost = self.get_method_cost(task.get("method_id", ""), task.get("quantity", 1))
            enriched.append({**task, "cost": cost})
        return enriched

    def add_task(self, item_name: str, method_id: str, quantity: int = 1, notes: str = ""):
        """Add a crafting goal to the queue."""
        task = {
            "item_name": item_name,
            "method_id": method_id,
            "quantity": quantity,
            "notes": notes,
            "completed": False,
        }
        self._state.add_crafting_task(task)
        self._fire_update()

    def complete_task(self, index: int):
        queue = self._state.get_crafting_queue()
        if 0 <= index < len(queue):
            queue[index]["completed"] = True
            self._state.set_crafting_queue(queue)
            self._fire_update()

    def remove_task(self, index: int):
        self._state.remove_crafting_task(index)
        self._fire_update()

    def reorder_task(self, from_idx: int, to_idx: int):
        queue = self._state.get_crafting_queue()
        if 0 <= from_idx < len(queue) and 0 <= to_idx < len(queue):
            task = queue.pop(from_idx)
            queue.insert(to_idx, task)
            self._state.set_crafting_queue(queue)
            self._fire_update()

    def get_total_queue_cost(self) -> dict:
        """Sum cost across all pending tasks."""
        queue = self.get_queue()
        total = 0.0
        pending = [t for t in queue if not t.get("completed")]
        for task in pending:
            total += task.get("cost", {}).get("total_chaos", 0)
        return {"total_chaos": round(total, 2), "pending_tasks": len(pending)}

    def _fire_update(self):
        data = self.get_queue()
        for cb in self._on_update:
            try:
                cb(data)
            except Exception as e:
                print(f"[Crafting] callback error: {e}")
