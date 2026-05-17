import type { CardRead } from '@renderer/api/cards'
import type { AssembleContextResponse } from '@renderer/api/ai'

// 上下文解析变量
export interface ResolveVars {
  currentCard?: CardRead
  // 当前卷号（优先从内容字段读取，其次从标题解析）
  volumeNumber?: number
  // 当前章节号（若存在）
  chapterNumber?: number
}

export interface ResolveContext {
  template: string
  cards: CardRead[]
  currentCard?: CardRead
  assembledContext?: AssembleContextResponse | null
}

export interface TemplateToken {
  start: number
  end: number
  raw: string
}

export interface ResolvedTemplateToken extends TemplateToken {
  token: string
  value: string
  resolved: boolean
}

export interface ResolveTemplateDetails {
  template: string
  result: string
  tokens: ResolvedTemplateToken[]
}

// 构建树并输出先序顺序（按每层 display_order 排序），用于“全局之前”判定
function buildPreorder(cards: CardRead[]): CardRead[] {
  type Node = CardRead & { children: Node[] }
  const map = new Map<number, Node>()
  const nodes: Node[] = cards.map(c => ({ ...(c as CardRead), children: [] }))
  nodes.forEach(n => map.set(n.id, n))
  const roots: Node[] = []
  nodes.forEach(n => {
    if (n.parent_id && map.has(n.parent_id)) map.get(n.parent_id)!.children.push(n)
    else roots.push(n)
  })
  const sortRec = (arr: Node[]) => {
    arr.sort((a, b) => a.display_order - b.display_order)
    arr.forEach(ch => sortRec(ch.children))
  }
  sortRec(roots)
  const out: CardRead[] = []
  const visit = (arr: Node[]) => {
    for (const n of arr) { out.push(n); if ((n as any).children?.length) visit((n as any).children) }
  }
  visit(roots)
  return out
}

function extractVolumeNumberFromTitle(title?: string): number | undefined {
  if (!title) return undefined
  const m = title.match(/^第(\d+)卷$/)
  if (m) return parseInt(m[1], 10)
  return undefined
}

function getVolumeNumberFromCard(card?: CardRead): number | undefined {
  if (!card) return undefined
  const c = card.content as any
  const toNum = (v: any) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }
  const byTop = toNum(c?.volume_number)
  if (byTop !== undefined) return byTop
  const byOutline = toNum(c?.volume_outline?.volume_number)
  if (byOutline !== undefined) return byOutline
  const byChapter = toNum(c?.chapter_outline?.volume_number)
  if (byChapter !== undefined) return byChapter
  return extractVolumeNumberFromTitle(card.title)
}

// 兼容多种 VolumeOutline 包装：volume_outline/VolumeOutline/volumeOutline/volume_outline_response/VolumeOutlineResponse
function unwrapVolumeOutline(content: any): any {
  if (!content || typeof content !== 'object') return {}
  if (content.volume_outline && typeof content.volume_outline === 'object') return content.volume_outline
  if (content.VolumeOutline && typeof content.VolumeOutline === 'object') return content.VolumeOutline
  if (content.volumeOutline && typeof content.volumeOutline === 'object') return content.volumeOutline
  if (content.volume_outline_response && typeof content.volume_outline_response === 'object') return content.volume_outline_response
  if (content.VolumeOutlineResponse && typeof content.VolumeOutlineResponse === 'object') return content.VolumeOutlineResponse
  // 若 content 本身包含 VolumeOutline 的典型字段，直接返回
  const hallmark = ['stage_lines','main_target','thinking','character_snapshot','branch_line']
  const keys = Object.keys(content)
  if (keys.some(k => hallmark.includes(k))) return content
  return {}
}

function getChapterNumberFromCard(card?: CardRead): number | undefined {
  if (!card) return undefined
  const c = card.content as any
  const toNum = (v: any) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }
  const nTop = toNum(c?.chapter_number)
  if (nTop !== undefined) return nTop
  const n = toNum(c?.chapter_outline?.chapter_number)
  if (n !== undefined) return n
  return undefined
}

function buildVars(ctx: ResolveContext): ResolveVars {
  const v: ResolveVars = {}
  v.currentCard = ctx.currentCard
  v.volumeNumber = getVolumeNumberFromCard(ctx.currentCard)
  v.chapterNumber = getChapterNumberFromCard(ctx.currentCard)
  return v
}

