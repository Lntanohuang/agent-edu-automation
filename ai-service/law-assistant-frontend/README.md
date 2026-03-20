# 法律助手前端（Mock 版）

## 技术栈
- Vue 3 + Vite + TypeScript
- Element Plus
- Pinia + Vue Router

## 已实现
- 登录与角色切换（合伙人 / 律师 / 实习生）
- 主布局（侧边栏 + 顶栏 + 面包屑 + 亮暗模式）
- 三个核心页面（案件工作台、资料库、检索问答）
- 路由级与按钮级角色权限
- 本地 mock 数据流（无需后端可联调页面）

## 启动
```bash
npm install
npm run dev
```

## 说明
- 当前环境网络受限时可能无法安装依赖，建议在可访问 `registry.npmjs.org` 的网络下执行安装。
- 后续接入后端时可将 `src/services/mockGateway.ts` 替换为真实 API 请求。
