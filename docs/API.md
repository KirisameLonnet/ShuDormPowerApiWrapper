# SHU Dorm Power API 文档

本文档详细描述了上海大学电费查询服务的 API 接口。

**Base URL**: `http://localhost:8000`

## 1. 认证机制

本 API 支持两种认证方式。凭证信息通过 HTTP 请求体传递，或默认读取服务端的环境变量。

### 方法一：默认凭证 (环境变量)
直接调用接口，无需在请求体中传递凭证参数。服务器将使用环境变量 `SHU_STUEMPNO`, `SHU_PASSWORD` 或 `SHU_HMAC_SIGN`, `SHU_HMAC_TIMESTAMP`。

### 方法二：自定义凭证 (Request Body)
可以在任意查询请求中携带以下参数来覆盖默认凭证：

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `stuempno` | string | 是(自定义时) | 学号 (e.g., "21123456") |
| `hmac_sign` | string | 否 | HMAC 签名 (优于密码) |
| `hmac_timestamp` | string | 否 | HMAC 时间戳 |

---

## 2. 接口详情

### 2.1 健康检查

检查服务是否正常运行，以及能否连接到上海大学官方服务器。

- **URL**: `/health`
- **Method**: `GET`
- **Response**:

```json
{
  "status": "UP",
  "shu_api_reachable": true,
  "config": {
    "auth_mode": "HMAC/PASSWORD",
    "has_credentials": true
  }
}
```

#### 请求示例

```bash
curl http://localhost:8000/health
```

---

### 2.2 友好查询 (推荐)

通过中文楼栋名和房间号查询电费，无需知晓内部 ID。

- **URL**: `/query/friendly`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (Body)

| 参数 | 类型 | 必须 | 说明 | 示例 |
|------|------|------|------|------|
| `building` | string | 是 | 楼栋名称 (支持中文/阿拉伯数字，忽略"号楼"后缀) | `嘉定1号楼`, `南区4号楼`, `校内W楼` |
| `room` | string | 是 | 房间号 | `102`, `101`, `424` |
| `stuempno` | string | 否 | 自定义学号 | |
| `hmac...` | string | 否 | 自定义 HMAC 凭证 | |

#### 请求示例

```bash
# 查询嘉定一号楼 102
curl -X POST "http://localhost:8000/query/friendly" \
     -H "Content-Type: application/json" \
     -d '{"building": "嘉定一号楼", "room": "102"}'
```

#### 楼栋命名规范

系统内置归一化匹配，以下格式均可被正确识别：
- `1` / `一` 互通：`嘉定1号楼` == `嘉定一号楼`
- 后缀可选：`南区4号楼` == `南区四` (虽然建议写完整以防歧义)
- 大小写不敏感：`嘉定E楼` == `嘉定e楼`

#### 响应示例 (成功)

```json
{
  "success": true,
  "location": "嘉定校区 本校区 嘉定一号楼 1层 102房间",
  "data": {
    "roomid": "102",
    "room_name": "102",
    "rest_elec_degree": 2016.88,
    "areaid": "103",
    "buildid": "12"
  }
}
```

#### 响应示例 (失败)

```json
{
  "success": false,
  "error": "未找到房间: 嘉定E楼 101",
  "hint": "请使用 /search 接口确认房间名称"
}
```

---

### 2.3 模糊搜索

不确定确切的楼栋名或房间号时，使用此接口进行搜索。

- **URL**: `/search`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (Body)

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `keyword` | string | 是 | 搜索关键词，空格分隔可进行多词匹配 |
| `limit` | integer | 否 | 返回结果数量限制 (默认 10) |

#### 请求示例

```bash
# 搜索包含 "嘉定E楼" 的房间
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"keyword": "嘉定E楼"}'
```

---

### 2.4 原始查询 (Raw ID)

如果您已经知道完整的 6 级 ID 链，可以直接使用此接口进行底层查询。

- **URL**: `/query`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### 请求参数 (Body)

需完整提供以下 6 个 ID：

| 参数 | 说明 | 示例 (嘉定) | 示例 (宝山校内) | 示例 (南区) | 示例 (新世纪) |
|------|------|------------|--------------|------------|--------------|
| `elcsysid` | 系统 ID | `"1"` | `"2"` | `"3"` | `"4"` |
| `areaid` | 校区 ID | `"103"` | `"99"` | `"101"` | `"102"` |
| `districtid` | 区域 ID | `"1"` | `"1"` | `"1"` | `"1"` |
| `buildid` | 楼栋 ID | `"12"` | `"1"` | `"9"` | `"4"` |
| `floorid` | 楼层 ID | `"79"` | `"1"` | `"61"` | `"31"` |
| `roomid` | 房间 ID | `"102"` | `"101"` | `"101"` | `"101"` |

#### 请求示例

```bash
# 查询嘉定校区某房间 (注意参数需完整)
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
           "elcsysid": "1",
           "areaid": "103", 
           "districtid": "1", 
           "buildid": "12", 
           "floorid": "79", 
           "roomid": "102"
         }'
```

#### 响应结构

与 `/query/friendly` 的 `data` 字段一致。

---

## 3. 常见错误代码

| HTTP Status | Error Field | 说明 |
|-------------|-------------|------|
| 200 | null | 成功 |
| 401 | "认证失败" | 账号密码错误或 Token 过期 |
| 404 | "未找到房间" | 楼栋或房间名不匹配 |
| 500 | "网络错误" | 无法连接到上海大学服务器 |
