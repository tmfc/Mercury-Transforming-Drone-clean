# Mantine 与 Vite 前端模板

## 功能

该模板包含以下开发配置：

- [PostCSS](https://postcss.org/)，配合 [mantine-postcss-preset](https://mantine.dev/styles/postcss-preset)。
- [TypeScript](https://www.typescriptlang.org/)。
- [Storybook](https://storybook.js.org/) 组件开发环境。
- [Vitest](https://vitest.dev/)，配合 [React Testing Library](https://testing-library.com/docs/react-testing-library/intro)。
- ESLint，使用 [eslint-config-mantine](https://github.com/mantinedev/eslint-config-mantine)。

## npm 脚本

脚本标识保持英文不变；以下只翻译其用途，不更改实际命令。

### 开发与构建

- `dev`：启动开发服务器。
- `build`：构建应用的生产版本。
- `preview`：在本地预览生产构建。

### 测试与检查

- `typecheck`：检查 TypeScript 类型。
- `lint`：运行 ESLint。
- `prettier:check`：使用 Prettier 检查文件格式。
- `vitest`：运行 Vitest 测试。
- `vitest:watch`：以监听模式运行 Vitest。
- `test`：运行 `vitest`、`prettier:check`、`lint` 和 `typecheck` 脚本。

### 其他脚本

- `storybook`：启动 Storybook 开发服务器。
- `storybook:build`：构建 Storybook 生产文件，输出至 `storybook-static`。
- `prettier:write`：使用 Prettier 格式化所有文件。
