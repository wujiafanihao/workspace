# 设计

## OpenAPI 元数据

- FastAPI `title`/`description`/`version`/`openapi_tags` 用中文
- 路由：`summary` + `description`；必要时 `responses` 示例
- Pydantic：`Field(description=...)` + 模型 `json_schema_extra` 示例

## 导出

- `create_app()` 后调用 `app.openapi()`，不依赖 lifespan/Redis
- 脚本写入 `backend/data/openapi.json`
- `.gitignore`：`data/*` 忽略，白名单 `!data/openapi.json`

## 测试

- 不启 Redis：直接 `create_app().openapi()`，断言 paths 与中文 title
