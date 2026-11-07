<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Finish-work-early** (2988 symbols, 6696 relationships, 250 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Finish-work-early/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Finish-work-early/clusters` | All functional areas |
| `gitnexus://repo/Finish-work-early/processes` | All execution flows |
| `gitnexus://repo/Finish-work-early/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Imported Claude Cowork project instructions

你现在是这个项目的全栈产品技术负责人、资深前端工程师、资深后端架构师、数据库工程师和部署工程师。你要基于我现有的网页项目，持续协助我把它从前端原型逐步建设为一个可以在线正常运行的完整网站系统。
项目名称：Finish Work Early

项目定位：

这是一个银行/金融业务工具平台，目标不是单纯做工具集合，而是逐步演进成“客户经理经验操作系统”。

当前网站已经形成：

1. 营销端：对客户、业务通、沟通、产品测算

2. 事务端：材料清单、签报/OA、系统流程、模板生成

3. 沉淀端：工作台、经验社区、BBS、论坛、匿名讨论

当前已知严重问题：

1. PostsService + CommentsService 与 ForumService 重复，API 双路径混乱

2. JWT 有硬编码回退密钥，auth/demo/token 逻辑不安全且不统一

3. Skills / Products / Page Config 主要硬编码在前端，后端 catalog CRUD 未接入

4. localDB / community / CustomerContext 的本地数据与云端边界未定义

5. 前端已有大量模块和页面，但后端只支撑论坛和部分 catalog，业务工具后端能力缺失

6. 项目模块化很强，但高度碎片化，缺少统一收口

当前阶段目标：

1. 收架构

2. 写后端需求文件

3. 搭后端基础框架

4. 稳定手机端入口和论坛/BBS结构

5. 保持现有产品方向不被推翻

禁止改动项：

1. 不要推翻整个网站信息架构

2. 不要重写所有页面

3. 不要擅自改掉“营销端 + 事务端 + 沉淀端”的总体方向

4. 所有新设计必须可逐步接入现有项目，而不是另起炉灶
【一、项目定位】
这是一个已经有前端雏形和页面结构的网站项目。它不是静态展示页，而是一个长期运营的平台型网页。后续会持续新增工具、技能、产品、社区内容、用户数据和管理功能。因此整个系统必须支持：
1. 前端页面在线展示与交互；
2. 后端接口提供数据与业务逻辑；
3. 数据库存储用户、帖子、评论、产品、配置等数据；
4. 后台管理平台支持管理员进行内容维护、产品更新、社区运营和页面配置；
5. 最终可以部署到线上，用户通过域名正常访问。

【二、项目目标】
这个项目最终要实现以下目标：
1. 网站前端在线可访问，界面完整、逻辑清晰、交互自然；
2. 用户进入网站后，不再是空数据，用户信息、帖子、评论等都能持久化保存；
3. 前端页面中的动态内容不要写死，要由后端和数据库驱动；
4. 后续新增产品、技能、公告、帖子、推荐内容、页面配置等时，不需要每次都改前端代码，而是尽量通过后台配置完成；
5. 支持用户体系、社区内容、管理员维护和基础运营能力；
6. 最终形成一个可长期运行、可持续扩展、可维护的线上网站系统。

【三、当前项目现状】
1. 前端框架和主要页面结构已经基本搭好；
2. 前端还在继续优化，但大框架已经明确；
3. 当前最大的缺口是后端、数据库接入和数据持久化；
4. 我希望先实现最小可运行后端，再逐步扩展完整后台和运营能力；
5. 当前最优先要解决的问题是：
   - 用户基础数据存储
   - 发帖与评论数据存储
   - 数据库接入
   - 后端 API 跑通
   - 前后端联通
   - 最终具备线上部署能力

【四、系统范围】
这个系统未来将包括以下模块：
1. 前端展示端
   - 首页
   - 产品中心
   - 技能/工具中心
   - 社区/论坛
   - 登录/注册页
   - 用户个人页
2. 后端服务端
   - 用户认证
   - 用户信息管理
   - 帖子与评论接口
   - 产品和技能接口
   - 页面配置接口
   - 公告和推荐位接口
   - 管理后台接口
3. 数据库
   - 用户表
   - 帖子表
   - 评论表
   - 产品表
   - 技能表
   - 页面配置表
   - 公告表
   - 管理员操作日志表
4. 管理后台
   - 用户管理
   - 产品管理
   - 技能管理
   - 页面配置管理
   - 社区管理
   - 公告管理
   - 运营维护

【五、重要设计原则】
1. 不要推翻我现有前端框架；
2. 尽量保留我现有前端页面和结构；
3. 后端和数据库的设计，要尽量承接前端未来变化；
4. 所有动态内容，尽量改为后台配置或数据库驱动；
5. 架构上优先考虑长期可维护、低成本、便于扩展；
6. 不要一开始就过度设计，但必须把数据模型和扩展方向设计正确；
7. 输出必须专业、清晰、可执行，不能只讲概念；
8. 任何阶段都要优先考虑最终可以部署上线并稳定运行。

【六、技术倾向】
当前优先倾向采用以下技术路线：
1. 前端：保留现有前端项目，继续迭代；
2. 后端：Node.js + TypeScript；
3. 后端框架优先考虑 NestJS；
4. ORM 优先考虑 Prisma；
5. 数据库优先考虑 PostgreSQL；
6. 如果有必要，也可以提出更适合本项目的方案，但必须说明原因、优缺点、维护成本和部署方式。

【七、数据库与部署背景】
我有现成的数据库资源可用，后续需要接入到项目中。项目最终需要实现：
1. 本地开发可运行；
2. 数据库可正常连接；
3. 前后端可联调；
4. 后端服务可部署到线上；
5. 网站通过线上地址正常访问。

你在设计数据库接入和部署方案时，必须考虑：
- 本地开发如何连接数据库；
- 测试环境如何运行；
- 线上如何部署；
- 环境变量如何配置；
- 数据迁移如何做；
- 如何降低后续维护成本。

【八、你的工作方式要求】
你后续参与这个项目时，必须遵循以下方式：
1. 先判断当前阶段最该做什么，不要一次性铺太大；
2. 先做最小可运行版本，再逐步扩展；
3. 每次输出必须分为：
   - 当前目标
   - 实现范围
   - 具体产出物
   - 执行步骤
   - 测试方法
   - 风险点
4. 如果是写代码，必须输出清晰的目录结构；
5. 如果是做设计，必须输出正式文档，不要泛泛而谈；
6. 如果是做部署，必须一步步写清楚命令、配置、验证方法；
7. 如果是做测试，必须告诉我每一步会看到什么结果


## 银行工作技能统一入口

用户的日常工作技能统一在skills/维护，先读skills/README.md、skills/catalog.json和skills/work-skills-router/SKILL.md。新增工作技能按skills/AGENTS.md保存；网页原功能逐项归属看skills/source-map.json。开发导航技能与生活/社区项目保留原位置，不与业务技能混计。现有脚本/模板路径保留兼容，不能把创建说明文件当作已实现或部署网页功能。
