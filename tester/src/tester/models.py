from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

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
    action: Optional[str] = None
    narrative: Optional[str] = None
    dialogue: Optional[str] = None
    outputs: Optional[List[Dict[str, Any]]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    current_act_id: Optional[str] = None
    current_sequence_id: Optional[str] = None
    session_status: Optional[str] = None
    is_session_ended: Optional[bool] = None
    transition: Optional[Dict[str, Any]] = None
    session_id: str
    commit_id: Optional[str] = None
    active_entity_id: Optional[str] = "player"
    active_entity_name: Optional[str] = None
    output_type: Optional[str] = None
    is_npc_turn: bool = False
    # GM can return more fields, but we focus on these
    npc_turn: Optional["GameTurnResponse"] = None
    npc_turns: List["GameTurnResponse"] = Field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None
