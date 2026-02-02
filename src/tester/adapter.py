from typing import Any, List, Optional
import httpx
import json
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ChatMessage as LCChatMessage, SystemMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.tester.models import ChatCompletionRequest, ChatCompletionResponse, ChatMessage

class TesterSettings(BaseSettings):
    LLM_GATEWAY_URL: str = "http://localhost:18060"
    LLM_MODEL_NAME: str = "gemini-2.0-flash-lite"
    GM_URL: str = "http://localhost:18020"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = TesterSettings()

class LLMGatewayChatModel(BaseChatModel):
    """
    LangChain adapter for LLM Gateway.
    """
    
    base_url: str = Field(default_factory=lambda: settings.LLM_GATEWAY_URL)
    model_name: str = Field(default_factory=lambda: settings.LLM_MODEL_NAME)
    client: httpx.AsyncClient = Field(default_factory=lambda: httpx.AsyncClient())

    @property
    def _llm_type(self) -> str:
        return "llm_gateway_tester"

    def _convert_lc_to_schema(self, message: BaseMessage) -> ChatMessage:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, LCChatMessage):
            role = message.role
        else:
            role = "user"
        return ChatMessage(role=role, content=str(message.content))

    def _generate(self, *args: Any, **kwargs: Any) -> ChatResult:
        raise NotImplementedError("Use agenerate")

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        schema_messages = [self._convert_lc_to_schema(m) for m in messages]
        
        request = ChatCompletionRequest(
            model=self.model_name,
            messages=schema_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            response_format=kwargs.get("response_format"),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/chat/completions",
                json=request.model_dump(exclude_none=True),
            )
            response.raise_for_status()
            
            chat_response = ChatCompletionResponse(**response.json())
            
            if not chat_response.choices:
                return ChatResult(generations=[])
            
            choice = chat_response.choices[0]
            
            generation = ChatGeneration(
                message=AIMessage(content=choice.message.content or ""),
                generation_info={"finish_reason": choice.finish_reason},
            )
            return ChatResult(generations=[generation])
