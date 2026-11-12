"""这个插件合不合 JianShanAgent 的插件规范（核心仓库的 docs/插件规范.md）。"""

from jianshanagent.testing.conformance import check_plugin


def test_conforms_to_the_plugin_spec() -> None:
    manifest = check_plugin("jianshanagent_site_bwiki_yys")
    assert (manifest.id, manifest.platform) == ("bwiki_yys", "bwiki")
    assert set(manifest.capabilities) == {"wiki", "knowledge", "extend"}
