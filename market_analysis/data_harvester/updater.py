#!/usr/bin/python3
import time

from process_market_snapshots import process_market_snapshots
from summarize_market_snapshots import generate_market_summary   
from summarize_recipes import summarize_recipes
from fetch_listings import take_market_snapshot


_RAW_RECIPE_FILE = "/home/jdforres/gw2_tools/market_analysis/data_harvester/raw_data/recipes_metadata.json"
_ITEM_METADATA = "/home/jdforres/gw2_tools/market_analysis/data_harvester/raw_data/items_metadata.json"
_RAW_LISTINGS_DIR = "/home/jdforres/gw2_tools/market_analysis/data_harvester/raw_data/listings_snapshots"

_PROCESSED_LISTINGS_DIR = "/home/jdforres/gw2_tools/market_analysis/data_harvester/processed_data/listings_snapshots"
_MARKET_SUMMARY = "/home/jdforres/gw2_tools/market_analysis/data_harvester/processed_data/market_summary.json"
_PROCESSED_RECIPES_FILE = "/home/jdforres/gw2_tools/market_analysis/data_harvester/processed_data/recipes_processed.json"


def main():
  take_market_snapshot(_RAW_LISTINGS_DIR)
  process_market_snapshots(_RAW_LISTINGS_DIR, _PROCESSED_LISTINGS_DIR)
  generate_market_summary(_PROCESSED_LISTINGS_DIR, _ITEM_METADATA, _MARKET_SUMMARY, window_days=3) 
  summarize_recipes(_RAW_RECIPE_FILE, _MARKET_SUMMARY, _PROCESSED_RECIPES_FILE)

if __name__ == '__main__':
  while True:
    main()
    time.sleep(15 * 60)

