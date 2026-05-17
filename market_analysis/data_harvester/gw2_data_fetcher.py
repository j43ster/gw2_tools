"""Unified asynchronous fetcher that returns a flat list of results."""

import asyncio
import sys
from typing import Any, Dict, List, Optional, Union

import aiohttp

_BASE_URL = "https://api.guildwars2.com/v2"
_BATCH_SIZE = 200
_CONCURRENT_LIMIT = 15


async def fetch_gw2_data(
    endpoint: str, 
    ids: Optional[List[Union[int, str]]] = None,
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
  """Fetches data from a GW2 endpoint and returns a flat list of objects.

  If ids is None, it discovers all IDs and fetches their details automatically.

  Args:
    endpoint: The API path.
    ids: Specific IDs to fetch. If None, fetches all.
    params: Optional query parameters.

  Returns:
    A list containing the full data objects for the requested endpoint.
  """
  url = f"{_BASE_URL}/{endpoint}"
  semaphore = asyncio.Semaphore(_CONCURRENT_LIMIT)
  
  async with aiohttp.ClientSession() as session:
    # 1. Discovery Phase
    target_ids = ids
    if target_ids is None:
      print(f"🔍 Discovering all IDs for /{endpoint}...")
      async with session.get(url, params=params) as resp:
        if resp.status != 200:
          print(f"❌ Failed to discover IDs for {endpoint}: {resp.status}")
          return []
        target_ids = await resp.json()

    if not target_ids:
      return []

    # 2. Batching Phase
    batches = [target_ids[i:i + _BATCH_SIZE] 
               for i in range(0, len(target_ids), _BATCH_SIZE)]
    total_batches = len(batches)
    completed_batches = 0
    all_results = []

    async def fetch_batch(batch_ids: List[Union[int, str]]):
      nonlocal completed_batches
      ids_str = ",".join(map(str, batch_ids))
      query_params = params.copy() if params else {}
      query_params["ids"] = ids_str
      
      async with semaphore:
        try:
          async with session.get(url, params=query_params, timeout=30) as resp:
            if resp.status in (200, 206):
              batch_data = await resp.json()
              # We extend the list in a thread-safe manner within the async loop
              all_results.extend(batch_data)
            else:
              print(f"\n⚠️ API Error {resp.status} on {endpoint} batch")
        except Exception as e:
          print(f"\n🔥 Request failed on {endpoint}: {e}")
        finally:
          completed_batches += 1
          # Progress reporting using carriage return (\r)
          percent = (completed_batches / total_batches) * 100
          sys.stdout.write(
              f"\r📡 /{endpoint}: {percent:>5.1f}% | "
              f"Batch {completed_batches}/{total_batches} | "
              f"Items Gathered: {len(all_results):,}"
          )
          sys.stdout.flush()

    print(f"📡 Starting fetch for {len(target_ids):,} items...")
    tasks = [fetch_batch(b) for b in batches]
    await asyncio.gather(*tasks)
    print(f"\n✅ Finished /{endpoint}. Total items: {len(all_results):,}\n")

    return all_results
