#!/usr/bin/python3
"""A standalone script to harvest market and recipe data from Guild Wars 2 API.

This program fetches full commerce listings periodically and maintains a 
local library of crafting recipes, saving both to JSON format.
"""

import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
import requests
from gw2_data_fetcher import fetch_gw2_data
import asyncio


def _setup_directory(directory) -> None:
  """Creates the necessary folder structure if it doesn't exist."""
  os.makedirs(directory, exist_ok=True)

def take_market_snapshot(listings_snapshot_dir):
  """Fetches full market listings and saves to a timestamped JSON file."""
  logging.info("Starting market snapshot...")
  # We fetch IDs from commerce/listings to ensure we only get items 
  # currently on the trading post.
  market_listings = asyncio.run(fetch_gw2_data("commerce/listings"))

  now = datetime.datetime.utcnow()
  timestamp = now.strftime("%Y%m%d_%H%M%S")
  filename = f"listings_{timestamp}.json"
  file_path = os.path.join(listings_snapshot_dir, filename)
    
  _setup_directory(listings_snapshot_dir)
  snapshot_data = {
      "timestamp": now.isoformat(),
      "item_count": len(market_listings),
      "listings": market_listings
  }
    
  with open(file_path, "w", encoding="utf-8") as f:
    json.dump(snapshot_data, f, indent=2)
  logging.info(f"Market snapshot saved to {filename}")

