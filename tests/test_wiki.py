"""/查 在这个站上多出来的东西：式神。"""

from __future__ import annotations

from typing import Any

import httpx
from jianshanagent.core.config import load_config
from jianshanagent.core.sites import EXTENSION_WIKI, load_sites
from jianshanagent.core.wiki import load_wiki
from jianshanagent.plugins.wiki_query.client import WikiQueryClient
from jianshanagent.plugins.wiki_query.formatters import format_page
from jianshanagent_site_bwiki.wiki import BwikiPlatform

from jianshanagent_site_bwiki_yys.wiki import KIND_SHIKIGAMI, YysProvider

SITE = "https://wiki.biligame.com/yys"


def _entry(title: str, **printouts: Any) -> dict[str, Any]:
    return {
        "printouts": printouts,
        "fulltext": title,
        "fullurl": f"{SITE}/{title}",
        "namespace": 0,
        "exists": "1",
        "displaytitle": "",
    }


#: 形状照抄 wiki.biligame.com/yys 的 action=ask 的真实返回。设定摘要做了删减，山风的两个日期调了先后
SHIKIGAMI: dict[str, dict[str, Any]] = {
    "大天狗·高天铁羽": _entry(
        "大天狗·高天铁羽",
        **{
            "稀有度": ["UR"],
            "性别": ["男"],
            "降临世界": ["未来世界"],
            "本家/联动": ["本家"],
            "上线日期": [{"timestamp": "1793145600", "raw": "1/2026/10/28"}],
            "日文CV": ["前野智昭"],
            "中文CV": ["郑武文杰"],
            "其他形态": ["[[大天狗]]、[[少羽大天狗]]"],
            "设定摘要": [
                "来自于崇天高云、现居住在黑夜山的传奇车手。\n已然驾驶「羽刃」，去奔赴下一场对决！"
            ],
        },
    ),
    "大天狗": _entry(
        "大天狗",
        **{
            "稀有度": ["SSR"],
            "性别": ["男"],
            "降临世界": ["平安世界"],
            "本家/联动": ["本家"],
            "上线日期": [{"timestamp": "1473379200", "raw": "1/2016/9/9"}],
            "日文CV": ["前野智昭"],
            "中文CV": ["暂无"],
            "其他形态": ["[[少羽大天狗]]"],
            "设定摘要": ["面容清秀，背上长有翅膀的大天狗。"],
        },
    ),
    "大天狗呱": _entry(
        "大天狗呱",
        **{
            "稀有度": ["N"],
            "性别": ["男"],
            "降临世界": ["平安世界"],
            "本家/联动": ["本家"],
            "上线日期": [{"timestamp": "1514332800", "raw": "1/2017/12/27"}],
            "日文CV": ["君岛哲"],
            "中文CV": ["暂无"],
            "其他形态": [],
            "设定摘要": ["胧车的青蛙部下。"],
        },
    ),
    "山风": _entry(
        "山风",
        **{
            "稀有度": ["SSR"],
            "性别": ["男"],
            "降临世界": ["平安世界"],
            "本家/联动": ["本家"],
            "上线日期": [
                {"timestamp": "1517961600", "raw": "1/2018/2/7"},
                {"timestamp": "1516147200", "raw": "1/2018/1/17"},
            ],
            "日文CV": ["增田俊树"],
            "中文CV": ["暂无"],
            "其他形态": ["[[初翎山风]]"],
            "设定摘要": [],
        },
    ),
    # 页面预设里的占位值没改的页面
    "月城雪兔&月": _entry(
        "月城雪兔&月",
        **{
            "稀有度": ["SSR"],
            "性别": ["男"],
            "降临世界": ["平安世界"],
            "本家/联动": ["联动"],
            "上线日期": [
                {"timestamp": "-2208988800", "raw": "1/1900/1/1"},
                {"timestamp": "1767225600", "raw": "1/2026"},
            ],
            "日文CV": [],
            "中文CV": ["没有的不填这行"],
            "其他形态": ["没有的不填这行"],
            "设定摘要": ["式神图鉴简介内容"],
        },
    ),
}


class FakeBwiki:
    """假的 BWiki：只认取全部式神的那一个语义查询。"""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        assert str(request.url).startswith(f"{SITE}/api.php") and params["action"] == "ask"
        self.queries.append(params["query"])
        assert params["query"].startswith("[[式神名::+]]|?稀有度|")
        return httpx.Response(200, json={"query": {"results": SHIKIGAMI}})