function evalIndexExpr(expr: string, vars: ResolveVars, ctx?: ResolveContext, candidatesLen?: number): number | 'last' | undefined {
  const trimmed = (expr || '').trim()
  if (trimmed === 'last' || trimmed === 'first') return trimmed === 'last' ? 'last' : 1
  // 负数：从末尾倒数，例如 -1 表示最后一个
  if (/^-[0-9]+$/.test(trimmed)) {
    const neg = parseInt(trimmed, 10) // negative
    if (typeof candidatesLen === 'number') return Math.max(1, candidatesLen + 1 + neg)
    return undefined
  }
  // $self.<path>(±int)
  const mSelf = trimmed.match(/^\$self\.(.+?)(?:\s*([+-])\s*(\d+))?$/)
  if (mSelf && ctx?.currentCard) {
    const base = Number(getPathValue(ctx.currentCard, mSelf[1]))
    if (!isNaN(base)) {
      const delta = mSelf[2] && mSelf[3] ? (mSelf[2] === '+' ? parseInt(mSelf[3], 10) : -parseInt(mSelf[3], 10)) : 0
      return base + delta
    }
  }
  // $current.volumeNumber±int
  const vm = vars.volumeNumber
  const m = trimmed.match(/^\$current\.volumeNumber\s*([+-])\s*(\d+)$/)
  if (m && typeof vm === 'number') {
    const op = m[1]
    const n = parseInt(m[2], 10)
    return op === '+' ? vm + n : vm - n
  }
  // $current.chapterNumber
  if (trimmed === '$current.chapterNumber' && typeof vars.chapterNumber === 'number') return vars.chapterNumber
  // 纯数字
  if (/^\d+$/.test(trimmed)) return parseInt(trimmed, 10)
  // 直接 $current.volumeNumber
  if (trimmed === '$current.volumeNumber' && typeof vm === 'number') return vm
  return undefined
}

function selectByType(cards: CardRead[], typeName: string): CardRead[] {
  return cards.filter(c => c.card_type?.name === typeName)
}

function selectByTitle(cards: CardRead[], title: string): CardRead | undefined {
  return cards.find(c => c.title === title)
}

function selectParent(cards: CardRead[], card?: CardRead): CardRead | undefined {
  if (!card?.parent_id) return undefined
  return cards.find(c => c.id === card.parent_id)
}

// 获取某卡片向上追溯的最近一个特定类型祖先
function getNearestAncestorOfType(cards: CardRead[], card: CardRead | undefined, typeName: string): CardRead | undefined {
  let cur = card
  while (cur && cur.parent_id) {
    const parent = cards.find(c => c.id === cur!.parent_id)
    if (!parent) return undefined
    if (parent.card_type?.name === typeName) return parent
    cur = parent
  }
  return undefined
}

// 针对实体卡（角色/场景/组织/物品/概念）：若 life_span 为“短期”，且候选卡不在当前卡片所在分卷下，则忽略
function filterShortLivedEntityAcrossVolumes(cards: CardRead[], currentCard: CardRead | undefined, list: CardRead[]): CardRead[] {
  const entityTypes = new Set(['角色卡', '场景卡', '组织卡', '物品卡', '概念卡'])
  if (!currentCard) return list
  const currentVol = getNearestAncestorOfType(cards, currentCard, '分卷大纲')
  const currentVolId = currentVol?.id
  return list.filter(c => {
    if (!entityTypes.has(c.card_type?.name || '')) return true
    const lifeSpan = (c.content as any)?.life_span
    if (lifeSpan !== '短期') return true
    const vol = getNearestAncestorOfType(cards, c, '分卷大纲')
    return (vol?.id ?? null) === (currentVolId ?? null)
  })
}

function getPathValue(obj: any, path?: string): any {
  if (!path || path.length === 0) return obj
  return path.split('.').reduce((acc, part) => (acc != null ? acc[part] : undefined), obj)
}

function stringifyValue(val: any): string {
  if (val == null) return ''
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return String(val)
}

