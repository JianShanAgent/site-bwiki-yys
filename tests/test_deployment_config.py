"""一个用了这个插件的部署，读出来的配置是什么样（核心的测试里说的是不带站点插件的样子）。"""

from __future__ import annotations

from jianshanagent.admin.schema import build_schema
from jianshanagent.core.config import load_config
from jianshanagent.core.manifest import installed_sites
from jianshanagent.core.sites import EXTENSION_KNOWLEDGE, load_sites
from jianshanagent.core.wiki import load_wiki, wiki_subject
from jianshanagent.plugins.knowledge.settings import load_settings

from conftest import CONFIG_DIR


def test_naming_the_site_brings_the_platform_and_their_additions() -> None:
    assert "bwiki_yys" in installed_sites()  # 这个包装着、登记了
    config = load_config(CONFIG_DIR, with_overrides=False)
    # 配置里只写了 bwiki_yys：它是 BWiki 上的站，核心带着的 BWiki 平台那一份跟着加载
    assert [wiki["site"] for wiki in config.get("core.wiki")["wikis"]] == ["bwiki_yys"]
    assert (config.platforms, config.sites) == (["bwiki"], ["bwiki_yys"])
    assert config.site("bwiki_yys")["wiki"]["shikigami"]["condition"] == "[[式神名::+]]"
    # 默认配置各在各的地方：站点插件的在自己的包里，平台的在核心里
    assert config.source_path("site.bwiki_yys").parent.name == "jianshanagent_site_bwiki_yys"
    assert config.source_path("platform.bwiki").parent.parent.name == "platforms"

    # 这个站对通用配置的补充，读配置时就并进去了
    research = config.plugin("research")
    assert {"式神", "剧情", "设定"} <= set(research["analysis"]["topics"])
    assert research["wording"]["generic_words"] == ["式神", "剧情", "活动"]
    assert research["wording"]["analyst_note"].startswith("同一个角色常有几个形态")
    assert (
        config.plugin("wiki_query")["commands"]["lookup"]["description"] == "查询式神或 wiki 条目"
    )
    assert config.get("persona/persona.default")["name"] == "阴阳师剧情百科助手"
    subject = wiki_subject(config)
    assert (subject.bot, subject.intro) == ("阴阳师 wiki 机器人", "阴阳师（网易手游）wiki")


def test_the_knowledge_base_gets_the_rules_of_both_levels() -> None:
    config = load_config(CONFIG_DIR, with_overrides=False)
    settings = load_settings(config)
    # 平台的：取数放慢、导航性的内容不要、标签页的名字在 title 属性上；
    # 这个站的：立绘框、传记的小目录、标签页的按钮、不入库的页面
    assert (settings.fetch.max_concurrency, settings.fetch.requests_per_second) == (1, 0.5)
    assert {"navigation-not-searchable", "role-card__image-frame", "role-bio__toc"} <= set(
        settings.clean.remove_classes
    )
    assert settings.clean.tabber_label_attribute == "title"
    excluded = settings.sources.exclude_titles
    assert {"沙盒/式神录", "音乐曲库/数据", "首页式神录板块"} <= excluded and "首页" not in excluded
    assert (
        settings.wiki.page_url("大天狗")
        == "https://wiki.biligame.com/yys/%E5%A4%A7%E5%A4%A9%E7%8B%97"
    )
    # 平台和这个插件都没接知识库这个扩展点：入库的只有条目页
    assert load_sites(config, EXTENSION_KNOWLEDGE, load_wiki(config, "bwiki")) == []


def test_the_additions_cannot_be_edited_from_the_admin_pages() -> None:
    config = load_config(CONFIG_DIR, with_overrides=False)
    for name in ("platform.bwiki", "site.bwiki_yys"):
        data = config.get(name)
        fields = build_schema(data, data, {}, name=name)
        locked = {".".join(field["path"]) for field in fields if field["locked"]}
        # 平台、站点插件对通用配置的补充：读配置时就并进去了，在网页上改它不会生效
        assert locked == {"extend"}, name
