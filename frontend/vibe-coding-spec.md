

---

# AI HealthCanvas Co-Pilot: 前端原型开发规范

## 1. 技术栈与视觉规范 (Tech Stack & Branding)

* **框架**: React (Next.js App Router)
* **样式**: Tailwind CSS + Shadcn UI (关键组件库)
* **动画**: Framer Motion (用于模拟 AI 思考和组件入场效果)
* **图标**: Lucide React
* **配色方案**:
* 主色 (Primary): `Teal` (参考截图中的 #0D9488 或类似青绿色)
* 背景: 纯白/浅灰 (`#F9FAFB`)
* 卡片: 带有细微阴影和 1px 描边的白色容器



## 2. 全局状态机逻辑 (State Machine)

原型需要通过一个全局状态 `appState` 来驱动 UI 变化，模拟后端流转：

1. **IDLE**: 初始状态，展示“项目初始界面”。
2. **THINKING**: 用户点击发送，左侧进入“AI 思考”动画。
3. **GENERATING**: 脚本与分镜生成中，右侧 Workbench 实时渲染。
4. **EDITING**: 生成完毕，用户可交互修改。
5. **RENDERING**: 点击生成视频后的渲染等待态。
6. **COMPLETED**: 最终页面，展示视频播放与时间轴。

## 3. 页面详细需求 (Page Requirements)

### 页面 A：项目初始界面 (Landing/Project Home)

* **左侧侧边栏 (AI Assistant)**:
* 常驻输入框，底部带有“风格预设”快捷标签（动画、卡通人物播报、实拍素材）。


* **右侧主区 (Workbench)**:
* 上方 Tab: “推荐模板”、“最近项目”。
* 项目卡片: 展示封面图、时长标签（如 60s）、标题、视频类型。

![initial](D:\Works\Prism\initial.png)

### 页面 B：脚本交互页面 (AI Generating/Editor)

* **左侧任务进度 (Task Progress)**:
* 实现一个 **Checklist 动画组件**。包含：智能脚本构思、分镜绘制中（带进度条 45%）、最终视频渲染。


* **右侧编辑器 (Workspace Active)**:
* **Script 区域**: 像代码编辑器一样展示脚本。每一行包含时间戳（如 00:00）、场景描述、旁白内容。
* **Visual Storyboard**: 响应式网格展示分镜草图。加载中的卡片应有 Skeleton 骨架屏或 Loading 动画。

![script_generate](D:\Works\Prism\script_generate.png)

### 页面 C：视频生成页面 (Video Preview & Timeline)

* **核心展示**: 居中的大屏视频播放器（Mock 一个视频文件）。
* **时间轴 (Timeline)**:
* 双轨道：Video 轨道与 Audio 轨道。
* Audio 轨道需要展示 Mock 的波形图 (Waveform)。
* 支持播放进度条随视频同步。


* **左侧反馈区**: 视频信息概览（分辨率、时长）+ “对话式微调”输入框。

![video_generate](D:\Works\Prism\video_generate.png)

## 4. 交互式 Mock 逻辑 (Vibe Protocol)

为了在没有后端的情况下“搓出”生命力，请 AI 实现以下逻辑：

* **流式模拟**: 当状态变为 `GENERATING` 时，利用 `setInterval` 让脚本内容逐行显示，而不是直接弹出全屏。
* **双向联动**: 点击右侧的某个“分镜卡片”，左侧 AI 对话框应自动发送一条消息：“我选中了场景 2，请问需要调整什么？”
* **本地模拟**: 用户导入素材功能仅做 UI 展示，点击上传后，在 `visual-storyboard` 中新增一张带有“用户上传”标签的占位图。

## 5. 关键提示词技巧 (Prompt Hints)

> "请严格遵守 Figma 截图中的间距（Padding/Margin）和圆角规范。AI Assistant 的对话气泡需要有平滑的入场动画。所有的 Button 在点击时应有明显的 Scale 缩放反馈。"

---
