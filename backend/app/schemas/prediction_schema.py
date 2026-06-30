from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    symbol: str = Field(..., examples=['BTC/USD'])
    timeframe: str = Field(default='1h', examples=['1h'])
