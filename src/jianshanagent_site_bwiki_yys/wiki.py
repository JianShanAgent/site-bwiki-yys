"""站插件里管查询的那一摊：式神。

这个站的式神页是模板拼的，稀有度、上线日期、CV、其他形态、设定摘要都记成了语义属性
（Semantic MediaWiki）。``/查 大天狗`` 要的是这些，不是页面摘要（BWiki 也给不出页面摘要），
所以式神由这个插件接进通用的查询：一次语义查询取回全部式神（接口在上级 ``bwiki`` 那里），
按名字找、排成卡片。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from jianshanagent.plugins.wiki_query.client import (
    NameMatch,
    PageContent,
    SearchHit,
    WikiQueryClient,
)
from jianshanagent.plugins.wiki_query.formatters import bold, finish
from jianshanagent.plugins.wiki_query.provider import SiteSetup, WikiProvider
from jianshanagent_site_bwiki.wiki import BwikiPlatform, SemanticRow

KIND_SHIKIGAMI = "shikigami"

DEFAULT_CONDITION = "[[式神名::+]]"

#: 卡片用到的属性（这个站的式神页模板记下的）
PROPERTIES = (
    "稀有度",
    "性别",
    "降临世界",
    "本家/联动",
    "上线日期",
    "日文CV",
    "中文CV",
    "其他形态",
    "设定摘要",
)

#: 卡片上 CV 那一行：属性 → 括号里的说法
_VOICES = (("日文CV", "日"), ("中文CV", "中"))

#: 「其他形态」是文本类型的属性，值里是 wiki 的链接写法：``[[大天狗]]、[[少羽大天狗]]``
_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


@dataclass(frozen=True, slots=True)
class Shikigami:
    name: str
    url: str
    rarity: str = ""
    gender: str = ""
    #: 降临世界：平安世界 / 广夏世界 / 未来世界
    world: str = ""
    #: 本家 / 联动
    origin: str = ""
    #: 上线日期（``2016-09-09``）。有的式神不止一个
    released: tuple[str, ...] = ()
    cv_jp: str = ""
    cv_cn: str = ""
    #: 同一个角色的其他形态（页面标题）
    forms: tuple[str, ...] = ()
    summary: str = ""

    def as_data(self) -> dict[str, Any]:
        """给对话模型看的样子（wiki_get 的返回里的 ``data``）：没填的项不带。"""
        fields = {
            "稀有度": self.rarity,
            "性别": self.gender,
            "降临世界": self.world,
            "本家/联动": self.origin,
            "上线日期": list(self.released),
            "日文CV": self.cv_jp,
            "中文CV": self.cv_cn,
            "其他形态": list(self.forms),
        }
        return {name: value for name, value in fields.items() if value}


class ShikigamiIndex:
    """全部式神，按名字找。"""

    def __init__(self, entries: Sequence[Shikigami]):
        self.entries = list(entries)
        self._by_name = {entry.name.casefold(): entry for entry in self.entries}

    def get(self, name: str) -> Shikigami | None:
        return self._by_name.get(name.strip().casefold())

    def match(self, query: str) -> list[SearchHit]:
        """名字完全一致的在前，名字里包含查询词的在后（短的在前）。"""
        folded = query.strip().casefold()
        exact = self._by_name.get(folded)
        hits = [SearchHit(exact.name, KIND_SHIKIGAMI, exact=True)] if exact else []
        partial = [
            entry
            for entry in self.entries
            if entry is not exact and folded and folded in entry.name.casefold()
        ]
        partial.sort(key=lambda entry: len(entry.name))
        return hits + [SearchHit(entry.name, KIND_SHIKIGAMI) for entry in partial]


class YysProvider(WikiProvider):
    id = "bwiki_yys"
    kinds = {KIND_SHIKIGAMI: "式神"}
    search_hint = "支持式神名、页面标题。"
    get_hint = "式神返回稀有度、性别、上线日期、CV、其他形态和设定摘要；"

    def __init__(
        self,
        platform: BwikiPlatform,
        *,
        condition: str = DEFAULT_CONDITION,
        blank_values: Sequence[str] = (),
    ):
        #: 上级（BWiki 平台）在查询这个扩展点上的实例：语义查询走它
        self.platform = platform
        #: 哪些页面算式神（语义查询的条件）
        self.condition = condition
        #: 等于没填的值（「暂无」，和页面预设里留着没改的占位值）
        self.blank_values = frozenset(blank_values)
        self._client: WikiQueryClient | None = None

    def bind(self, client: WikiQueryClient) -> None:
        self._client = client

    @property
    def client(self) -> WikiQueryClient:
        if self._client is None:
            raise RuntimeError("阴阳师插件还没有接到查询客户端上")
        return self._client

    async def index(self) -> ShikigamiIndex:
        """全部式神（解析后的对象缓存一阵，和请求结果同样久）。"""
        cached = self.client.recall("shikigami")
        if isinstance(cached, ShikigamiIndex):
            return cached
        rows = await self.platform.ask(self.condition, PROPERTIES)
        index = ShikigamiIndex([self._shikigami(row) for row in rows])
        self.client.remember("shikigami", index)
        return index

    def _shikigami(self, row: SemanticRow) -> Shikigami:
        def one(name: str) -> str:
            value = row.first(name).strip()
            return "" if value in self.blank_values else value

        return Shikigami(
            name=row.title,
            url=row.url or self.client.page_url(row.title),
            rarity=one("稀有度"),
            gender=one("性别"),
            world=one("降临世界"),
            origin=one("本家/联动"),
            released=tuple(sorted(set(row.values.get("上线日期", ())) - self.blank_values)),
            cv_jp=one("日文CV"),
            cv_cn=one("中文CV"),
            forms=tuple(_LINK_RE.findall(row.first("其他形态"))),
            summary=one("设定摘要"),
        )

    # ── 接进通用查询的方法 ────────────────────────────────────────────

    async def search(self, query: str) -> list[SearchHit]:
        return (await self.index()).match(query)

    async def lookup_name(self, name: str) -> list[NameMatch]:
        """``name`` 就是哪个式神的名字（完全一致）。"""
        entry = (await self.index()).get(name)
        return [NameMatch(entry.name, KIND_SHIKIGAMI)] if entry else []

    async def name_candidates(self, name: str, limit: int) -> list[NameMatch]:
        """名字里包含它的式神。"""
        partial = [hit for hit in (await self.index()).match(name) if not hit.exact]
        return [NameMatch(hit.title, hit.kind, exact=False) for hit in partial[: max(limit, 0)]]

    async def get_page(self, title: str, kind: str | None) -> PageContent | None:
        entry = (await self.index()).get(title)
        if entry is None:
            return None
        return PageContent(
            title=entry.name,
            kind=KIND_SHIKIGAMI,
            url=entry.url,
            extract=entry.summary,
            data=entry.as_data(),
        )

    def format_page(
        self, page: PageContent, *, max_chars: int, include_link: bool, markdown: bool
    ) -> str | None:
        if page.kind != KIND_SHIKIGAMI:
            return None
        return format_shikigami(
            page, max_chars=max_chars, include_link=include_link, markdown=markdown
        )


def format_shikigami(
    page: PageContent, *, max_chars: int = 800, include_link: bool = True, markdown: bool = False
) -> str:
    """式神卡片：名字和几项分类一行，上线日期、CV、其他形态各一行，然后是设定摘要。"""
    data = page.data
    head = [bold(f"【{page.title}】", markdown)]
    head += [
        str(data[name]) for name in ("稀有度", "性别", "降临世界", "本家/联动") if name in data
    ]
    voices = [f"{data[name]}（{label}）" for name, label in _VOICES if name in data]
    lines = [
        " · ".join(head),
        _line("上线", "、".join(data.get("上线日期") or [])),
        _line("CV", " / ".join(voices)),
        _line("其他形态", "、".join(data.get("其他形态") or [])),
        page.extract,
    ]
    return finish(
        lines, page.url, max_chars=max_chars, include_link=include_link, markdown=markdown
    )


def _line(label: str, value: str) -> str:
    return f"{label}：{value}" if value else ""


def create(setup: SiteSetup) -> YysProvider:
    """入口：``setup.raw`` 是这个插件自己的配置；``setup.parent(类)`` 拿上级的实例。"""
    options = (setup.raw.get("wiki") or {}).get("shikigami") or {}
    return YysProvider(
        setup.parent(BwikiPlatform),
        condition=str(options.get("condition") or DEFAULT_CONDITION),
        blank_values=[str(value) for value in options.get("blank_values") or []],
    )
