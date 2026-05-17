from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.db.models import Card
from app.schemas.context import ConceptSummary, FactsStructured, ItemSummary
from app.schemas.relation_extract import CN_TO_EN_KIND
from app.services.kg_provider import get_provider
from app.utils.text_utils import truncate_text

FACTS_QUOTA_CHARS = 5000
TRACE_PREVIEW_CHARS = 180


@dataclass
class ContextAssembleParams:
	project_id: Optional[int]
	volume_number: Optional[int]
	chapter_number: Optional[int]
	participants: Optional[List[str]]
	current_draft_tail: Optional[str]
	recent_chapters_window: Optional[int] = None
	chapter_id: Optional[int] = None


@dataclass
class AssembledContext:
	facts_subgraph: str
	budget_stats: Dict[str, Any]
	facts_structured: Optional[Dict[str, Any]] = None
	trace: Optional[Dict[str, Any]] = None

	def to_system_prompt_block(self) -> str:
		parts: List[str] = []
		if self.facts_subgraph:
			parts.append(f"[事实子图]\n{self.facts_subgraph}")
		return "\n\n".join(parts)


def _compose_facts_subgraph_stub() -> str:
	return "关键事实：暂无（尚未收集）"


def _clean_text(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _clean_list(value: Any) -> List[str]:
	if not isinstance(value, list):
		return []
	items: List[str] = []
	for item in value:
		text = _clean_text(item)
		if text:
			items.append(text)
	return items


def _preview(value: Any) -> str:
	text = _clean_text(value)
	if not text:
		return ""
	return truncate_text(text, TRACE_PREVIEW_CHARS, suffix="...")


def _trace_source(
	kind: str,
	label: str,
	source_ref: Optional[str],
	preview: str,
	count: int = 1,
	truncated: bool = False,
) -> Dict[str, Any]:
	return {
		"kind": kind,
		"label": label,
		"source_ref": source_ref,
		"preview": _preview(preview),
		"count": count,
		"truncated": truncated,
	}


def _relation_preview(item: Dict[str, Any]) -> str:
	parts = [
		_clean_text(item.get("a")),
		_clean_text(item.get("kind")) or "关系",
		_clean_text(item.get("b")),
	]
	description = _clean_text(item.get("description"))
	if description:
		parts.append(description)
	return " / ".join(part for part in parts if part)


def _entity_summary_preview(item: Dict[str, Any]) -> str:
	parts = [
		_clean_text(item.get("description")),
		_clean_text(item.get("current_state")),
		_clean_text(item.get("rule_definition")),
	]
	events = item.get("important_events")
	if isinstance(events, list) and events:
		parts.append("；".join(_clean_text(event) for event in events if _clean_text(event)))
	return "；".join(part for part in parts if part)


def _build_fact_trace_sources(structured: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
	if not structured:
		return []
	sources: List[Dict[str, Any]] = []
	for index, fact in enumerate(structured.get("fact_summaries") or [], start=1):
		sources.append(_trace_source("fact_summary", f"关键事实 {index}", f"fact:{index}", str(fact)))
	for index, item in enumerate(structured.get("relation_summaries") or [], start=1):
		if isinstance(item, dict):
			label = f"{_clean_text(item.get('a'))} ↔ {_clean_text(item.get('b'))}"
			sources.append(_trace_source("facts_relation", label, f"relation:{index}", _relation_preview(item)))
	for item in structured.get("item_summaries") or []:
		if isinstance(item, dict):
			name = _clean_text(item.get("name")) or "未命名物品"
			sources.append(_trace_source("item_summary", name, f"item:{name}", _entity_summary_preview(item)))
	for item in structured.get("concept_summaries") or []:
		if isinstance(item, dict):
			name = _clean_text(item.get("name")) or "未命名概念"
			sources.append(_trace_source("concept_summary", name, f"concept:{name}", _entity_summary_preview(item)))
	return sources


def _empty_source_labels(participants: List[str], structured: Optional[Dict[str, Any]]) -> List[str]:
	labels: List[str] = []
	if not participants:
		labels.append("participants")
	if not structured:
		return labels + ["facts_structured"]
	for key in ("fact_summaries", "relation_summaries", "item_summaries", "concept_summaries"):
		if not structured.get(key):
			labels.append(key)
	return labels


def _trace_status(
	sources: List[Dict[str, Any]],
	empty_sources: List[str],
	errors: List[str],
) -> str:
	if errors and not sources:
		return "error"
	if errors:
		return "partial"
	if not sources or empty_sources:
		return "empty" if not sources else "partial"
	return "ok"


def _build_trace(
	structured: Optional[Dict[str, Any]],
	facts_text: str,
	facts: str,
	participants: List[str],
	errors: List[str],
) -> Dict[str, Any]:
	sources = _build_fact_trace_sources(structured)
	if facts:
		sources.insert(0, _trace_source(
			"facts_subgraph",
			"事实子图文本",
			"facts_subgraph",
			facts,
			max(1, len(sources)),
			facts != facts_text,
		))
	empty_sources = _empty_source_labels(participants, structured)
	return {
		"status": _trace_status(sources, empty_sources, errors),
		"sources": sources,
		"empty_sources": empty_sources,
		"errors": errors,
	}


def _card_entity_type(card: Card) -> str:
	content = card.content if isinstance(card.content, dict) else {}
	entity_type = _clean_text(content.get("entity_type"))
	if entity_type:
		return entity_type

	card_type_name = _clean_text(getattr(card.card_type, "name", ""))
	if "物品" in card_type_name:
		return "item"
	if "概念" in card_type_name:
		return "concept"

	model_name = _clean_text(getattr(card, "model_name", "") or getattr(card.card_type, "model_name", ""))
	if model_name == "ItemCard":
		return "item"
	if model_name == "ConceptCard":
		return "concept"
	return ""


def _card_name(card: Card) -> str:
	content = card.content if isinstance(card.content, dict) else {}
	return _clean_text(content.get("name")) or _clean_text(card.title)


def _collect_referenced_entity_cards(
	session: Session,
	project_id: Optional[int],
	participants: List[str],
	entity_type: str,
) -> List[Card]:
	if not project_id or not participants:
		return []

	normalized_participants = {_clean_text(name).lower() for name in participants if _clean_text(name)}
	if not normalized_participants:
		return []

	cards = session.exec(select(Card).where(Card.project_id == project_id)).all()
	matched: List[Card] = []
	for card in cards:
		if _card_entity_type(card) != entity_type:
			continue
		card_name = _card_name(card)
		if card_name and card_name.lower() in normalized_participants:
			matched.append(card)

	matched.sort(key=lambda card: (card.display_order, card.id or 0))
	return matched


def _build_item_summaries(session: Session, project_id: Optional[int], participants: List[str]) -> List[Dict[str, Any]]:
	items = _collect_referenced_entity_cards(session, project_id, participants, "item")
	summaries: List[Dict[str, Any]] = []
	for card in items:
		content = card.content if isinstance(card.content, dict) else {}
		summary = ItemSummary(
			name=_card_name(card),
			category=_clean_text(content.get("category")),
			description=_clean_text(content.get("description")),
			owner_hint=_clean_text(content.get("owner_hint")) or None,
			current_state=_clean_text(content.get("current_state")) or None,
			power_or_effect=_clean_text(content.get("power_or_effect")) or None,
			constraints=_clean_text(content.get("constraints")) or None,
			important_events=_clean_list(content.get("important_events")),
		)
		summaries.append(summary.model_dump())
	return summaries


def _build_concept_summaries(session: Session, project_id: Optional[int], participants: List[str]) -> List[Dict[str, Any]]:
	concepts = _collect_referenced_entity_cards(session, project_id, participants, "concept")
	summaries: List[Dict[str, Any]] = []
	for card in concepts:
		content = card.content if isinstance(card.content, dict) else {}
		summary = ConceptSummary(
			name=_card_name(card),
			category=_clean_text(content.get("category")),
			description=_clean_text(content.get("description")),
			rule_definition=_clean_text(content.get("rule_definition")),
			cost=_clean_text(content.get("cost")) or None,
			mastery_hint=_clean_text(content.get("mastery_hint")) or None,
			known_by=_clean_list(content.get("known_by")),
			counter_relations=_clean_list(content.get("counter_relations")),
		)
		summaries.append(summary.model_dump())
	return summaries


def assemble_context(session: Session, params: ContextAssembleParams) -> AssembledContext:
	facts_quota = FACTS_QUOTA_CHARS

	eff_participants: List[str] = list(params.participants or [])
	participant_set = {name for name in eff_participants if name}
	trace_errors: List[str] = []

	facts_text = _compose_facts_subgraph_stub()
	facts_structured: Optional[Dict[str, Any]] = None
	item_summaries = _build_item_summaries(session, params.project_id, eff_participants)
	concept_summaries = _build_concept_summaries(session, params.project_id, eff_participants)

	try:
		provider = get_provider()
		edge_whitelist = None
		est_top_k = max(5, min(100, facts_quota // 100))
		sub_struct = provider.query_subgraph(
			project_id=params.project_id or -1,
			participants=eff_participants,
			radius=2,
			edge_type_whitelist=edge_whitelist,
			top_k=est_top_k,
			max_chapter_id=None,
		)
		raw_relation_items = [it for it in (sub_struct.get("relation_summaries") or []) if isinstance(it, dict)]
		filtered_relation_items = [
			it for it in raw_relation_items
			if (str(it.get("a")) in participant_set and str(it.get("b")) in participant_set)
		]
		if filtered_relation_items:
			lines: List[str] = ["关键事实："]
			for it in filtered_relation_items:
				a = str(it.get("a"))
				b = str(it.get("b"))
				kind_cn = str(it.get("kind") or "其他")
				pred_en = CN_TO_EN_KIND.get(kind_cn, kind_cn)
				lines.append(f"- {a} {pred_en} {b}")
			facts_text = "\n".join(lines)
		else:
			txt = "\n".join([f"- {f}" for f in (sub_struct.get("fact_summaries") or [])])
			if txt:
				facts_text = "关键事实：\n" + txt

		try:
			fs_model = FactsStructured(
				fact_summaries=list(sub_struct.get("fact_summaries") or []),
				relation_summaries=[
					{
						"a": it.get("a"),
						"b": it.get("b"),
						"kind": it.get("kind"),
						"description": it.get("description"),
						"a_to_b_addressing": it.get("a_to_b_addressing"),
						"b_to_a_addressing": it.get("b_to_a_addressing"),
						"recent_dialogues": it.get("recent_dialogues") or [],
						"recent_event_summaries": it.get("recent_event_summaries") or [],
						"stance": it.get("stance"),
					}
					for it in filtered_relation_items
				],
				item_summaries=item_summaries,
				concept_summaries=concept_summaries,
			)
			facts_structured = fs_model.model_dump()
		except Exception:
			facts_structured = {
				"fact_summaries": sub_struct.get("fact_summaries") or [],
				"relation_summaries": filtered_relation_items,
				"item_summaries": item_summaries,
				"concept_summaries": concept_summaries,
			}
	except Exception as exc:
		trace_errors.append(f"知识图谱查询失败: {type(exc).__name__}: {exc}")
		if item_summaries or concept_summaries:
			facts_structured = {
				"fact_summaries": [],
				"relation_summaries": [],
				"item_summaries": item_summaries,
				"concept_summaries": concept_summaries,
			}

	facts = truncate_text(facts_text, facts_quota, suffix="\n...[已截断]")
	trace = _build_trace(facts_structured, facts_text, facts, eff_participants, trace_errors)

	return AssembledContext(
		facts_subgraph=facts,
		budget_stats={},
		facts_structured=facts_structured,
		trace=trace,
	)
