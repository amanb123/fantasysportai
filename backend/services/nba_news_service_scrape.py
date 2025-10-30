"""
NBA News Service - Fetches latest news and injury updates by scraping ESPN NBA Injuries page.
Provides real-time context about player injuries for better roster recommendations.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NBANewsService:
    """Service for fetching NBA injury updates by scraping ESPN."""
    
    def __init__(self, redis_service=None):
        self.redis_service = redis_service
        self.cache_prefix = "nba_news"
        self.cache_ttl = 1800  # 30 minutes
        self.espn_url = "https://www.espn.com/nba/injuries"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        }

    async def get_injuries(self) -> List[Dict[str, Any]]:
        """
        Get current NBA injury reports by scraping ESPN.
        Returns:
            List of injury reports with player, team, status, details
        """
        try:
            cache_key = f"{self.cache_prefix}:injuries"
            if self.redis_service and self.redis_service.is_connected():
                cached_data = self.redis_service.get_json(cache_key)
                if cached_data:
                    logger.debug("Cache hit for injury reports")
                    return cached_data

            resp = requests.get(self.espn_url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table", class_="Table")
            if not tables:
                logger.warning("No injury tables found. ESPN may have changed their layout.")
                return []
            injuries = []
            for table in tables:
                team_header = table.find_previous("h2")
                team = team_header.text.strip() if team_header else "Unknown"
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = [td.text.strip() for td in row.find_all("td")]
                    if len(cols) < 5:
                        continue
                    name, pos, date, status, description = cols[:5]
                    injuries.append({
                        "team": team,
                        "name": name,
                        "position": pos,
                        "date": date,
                        "game_status": status,
                        "injury": description
                    })
            if self.redis_service and self.redis_service.is_connected():
                self.redis_service.set_json(cache_key, injuries, self.cache_ttl)
            logger.info(f"Retrieved {len(injuries)} injury reports from ESPN")
            return injuries
        except Exception as e:
            logger.error(f"Error scraping ESPN for injuries: {e}")
            return []

    async def get_player_injury(self, player_name: str) -> Optional[Dict[str, Any]]:
        try:
            injuries = await self.get_injuries()
            player_lower = player_name.lower()
            for injury in injuries:
                if player_lower in injury.get('name', '').lower():
                    return injury
            return None
        except Exception as e:
            logger.error(f"Error getting injury info for {player_name}: {e}")
            return None

    async def check_injury_status(self, player_name: str) -> Optional[Dict[str, Any]]:
        """
        Check injury status for a player from ESPN injury report.
        Returns a dict with keys: team, name, position, date, game_status, injury
        """
        try:
            injury = await self.get_player_injury(player_name)
            if injury:
                # Return the full injury dict with all available data
                return {
                    "status": injury.get('game_status', 'Unknown'),
                    "injury": injury.get('injury', 'Unknown'),
                    "description": injury.get('injury', 'Unknown'),
                    "date": injury.get('date', 'Unknown'),
                    "team": injury.get('team', 'Unknown'),
                    "position": injury.get('position', 'Unknown'),
                    "name": injury.get('name', 'Unknown')
                }
            return None
        except Exception as e:
            logger.error(f"Error checking injury status for {player_name}: {e}")
            return None
