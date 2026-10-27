// RF-1.2 static filter options (must match backend/app/schemas.py CATEGORIES). Backend also serves them at GET /api/filters.
import type { Platform, SortBy } from "./types";

export const PLATFORMS: Platform[] = ["all", "pc", "browser"];
export const SORT_OPTIONS: SortBy[] = ["relevance", "popularity", "release-date", "alphabetical"];
export const CATEGORIES = [
  "mmorpg", "shooter", "pvp", "moba", "anime", "strategy", "fantasy",
  "sci-fi", "card", "racing", "fighting", "social", "sports",
];
