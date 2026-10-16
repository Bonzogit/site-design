# 可选资源接入

不内置或恢复历史固定参考库。资源目录由用户本机配置指向已有成果；缺失时用本次资料和可访问实际来源继续。配置位置优先 `--config`，其次环境变量 `WEBSITE_RESOURCES_CONFIG`，再用户主目录 `.codex/private-config/website-resources.json`。路径不进入公开仓库、ZIP、来源摘录或客户网页；配置不含凭据。

复制 assets/resources.example.json 至私有配置，填写实际 roots。design-md 的 root 指含 spec-manifest.json、spec-analysis-index.json 与 spec-text-*.txt 的发布目录；motion-lab 的 root 指实验室 public 目录。只读取，不写入、搬迁或重新部署资源库。

```text
python scripts/resources.py doctor
python scripts/resources.py search --query "editorial hardware product" --kind design-md --limit 6
python scripts/resources.py search --query "tabs dialog 图片" --kind motion-lab --limit 6
python scripts/resources.py inspect --id <检索返回的ID>
```

检索按元数据与规则提取特征匹配，返回来源、版本、证据等级、许可及限制；不是语义设计师或质量排名。结果里的本机文件路径仅供当前执行，不写公开报告。采用项必须 inspect 回读原文；原始 SHA 不符时警告并重新核实。文本乱码或替换字符须保留警告，不据损坏文本推断设计。

产品类别词可能有歧义，例如 hardware 也会匹配建筑五金。按实际任务审阅候选，必要时换更具体的名称或视觉问题；不直接采用最高匹配分。历史规范中的站点域名也可能过时，使用实际当前地址核验。

规范快照中的历史、局部 CSS 实测和社区提案分别识别。批量提取不能证明观察过源网站；没有动效字段不能证明原站没有动效。研究相关实际页面再确定布局/交互。

实验室五种独立组件适合已有 HTML 渐进增强；效果层需要项目适配，research 层只提供研究线索。目录中没有可靠 source/license 时记录未知，读取被选实现的真实说明，不自动复制品牌图片、字体或第三方代码。不要导入全部案例和所有引擎。

用户明确要求精确还原时以提供的目标为准；通常原创设计沿用 Refero 研究方法并选择主要方向。Refero MCP 失败只表明该接口不可用，不能把公开风格页、原站观察或其他资源一并写成不可用。
