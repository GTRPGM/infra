from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# --- LLM Gateway Models ---

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None

class ChatCompletionChoice(BaseModel):
    message: ChatMessage
    finish_reason: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    choices: List[ChatCompletionChoice]

# --- GM Service Models ---

class UserInput(BaseModel):
    session_id: str
    content: str

class GameTurnResponse(BaseModel):
    turn_id: str
    narrative: str
    session_id: str
    # GM can return more fields, but we focus on these
    raw_response: Optional[Dict[str, Any]] = None
