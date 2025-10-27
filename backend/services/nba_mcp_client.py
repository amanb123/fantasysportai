"""
NBA MCP Client - Connects to the obinopaul/nba-mcp-server for NBA data.

This replaces the direct nba_api integration with an MCP-based approach.
Uses the free, official NBA API via the nba-mcp-server.

Server repository: https://github.com/obinopaul/nba-mcp-server
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


class NBAMCPClient:
    """Client for interacting with the NBA MCP server (obinopaul/nba-mcp-server)."""
    
    def __init__(self, server_path: str):
        """
        Initialize the NBA MCP client.
        
        Args:
            server_path: Path to the nba_server.py file from obinopaul/nba-mcp-server
        """
        self.server_path = server_path
        self._mcp_process = None
        self._mcp_reader = None
        self._mcp_writer = None
        self._request_id = 0
        self._initialized = False
        self._player_cache = {}  # Cache for player ID lookups
        
    async def initialize(self):
        """Initialize the MCP server connection."""
        if self._initialized:
            return
            
        try:
            # Get Python executable - use the same interpreter running this code (virtualenv)
            import sys
            python_executable = sys.executable
            
            # Start the MCP server as a subprocess with stdio transport
            self._mcp_process = await asyncio.create_subprocess_exec(
                python_executable, self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._mcp_reader = self._mcp_process.stdout
            self._mcp_writer = self._mcp_process.stdin
            
            # Increase the buffer limit to handle large responses (like player lists)
            # Default is 64KB, set to 10MB
            if hasattr(self._mcp_reader, '_limit'):
                self._mcp_reader._limit = 10 * 1024 * 1024
            
            # Initialize the MCP protocol
            await self._send_initialize()
            
            self._initialized = True
            logger.info("NBA MCP client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NBA MCP client: {e}")
            raise
    
    async def close(self):
        """Close the MCP server connection."""
        if self._mcp_process:
            self._mcp_process.terminate()
            await self._mcp_process.wait()
            self._initialized = False
            logger.info("NBA MCP client closed")
    
    async def _send_initialize(self):
        """Send MCP initialize request."""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "fantasy-basketball-league",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await self._send_request(init_request)
        logger.debug(f"MCP initialized: {response}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self._send_notification(initialized_notification)
    
    def _get_next_id(self) -> int:
        """Get the next request ID."""
        self._request_id += 1
        return self._request_id
    
    async def _send_request(self, request: Dict) -> Dict:
        """Send a JSON-RPC request and wait for response."""
        if not self._mcp_writer or not self._mcp_reader:
            raise RuntimeError("MCP client not initialized")
        
        # Write request
        request_str = json.dumps(request) + '\n'
        self._mcp_writer.write(request_str.encode())
        await self._mcp_writer.drain()
        
        # Read response (reader has 10MB limit set at initialization)
        response_line = await self._mcp_reader.readline()
        
        if not response_line:
            # Check if process has stderr output
            stderr_data = await self._mcp_process.stderr.read(1024)
            if stderr_data:
                logger.error(f"MCP subprocess stderr: {stderr_data.decode()}")
            raise RuntimeError("MCP server returned empty response")
        
        try:
            response = json.loads(response_line.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode MCP response: {response_line.decode()[:200]}")
            raise RuntimeError(f"Invalid JSON from MCP server: {e}")
        
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        
        return response.get("result", {})
    
    async def _send_notification(self, notification: Dict):
        """Send a JSON-RPC notification (no response expected)."""
        if not self._mcp_writer:
            raise RuntimeError("MCP client not initialized")
        
        notification_str = json.dumps(notification) + '\n'
        self._mcp_writer.write(notification_str.encode())
        await self._mcp_writer.drain()
    
    async def _call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Call an MCP tool and return the result (text or structured data)."""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        
        # obinopaul/nba-mcp-server returns structured data directly
        # Extract content from response
        if "content" in response and len(response["content"]) > 0:
            content = response["content"][0]
            
            # Check if it's text that looks like JSON
            if "text" in content:
                text = content["text"]
                try:
                    # Try to parse as JSON
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Return as text if not JSON
                    return text
            
            # Return content directly if not text
            return content
        
        return None
    
    async def get_active_players(self) -> List[Dict]:
        """
        Get all active NBA players.
        
        Returns:
            List of player dictionaries with id, full_name, first_name, last_name
        """
        try:
            result = await self._call_tool("nba_list_active_players", {"dummy": ""})
            
            # Result should be a list of dicts
            if isinstance(result, list):
                logger.info(f"Retrieved {len(result)} active NBA players")
                return result
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"Error getting active players: {result['error']}")
                return []
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting active players: {e}")
            return []
    
    async def search_player(self, player_name: str) -> Optional[Dict]:
        """
        Search for a player by name.
        
        Args:
            player_name: Full name
            
        Returns:
            Player dictionary with id, full_name, etc. or None
        """
        try:
            # Check cache first
            if player_name in self._player_cache:
                return self._player_cache[player_name]
            
            # Use nba_api directly to search for players (avoid large MCP response)
            from nba_api.stats.static import players
            
            player_name_lower = player_name.lower().strip()
            
            # Get all active players using nba_api directly
            all_players = players.get_active_players()
            
            # Exact match
            for player in all_players:
                if player.get("full_name", "").lower() == player_name_lower:
                    self._player_cache[player_name] = player
                    return player
            
            # Partial match fallback
            for player in all_players:
                if player_name_lower in player.get("full_name", "").lower():
                    self._player_cache[player_name] = player
                    return player
            
            logger.warning(f"Player '{player_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for player '{player_name}': {e}")
            return None
    
    async def get_games_by_date(self, game_date: date) -> List[Dict]:
        """
        Get NBA games for a specific date.
        
        Args:
            game_date: Date to get games for
            
        Returns:
            List of game dictionaries
        """
        try:
            date_str = game_date.strftime("%Y-%m-%d")
            result = await self._call_tool("nba_list_todays_games", {
                "game_date": date_str,
                "league_id": "00"
            })
            
            # Result is a normalized dict with game data
            if isinstance(result, dict) and "GameHeader" in result:
                games = result["GameHeader"]
                logger.info(f"Retrieved {len(games)} games for {date_str}")
                return games
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"Error getting games for {date_str}: {result['error']}")
                return []
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting games for date {game_date}: {e}")
            return []
    
    async def get_player_career_stats(self, player_id: str, per_mode: str = "PerGame") -> Optional[Dict]:
        """
        Get player career statistics.
        
        Args:
            player_id: NBA player ID
            per_mode: "PerGame", "Totals", or "Per36"
            
        Returns:
            Career stats dictionary or None
        """
        try:
            result = await self._call_tool("nba_player_career_stats", {
                "player_id": str(player_id),
                "per_mode": per_mode
            })
            
            if isinstance(result, dict) and "error" not in result:
                return result
            elif isinstance(result, dict) and "error" in result:
                logger.error(f"Error getting career stats for player {player_id}: {result['error']}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting career stats for player {player_id}: {e}")
            return None
    
    async def get_player_game_logs(
        self, 
        player_id: str, 
        start_date: date, 
        end_date: date,
        season_type: str = "Regular Season"
    ) -> List[Dict]:
        """
        Get player game logs for a date range.
        
        Args:
            player_id: NBA player ID
            start_date: Start date
            end_date: End date
            season_type: "Regular Season", "Playoffs", etc.
            
        Returns:
            List of game log dictionaries
        """
        try:
            logger.info(f"Requesting game logs for player {player_id} from {start_date} to {end_date}")
            result = await self._call_tool("nba_player_game_logs", {
                "player_id": str(player_id),
                "date_range": [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")],
                "season_type": season_type
            })
            
            logger.info(f"MCP returned result type: {type(result)}, length: {len(result) if isinstance(result, (list, dict)) else 'N/A'}")
            
            # Handle dict response (might be a single game or have 'content' key)
            if isinstance(result, dict):
                # Check if it's an error response
                if "error" in result:
                    logger.error(f"Error getting game logs: {result['error']}")
                    return []
                
                # Check if game logs are in a 'content' or 'data' field
                if "content" in result and isinstance(result["content"], list):
                    logger.info(f"✅ Retrieved {len(result['content'])} game logs from dict.content")
                    return result["content"]
                if "data" in result and isinstance(result["data"], list):
                    logger.info(f"✅ Retrieved {len(result['data'])} game logs from dict.data")
                    return result["data"]
                
                # Check if it's a single game log dict (has GAME_ID or PTS fields)
                if "GAME_ID" in result or "PTS" in result or "GAME_DATE" in result:
                    logger.info(f"✅ MCP returned single game dict, wrapping in list")
                    return [result]  # Wrap single game in a list
                
                # Log the dict structure to understand it
                logger.warning(f"MCP returned dict with keys: {list(result.keys())[:10]}, unable to parse as game log")
                return []
            
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], dict) and "error" in result[0]:
                    logger.error(f"Error getting game logs: {result[0]['error']}")
                    return []
                if len(result) > 0:
                    logger.info(f"✅ Retrieved {len(result)} game logs for player {player_id}")
                    logger.info(f"Sample game log: {result[0] if len(result) > 0 else 'N/A'}")
                else:
                    logger.warning(f"MCP returned empty list for player {player_id}")
                return result
            
            logger.warning(f"MCP returned unexpected type: {type(result)}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting game logs for player {player_id}: {e}")
            return []
