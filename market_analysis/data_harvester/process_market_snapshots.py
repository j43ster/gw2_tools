#!/usr/bin/python3
"""Orchestrates market state generation from raw GW2 snapshots."""

import datetime
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


def get_fill_volume(prev_orders: List[Dict[str, int]],
                    curr_orders: List[Dict[str, int]]) -> int:
  """Calculates the quantity of orders filled between snapshots."""
  prev_map = {o['unit_price']: o['quantity'] for o in prev_orders}
  curr_map = {o['unit_price']: o['quantity'] for o in curr_orders}

  volume = 0
  for price, prev_qty in prev_map.items():
    curr_qty = curr_map.get(price, 0)
    if prev_qty > curr_qty:
      volume += (prev_qty - curr_qty)
  return volume


def generate_market_state(snap_prev: Dict[str, Any],
                          snap_curr: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
  """Processes two snapshots into a state with precise time deltas."""
  t1 = datetime.datetime.strptime(snap_prev['timestamp'], _TIMESTAMP_FORMAT)
  t2 = datetime.datetime.strptime(snap_curr['timestamp'], _TIMESTAMP_FORMAT)
  duration_seconds = int((t2 - t1).total_seconds())

  prev_listings = {item['id']: item for item in snap_prev['listings']}
  market_state = {}

  for item in snap_curr['listings']:
    item_id = item['id']
    prev_item = prev_listings.get(item_id)

    buy = item['buys'][0]['unit_price'] if item['buys'] else 0
    sell = item['sells'][0]['unit_price'] if item['sells'] else 0
    supply = sum(o['quantity'] for o in item['sells'])
    demand = sum(o['quantity'] for o in item['buys'])

    sold_delta = 0
    bought_delta = 0
    if prev_item:
      sold_delta = get_fill_volume(prev_item['sells'], item['sells'])
      bought_delta = get_fill_volume(prev_item['buys'], item['buys'])

    market_state[item_id] = {
        'buy': buy,
        'sell': sell,
        'supply': supply,
        'demand': demand,
        'sold_delta': sold_delta,
        'bought_delta': bought_delta,
        'duration': duration_seconds,
        'timestamp': snap_curr['timestamp']
    }

  return market_state


def get_latest_snapshots(base_dir: str) -> Tuple[Optional[Dict], Optional[Dict]]:
  """Recursively finds and loads the two most recent snapshots."""
  paths = []
  for root, _, files in os.walk(base_dir):
    for file in files:
      if file.startswith('listings_') and file.endswith('.json'):
        paths.append(os.path.join(root, file))

  paths.sort()
  return paths

def process_market_snapshots(input_data_dir, output_data_dir):
  """Main execution flow for processing snapshots and saving the state."""
  snapshots = get_latest_snapshots(input_data_dir)

  if len(snapshots) < 2:
    print("⚠️ Insufficient snapshots found to generate market state.")
    return

  for previous, current in zip(snapshots, snapshots[1:]):
    # Prepare output directory and filename
    os.makedirs(output_data_dir, exist_ok=True)
    
    # Get name of the current filename of input, we mirror name in output.
    output_path = os.path.join(
        output_data_dir,
        os.path.split(current)[-1].replace("listings", "market_state")
    )
    file_path = Path(output_path)
    # If the processed data has already been generated, skip it before we
    # load and process the large json files
    if file_path.is_file():
      print(f"Skipping generation of {output_path} as it already exists.")
      continue

    print(f"Opening {previous}")
    with open(previous, 'r', encoding='utf-8') as f:
      prev_snap = json.load(f)
      print("previous opened.")

    print(f"Opening {current}")
    with open(current, 'r', encoding='utf-8') as f:
      curr_snap = json.load(f)
      print("current opened.")

    # Generate the state
    state_data = generate_market_state(prev_snap, curr_snap)

    with open(output_path, 'w', encoding='utf-8') as f:
      json.dump(state_data, f, indent=2)

    print(f"✅ Market state successfully saved to: {output_path}")

  if len(snapshots) >= 10:
    print(f"Cleaning up oldest snapshot {snapshots[0]} to save disk space.")
    os.remove(snapshots[0])


  print("All snapshots successfully saved.")

