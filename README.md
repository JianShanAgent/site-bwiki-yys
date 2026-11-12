<p align="center"><img src="assets/icon.svg" width="88" alt="JianShanAgent"></p>

<h1 align="center">site-bwiki-yys</h1>

<p align="center"><a href="https://github.com/JianShanAgent/agent-core">JianShanAgent（见山）</a>的 <a href="https://wiki.biligame.com/yys">BWiki 阴阳师剧情百科</a>站点插件。</p>

<p align="center">
  <img src="https://img.shields.io/badge/插件-站点-2f6b5a?style=flat-square&labelColor=1f3b34" alt="站点插件">
  <img src="https://img.shields.io/badge/id-bwiki__yys-e9a66b?style=flat-square&labelColor=1f3b34" alt="id: bwiki_yys">
  <img src="https://img.shields.io/badge/平台-bwiki-e9a66b?style=flat-square&labelColor=1f3b34" alt="平台: bwiki">
  <img src="https://img.shields.io/github/license/JianShanAgent/site-bwiki-yys?label=License&color=2f6b5a&style=flat-square&labelColor=1f3b34" alt="License">
</p>

<sub>JianShanAgent site plugin for the Onmyoji story wiki on BWiki (`wiki.biligame.com/yys`), built on the BWiki platform support bundled with the core. Adds structured shikigami lookups via Semantic MediaWiki, song titles and album info for the lyrics pages in the knowledge base, plus this site's HTML cleaning rules, page exclusions, research wording and persona.</sub>

## 插件简介

[阴阳师剧情百科](https://wiki.biligame.com/yys)是玩家在 BWiki 上自建的《阴阳师》剧情资料站：主线、活动与式神伴生剧情的文本，式神的档案、传记、语音，剧情设定辞书，以及插画、影像、音乐的索引。

BWiki 平台的东西（语义查询接口、取数的速率、平台组件的清洗规则）核心自带；本插件在它之上，把这个站特有的东西接进见山：

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

### 2. 带着歌名的歌词

「音乐曲库」的歌词一首一页（491 页），标题是编号（`音乐曲库/歌词/402981386-1`），正文只有制作信息和带时间轴的歌词，没有歌名。歌名、专辑、发行日期、对应的式神和活动记在「音乐曲库/数据」这一页的源码里。插件建知识库时多取这一页的源码，把歌词页的文档写成：

```text
《奔向刹那之后（刹那のその先へ）》歌词

《奔向刹那之后（刹那のその先へ）》的歌词。
出处：专辑《奔向刹那之后（刹那のその先へ）》的第 1 首（2026-10-10 发行，官方专辑 · 周年·印象曲）
时长：3:30
演唱：R!N/Gemie、网易阴阳师手游
语种：日文
活动：十周年

## 制作信息
- 演唱：R!N/网易阴阳师手游
- ……

## 歌词
ハイラ ハイラ（Hai-La Hai-La）
刹那のその先へ（刹那之后）
……
```

歌词去掉了时间轴，译文跟在原文后面。数据页里没有的歌词页标题照旧。数据页或歌词页在 wiki 上改了，知识库的自动更新会跟着重做。

### 3. 清洗规则、不入库的页面、查证提示词与人设（纯配置）

在 [`config.yaml`](src/jianshanagent_site_bwiki_yys/config.yaml) 的 `extend` 段里：

- **清洗规则**：式神页的立绘框、传记前面的小目录、按钮式标签页的那排按钮、插画故事页顶部的字数统计、面包屑不进知识库。页面底部的导航表平台已经去掉了；整页只有导航表的页面（「花合战」是一张历年皮肤的名单）留着它；
- **不入库的页面**：首页的各个板块、新建页面用的预设、沙盒、检索页背后的数据页，共 38 个，都是给编辑用的；
- **查证提示词**：问题分类（式神、剧情、设定、活动……）、容易张冠李戴的地方（同一个角色的几个形态各有各的页面）；
- **人设**：阴阳师剧情百科助手。

## 如何安装使用

**在管理后台里一键添加（最省事）**：打开机器人管理后台的「Wiki」页，在站点目录里选平台「BWiki」，点「阴阳师剧情百科」的「添加」。机器人会下载本插件最新的发布、核对校验和后装上，`/查` 马上能用，不用重启；知识库在同一页里点「建知识库」。

**随部署装进环境**：在实例仓库（参考线上实例 [`instance-yys`](https://github.com/JianShanAgent/instance-yys) 或模板 [`template-instance`](https://github.com/JianShanAgent/template-instance)）的 `pyproject.toml` 中加入本插件：

```toml
dependencies = [
  "jianshanagent @ git+https://github.com/JianShanAgent/agent-core.git",
  "jianshanagent-site-bwiki-yys @ git+https://github.com/JianShanAgent/site-bwiki-yys.git",
]
```

然后在实例的 `config/core.wiki.yaml` 的 `wikis` 名单里加上这个 wiki（它在 BWiki 上写在它自己的清单里，核心带着的 BWiki 平台会先加载）：

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

配置名 `site.bwiki_yys`，默认配置在 [`src/jianshanagent_site_bwiki_yys/config.yaml`](src/jianshanagent_site_bwiki_yys/config.yaml)：`wiki` 段是哪些页面算式神、哪些值等于没填；`knowledge` 段是歌词页的前缀和数据页的标题；`extend` 段是并进通用配置的内容。要改某一项，在实例仓库新建 `config/site.bwiki_yys.yaml` 只写要改的字段。

## 目录结构与本地开发

```text
src/jianshanagent_site_bwiki_yys/
├── plugin.yaml      # 插件清单（id: bwiki_yys, platform: bwiki）
├── config.yaml      # 默认配置与这个站对通用配置的补充（extend）
├── wiki.py          # 查询扩展点实现：YysProvider（式神）
└── knowledge.py     # 知识库扩展点实现：YysKnowledge（歌词页配上歌名）
```

本地开发时把 [`agent-core`](https://github.com/JianShanAgent/agent-core) 放在同级目录后运行：

```bash
uv sync --extra dev
uv run pytest
```

**发版**：改 `pyproject.toml` 里的 `version` 并提交，打一个带附注的标签 `v<版本>` 推上来，[发版流程](.github/workflows/release.yml)会跑测试、打安装包并发 Release；管理后台的一键添加和「更新插件」取的就是最新的 Release。

## 开源许可

[MIT License](LICENSE)