def _client(fake: FakeBwiki) -> WikiQueryClient:
    """照 wiki_query 插件的做法接起来：配置里点了 bwiki_yys，上级 bwiki 排在前面。"""
    config = load_config()
    wiki = load_wiki(config, "bwiki")
    client = WikiQueryClient(wiki, transport=httpx.MockTransport(fake))
    platform, yys = load_sites(config, EXTENSION_WIKI, wiki)
    assert isinstance(platform, BwikiPlatform) and isinstance(yys, YysProvider)
    assert yys.platform is platform  # 站插件拿到了上级的实例
    for provider in (platform, yys):
        client.add_provider(provider)
        provider.bind(client)
    return client


async def test_searching_finds_shikigami_by_name() -> None:
    fake = FakeBwiki()
    client = _client(fake)
    hits = await client.search("大天狗")
    # 名字完全一致的在前，包含的在后（短的在前）
    assert [(h.title, h.kind, h.exact) for h in hits] == [
        ("大天狗", KIND_SHIKIGAMI, True),
        ("大天狗呱", KIND_SHIKIGAMI, False),
        ("大天狗·高天铁羽", KIND_SHIKIGAMI, False),
    ]
    assert client.kind_labels == {KIND_SHIKIGAMI: "式神"}

    (match,) = await client.lookup_name("山风")
    assert (match.title, match.kind, match.exact) == ("山风", KIND_SHIKIGAMI, True)
    # 全部式神一次取回，之后都用缓存里解析好的
    assert len(fake.queries) == 1


async def test_a_partial_name_only_gives_candidates() -> None:
    yys = _client(FakeBwiki()).provider("bwiki_yys")
    assert yys is not None
    assert await yys.lookup_name("天狗") == []
    hints = await yys.name_candidates("天狗", limit=2)
    assert [(h.title, h.exact) for h in hints] == [("大天狗", False), ("大天狗呱", False)]


async def test_a_shikigami_page_carries_its_properties() -> None:
    client = _client(FakeBwiki())
    page = await client.get_page("大天狗·高天铁羽")
    assert page is not None
    assert (page.kind, page.url) == (KIND_SHIKIGAMI, f"{SITE}/大天狗·高天铁羽")
    assert page.extract.startswith("来自于崇天高云")
    assert page.data == {
        "稀有度": "UR",
        "性别": "男",
        "降临世界": "未来世界",
        "本家/联动": "本家",
        "上线日期": ["2026-10-28"],
        "日文CV": "前野智昭",
        "中文CV": "郑武文杰",
        "其他形态": ["大天狗", "少羽大天狗"],  # 链接写法里的页面标题
    }

    blank = await client.get_page("月城雪兔&月")
    assert blank is not None and blank.extract == ""
    # 没填的项不带：「暂无」、页面预设里留着没改的占位值都等于没填
    assert blank.data == {
        "稀有度": "SSR",
        "性别": "男",
        "降临世界": "平安世界",
        "本家/联动": "联动",
        "上线日期": ["2026"],
    }
    # 不是式神的：这个插件不认，交给通用的页面查询
    yys = client.provider("bwiki_yys")
    assert yys is not None and await yys.get_page("飞羽凌云", None) is None


async def test_the_card_of_a_shikigami() -> None:
    client = _client(FakeBwiki())
    page = await client.get_page("大天狗·高天铁羽", kind=KIND_SHIKIGAMI)
    assert page is not None
    assert format_page(page, providers=client.providers).splitlines() == [
        "【大天狗·高天铁羽】 · UR · 男 · 未来世界 · 本家",
        "上线：2026-10-28",
        "CV：前野智昭（日） / 郑武文杰（中）",
        "其他形态：大天狗、少羽大天狗",
        "来自于崇天高云、现居住在黑夜山的传奇车手。",
        "已然驾驶「羽刃」，去奔赴下一场对决！",
        f"{SITE}/大天狗·高天铁羽",
    ]

    # 上线日期不止一个的都写上（早的在前）；没有的行不出现
    page = await client.get_page("山风")
    assert page is not None
    text = format_page(page, providers=client.providers, include_link=False, markdown=True)
    assert text.splitlines() == [
        "**【山风】** · SSR · 男 · 平安世界 · 本家",
        "上线：2018-01-17、2018-02-07",
        "CV：增田俊树（日）",
        "其他形态：初翎山风",
    ]