function getStructuredFacts(ctx: ResolveContext): Record<string, any> {
  return ((ctx.assembledContext as any)?.facts_structured || {}) as Record<string, any>
}

function getFactsTokenValue(token: string, ctx: ResolveContext): any {
  const facts = getStructuredFacts(ctx)
  if (token === 'facts.fact_summaries') return facts.fact_summaries || []
  if (token === 'facts.relation_summaries') return facts.relation_summaries || []
  if (token === 'facts.item_summaries' || token === 'facts.entity:item') return facts.item_summaries || []
  if (token === 'facts.concept_summaries' || token === 'facts.entity:concept') return facts.concept_summaries || []
  return undefined
}

function getKgTokenValue(token: string, ctx: ResolveContext): any {
  const m = token.match(/^kg:(.+)$/)
  if (!m) return undefined
  const entityName = m[1].trim().toLowerCase()
  if (!entityName) return []
  const relations = getStructuredFacts(ctx).relation_summaries
  if (!Array.isArray(relations)) return []
  return relations.filter((item: any) => {
    const a = String(item?.a || '').trim().toLowerCase()
    const b = String(item?.b || '').trim().toLowerCase()
    return a === entityName || b === entityName
  })
}

// 解析值表达式：支持 $self.$parent.$current 引用，JSON，数字与普通字符串
function evalValueExpr(expr: string, ctx: ResolveContext, vars: ResolveVars): any {
  const trimmed = (expr || '').trim()
  const tryJson = () => {
    try { return JSON.parse(trimmed) } catch { return undefined }
  }
  // $self.<path>(±int)
  const mSelf = trimmed.match(/^\$self\.(.+?)(?:\s*([+-])\s*(\d+))?$/)
  if (mSelf && ctx.currentCard) {
    const baseRaw = getPathValue(ctx.currentCard, mSelf[1])
    const delta = mSelf[2] && mSelf[3] ? (mSelf[2] === '+' ? parseInt(mSelf[3], 10) : -parseInt(mSelf[3], 10)) : 0
    const baseNum = Number(baseRaw)
    if (Number.isFinite(baseNum)) return baseNum + delta
    return baseRaw
  }
  // $parent.<path>(±int)
  const mParent = trimmed.match(/^\$parent\.(.+?)(?:\s*([+-])\s*(\d+))?$/)
  if (mParent) {
    const parent = selectParent(ctx.cards, ctx.currentCard)
    const baseRaw = getPathValue(parent, mParent[1])
    const delta = mParent[2] && mParent[3] ? (mParent[2] === '+' ? parseInt(mParent[3], 10) : -parseInt(mParent[3], 10)) : 0
    const baseNum = Number(baseRaw)
    if (Number.isFinite(baseNum)) return baseNum + delta
    return baseRaw
  }
  // $current.<path>(±int) （默认从 content. 起）
  const mCurrent = trimmed.match(/^\$current\.(.+?)(?:\s*([+-])\s*(\d+))?$/)
  if (mCurrent && ctx.currentCard) {
    const p = mCurrent[1]
    const full = p.startsWith('content.') ? p : `content.${p}`
    const baseRaw = getPathValue(ctx.currentCard, full)
    const delta = mCurrent[2] && mCurrent[3] ? (mCurrent[2] === '+' ? parseInt(mCurrent[3], 10) : -parseInt(mCurrent[3], 10)) : 0
    const baseNum = Number(baseRaw)
    if (Number.isFinite(baseNum)) return baseNum + delta
    return baseRaw
  }
  if (trimmed.startsWith('$self.')) {
    const p = trimmed.substring('$self.'.length)
    return getPathValue(ctx.currentCard, p)
  }
  if (trimmed.startsWith('$parent.')) {
    const parent = selectParent(ctx.cards, ctx.currentCard)
    const p = trimmed.substring('$parent.'.length)
    return getPathValue(parent, p)
  }
  if (trimmed.startsWith('$current.')) {
    const p = trimmed.substring('$current.'.length)
    // $current.<path> 默认从当前卡片 content 开始
    const full = p.startsWith('content.') ? p : `content.${p}`
    return getPathValue(ctx.currentCard, full)
  }
  if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
    const j = tryJson(); if (j !== undefined) return j
  }
  // 数字
  if (/^[-+]?\d+(?:\.\d+)?$/.test(trimmed)) return Number(trimmed)
  // 去引号
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

