"""知识库里这个站特有的东西：歌词页配上歌名；整页只有导航表的「花合战」。"""

from __future__ import annotations

from typing import Any

import pytest
from jianshanagent.core.config import load_config
from jianshanagent.plugins.knowledge.collect import CollectContext, RawCorpus
from jianshanagent.plugins.knowledge.fetcher import FetchError
from jianshanagent.plugins.knowledge.pipeline import build_documents, process
from jianshanagent.plugins.knowledge.settings import Settings, load_settings
from jianshanagent.plugins.knowledge.sources import Fetched, Listing, PageRef

from conftest import CONFIG_DIR
from jianshanagent_site_bwiki_yys.knowledge import (
    PLUGIN_ID,
    MusicData,
    YysKnowledge,
    find_track,
    parse_albums,
    parse_lyrics,
)

#: 「音乐曲库/数据」的源码：说明文字里的范本包在 nowiki 里，不算数
DATA = """__NOINDEX__
本页是'''[[音乐曲库]]'''的结构化数据源。范本：<nowiki>{{#subobject:专辑-范本
|专辑名=范本专辑
|专辑编号=1
|曲1=范本曲#1:00}}</nowiki>
<!-- {{#subobject:专辑-注释里的|专辑名=注释里的|专辑编号=2|曲1=不算#1:00}} -->

{{#subobject:专辑-402981386
|专辑名=奔向刹那之后（刹那のその先へ）
|专辑封面=https://p2.music.126.net/cover.jpg
|专辑时间=2026-10-10
|专辑来源=官方专辑
|专辑子类=周年·印象曲
|专辑式神=
|专辑活动=十周年
|专辑编号=402981386
|专辑语种=日文
|专辑歌词=1,2
|曲1=奔向刹那之后（刹那のその先へ）#3:30#奔向刹那之后.mp3##R!N/Gemie、网易阴阳师手游
|曲2=奔向刹那之后（刹那のその先へ）（伴奏）#3:30#伴奏.mp3#伴奏#R!N/Gemie、网易阴阳师手游
}}

{{#subobject:专辑-拾此一瞬
|专辑名=拾此一瞬版本活动原声
|专辑时间=2026-10-10
|专辑来源=游戏本体
|专辑子类=游戏原声
|专辑式神=咲耶、缘结神
|专辑编号=
|曲1=拾此一瞬-登录#3:30#拾此一瞬-登录.mp3
|曲3=拾此一瞬-战斗
|曲2=
}}

{{#subobject:专辑-5289575310
|专辑名=2020阴阳师大触觉醒·礼乐和鸣原创音乐大赛
|专辑时间=2020/10/15
|专辑来源=大触觉醒
|专辑类型=歌单
|专辑编号=5289575310
|曲7=风起 &#124; 平安京#4:01##专业原创#萧荷、月知
}}

{{#subobject:没有名字的|专辑编号=9|曲1=不算#1:00}}
"""

LYRICS = """<div class="mw-parser-output"><pre>@演唱：R!N/网易阴阳师手游
@曲：何官锭AL
@

00:00.77\tハイラ ハイラ\tHai-La Hai-La
00:07.93\t刹那のその先へ\t刹那之后
00:20.36\t朝焼けを追い越して\t越过清晨的霞光
01:14.96\tLa La La\tLa La La
02:02.73\t待って——
这一行没有时间，不是歌词
103:05.1\t&lt;间奏&gt;\t
</pre></div>"""

PLAIN_LYRICS = """<div class="mw-parser-output"><pre>@词：音扬师工坊
--\t风起平安京\t
--\t一梦千年\t
</pre></div>"""

PREFIX = "音乐曲库/歌词/"
DATA_REF = PageRef(page_id=2573, title="音乐曲库/数据", rev_id=23706)


@pytest.fixture(scope="module")
def settings() -> Settings:
    return load_settings(load_config(CONFIG_DIR, with_overrides=False))


def _page(page_id: int, title: str, html: str) -> Fetched:
    return Fetched(PageRef(page_id=page_id, title=title, rev_id=1), value={"text": html})


def _corpus(*pages: Fetched, data: str = DATA) -> RawCorpus:
    listing = Listing(pages=[DATA_REF, *(page.ref for page in pages)], data={})
    return RawCorpus(listing=listing, rendered=list(pages), extras={PLUGIN_ID: MusicData(data)})


# ── 数据页 ────────────────────────────────────────────────────────────


