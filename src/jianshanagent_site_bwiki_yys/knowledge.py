"""站插件里管知识库的那一摊：歌词页。

「音乐曲库」的歌词一首一页，标题是编号（``音乐曲库/歌词/<专辑编号>-<曲序>``），正文只有制作信息和
带时间轴的歌词，没有歌名。歌名、专辑、发行日期、对应的式神和活动都记在「音乐曲库/数据」这一页的源码里
（一张专辑一个 ``{{#subobject:…}}``，曲库页的脚本读的也是它）。照原样入库的话，
搜歌名找不到歌词，找到了也不知道是哪首歌。

所以这个插件多取一份数据页的源码，把歌词页的文档改写成：标题是「《歌名》歌词」，开头交代这首歌
（专辑、发行日期、演唱、对应的式神和活动），然后是制作信息和歌词——歌词去掉时间轴，译文跟在原文后面。
数据页里没有的歌词页只去时间轴，标题照旧。

数据页和歌词页都是条目页，谁改了核心的自动更新都会重跑，不用另外看最近更改。
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from jianshanagent.core.logging import get_logger
from jianshanagent.plugins.knowledge.cleaner import parse_html
from jianshanagent.plugins.knowledge.fetcher import FetchError
from jianshanagent.plugins.knowledge.models import (
    BLOCK_HEADING,
    BLOCK_LIST,
    BLOCK_PARA,
    KIND_ENTRY,
    Block,
)
from jianshanagent.plugins.knowledge.site import SitePlugin, SiteSetup

if TYPE_CHECKING:
    from jianshanagent.plugins.knowledge.collect import CollectContext, RawCorpus
    from jianshanagent.plugins.knowledge.pipeline import BuildContext, ProcessContext

logger = get_logger(__name__)

PLUGIN_ID = "bwiki_yys"

DEFAULT_LYRICS_PREFIX = "音乐曲库/歌词/"
DEFAULT_DATA_PAGE = "音乐曲库/数据"

_NOWIKI_RE = re.compile(r"<nowiki>.*?</nowiki>", re.IGNORECASE | re.DOTALL)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_SUBOBJECT_RE = re.compile(r"\{\{#subobject:(.*?)\}\}", re.DOTALL)
_TRACK_KEY_RE = re.compile(r"曲(\d+)")
_NAME_SPLIT_RE = re.compile(r"[、,，/]")
_DATE_RE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}")
#: 歌词页的标题里前缀后面的部分：``<专辑编号>-<曲序>``
_LYRIC_KEY_RE = re.compile(r"(.+)-(\d+)")
#: 歌词一行开头的时间：``01:23.45``；没有时间轴的写 ``--``
_TIME_RE = re.compile(r"\d{1,3}:\d{1,2}(?:\.\d+)?|--")


# ── 数据页：专辑和曲目 ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Track:
    #: 在专辑里是第几首（``曲N`` 的 N）
    index: int
    name: str
    duration: str = ""
    #: 版本标记：伴奏、参赛的赛道……
    tag: str = ""
    #: 演唱者 / 创作者，数据页里写的原样（多人用「、」分隔）
    artists: str = ""


@dataclass(frozen=True, slots=True)
class Album:
    name: str
    #: 首次发行的日期（``2026-10-10``）；歌单是创建的日期
    date: str = ""
    #: 官方专辑 / 游戏本体 / 大触觉醒
    source: str = ""
    #: 角色主题曲、版本·活动主题曲……
    category: str = ""
    #: 专辑 / 歌单
    form: str = "专辑"
    #: 网易云音乐的专辑（歌单）编号；站内自己整理的条目没有
    number: str = ""
    language: str = ""
    shikigami: tuple[str, ...] = ()
    event: str = ""
    tracks: tuple[Track, ...] = ()

    def track(self, index: int) -> Track | None:
        return next((track for track in self.tracks if track.index == index), None)


def parse_albums(wikitext: str) -> list[Album]:
    """数据页的源码 → 专辑。和曲库页的脚本是同一种读法：一个 ``{{#subobject:…}}`` 一张专辑，
    参数用 ``|`` 隔开，``曲N=曲名#时长#音频#标记#创作者``（后面几段可以不写）。"""
    text = _COMMENT_RE.sub("", _NOWIKI_RE.sub("", wikitext or ""))
    albums: list[Album] = []
    for match in _SUBOBJECT_RE.finditer(text):
        fields: dict[str, str] = {}
        tracks: list[Track] = []
        for part in match.group(1).split("|")[1:]:
            key, sep, value = part.partition("=")
            key, value = re.sub(r"\s+", "", key), value.strip().replace("&#124;", "|")
            if not sep or not key:
                continue
            numbered = _TRACK_KEY_RE.fullmatch(key)
            if numbered is None:
                fields[key] = value
                continue
            name, duration, _audio, tag, artists = ((value + "####").split("#"))[:5]
            if name.strip():
                tracks.append(
                    Track(
                        int(numbered.group(1)),
                        name.strip(),
                        duration.strip(),
                        tag.strip(),
                        artists.strip(),
                    )
                )
        name = fields.get("专辑名", "")
        if not name:
            continue
        date = fields.get("专辑时间", "")[:10].replace("/", "-")
        albums.append(
            Album(
                name=name,
                date=date if _DATE_RE.fullmatch(date) else "",
                source=fields.get("专辑来源") or fields.get("专辑类别") or "官方专辑",
                category=fields.get("专辑子类", ""),
                form=fields.get("专辑类型") or "专辑",
                number=fields.get("专辑编号", ""),
                language=fields.get("专辑语种", ""),
                shikigami=tuple(
                    n.strip() for n in _NAME_SPLIT_RE.split(fields.get("专辑式神", "")) if n.strip()
                ),
                event=fields.get("专辑活动", ""),
                tracks=tuple(sorted(tracks, key=lambda track: track.index)),
            )
        )
    return albums


def find_track(albums: list[Album], key: str) -> tuple[Album, Track] | None:
    """歌词页标题里的 ``<专辑编号>-<曲序>`` 是哪张专辑的哪一首；数据页里没有返回 None。"""
    match = _LYRIC_KEY_RE.fullmatch(key.strip())
    if match is None:
        return None
    for album in albums:
        if album.number and album.number == match.group(1):
            track = album.track(int(match.group(2)))
            return (album, track) if track is not None else None
    return None


# ── 歌词页 ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class Lyrics:
    #: 制作信息（``@演唱：…`` 那几行，不带 ``@``）
    credits: list[str] = field(default_factory=list)
    #: 歌词：（原文，译文），译文可以是空的
    lines: list[tuple[str, str]] = field(default_factory=list)


def parse_lyrics(html: str) -> Lyrics | None:
    """歌词页渲染出来的 HTML → 歌词。正文在 ``<pre>`` 里，一行一句：``时间<Tab>原文<Tab>译文``，
    ``@`` 开头的行是制作信息。不是这个样子的页面（没有 ``<pre>``、一句歌词也没有）返回 None。"""
    pre = next(iter(parse_html(html).iter("pre")), None)
    if pre is None:
        return None
    lyrics = Lyrics()
    for raw in pre.text_content().split("\n"):
        line = raw.strip()
        if line.startswith("@"):
            if credit := line[1:].strip():
                lyrics.credits.append(credit)
            continue
        time, _, rest = line.partition("\t")
        if not _TIME_RE.fullmatch(time.strip()):
            continue
        text, _, translation = rest.partition("\t")
        if text.strip():
            lyrics.lines.append((text.strip(), translation.strip()))
    return lyrics if lyrics.lines else None


def song_title(track: Track) -> str:
    return f"《{track.name}》歌词"


def lyric_blocks(lyrics: Lyrics, found: tuple[Album, Track] | None) -> list[Block]:
    """一首歌的文档：这首歌是什么（数据页里有才写得出来）、制作信息、歌词。"""
    blocks: list[Block] = []
    if found is not None:
        blocks.append(Block(BLOCK_PARA, text="\n".join(_about(*found))))
    if lyrics.credits:
        blocks.append(Block(BLOCK_HEADING, text="制作信息", level=1))
        blocks.append(Block(BLOCK_LIST, items=[f"- {credit}" for credit in lyrics.credits]))
    blocks.append(Block(BLOCK_HEADING, text="歌词", level=1))
    lines = [
        f"{text}（{translation}）" if translation and translation != text else text
        for text, translation in lyrics.lines
    ]
    blocks.append(Block(BLOCK_PARA, text="\n".join(lines)))
    return blocks


def _about(album: Album, track: Track) -> list[str]:
    where = f"{album.form}《{album.name}》的第 {track.index} 首"
    released = " · ".join(part for part in (album.source, album.category) if part)
    if album.date:
        released = f"{album.date} 发行，{released}" if released else f"{album.date} 发行"
    rows = [
        f"《{track.name}》的歌词。",
        f"出处：{where}（{released}）" if released else f"出处：{where}",
        _row("版本", track.tag),
        _row("时长", track.duration),
        _row("演唱", track.artists),
        _row("语种", album.language),
        _row("式神", "、".join(album.shikigami)),
        _row("活动", album.event),
    ]
    return [row for row in rows if row]


def _row(label: str, value: str) -> str:
    return f"{label}：{value}" if value else ""


# ── 接进知识库 ────────────────────────────────────────────────────────


@dataclass(slots=True)
class MusicData:
    """这个插件取的原始内容（放在 ``RawCorpus.extras["bwiki_yys"]``）。"""

    #: 数据页的源码；没有这一页、离线时缓存里没有，就是空的
    wikitext: str = ""


class YysKnowledge(SitePlugin):
    id = PLUGIN_ID

    def __init__(
        self, lyrics_prefix: str = DEFAULT_LYRICS_PREFIX, data_page: str = DEFAULT_DATA_PAGE
    ):
        self.lyrics_prefix = lyrics_prefix
        self.data_page = data_page

    def _is_lyrics(self, title: str) -> bool:
        return bool(self.lyrics_prefix) and title.startswith(self.lyrics_prefix)

    async def collect(self, ctx: CollectContext) -> None:
        data = ctx.corpus.extras[PLUGIN_ID] = MusicData()
        if not any(self._is_lyrics(f.ref.title) for f in ctx.corpus.rendered):
            return
        ref = next((r for r in ctx.listing.pages if r.title == self.data_page), None)
        if ref is None:
            logger.warning("kb_lyrics_no_data_page", page=self.data_page)
            return
        data.wikitext = (await ctx.source.wikitext([ref])).get(ref.page_id, "")
        if not data.wikitext and not ctx.source.offline:
            # 这一轮不做了，下一轮再来：不然全部歌词页的标题都退回编号，下次取到了又要全部重算
            raise FetchError(f"「{self.data_page}」的源码没有取到")

    def summary(self, corpus: RawCorpus) -> dict[str, Any]:
        return {"lyric_pages": sum(1 for f in corpus.rendered if self._is_lyrics(f.ref.title))}

    def build_documents(self, ctx: BuildContext) -> None:
        data = ctx.corpus.extras.get(PLUGIN_ID)
        albums = parse_albums(data.wikitext) if isinstance(data, MusicData) else []
        rendered = {f.ref.page_id: f.value for f in ctx.corpus.rendered if not f.error}
        counts: Counter[str] = Counter()
        for doc in ctx.built.documents:
            if doc.kind != KIND_ENTRY or not self._is_lyrics(doc.title):
                continue
            lyrics = parse_lyrics(str((rendered.get(doc.page_id) or {}).get("text") or ""))
            if lyrics is None:
                counts["unparsed"] += 1  # 不是歌词页的样子：照普通条目留着
                continue
            found = find_track(albums, doc.title[len(self.lyrics_prefix) :])
            counts["titled" if found is not None else "untitled"] += 1
            if found is not None:
                doc.title = song_title(found[1])
            doc.blocks = lyric_blocks(lyrics, found)
        ctx.built.extras[PLUGIN_ID] = {"albums": len(albums), **counts}

    def stats(self, ctx: ProcessContext) -> dict[str, Any]:
        """歌词页的情况：数据页里有几张专辑；几个歌词页对上了歌名（``titled``）、
        几个没对上（``untitled``）、几个不是歌词页的样子（``unparsed``）。"""
        return {"lyrics": dict(ctx.built.extras.get(PLUGIN_ID) or {})}


def create(setup: SiteSetup) -> YysKnowledge:
    """入口：``setup.raw`` 是这个插件自己的配置。"""
    options = (setup.raw.get("knowledge") or {}).get("lyrics") or {}
    return YysKnowledge(
        str(options.get("prefix") or DEFAULT_LYRICS_PREFIX),
        str(options.get("data_page") or DEFAULT_DATA_PAGE),
    )