function toArray(val: any): any[] { if (Array.isArray(val)) return val; if (val == null) return []; return [val] }

// 解析 filter 表达式：
// - 多条件：filter:<cond> && <cond> && ...
// - 条件形态：field in <rhs> | field = <rhs> | field < <rhs> | field > <rhs>
// - field 可带前缀 card.，可省略 content.（默认补全）
type FilterCond = { field: string; op: 'in'|'='|'<'|'>'; rhsRaw: string }
function parseFilterExpr(expr: string): { conditions: FilterCond[] } | null {
  const raw = (expr || '').trim()
  const body = raw.startsWith('filter:') ? raw.substring('filter:'.length).trim() : raw
  if (!body) return null
  // 以 && 拆分多个条件
  const parts = body.split(/\s*&&\s*/).map(s => s.trim()).filter(Boolean)
  const conds: FilterCond[] = []
  for (const p of parts) {
    // 优先匹配 in（允许任意空白）
    const inMatch = p.match(/^(.*?)\s+in\s+(.+)$/i)
    if (inMatch) {
      let field = inMatch[1].trim()
      let rhsRaw = inMatch[2].trim()
      if (!field || !rhsRaw) return null
      if (field.startsWith('card.')) field = field.substring('card.'.length)
      if (!field.startsWith('content.')) field = `content.${field}`
      conds.push({ field, op: 'in', rhsRaw })
      continue
    }

    // 其次匹配 = / < / >（允许两侧无空格，如 a=1）
    const cmpMatch = p.match(/^(.*?)\s*([=<>])\s*(.+)$/)
    if (cmpMatch) {
      let field = cmpMatch[1].trim()
      const opChar = cmpMatch[2] as '=' | '<' | '>'
      let rhsRaw = cmpMatch[3].trim()
      if (!field || !rhsRaw) return null
      if (field.startsWith('card.')) field = field.substring('card.'.length)
      if (!field.startsWith('content.')) field = `content.${field}`
      conds.push({ field, op: opChar, rhsRaw })
      continue
    }

    // 未识别
    return null
  }
  return conds.length ? { conditions: conds } : null
}

function normalizeToStringArray(val: any): string[] {
  const flat: any[] = []
  const push = (x: any) => {
    if (x == null) return
    if (Array.isArray(x)) { x.forEach(push); return }
    flat.push(x)
  }
  push(val)
  const out: string[] = []
  for (const it of flat) {
    if (typeof it === 'string' || typeof it === 'number' || typeof it === 'boolean') {
      out.push(String(it))
      continue
    }
    if (typeof it === 'object') {
      // 常见字段优先：EntityInvolved.name / title / label / content.name
      const cand = (it as any).name ?? (it as any).title ?? (it as any).label ?? ((it as any).content?.name)
      if (cand != null) { out.push(String(cand)); continue }
    }
  }
  // 去重、标准化大小写
  return Array.from(new Set(out.map(s => String(s))))
}

function parseMultiPathSpec(path?: string): { mode: 'single' | 'multi'; paths: string[] } {
  if (!path) return { mode: 'single', paths: [] }
  // .{a,b,c} 或 已去掉前导点后的 {a,b,c}
  const trimmed = path.replace(/^\./, '')
  const m = trimmed.match(/^\{(.+)\}$/)
  if (m) {
    const raw = m[1]
    const parts = raw.split(',').map(s => s.trim()).filter(Boolean)
    return { mode: 'multi', paths: parts }
  }
  return { mode: 'single', paths: [trimmed] }
}

function pickFields(obj: any, paths: string[]): any {
  const out: Record<string, any> = {}
  for (const p of paths) {
    const val = getPathValue(obj, p)
    const key = p.split('.').pop() || p
    out[key] = val
  }
  return out
}

// 辅助：获取当前卷的分卷大纲卡片
function getCurrentVolumeCard(cards: CardRead[], vars: ResolveVars): CardRead | undefined {
  if (typeof vars.volumeNumber !== 'number') return undefined
  const list = selectByType(cards, '分卷大纲')
  const sorted = [...list].sort((a, b) => {
    const na = extractVolumeNumberFromTitle(a.title)
    const nb = extractVolumeNumberFromTitle(b.title)
    if (na != null && nb != null) return na - nb
    return a.display_order - b.display_order
  })
  return sorted[vars.volumeNumber - 1]
}

