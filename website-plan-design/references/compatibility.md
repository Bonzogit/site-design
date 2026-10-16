# 交接前检查

建站 Skill 的 `assets/interface-contract.json` 是共同接口源，详读其 `references/skill-interfaces.md`。设计包不复制主题、内容模型、翻译核心或业务适配器。支持共同接口 theme=unified-theme-v1、inquiry=unified-inquiry-v1、designRecord=2.0、translation=2；新能力先检查接口，不能仅比较包版本字符串。

运行 `python scripts/compatibility_check.py --builder <建站Skill目录>`；有工程时加 `--project <工程目录> --version <本次网站版本>`，会调用建站原始 design_check 并校对真实核心文件，不把文档宣告当成已接线。设计阶段可以保留 unverified；结构通过不等于研究或页面通过。更新版本后仍需重新检查。

旧版建站没有共同契约时检查失败，报告缺项；已有工程先保留数据与业务代码，分析差异后通过原项目更新。不能将新 contract 文件单独贴进旧工程绕过检查。仅策划且还没有工程时，只检查建站能力，不强制提前造项目。