def test_albums_are_read_the_way_the_page_script_reads_them() -> None:
    albums = parse_albums(DATA)
    assert [album.name for album in albums] == [
        "奔向刹那之后（刹那のその先へ）",
        "拾此一瞬版本活动原声",
        "2020阴阳师大触觉醒·礼乐和鸣原创音乐大赛",
    ]
    anniversary, ost, contest = albums
    assert (anniversary.date, anniversary.source, anniversary.category) == (
        "2026-10-10",
        "官方专辑",
        "周年·印象曲",
    )
    assert (anniversary.number, anniversary.language, anniversary.event, anniversary.form) == (
        "402981386",
        "日文",
        "十周年",
        "专辑",
    )
    assert anniversary.shikigami == ()
    backing = anniversary.track(2)
    assert backing is not None and backing.name == "奔向刹那之后（刹那のその先へ）（伴奏）"
    assert (backing.duration, backing.tag, backing.artists) == (
        "3:30",
        "伴奏",
        "R!N/Gemie、网易阴阳师手游",
    )
    # 后面几段可以不写；没写曲名的不算；按曲序排
    assert ost.shikigami == ("咲耶", "缘结神") and ost.number == ""
    assert [(t.index, t.name, t.duration) for t in ost.tracks] == [
        (1, "拾此一瞬-登录", "3:30"),
        (3, "拾此一瞬-战斗", ""),
    ]
    # 歌单；日期的另一种写法；值里的竖线
    assert (contest.form, contest.date, contest.source) == ("歌单", "2020-10-15", "大触觉醒")
    assert [(t.index, t.name, t.tag) for t in contest.tracks] == [(7, "风起 | 平安京", "专业原创")]


def test_a_lyrics_page_is_matched_by_album_number_and_track_number() -> None:
    albums = parse_albums(DATA)
    found = find_track(albums, "402981386-2")
    assert found is not None and found[1].tag == "伴奏"
    assert find_track(albums, "5289575310-7") is not None
    assert find_track(albums, "402981386-3") is None  # 这张专辑没有第 3 首
    assert find_track(albums, "999-1") is None
    assert find_track(albums, "-1") is None  # 站内整理的条目没有编号，不会被空编号对上
    assert find_track(albums, "说明") is None


# ── 歌词页 ────────────────────────────────────────────────────────────


def test_lyrics_lose_the_timeline_and_keep_credits_and_translations() -> None:
    lyrics = parse_lyrics(LYRICS)
    assert lyrics is not None
    assert lyrics.credits == ["演唱：R!N/网易阴阳师手游", "曲：何官锭AL"]
    assert lyrics.lines == [
        ("ハイラ ハイラ", "Hai-La Hai-La"),
        ("刹那のその先へ", "刹那之后"),
        ("朝焼けを追い越して", "越过清晨的霞光"),
        ("La La La", "La La La"),
        ("待って——", ""),
        ("<间奏>", ""),
    ]
    plain = parse_lyrics(PLAIN_LYRICS)  # 没有时间轴的写 --
    assert plain is not None and plain.lines == [("风起平安京", ""), ("一梦千年", "")]
    # 不是歌词页的样子
    assert parse_lyrics("<p>本页收录歌词。</p>") is None
    assert parse_lyrics("<pre>@演唱：某某\n这里没有一句带时间的歌词</pre>") is None


def test_a_lyrics_page_becomes_a_document_about_the_song(settings: Settings) -> None:
    corpus = _corpus(
        _page(3040, f"{PREFIX}402981386-1", LYRICS),
        _page(3041, f"{PREFIX}999-1", PLAIN_LYRICS),
        _page(
            3042, f"{PREFIX}说明", "<p>歌词页的格式：一行一句，时间、原文、译文用制表符隔开。</p>"
        ),
        _page(10, "大天狗", "<p>大天狗是《阴阳师》里的 SSR 式神，黑夜山之主，以羽刃暴风闻名。</p>"),
    )
    built = build_documents(corpus, settings)
    docs = {doc.doc_key: doc for doc in built.documents}

    song = docs["page:3040"]
    assert song.title == "《奔向刹那之后（刹那のその先へ）》歌词"
    assert song.url == settings.wiki.page_url(f"{PREFIX}402981386-1")  # 出处还是那个歌词页
    about, credits_title, credits, lyrics_title, lyrics = song.blocks
    assert about.text.split("\n") == [
        "《奔向刹那之后（刹那のその先へ）》的歌词。",
        "出处：专辑《奔向刹那之后（刹那のその先へ）》的第 1 首"
        "（2026-10-10 发行，官方专辑 · 周年·印象曲）",
        "时长：3:30",
        "演唱：R!N/Gemie、网易阴阳师手游",
        "语种：日文",
        "活动：十周年",
    ]
    assert (credits_title.text, lyrics_title.text) == ("制作信息", "歌词")
    assert credits.items == ["- 演唱：R!N/网易阴阳师手游", "- 曲：何官锭AL"]
    assert lyrics.text.split("\n") == [
        "ハイラ ハイラ（Hai-La Hai-La）",
        "刹那のその先へ（刹那之后）",
        "朝焼けを追い越して（越过清晨的霞光）",
        "La La La",  # 译文和原文一样的不重复
        "待って——",
        "<间奏>",
    ]

    # 数据页里没有的：标题照旧，歌词照样去掉时间轴
    unknown = docs["page:3041"]
    assert unknown.title == f"{PREFIX}999-1"
    assert [b.text for b in unknown.blocks if b.kind == "para"] == ["风起平安京\n一梦千年"]
    # 不是歌词页的样子、别的条目：原样
    assert docs["page:3042"].blocks[0].text.startswith("歌词页的格式")
    assert docs["page:10"].title == "大天狗"

    # 切片的首行带着歌名：搜歌名能找到歌词
    result = process(built, corpus, settings)
    chunk = next(c for c in result.chunks if c.doc_key == "page:3040")
    assert chunk.text.startswith("《奔向刹那之后（刹那のその先へ）》歌词")
    assert "刹那のその先へ（刹那之后）" in chunk.text and "00:07" not in chunk.text
    assert result.stats["lyrics"] == {"albums": 3, "titled": 1, "untitled": 1, "unparsed": 1}


