# Finish Work Early · 工作技能与工具平台

**[进入工作技能区 →](skills/README.md)**

银行日常工作技能统一维护在`skills/`：授信与分析、材料与调查、票据与存单、贷后与期限、OA与文稿、客户经营、日常执行。

- 人员查阅：[分类技能目录](skills/README.md)
- Agent调用：[统一路由](skills/work-skills-router/SKILL.md)与[机器目录](skills/catalog.json)
- 已有工具对应关系：[逐项来源映射](skills/source-map.json)
- 后续新增约定：[工作区维护规则](skills/AGENTS.md)
- 其他仓库归属：[仓库导航](skills/REPOSITORIES.md)

工作技能收录表示其办理说明/依赖已经整理，具体自动化能力以各技能为准。现有网站与部署入口继续保留，开发说明如下。

---

<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/0d4a0812-1781-4e44-a2c0-705ba374879a

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## Run Full Stack Locally

前端原型已经接入一个独立的 NestJS 后端目录 [backend](./backend)。

1. 启动后端
   ```bash
   cd backend
   npm install
   cp .env.example .env
   npm run prisma:generate
   npm run start:dev
   ```
2. 配置前端 API 地址
   ```bash
   cp .env.example .env.local
   ```
   默认 `VITE_API_BASE_URL=http://localhost:3000`
3. 启动前端
   ```bash
   npm install
   npm run dev
   ```

当前已经打通的链路：
- 发现页从后端 API 读取帖子列表
- 发布页通过后端 API 写入 PostgreSQL
- 前端会自动创建一个演示用户身份，用于本地联调

## Deploy to GitHub Pages

This repo now deploys through GitHub Actions and publishes the Vite `dist/` output to GitHub Pages.

1. In GitHub repository settings, set Pages to use **GitHub Actions** as the source.
2. Push to `main`.
3. Wait for the `Deploy GitHub Pages` workflow to finish.

The production build uses the repository base path `/Finish-work-early/` and hash-based routes for Pages compatibility.
