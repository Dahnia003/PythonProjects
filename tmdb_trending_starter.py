#!/usr/bin/env python3
"""
TMDB DIY Project, Week Starter Script
- Fetch weekly trending titles
- Build genre ID to name mapping
- Normalize and save a clean CSV for exploration
- Optional: pull a few casts and show frequent actors

Auth: uses TMDB V4 Read Access Token from env var TMDB_V4_TOKEN
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List

import requests
import pandas as pd

API_BASE = "https://api.themoviedb.org/3"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('TMDB_V4_TOKEN', '')}",
    "Accept": "application/json",
}
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_json(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Generic GET to TMDB v3 with V4 bearer tokenauth."""
    url = f"{API_BASE}{path}"
    resp = requests.get(url, headers=HEADERS, params=params or {})
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}: {resp.text[:300]}")
    return resp.json()


def get_trending(media_type: str = "all", time_window: str = "week") -> Dict[str, Any]:
    """
    media_type: "all", "movie", "tv", or "person"
    time_window: "day" or "week"
    """
    return fetch_json(f"/trending/{media_type}/{time_window}")


def get_genre_map() -> Dict[int, str]:
    """Build a single ID to name mapping across movie and TV genres."""
    movie = fetch_json("/genre/movie/list")
    tv = fetch_json("/genre/tv/list")
    genre_map = {g["id"]: g["name"] for g in movie.get("genres", [])}
    # Merge TV genres too, override if duplicates share same id
    genre_map.update({g["id"]: g["name"] for g in tv.get("genres", [])})
    # Save for reference
    (DATA_DIR / "genres.json").write_text(json.dumps(genre_map, indent=2), encoding="utf-8")
    return genre_map


def normalize_trending(results: List[Dict[str, Any]], genre_map: Dict[int, str]) -> pd.DataFrame:
    """
    Create a tidy DataFrame with common fields across movie and TV rows.
    Maps genre_ids to a semicolon joined genre_names.
    """
    rows = []
    for r in results:
        media_type = r.get("media_type")
        # title vs. name
        title = r.get("title") or r.get("name")
        # release_date vs. first_air_date
        date = r.get("release_date") or r.get("first_air_date")
        genre_ids = r.get("genre_ids") or []
        genres = [genre_map.get(gid, str(gid)) for gid in genre_ids]
        rows.append({
            "id": r.get("id"),
            "media_type": media_type,
            "title": title,
            "date": date,
            "popularity": r.get("popularity"),
            "vote_average": r.get("vote_average"),
            "vote_count": r.get("vote_count"),
            "original_language": r.get("original_language"),
            "genres": "; ".join(genres),
        })
    df = pd.DataFrame(rows)
    # Sort by popularity as a basic default
    if not df.empty:
        df = df.sort_values(by=["popularity"], ascending=False, kind="mergesort").reset_index(drop=True)
    return df


def get_credits(media_type: str, tmdb_id: int) -> Dict[str, Any]:
    """
    Fetch credits for a given title.
    Movie: /movie/{id}/credits
    TV: /tv/{id}/credits  (aggregate_credits also exists, credits is simpler to start)
    """
    if media_type == "movie":
        return fetch_json(f"/movie/{tmdb_id}/credits")
    elif media_type == "tv":
        return fetch_json(f"/tv/{tmdb_id}/credits")
    else:
        return {"cast": [], "crew": []}


def top_cast_from_sample(df: pd.DataFrame, sample_size: int = 10) -> pd.DataFrame:
    """
    Pull credits for a few top titles and count actor frequency.
    """
    cast_counts = {}
    sample = df.head(sample_size)
    for _, row in sample.iterrows():
        credits = get_credits(row["media_type"], int(row["id"]))
        for c in credits.get("cast", []):
            name = c.get("name")
            if not name:
                continue
            cast_counts[name] = cast_counts.get(name, 0) + 1
        time.sleep(0.2)  # be gentle
    if not cast_counts:
        return pd.DataFrame(columns=["name", "count"])
    out = pd.DataFrame([{"name": k, "count": v} for k, v in cast_counts.items()])
    return out.sort_values("count", ascending=False).reset_index(drop=True)


def main():
    if not os.getenv("TMDB_V4_TOKEN"):
        raise SystemExit("Set environment variable TMDB_V4_TOKEN to your V4 Read Access Token.")

    # 1) Trending all-week and save raw JSON
    trending = get_trending(media_type="all", time_window="week")
    (DATA_DIR / "trending_week_raw.json").write_text(json.dumps(trending, indent=2), encoding="utf-8")

    # 2) Build genre map
    genre_map = get_genre_map()

    # 3) Normalize and save CSV
    results = trending.get("results", [])
    df = normalize_trending(results, genre_map)
    csv_path = DATA_DIR / "trending_week_clean.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"Saved clean trending CSV to {csv_path.resolve()}")
    print(df.head(10))

    # 4) Optional small cast sample
    if not df.empty:
        cast_df = top_cast_from_sample(df, sample_size=8)
        cast_path = DATA_DIR / "sample_cast_counts.csv"
        cast_df.to_csv(cast_path, index=False, encoding="utf-8")
        print("Sample frequent cast from top 8 titles:")
        print(cast_df.head(10))
        print(f"Saved sample cast counts to {cast_path.resolve()}")


if __name__ == "__main__":
    main()