def test_without_the_data_page_lyrics_keep_their_numbered_titles(settings: Settings) -> None:
    corpus = _corpus(_page(3040, f"{PREFIX}402981386-1", LYRICS), data="")
    (doc,) = build_documents(corpus, settings).documents
    assert doc.title == f"{PREFIX}402981386-1"
    assert [b.text for b in doc.blocks if b.kind == "heading"] == ["制作信息", "歌词"]


# ── 取数：多取一份数据页的源码 ────────────────────────────────────────


class FakeSource:
    def __init__(self, texts: dict[int, str], *, offline: bool = False):
        self.texts, self.offline = texts, offline
        self.asked: list[list[str]] = []

    async def wikitext(self, refs: list[PageRef]) -> dict[int, str]:
        self.asked.append([ref.title for ref in refs])
        return {ref.page_id: self.texts[ref.page_id] for ref in refs if ref.page_id in self.texts}


def _context(source: Any, settings: Settings, corpus: RawCorpus) -> CollectContext:
    return CollectContext(source, settings, corpus)


async def test_the_data_page_is_fetched_once_when_there_are_lyrics(settings: Settings) -> None:
    plugin = YysKnowledge()
    corpus = _corpus(_page(3040, f"{PREFIX}402981386-1", LYRICS), data="")
    source = FakeSource({DATA_REF.page_id: DATA})
    await plugin.collect(_context(source, settings, corpus))
    assert source.asked == [["音乐曲库/数据"]]
    assert corpus.extras[PLUGIN_ID].wikitext == DATA
    assert plugin.summary(corpus) == {"lyric_pages": 1}

    # 这次没有歌词页（只调试某个页面）：不取
    idle = FakeSource({DATA_REF.page_id: DATA})
    corpus = _corpus(_page(10, "大天狗", "<p>式神。</p>"), data="")
    await plugin.collect(_context(idle, settings, corpus))
    assert idle.asked == [] and corpus.extras[PLUGIN_ID].wikitext == ""


async def test_a_failed_fetch_of_the_data_page_stops_the_run(settings: Settings) -> None:
    plugin = YysKnowledge()
    lyrics = _page(3040, f"{PREFIX}402981386-1", LYRICS)
    # 没取到：这一轮不做了，免得全部歌词页的标题退回编号
    with pytest.raises(FetchError, match="音乐曲库/数据"):
        await plugin.collect(_context(FakeSource({}), settings, _corpus(lyrics, data="")))
    # 离线、缓存里没有：照编号的标题做
    corpus = _corpus(lyrics, data="")
    await plugin.collect(_context(FakeSource({}, offline=True), settings, corpus))
    assert corpus.extras[PLUGIN_ID].wikitext == ""
    # 站上没有数据页了：也照编号的标题做
    corpus = RawCorpus(listing=Listing(pages=[lyrics.ref], data={}), rendered=[lyrics])
    source = FakeSource({})
    await plugin.collect(_context(source, settings, corpus))
    assert source.asked == [] and corpus.extras[PLUGIN_ID].wikitext == ""


# ── 整页只有导航表的页面 ──────────────────────────────────────────────


def test_the_page_that_is_only_a_navigation_table_is_kept_without_its_breadcrumb(
    settings: Settings,
) -> None:
    def year(number: int) -> str:
        rows = "".join(
            f'<tr><td>{month}月</td><td><a href="/yys/皮肤{number}{month}">'
            f"式神{month}：{number}年的皮肤{month}</a></td></tr>"
            for month in range(1, 13)
        )
        return f'<div class="tabbertab" title="{number}"><table>{rows}</table></div>'

    html = (
        '<div class="mw-parser-output"><div class="crumb navigation-not-searchable">'
        '<a href="/yys/首页">首页</a> &gt; 花合战 <small>短</small> • <small>刷</small></div>'
        '<div class="navigation-not-searchable"><p>花合战导航</p><div class="tabber">'
        f"{''.join(year(number) for number in range(2020, 2027))}</div></div></div>"
    )
    (doc,) = build_documents(_corpus(_page(1569, "花合战", html)), settings).documents
    assert [b.text for b in doc.blocks if b.kind == "heading"] == [
        str(n) for n in range(2020, 2027)
    ]
    text = "\n".join(block.render() for block in doc.blocks)
    assert "1月：式神1：2020年的皮肤1" in text and "12月：式神12：2026年的皮肤12" in text
    assert "首页" not in text and "短" not in text
