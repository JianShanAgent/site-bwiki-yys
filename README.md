<p align="center"><img src="assets/icon.svg" width="88" alt="JianShanAgent"></p>

<h1 align="center">site-bwiki-yys</h1>

<p align="center"><a href="https://github.com/JianShanAgent/agent-core">JianShanAgent（见山）</a>的 <a href="https://wiki.biligame.com/yys">BWiki 阴阳师剧情百科</a>站点插件。</p>

<p align="center">
  <img src="https://img.shields.io/badge/插件-站点%20·%20站-2f6b5a?style=flat-square&labelColor=1f3b34" alt="站点插件 · 站">
  <img src="https://img.shields.io/badge/id-bwiki__yys-e9a66b?style=flat-square&labelColor=1f3b34" alt="id: bwiki_yys">
  <img src="https://img.shields.io/badge/上级-bwiki-e9a66b?style=flat-square&labelColor=1f3b34" alt="上级: bwiki">
  <img src="https://img.shields.io/github/license/JianShanAgent/site-bwiki-yys?label=License&color=2f6b5a&style=flat-square&labelColor=1f3b34" alt="License">
</p>

<sub>JianShanAgent site plugin for the Onmyoji story wiki on BWiki (`wiki.biligame.com/yys`), built on top of `site-bwiki`. Adds structured shikigami lookups via Semantic MediaWiki, plus this site's HTML cleaning rules, page exclusions, research wording and persona.</sub>

## 插件简介

[阴阳师剧情百科](https://wiki.biligame.com/yys)是玩家在 BWiki 上自建的《阴阳师》剧情资料站：主线、活动与式神伴生剧情的文本，式神的档案、传记、语音，剧情设定辞书，以及插画、影像、音乐的索引。

本插件构建在 BWiki 平台插件 [`site-bwiki`](https://github.com/JianShanAgent/site-bwiki) 之上，把这个站特有的东西接进见山：

### 1. 式神直查

```text
用户  /查 大天狗·高天铁羽
见山  【大天狗·高天铁羽】 · UR · 男 · 未来世界 · 本家
      上线：2026-10-28
      CV：前野智昭（日） / 郑武文杰（中）
      其他形态：大天狗、少羽大天狗
      来自于崇天高云、现居住在黑夜山的传奇车手。……
      https://wiki.biligame.com/yys/%E5%A4%A7%E5%A4%A9%E7%8B%97%C2%B7%E9%AB%98%E5%A4%A9%E9%93%81%E7%BE%BD
```

式神页上的模板把稀有度、性别、上线日期、CV、其他形态、设定摘要记成了语义属性。插件用一次语义查询取回全部式神，按名字找（完全一致的直接给卡片，只包含的列成候选），同样的查询也注册给对话模型用（`wiki_search` / `wiki_get`）。没填的项和页面预设里留着没改的占位值（「暂无」「没有的不填这行」……）不上卡片。

式神以外的页面走通用的查询：按标题找、全文搜索。

### 2. 清洗规则、不入库的页面、查证提示词与人设（纯配置）

在 [`config.yaml`](src/jianshanagent_site_bwiki_yys/config.yaml) 的 `extend` 段里：

- **清洗规则**：式神页的立绘框、传记前面的小目录、按钮式标签页的那排按钮、插画故事页顶部的字数统计不进知识库；
- **不入库的页面**：首页的各个板块、新建页面用的预设、沙盒、检索页背后的数据页，共 38 个，都是给编辑用的；
- **查证提示词**：问题分类（式神、剧情、设定、活动……）、容易张冠李戴的地方（同一个角色的几个形态各有各的页面）；
- **人设**：阴阳师剧情百科助手。

## 如何安装使用

在实例仓库（参考线上实例 [`instance-yys`](https://github.com/JianShanAgent/instance-yys) 或模板 [`template-instance`](https://github.com/JianShanAgent/template-instance)）的 `pyproject.toml` 中同时加入 BWiki 平台插件与本插件：

```toml
dependencies = [
  "jianshanagent @ git+https://github.com/JianShanAgent/agent-core.git",
  "jianshanagent-site-bwiki @ git+https://github.com/JianShanAgent/site-bwiki.git",
  "jianshanagent-site-bwiki-yys @ git+https://github.com/JianShanAgent/site-bwiki-yys.git",
]
```

然后在实例的 `config/core.wiki.yaml` 的 `wikis` 名单里加上这个 wiki（上级 `bwiki` 会自动先加载）：

```yaml
name: "阴阳师"
about: "网易手游"
wikis:
  - id: bwiki                # 这个 wiki 在部署里的名字：知识库的目录名、密钥的键
    label: "BWiki"           # 挂了不止一个 wiki 时，回答里标出处用
    api_url: "https://wiki.biligame.com/yys/api.php"
    site_base: "https://wiki.biligame.com/yys"
    article_path: "/$1"
    site: bwiki_yys
```

> `wikis` 是一份名单：同一个实例可以和灰机阴阳师 Wiki 的插件 [`site-huiji-yys`](https://github.com/JianShanAgent/site-huiji-yys) 一起挂（线上实例 [`instance-yys`](https://github.com/JianShanAgent/instance-yys) 就是这样），两个 wiki 的资料合在一起检索，回答里标明出处。

## 配置说明

配置名 `site.bwiki_yys`，默认配置在 [`src/jianshanagent_site_bwiki_yys/config.yaml`](src/jianshanagent_site_bwiki_yys/config.yaml)：`wiki` 段是哪些页面算式神、哪些值等于没填；`extend` 段是并进通用配置的内容。要改某一项，在实例仓库新建 `config/site.bwiki_yys.yaml` 只写要改的字段。

## 目录结构与本地开发

```text
src/jianshanagent_site_bwiki_yys/
├── plugin.yaml      # 插件清单（id: bwiki_yys, parent: bwiki）
├── config.yaml      # 默认配置与这个站对通用配置的补充（extend）
└── wiki.py          # 查询扩展点实现：YysProvider（式神）
```

本地开发时把 [`agent-core`](https://github.com/JianShanAgent/agent-core) 和 [`site-bwiki`](https://github.com/JianShanAgent/site-bwiki) 放在同级目录后运行：

```bash
uv sync --extra dev
uv run pytest
```

## 开源许可

[MIT License](LICENSE)
