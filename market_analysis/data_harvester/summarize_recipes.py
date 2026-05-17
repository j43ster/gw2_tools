#!/usr/bin/python3
"""Calculates crafting profitability with recursive sub-crafting logic."""

import json
import os
from typing import Any, Dict, List, Tuple

_LIQUIDITY_THRESHOLD = 0.2


def load_json(filepath: str) -> Any:
  """Helper to load JSON data with error handling."""
  if not os.path.exists(filepath):
    return None
  with open(filepath, 'r', encoding='utf-8') as f:
    return json.load(f)


def calculate_tp_sourcing_cost(
    item_id: int,
    qty_needed: int,
    product_v: int,
    market_summary: Dict[str, Dict[str, Any]]
) -> Tuple[int, str, float]:
  """Determines the TP cost of an item based on liquidity ratio."""
  item_data = market_summary.get(str(item_id))
  if not item_data:
    return (0, "no_data", 0.0)

  ing_v = item_data.get('daily_sold_est', 0)
  buy_price = item_data.get('buy', 0)
  sell_price = item_data.get('sell', 0)

  # Calculate Liquidity Ratio
  demand_per_day = product_v * qty_needed
  l_ratio = ing_v / demand_per_day if demand_per_day > 0 else 999.0

  if l_ratio >= _LIQUIDITY_THRESHOLD:
    return (buy_price + 1, "buy_order", round(l_ratio, 2))
  
  return (sell_price, "instant_buy", round(l_ratio, 2))


class RecipeResolver:
  """Solves for the lowest cost of an item by comparing TP and Crafting."""

  def __init__(self, market_summary: Dict, recipes_by_output: Dict):
    self.market_summary = market_summary
    self.recipes_by_output = recipes_by_output
    self.memo = {}  # Cache: {item_id: (cost, method, liquidity)}

  def resolve_item_cost(self, item_id: int, qty_needed: int, 
                        product_v: int) -> Tuple[int, str, float]:
    """Recursively finds the cheapest way to get an item."""
    if item_id in self.memo:
      return self.memo[item_id]

    # 1. Get cost to buy from Trading Post
    tp_cost, tp_method, l_ratio = calculate_tp_sourcing_cost(
        item_id, qty_needed, product_v, self.market_summary
    )

    # 2. Check if item can be crafted
    recipe = self.recipes_by_output.get(item_id)
    if not recipe:
      # Not craftable, TP is the only option
      self.memo[item_id] = (tp_cost, tp_method, l_ratio)
      return self.memo[item_id]

    # 3. Calculate internal craft cost
    total_internal_craft_cost = 0
    for ing in recipe['ingredients']:
      # Recursive call for sub-ingredients
      ing_cost, _, _ = self.resolve_item_cost(
          ing['item_id'], ing['count'], product_v
      )
      total_internal_craft_cost += (ing_cost * ing['count'])
    
    unit_craft_cost = int(total_internal_craft_cost / recipe['output_item_count'])

    # 4. Compare TP vs Craft
    # If TP cost is 0 (no market data), we MUST craft if a recipe exists
    if tp_cost == 0 or unit_craft_cost < tp_cost:
      result = (unit_craft_cost, "sub_craft", 1.0) # Crafting is effectively infinite liquidity
    else:
      result = (tp_cost, tp_method, l_ratio)

    self.memo[item_id] = result
    return result


def summarize_recipes(raw_recipe_file: str, market_summary_file: str, output_file: str):
  """Main entry point for recipe processing with recursive logic."""
  market_summary = load_json(market_summary_file)
  raw_recipes = load_json(raw_recipe_file)

  if not market_summary or not raw_recipes:
    print("❌ Error loading input files.")
    return

  # Index recipes by output for O(1) lookups during recursion
  recipes_by_output = {r['output_item_id']: r for r in raw_recipes if r.get('disciplines')}
  
  resolver = RecipeResolver(market_summary, recipes_by_output)
  processed = []

  print("🍳 Recursively calculating optimal crafting costs...")

  for recipe in raw_recipes:
    if not recipe.get('disciplines'):
      continue

    output_id = recipe['output_item_id']
    output_market = market_summary.get(str(output_id))
    if not output_market:
      continue

    product_v = output_market.get('daily_sold_est', 0)
    
    total_cost = 0
    ingredients_breakdown = []
    lowest_l_ratio = 1.0

    for ing in recipe['ingredients']:
      # Resolve the optimal cost (Buy vs Sub-Craft)
      unit_cost, method, l_ratio = resolver.resolve_item_cost(
          ing['item_id'], ing['count'], product_v
      )
      
      total_cost += (unit_cost * ing['count'])
      ingredients_breakdown.append({
          "item_id": ing['item_id'],
          "count": ing['count'],
          "unit_cost": unit_cost,
          "method": method,
          "l_ratio": l_ratio
      })
      lowest_l_ratio = min(lowest_l_ratio, l_ratio)

    revenue = int(output_market.get('sell', 0) * recipe.get('output_item_count', 1) * 0.85)
    profit = revenue - total_cost
    roi = (profit / total_cost) if total_cost > 0 else 0

    processed.append({
        "recipe_id": recipe['id'],
        "output_item_id": output_id,
        "name": output_market.get('name', f"Item {output_id}"),
        "profit": profit,
        "roi": round(roi, 4),
        "craft_cost": total_cost,
        "lowest_ing_l_ratio": lowest_l_ratio,
        "ingredients": ingredients_breakdown
    })

  with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(processed, f, indent=2)

  print(f"✅ Saved {len(processed)} optimized recipes to {output_file}")
