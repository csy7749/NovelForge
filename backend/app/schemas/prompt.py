from typing import Any, Dict, Literal, Optional

from sqlmodel import SQLModel, Field

class PromptBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    template: str

class PromptRead(PromptBase):
    id: int
    built_in: bool = False

class PromptCreate(PromptBase):
    pass

class PromptUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None

# 知识库Schema
KnowledgeType = Literal["design", "memory", "skill", "reference"]
InjectionMode = Literal["none", "full", "summary"]


class KnowledgeBase(SQLModel):
    name: str
    description: Optional[str] = None
    content: str
    built_in: bool = False
    knowledge_type: KnowledgeType = "reference"
    summary: Optional[str] = None
    summary_enabled: bool = False
    is_injectable: bool = False
    injection_mode: InjectionMode = "none"
    injection_config: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    maintenance_notes: Optional[str] = None

class KnowledgeRead(KnowledgeBase):
    id: int

class KnowledgeCreate(SQLModel):
    name: str
    description: Optional[str] = None
    content: str
    knowledge_type: KnowledgeType = "reference"
    summary: Optional[str] = None
    summary_enabled: bool = False
    is_injectable: bool = False
    injection_mode: InjectionMode = "none"
    injection_config: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    maintenance_notes: Optional[str] = None

class KnowledgeUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None 
    knowledge_type: Optional[KnowledgeType] = None
    summary: Optional[str] = None
    summary_enabled: Optional[bool] = None
    is_injectable: Optional[bool] = None
    injection_mode: Optional[InjectionMode] = None
    injection_config: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    maintenance_notes: Optional[str] = None


class KnowledgeMetadata(SQLModel):
    knowledge_types: list[str]
    injection_modes: list[str]
    retrieval_backends: list[str]
