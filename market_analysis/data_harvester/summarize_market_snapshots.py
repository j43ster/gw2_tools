#!/usr/bin/python3
"""Summarizes processed market states using a sliding 3-day window."""

import datetime
import json
import os
from typing import Any, Dict, List

_SECONDS_IN_DAY = 86400


def get_recent_processed_files(directory: str, days: int) -> List[str]:
  """Filters processed files to only include those from the last N days.

  Args:
    directory: Path to the processed data.
    days: Number of days to look back.

  Returns:
    Chronologically sorted list of file paths within the time window.
  """
  cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
  recent_files = []

  if not os.path.exists(directory):
    return []

  for filename in os.listdir(directory):
    if not (filename.startswith('market_state_') and filename.endswith('.json')):
      continue
    
    # Filename format: market_state_2026-01-23T221038_479859.json
    # Extract the date portion: 2026-01-23
    try:
      date_str = os.path.splitext(filename)[0].split('_')
      time_str = f"{date_str[2]}_{date_str[3]}"
      file_date = datetime.datetime.strptime(time_str, '%Y%m%d_%H%M%S')
      
      if file_date >= cutoff_date:
        recent_files.append(os.path.join(directory, filename))
      else:
        print(f"Deleting file {filename} which is older than look back window of {days} days.")
        os.remove(os.path.join(directory, filename))
        
    except (IndexError, ValueError):
      continue

  return sorted(recent_files)


def summarize_market_data(processed_files: List[str], item_metadata: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
  """Aggregates deltas from the selected window into a daily estimate."""
  if not processed_files:
    return {}

  # Map: item_id -> {'total_sold': int, 'total_bought': int, 'total_duration': int}
  accumulators = {}

  for file_path in processed_files:
    with open(file_path, 'r', encoding='utf-8') as f:
      print(f'Reading {file_path}')
      state_data = json.load(f)
      
      for item_id_str, metrics in state_data.items():
        item_id = int(item_id_str)
        if item_id not in accumulators:
          accumulators[item_id] = {
              'total_sold': 0, 
              'total_bought': 0, 
              'total_duration': 0
          }
        
        # Aggregate the raw deltas and the duration they represent
        accumulators[item_id]['total_sold'] += metrics['sold_delta']
        accumulators[item_id]['total_bought'] += metrics['bought_delta']
        accumulators[item_id]['total_duration'] += metrics['duration']

  # Use the absolute latest file for current market snapshots
  with open(processed_files[-1], 'r', encoding='utf-8') as f:
    latest_state = json.load(f)

  summary = {}
  for item_id_str, latest_metrics in latest_state.items():
    item_id = int(item_id_str)
    stats = accumulators.get(item_id)
    
    daily_sold = 0
    daily_bought = 0
    
    if stats and stats['total_duration'] > 0:
      # Normalize to a 24-hour period
      rate_sold = stats['total_sold'] / stats['total_duration']
      rate_bought = stats['total_bought'] / stats['total_duration']
      daily_sold = int(rate_sold * _SECONDS_IN_DAY)
      daily_bought = int(rate_bought * _SECONDS_IN_DAY)

    summary[item_id] = {
        'name': item_metadata[item_id_str]['name'] if item_id_str in item_metadata else "N/A",
        'buy': latest_metrics['buy'],
        'sell': latest_metrics['sell'],
        'supply': latest_metrics['supply'],
        'demand': latest_metrics['demand'],
        'daily_sold_est': daily_sold,
        'daily_bought_est': daily_bought,
        'timestamp': latest_metrics['timestamp'],
        'rarity': item_metadata[item_id_str]['rarity'] if item_id_str in item_metadata else "N/A"
    }

  return summary

def load_json(path: str) -> Any:
  if not os.path.exists(path):
    print(f"⚠️ Warning: File not found at {path}")
    return {}
  with open(path, 'r', encoding='utf-8') as f:
    return json.load(f)

def generate_market_summary(processed_listing_snapshots_dir, item_metadata_path, output_summary_path, window_days=3):
  """Generates the market summary based on the 3-day window."""
  recent_files = get_recent_processed_files(processed_listing_snapshots_dir, window_days)
  item_metadata = load_json(item_metadata_path)
  
  if not recent_files:
    print(f"⚠️ No processed files found in the last {window_days} days.")
    return

  print(f"📊 Summarizing {len(recent_files)} files from the 3-day window...")
  market_summary = summarize_market_data(recent_files, item_metadata)

  with open(output_summary_path, 'w', encoding='utf-8') as f:
    json.dump(market_summary, f, indent=2)

  print(f"✨ Summary saved to: {output_summary_path}")

