from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from app.db.models import Prompt
from app.schemas.prompt import PromptCreate, PromptUpdate
from string import Template
import re

def get_prompt(session: Session, prompt_id: int) -> Optional[Prompt]:
    """根据ID获取单个提示词"""
    return session.get(Prompt, prompt_id)

def get_prompt_by_name(session: Session, prompt_name: str) -> Optional[Prompt]:
    """根据名称获取单个提示词"""
    statement = select(Prompt).where(Prompt.name == prompt_name)
    return session.exec(statement).first()

def get_prompts(session: Session, skip: int = 0, limit: int = 100) -> List[Prompt]:
    """获取提示词列表"""
    statement = select(Prompt).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_prompt(session: Session, prompt_create: PromptCreate) -> Prompt:
    """创建新提示词"""
    # 检查名称是否已存在
    existing_prompt = get_prompt_by_name(session, prompt_create.name)
    if existing_prompt:
        raise ValueError(f"提示词名称 '{prompt_create.name}' 已存在")
    
    db_prompt = Prompt.model_validate(prompt_create)
    session.add(db_prompt)
    session.commit()
    session.refresh(db_prompt)
    return db_prompt

def update_prompt(session: Session, prompt_id: int, prompt_update: PromptUpdate) -> Optional[Prompt]:
    """更新提示词"""
    db_prompt = session.get(Prompt, prompt_id)
    if not db_prompt:
        return None
    prompt_data = prompt_update.model_dump(exclude_unset=True)
    for key, value in prompt_data.items():
        setattr(db_prompt, key, value)
    session.add(db_prompt)
    session.commit()
    session.refresh(db_prompt)
    return db_prompt

def delete_prompt(session: Session, prompt_id: int) -> bool:
    """删除提示词"""
    db_prompt = session.get(Prompt, prompt_id)
    if not db_prompt:
        return False
    session.delete(db_prompt)
    session.commit()
    return True

def render_prompt(prompt_template: str, context: Dict[str, Any]) -> str:
    """
    使用上下文渲染提示词模板。
    
    :param prompt_template: 带有占位符的字符串模板 (e.g., "你好, ${name}")
    :param context: 包含要填充到模板中的值的字典 (e.g., {"name": "世界"})
    :return: 渲染后的字符串 ("你好, 世界")
    """
    template = Template(prompt_template)
    try:
        return template.substitute(context)
    except KeyError as e:
        raise ValueError(f"渲染提示词失败：上下文中缺少变量 '{e.args[0]}'")
    except Exception as e:
        raise ValueError(f"渲染提示词时发生未知错误: {e}")


# 知识库占位符解析
_KB_ID_PATTERN = re.compile(r"@KB\{\s*id\s*=\s*(\d+)\s*\}")
_KB_NAME_PATTERN = re.compile(r"@KB\{\s*name\s*=\s*([^}]+)\}")


def inject_knowledge(session: Session, template: str) -> str:
    from app.services.knowledge_service import KnowledgeService

    svc = KnowledgeService(session)
    enumerated_text = _render_knowledge_sections(svc, template)
    return _replace_inline_knowledge(svc, enumerated_text)


def _render_knowledge_sections(svc: Any, template: str) -> str:
    lines = template.splitlines()
    out_lines: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^\s*-\s*knowledge\s*:\s*$", line, flags=re.IGNORECASE):
            out_lines.append(line)
            index += 1
            continue
        block_lines, next_index = _collect_knowledge_block(lines, index + 1)
        out_lines.extend(_render_knowledge_block(svc, line, block_lines))
        index = next_index
    return "\n".join(out_lines)


def _collect_knowledge_block(lines: list[str], start: int) -> tuple[list[str], int]:
    index = start
    block_lines: list[str] = []
    while index < len(lines) and not re.match(r"^\s*-\s*\w", lines[index]):
        block_lines.append(lines[index])
        index += 1
    return block_lines, index


def _render_knowledge_block(svc: Any, line: str, block_lines: list[str]) -> list[str]:
    placeholders = _extract_placeholders(block_lines)
    if not placeholders:
        rendered = [line, *block_lines]
        injectable_block = svc.render_injectable_block()
        if injectable_block:
            rendered.extend(["", injectable_block])
        return rendered
    return _render_placeholder_items(svc, line, placeholders)


def _extract_placeholders(block_lines: list[str]) -> list[tuple[str, str]]:
    placeholders: list[tuple[str, str]] = []
    for line in block_lines:
        placeholders.extend(("id", match.group(1)) for match in _KB_ID_PATTERN.finditer(line))
        placeholders.extend(_name_placeholder(match) for match in _KB_NAME_PATTERN.finditer(line))
    return placeholders


def _name_placeholder(match: re.Match) -> tuple[str, str]:
    return "name", match.group(1).strip().strip('\"\'')


def _render_placeholder_items(svc: Any, line: str, placeholders: list[tuple[str, str]]) -> list[str]:
    out_lines = [line]
    for idx, (mode, value) in enumerate(placeholders, start=1):
        out_lines.append(f"{idx}.")
        out_lines.append(_fetch_knowledge_content(svc, mode, value).strip())
        if idx < len(placeholders):
            out_lines.append("")
    return out_lines


def _replace_inline_knowledge(svc: Any, text: str) -> str:
    result = _KB_ID_PATTERN.sub(lambda match: _fetch_knowledge_content(svc, "id", match.group(1)), text)
    return _KB_NAME_PATTERN.sub(lambda match: _fetch_knowledge_content(svc, "name", _name_placeholder(match)[1]), result)


def _fetch_knowledge_content(svc: Any, mode: str, value: str) -> str:
    kb = svc.get_by_id(int(value)) if mode == "id" else svc.get_by_name(value)
    if not kb or not kb.content:
        return f"/* 知识库未找到: {mode}={value} */"
    return kb.content
