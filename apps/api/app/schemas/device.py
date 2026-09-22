from datetime import datetime

from pydantic import BaseModel


class DeviceTokenOut(BaseModel):
    token: str
    expires_at: datetime
