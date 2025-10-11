"""
Configuration settings for the Fantasy Basketball League API.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = {
        "env_file": [".env", "backend/.env"], 
        "env_file_encoding": "utf-8"
    }
    
    # Ollama Configuration
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API host")
    ollama_model: str = Field(default="llama2", description="Ollama model name")
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
        default="postgresql://user:password@ep-xxx.neon.tech/fantasy_basketball?sslmode=require",
        description="Neon PostgreSQL database URL"
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
    
    # AutoGen Configuration
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key for AutoGen agents")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model for agents")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="OpenAI base URL")
    AGENT_TIMEOUT: int = Field(default=60, description="Agent response timeout in seconds")
    AGENT_SEED: int = Field(default=42, description="Random seed for agent responses")
    AGENT_TEMPERATURE: float = Field(default=0.7, description="Agent temperature setting")
    MAX_NEGOTIATION_TURNS: int = Field(default=10, description="Maximum negotiation turns per session")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_database_url(self) -> str:
        """Get the database URL."""
        return self.database_url


# Global settings instance
settings = Settings()