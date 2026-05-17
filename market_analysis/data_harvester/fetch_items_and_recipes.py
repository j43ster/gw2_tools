#!/usr/bin/python3
"""Fetches item metadata from GW2 API without event loop conflicts."""

import asyncio
import json
import os
from typing import Any, Dict, List
from gw2_data_fetcher import fetch_gw2_data

_ITEM_METADATA_PATH = "/home/jdforres/gw2_tools/market_analysis/data_harvester/raw_data/items_metadata.json"
_RECIPE_METADATA_PATH = "/home/jdforres/gw2_tools/market_analysis/data_harvester/raw_data/recipes_metadata.json"

def fetch_items():
  item_metadata = asyncio.run(fetch_gw2_data("items"))

  item_metadata_dict = {}
  for item in item_metadata:
    item_metadata_dict[item['id']] = item

  os.makedirs(os.path.dirname(_ITEM_METADATA_PATH), exist_ok=True)
  with open(_ITEM_METADATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(item_metadata_dict, f, indent=2)
    
  print(f"Item Metadata saved to {_ITEM_METADATA_PATH}")


def fetch_recipes():
  recipes_metadata = asyncio.run(fetch_gw2_data("recipes"))

  os.makedirs(os.path.dirname(_RECIPE_METADATA_PATH), exist_ok=True)
  with open(_RECIPE_METADATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(recipes_metadata, f, indent=2)
    
  print(f"Recipe Metadata saved to {_RECIPE_METADATA_PATH}")


if __name__ == "__main__":
  fetch_items()
  fetch_recipes()