// stage:current -> 在当前卷的 stage_lines 中找到覆盖当前章节号的阶段
function resolveCurrentStage(cards: CardRead[], vars: ResolveVars): any {
  const vol = getCurrentVolumeCard(cards, vars)
  const raw = (vol?.content as any) || {}
  const vo = unwrapVolumeOutline(raw)
  const stageLines = Array.isArray(vo?.stage_lines) ? vo.stage_lines : []
  if (!Array.isArray(stageLines) || stageLines.length === 0) return undefined
  const ch = Number(vars.chapterNumber)
  if (!Number.isFinite(ch)) return undefined
  return stageLines.find((s: any) => {
    const ref = s?.reference_chapter
    if (!Array.isArray(ref) || ref.length < 2) return false
    const start = Number(ref[0])
    const end = Number(ref[1])
    return Number.isFinite(start) && Number.isFinite(end) && ch >= start && ch <= end
  })
}

// chapters:previous -> 当前卷、当前阶段内，章节号小于当前章节的已存在章节卡片，映射为 SmallChapter
function resolvePreviousChapters(cards: CardRead[], vars: ResolveVars): any[] {
  const volNum = vars.volumeNumber
  const chNum = vars.chapterNumber
  if (typeof volNum !== 'number' || typeof chNum !== 'number') return []
  // 所有章节大纲卡片
  const chapterCards = selectByType(cards, '章节大纲')
  // 过滤当前卷、且小于当前章节号
  const filtered = chapterCards.filter(c => {
    const cc = c.content as any
    const vol = cc?.chapter_outline?.volume_number
    const cn = cc?.chapter_outline?.chapter_number
    return vol === volNum && typeof cn === 'number' && cn < chNum
  })
  // 映射为 SmallChapter 结构
  return filtered
    .sort((a, b) => {
      const an = (a.content as any)?.chapter_outline?.chapter_number || 0
      const bn = (b.content as any)?.chapter_outline?.chapter_number || 0
      return an - bn
    })
    .map(c => {
      const cc = (c.content as any)?.chapter_outline || {}
      return {
        title: cc.title,
        chapter_number: cc.chapter_number,
        overview: cc.overview,
        enemy: cc.enemy || null,
        resolve_enemy: cc.resolve_enemy || null,
      }
    })
}

