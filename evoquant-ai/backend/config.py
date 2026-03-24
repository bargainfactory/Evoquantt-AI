from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "EvoQuantAI"
    APP_URL: str = "http://localhost:3000"
    SECRET_KEY: str = "change-me-in-production-min-32-chars-long"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://evoquant:evoquant_secret@localhost:5432/evoquant"

    # Redis
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://:redis_secret@localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://:redis_secret@localhost:6379/2"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # TOTP
    TOTP_ISSUER: str = "EvoQuantAI"
    TOTP_ENABLED: bool = True

    # PQ Security
    PQ_VAULT_MASTER_KEY: str = "0" * 64
    PQ_KEM_ALGORITHM: str = "Kyber768"
    PQ_SIG_ALGORITHM: str = "Dilithium2"
    VAULT_ENCRYPTION_ENABLED: bool = True

    # Rate limits
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 20

    # Market data
    FINNHUB_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    POLYGON_API_KEY: str = ""
    FRED_API_KEY: str = ""
    TIINGO_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    # AI
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # On-chain
    ETHERSCAN_API_KEY: str = ""
    GLASSNODE_API_KEY: str = ""
    COINGLASS_API_KEY: str = ""

    # Exchanges
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET: str = ""
    BINANCE_TESTNET: bool = True

    BYBIT_API_KEY: str = ""
    BYBIT_SECRET: str = ""
    BYBIT_TESTNET: bool = True

    COINBASE_API_KEY: str = ""
    COINBASE_SECRET: str = ""

    KRAKEN_API_KEY: str = ""
    KRAKEN_SECRET: str = ""

    OKX_API_KEY: str = ""
    OKX_SECRET: str = ""
    OKX_PASSPHRASE: str = ""

    # IBKR
    IBKR_HOST: str = "127.0.0.1"
    IBKR_PORT: int = 7497
    IBKR_CLIENT_ID: int = 1
    IBKR_PAPER_TRADING: bool = True

    # ETrade
    ETRADE_CONSUMER_KEY: str = ""
    ETRADE_CONSUMER_SECRET: str = ""
    ETRADE_SANDBOX: bool = True
    ETRADE_CALLBACK_URL: str = "http://localhost:8000/api/brokers/etrade/callback"

    # Schwab
    SCHWAB_APP_KEY: str = ""
    SCHWAB_APP_SECRET: str = ""
    SCHWAB_CALLBACK_URL: str = "http://localhost:8000/api/brokers/schwab/callback"

    # Tradier
    TRADIER_ACCESS_TOKEN: str = ""
    TRADIER_SANDBOX: bool = True

    # Fidelity
    FIDELITY_API_KEY: str = ""
    FIDELITY_SECRET: str = ""

    # Solana
    SOLANA_RPC_URL: str = "https://api.mainnet-beta.solana.com"
    JUPITER_API_URL: str = "https://quote-api.jup.ag/v6"
    JUPITER_API_KEY: str = ""

    # Ethereum
    ALCHEMY_ETH_MAINNET: str = ""
    ALCHEMY_ETH_SEPOLIA: str = ""
    UNISWAP_V4_POOL_MANAGER_ADDRESS: str = "0x0000000000000000000000000000000000000000"

    # ML
    OPTUNA_STORAGE: str = "sqlite:///optuna.db"
    MODEL_CACHE_DIR: str = "/app/models/cache"
    LSTM_EPOCHS: int = 50
    LSTM_BATCH_SIZE: int = 32
    EVOLUTION_NIGHTLY_ENABLED: bool = True
    RECURSIVE_SELL_MAX_DEPTH: int = 10

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            return [self.APP_URL]
        return ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://localhost", "http://127.0.0.1"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
