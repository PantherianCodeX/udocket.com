from __future__ import annotations

from packages.ai import CaseContext
from packages.ai.api import (
    ChatMessage,
    ChatRequest,
    ComposeRequest,
    EmbeddingRequest,
    EntityExtractionRequest,
    SummarizeRequest,
    TimelineExtractionRequest,
)
from packages.ai.providers.null import NullProvider
from packages.ai.types import AgentTask, Region
from packages.ai.types.identifiers import CaseID, ModelName, OrganizationID, RouteName


def _context() -> CaseContext:
    return CaseContext(org_id=OrganizationID("org"), case_id=CaseID("case"))


def test_null_provider_supported_tasks() -> None:
    provider = NullProvider()
    assert provider.name == "null-provider"
    assert provider.region == Region("test-region")
    assert provider.supported_tasks == tuple(AgentTask)


def test_null_provider_available_models() -> None:
    provider = NullProvider()
    assert provider.available_models(AgentTask.CHAT) == (ModelName("null-model"),)


def test_null_provider_summary_payloads_are_empty() -> None:
    provider = NullProvider()
    summary = provider.summarize(
        SummarizeRequest(context=_context(), transcript="text"),
    )
    assert summary.summary_text == ""
    compose = provider.compose(ComposeRequest(context=_context(), summary_text="body"))
    assert compose.client_markdown is None
    timeline = provider.extract_timeline(
        TimelineExtractionRequest(context=_context(), transcript="text"),
    )
    assert timeline.events == ()
    entities = provider.extract_entities(
        EntityExtractionRequest(context=_context(), transcript="text"),
    )
    assert entities.entities == ()


def test_null_provider_chat_and_embed() -> None:
    provider = NullProvider()
    request = ChatRequest(
        context=_context(),
        messages=(ChatMessage(role="user", content="Hi"),),
    )
    result = provider.chat(request)
    assert result.messages == request.messages
    embeddings = provider.embed(
        EmbeddingRequest(context=_context(), inputs=("hello",)),
    )
    assert embeddings.vectors == ()


def test_null_provider_describe_route() -> None:
    provider = NullProvider()
    route = provider.describe_route(task=AgentTask.CHAT, model=ModelName("demo"))
    assert route == RouteName("chat:demo")
