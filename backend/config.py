
"""
Configuration settings for the Fantasy Basketball League API.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Roster Ranking Configuration
    ROSTER_RANKING_CACHE_TTL: int = Field(default=3600, description="1 hour cache for rankings")
    ROSTER_RANKING_CACHE_KEY_PREFIX: str = Field(default="roster_ranking", description="Redis key prefix for roster ranking")
    ROSTER_RANKING_ENABLE_CATEGORY_BREAKDOWN: bool = Field(default=True, description="Enable per-category stats in ranking")
    ROSTER_RANKING_MAX_PLAYERS_TO_ANALYZE: int = Field(default=15, description="Max players per roster to analyze")
    """Application settings loaded from environment variables."""
    
    model_config = {
        "env_file": [".env", "backend/.env"], 
        "env_file_encoding": "utf-8"
    }
    
    # Ollama Configuration
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API host")
    ollama_model: str = Field(default="llama2", description="Ollama model name (e.g., llama3, llama2, mistral)")
    ollama_timeout: int = Field(default=300, description="Ollama request timeout in seconds")
    
    # Application Environment
    environment: str = Field(default="development", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=3002, description="API port")
    
    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./test_fantasy_db.db",
        description="SQLite database URL for local testing"
    )
    database_echo: bool = Field(default=False, description="Enable SQL query logging")
    
    # Session and Data Retention
    session_retention_hours: int = Field(default=168, description="Session retention in hours")
    
    # Fantasy Basketball Settings
    salary_cap: int = Field(default=100000000, description="Team salary cap in dollars")
    
    # Agent Configuration
    agent_max_turns: int = Field(default=10, description="Maximum agent conversation turns")
    agent_temperature: float = Field(default=0.7, description="Agent response temperature")
    agent_consensus_keyword: str = Field(default="TRADE_APPROVED", description="Keyword for consensus detection")
    
    # Authentication Configuration
    SECRET_KEY: str = Field(description="JWT signing secret key (required)")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration time in minutes")
    
    # Sleeper API Configuration
    SLEEPER_API_BASE_URL: str = Field(default="https://api.sleeper.app/v1", description="Sleeper API base URL")
    SLEEPER_API_TIMEOUT: int = Field(default=10, description="Sleeper API request timeout in seconds")
    
    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", description="Redis server host")
    REDIS_PORT: int = Field(default=6379, description="Redis server port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_SSL: bool = Field(default=False, description="Enable SSL for Redis connection")
    REDIS_DECODE_RESPONSES: bool = Field(default=True, description="Auto-decode responses to strings")
    SLEEPER_PLAYERS_CACHE_TTL: int = Field(default=86400, description="Cache TTL in seconds (24 hours)")
    SLEEPER_PLAYERS_CACHE_KEY: str = Field(default="sleeper:nba:players", description="Redis key for player cache")
    
    # Sleeper League Data Cache Configuration
    SLEEPER_LEAGUE_CACHE_TTL: int = Field(default=1800, description="Cache TTL for league data in seconds (30 minutes)")
    SLEEPER_ROSTER_CACHE_TTL: int = Field(default=1800, description="Cache TTL for roster data in seconds (30 minutes)")
    SLEEPER_TRANSACTION_CACHE_TTL: int = Field(default=3600, description="Cache TTL for transactions in seconds (1 hour)")
    SLEEPER_MATCHUP_CACHE_TTL: int = Field(default=3600, description="Cache TTL for matchups in seconds (1 hour)")
    
    # Sleeper Cache Key Prefixes
    SLEEPER_LEAGUE_CACHE_KEY_PREFIX: str = Field(default="sleeper:league", description="Redis key prefix for league cache")
    SLEEPER_ROSTER_CACHE_KEY_PREFIX: str = Field(default="sleeper:rosters", description="Redis key prefix for roster cache")
    SLEEPER_TRANSACTION_CACHE_KEY_PREFIX: str = Field(default="sleeper:transactions", description="Redis key prefix for transaction cache")
    SLEEPER_MATCHUP_CACHE_KEY_PREFIX: str = Field(default="sleeper:matchups", description="Redis key prefix for matchup cache")
    
    # Sleeper Polling Configuration
    SLEEPER_TRANSACTION_ROUNDS_TO_FETCH: int = Field(default=5, description="Number of transaction rounds to fetch")
    SLEEPER_MATCHUP_WEEKS_TO_FETCH: int = Field(default=3, description="Number of matchup weeks to fetch")

    # AutoGen Configuration
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key for AutoGen agents")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model for agents")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="OpenAI base URL")
    AGENT_TIMEOUT: int = Field(default=60, description="Agent response timeout in seconds")
    AGENT_SEED: int = Field(default=42, description="Random seed for agent responses")
    AGENT_TEMPERATURE: float = Field(default=0.7, description="Agent temperature setting")
    MAX_NEGOTIATION_TURNS: int = Field(default=10, description="Maximum negotiation turns per session")
    
    # Sleeper Season Configuration
    SLEEPER_DEFAULT_SEASON: str = Field(default="2025", description="Default NBA season year for Sleeper API")
    SLEEPER_SEASON_CACHE_TTL: int = Field(default=86400, description="Cache TTL for season lookup (seconds)")
    
    # NBA Stats Integration Configuration
    nba_stats_enabled: bool = Field(default=True, description="Enable/disable NBA stats integration")
    nba_mcp_enabled: bool = Field(default=True, description="Use MCP server for NBA data instead of direct API")
    nba_mcp_server_path: str = Field(default="", description="Path to nba_server.py from obinopaul/nba-mcp-server")
    nba_cdn_base_url: str = Field(default="https://cdn.nba.com/static/json", description="NBA CDN base URL for schedule data")
    NBA_CDN_BASE_URL: str = Field(default="https://cdn.nba.com/static/json", description="NBA CDN base URL for schedule data")
    nba_cdn_timeout: int = Field(default=10, description="Timeout for NBA CDN requests in seconds")
    NBA_CDN_TIMEOUT: int = Field(default=10, description="Timeout for NBA CDN requests in seconds")
    
    # NBA Cache Configuration
    NBA_SCHEDULE_CACHE_TTL: int = Field(default=43200, description="Cache TTL for schedule (12 hours)")
    NBA_PLAYER_INFO_CACHE_TTL: int = Field(default=86400, description="Cache TTL for player info (24 hours)")
    NBA_SCHEDULE_CACHE_KEY: str = Field(default="nba:schedule", description="Redis key for schedule cache")
    NBA_PLAYER_INFO_CACHE_KEY_PREFIX: str = Field(default="nba:player_info", description="Redis key prefix for player info")
    
    # NBA Data Refresh Configuration
    NBA_SCHEDULE_REFRESH_HOUR: int = Field(default=2, description="Hour of day (UTC) to refresh schedule (2 AM)")
    NBA_PLAYER_INFO_REFRESH_HOUR: int = Field(default=3, description="Hour of day (UTC) to refresh player info (3 AM)")
    NBA_CURRENT_SEASON: str = Field(default="2025", description="Current NBA season year")
    
    # NBA Historical Stats Configuration
    NBA_HISTORICAL_STATS_CACHE_TTL: int = Field(default=604800, description="Cache TTL for historical stats (7 days)")
    NBA_HISTORICAL_STATS_CACHE_KEY_PREFIX: str = Field(default="nba:historical", description="Redis key prefix for historical stats")
    NBA_API_REQUEST_DELAY: float = Field(default=0.6, description="Delay between nba_api requests (seconds)")
    
    # Roster Chat Configuration
    ROSTER_CHAT_MAX_HISTORY_MESSAGES: int = Field(default=10, description="Max messages to include in LLM context")
    ROSTER_CHAT_MAX_CONTEXT_TOKENS: int = Field(default=3000, description="Estimated max tokens for context")
    ROSTER_CHAT_ENABLE_HISTORICAL_STATS: bool = Field(default=True, description="Enable on-demand historical stats fetching")
    ROSTER_CHAT_HISTORICAL_STATS_MAX_SEASONS: int = Field(default=3, description="Max seasons to fetch for historical queries")
    
    # Fantasy Nerds API Configuration
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_database_url(self) -> str:
        """Get the database URL."""
        return self.database_url
    
    def get_redis_url(self) -> str:
        """Get the Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# Global settings instance
settings = Settings()