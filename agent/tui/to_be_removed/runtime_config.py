from pydantic import BaseModel
from pydantic import ConfigDict

from tui.config import EliaChatModel


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_model: EliaChatModel
    system_prompt: str