function resolveToken(rawToken: string, ctx: ResolveContext, vars: ResolveVars): string {
  // 支持三种前缀：type:、self、标题（默认）以及 parent
  // 语法：
  // @type:分卷大纲[index=last].content.volume_outline
  // @type:分卷大纲[index=$current.volumeNumber-1].content
  // @self.parent.content
  // @核心蓝图.content

  const token = rawToken.replace(/^@/, '')

  const factsTokenValue = getFactsTokenValue(token, ctx)
  if (factsTokenValue !== undefined) {
    return stringifyValue(factsTokenValue)
  }

  const kgTokenValue = getKgTokenValue(token, ctx)
  if (kgTokenValue !== undefined) {
    return stringifyValue(kgTokenValue)
  }

  // 优先处理特殊选择器，避免被标题规则误匹配
  if (token.startsWith('stage:current')) {
    const path = token.includes('.') ? token.substring('stage:current.'.length) : ''
    const stage = resolveCurrentStage(ctx.cards, vars)
    const value = getPathValue(stage, path)
    return stringifyValue(value)
  }
  if (token === 'chapters:previous') {
    const arr = resolvePreviousChapters(ctx.cards, vars)
    return stringifyValue(arr)
  }

  // type 选择器
  const typeMatch = token.match(/^type:([^\.\[\s]+)(?:\[([^\]]+)\])?(?:\.(.+))?$/)
  if (typeMatch) {
    const typeName = typeMatch[1]
    const filter = typeMatch[2]
    const rawPath = typeMatch[3]
    const { mode: pathMode, paths: multiPaths } = parseMultiPathSpec(rawPath)

    // 使用树的先序顺序，保证“无论层级”的全局顺序与左侧树一致
    const orderedAll = buildPreorder(ctx.cards)

    // previous: 全局之前（可选参数 n：仅返回最后 n 个）
    if (filter && filter.startsWith('previous')) {
      
      // 修正解析逻辑：更灵活地处理 previous:N, previous:global, previous:global:N
      const parts = filter.split(':');
      let mode = 'global';
      let takeN: number | undefined = undefined;
      
      for (const part of parts.slice(1)) {
        if (part === 'global' || part === 'local') {
          mode = part;
        } else if (/^\d+$/.test(part)) {
          takeN = parseInt(part, 10);
        }
      }
      
      let prevList: CardRead[] = []
      
      if (mode === 'local') {
        // 局部 previous：同一父卡片下的同类型兄弟卡片（按 display_order 排序）
        const pid = ctx.currentCard?.parent_id ?? null
        const siblings = ctx.cards.filter(c => 
          c.parent_id === pid && 
          c.card_type?.name === typeName && 
          c.id !== ctx.currentCard?.id
        ).sort((a, b) => a.display_order - b.display_order)
        
        // 找到当前卡片在同父下的位置，取之前的
        const currentIndex = siblings.findIndex(c => c.id === ctx.currentCard?.id)
        if (currentIndex > 0) {
          prevList = siblings.slice(0, currentIndex)
        }
        // 局部模式通常同父，无需跨卷过滤；但若父层不是分卷，仍按实体短期过滤
        prevList = filterShortLivedEntityAcrossVolumes(ctx.cards, ctx.currentCard, prevList)
      } else {
        // 全局 previous：当前树形先序顺序中，当前卡片之前的所有同类型卡片
        const indexById = new Map<number, number>()
        orderedAll.forEach((c, i) => indexById.set(c.id, i))
        const currentIndex = ctx.currentCard ? (indexById.get(ctx.currentCard.id) ?? -1) : -1
        prevList = orderedAll.filter((c, i) => c.card_type?.name === typeName && i < currentIndex)
        // 应用实体短期跨卷过滤
        prevList = filterShortLivedEntityAcrossVolumes(ctx.cards, ctx.currentCard, prevList)
        
        // 如果指定了 takeN，则取最后 n 个
        if (typeof takeN === 'number' && takeN > 0 && prevList.length > takeN) {
          prevList = prevList.slice(-takeN)
        }
      }
      
      if (!rawPath) {
        const collected = prevList.map(c => getPathValue(c, 'content'))
        return stringifyValue(collected)
      }
      if (pathMode === 'multi') {
        const collected = prevList.map(c => pickFields(c, multiPaths))
        return stringifyValue(collected)
      } else {
        const collected = prevList.map(c => getPathValue(c, multiPaths[0]))
        return stringifyValue(collected)
      }
    }

    // sibling: 同父节点下的同类型卡片（按 display_order）
    if (filter === 'sibling') {
      const pid = ctx.currentCard?.parent_id ?? null
      const siblings = ctx.cards.filter(c => c.parent_id === pid && c.card_type?.name === typeName && c.id !== ctx.currentCard?.id)
        .sort((a, b) => a.display_order - b.display_order)
      if (!rawPath) {
        const collected = siblings.map(c => getPathValue(c, 'content'))
        return stringifyValue(collected)
      }
      if (pathMode === 'multi') return stringifyValue(siblings.map(c => pickFields(c, multiPaths)))
      // 单路径：提取后过滤空值，若仅一个有效值则直接返回该值
      const collectedVals = siblings
        .map(c => getPathValue(c, multiPaths[0]))
        .filter(v => v !== undefined && v !== null && !(typeof v === 'string' && v.trim() === ''))
      if (collectedVals.length === 0) return ''
      if (collectedVals.length === 1) return stringifyValue(collectedVals[0])
      return stringifyValue(collectedVals)
    }

    // 其他情况：以稳定排序供 first/last/index 使用
    const rawCandidates = orderedAll.filter(c => c.card_type?.name === typeName)
    let candidates = [...rawCandidates]
    candidates = candidates.sort((a, b) => {
      const na = extractVolumeNumberFromTitle(a.title)
      const nb = extractVolumeNumberFromTitle(b.title)
      if (na != null && nb != null) return na - nb
      return a.display_order - b.display_order
    })

    let selected: CardRead | undefined
    if (filter === 'last') selected = candidates[candidates.length - 1]
    else if (filter === 'first' || !filter) selected = candidates[0]
    else if (filter && filter.startsWith('index=')) {
      const expr = filter.substring('index='.length).trim()
      // 先尝试解析为过滤表达式
      const f = parseFilterExpr(expr)
      if (f) {
        const matchFn = (card: CardRead) => {
          for (const cond of f.conditions) {
            // 计算左值
            let lv = getPathValue(card, cond.field)
            if ((cond.field.endsWith('.name') || cond.field === 'content.name') && (lv === undefined || lv === null || String(lv).trim() === '')) {
              lv = (card as any).title || (card as any)?.content?.title || ''
            }
            const lvStr = String(lv)
            if (cond.op === 'in') {
              const rhs = evalValueExpr(cond.rhsRaw, ctx, vars)
              const rhsArr = normalizeToStringArray(rhs)
              const setLower = new Set(rhsArr.map(x => String(x).toLowerCase()))
              if (!setLower.has(lvStr.toLowerCase())) return false
            } else if (cond.op === '=') {
              const rhs = evalValueExpr(cond.rhsRaw, ctx, vars)
              const rhsStr = String(Array.isArray(rhs) ? rhs[0] : rhs)
              // 数值优先比较
              const lvNum = Number(lvStr)
              const rhsNum = Number(rhsStr)
              if (Number.isFinite(lvNum) && Number.isFinite(rhsNum)) {
                if (lvNum !== rhsNum) return false
              } else {
                if (lvStr !== rhsStr) return false
              }
            } else if (cond.op === '<' || cond.op === '>') {
              const rhs = evalValueExpr(cond.rhsRaw, ctx, vars)
              const rhsStr = String(Array.isArray(rhs) ? rhs[0] : rhs)
              const a = Number(lvStr)
              const b = Number(rhsStr)
              if (Number.isFinite(a) && Number.isFinite(b)) {
                if (cond.op === '<' && !(a < b)) return false
                if (cond.op === '>' && !(a > b)) return false
              } else {
                // 字符串比较（本地化较复杂，这里用简单字典序）
                const cmp = lvStr.localeCompare(rhsStr)
                if (cond.op === '<' && !(cmp < 0)) return false
                if (cond.op === '>' && !(cmp > 0)) return false
              }
            }
          }
          return true
        }
        const matched = candidates.filter(matchFn)
        // 根据 pathMode 返回集合
        if (!rawPath) {
          const collected = matched.map(c => getPathValue(c, 'content'))
          return stringifyValue(collected)
        }
        if (pathMode === 'multi') {
          const collected = matched.map(c => pickFields(c, multiPaths))
          return stringifyValue(collected)
        } else {
          const collected = matched.map(c => getPathValue(c, multiPaths[0]))
          return stringifyValue(collected)
        }
      }
      // 显式 filter: 但未解析成功时，不回退到首项，避免注入错误上下文
      if (expr.startsWith('filter:')) {
        return ''
      }
      // 否则按原有数字/表达式处理
      const idx = evalIndexExpr(expr, vars, ctx, candidates.length)
      if (idx === 'last') selected = candidates[candidates.length - 1]
      else if (typeof idx === 'number') {
        if (idx < 1 || idx > candidates.length) return ''
        selected = candidates[idx - 1]
      }
    }

    if (!selected) selected = candidates[0]

    if (!rawPath) {
      const value = getPathValue(selected, 'content')
      return stringifyValue(value)
    }
    if (pathMode === 'multi') {
      const obj = pickFields(selected, multiPaths)
      return stringifyValue(obj)
    } else {
      const value = getPathValue(selected, multiPaths[0])
      return stringifyValue(value)
    }
  }

  // self / parent 选择器
  const selfMatch = token.match(/^self(?:\.(.+))?$/)
  if (selfMatch) {
    const raw = selfMatch[1]
    const { mode: pathMode, paths: multiPaths } = parseMultiPathSpec(raw)
    if (!raw) return stringifyValue(getPathValue(ctx.currentCard, 'content'))
    if (pathMode === 'multi') {
      const obj = pickFields(ctx.currentCard, multiPaths)
      return stringifyValue(obj)
    } else {
      const value = getPathValue(ctx.currentCard, multiPaths[0])
      return stringifyValue(value)
    }
  }
  const parentMatch = token.match(/^parent(?:\.(.+))?$/)
  if (parentMatch) {
    const raw = parentMatch[1]
    const parent = selectParent(ctx.cards, ctx.currentCard)
    const { mode: pathMode, paths: multiPaths } = parseMultiPathSpec(raw)
    if (!raw) return stringifyValue(getPathValue(parent, 'content'))
    if (pathMode === 'multi') {
      const obj = pickFields(parent, multiPaths)
      return stringifyValue(obj)
    } else {
      const value = getPathValue(parent, multiPaths[0])
      return stringifyValue(value)
    }
  }

  // 标题选择（向后兼容），显式排除特殊前缀
  if (!token.startsWith('stage:') && !token.startsWith('chapters:')) {
    const titleMatch = token.match(/^([^\.\[\s]+)(?:\.(.+))?$/)
    if (titleMatch) {
      const title = titleMatch[1]
      const raw = titleMatch[2]
      const card = selectByTitle(ctx.cards, title)
      if (!raw) return stringifyValue(getPathValue(card, 'content'))
      const { mode: pathMode, paths: multiPaths } = parseMultiPathSpec(raw)
      if (pathMode === 'multi') {
        const obj = pickFields(card, multiPaths)
        return stringifyValue(obj)
      } else {
        const value = getPathValue(card, multiPaths[0])
        return stringifyValue(value)
      }
    }
  }

  return `[Error: Invalid reference '${rawToken}']`
}

export function scanTemplateTokens(template: string): TemplateToken[] {
  const s = template || ''
  const tokens: TemplateToken[] = []
  const n = s.length
  let i = 0
  while (i < n) {
    const at = s.indexOf('@', i)
    if (at === -1) break
    // 扫描 token，允许 [] / {} / 引号 内的空格
    let j = at + 1
    let depthSquare = 0
    let depthCurly = 0
    let quote: '"' | "'" | null = null
    while (j < n) {
      const ch = s[j]
      const prev = j > 0 ? s[j - 1] : ''
      if (quote) {
        if (ch === quote && prev !== '\\') quote = null
        j++
        continue
      }
      if (ch === '"' || ch === "'") {
        quote = ch
        j++
        continue
      }
      if (ch === '[') { depthSquare++; j++; continue }
      if (ch === ']') { depthSquare = Math.max(0, depthSquare - 1); j++; continue }
      if (ch === '{') { depthCurly++; j++; continue }
      if (ch === '}') { depthCurly = Math.max(0, depthCurly - 1); j++; continue }
      // 结束条件：遇到空白或新的 @，且不在任何括号/引号内
      if ((ch === '@' || /\s/.test(ch)) && depthSquare === 0 && depthCurly === 0) break
      j++
    }
    const raw = s.substring(at, j)
    tokens.push({ start: at, end: j, raw })
    i = j + 1
  }
  return tokens
}

function isResolvedTokenValue(value: string): boolean {
  const trimmed = String(value || '').trim()
  return trimmed.length > 0 && !trimmed.startsWith('[Error:')
}

export function resolveTemplateDetails(ctx: ResolveContext): ResolveTemplateDetails {
  const vars = buildVars(ctx)
  const { template } = ctx
  if (!template) return { template: '', result: '', tokens: [] }

  const s = template
  const tokens = scanTemplateTokens(s)
  const resolvedTokens: ResolvedTemplateToken[] = []

  // 反向替换（仅使用内置解析，不支持跨项目 @）
  let result = s
  for (let k = tokens.length - 1; k >= 0; k--) {
    const t = tokens[k]
    const replacement = resolveToken(t.raw, ctx, vars)
    resolvedTokens.unshift({
      ...t,
      token: t.raw.replace(/^@/, ''),
      value: replacement,
      resolved: isResolvedTokenValue(replacement),
    })
    result = result.slice(0, t.start) + replacement + result.slice(t.end)
  }
  return { template: s, result, tokens: resolvedTokens }
}

export function resolveTemplate(ctx: ResolveContext): string {
  return resolveTemplateDetails(ctx).result
} 
