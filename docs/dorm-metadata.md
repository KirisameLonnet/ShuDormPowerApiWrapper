# 电费查询 API 元数据

## 接口信息

- **URL**: `http://10.10.10.147/openservice/miniprogram/queryroominfo`
- **方法**: `POST`
- **认证**: `sw-authorization: Bearer <token>`

---

## 级联映射结构

宿舍信息采用 **6 级级联体系**，每一级必须持有父级 ID 才能获取下一级数据：

```
系统 (System) → 校区 (Area) → 区域 (District) → 楼栋 (Building) → 楼层 (Floor) → 房间 (Room)
```

### 各级参数详解

| 层级 | 参数名 | 获取接口 | 说明 |
|------|--------|----------|------|
| **1. 系统** | `elcsysid` | 固定值 | `1`=嘉定, `2`=校内, `3`=南区, `4`=新世纪 |
| **2. 校区** | `areaid` | `queryarea` | 通过系统ID获取可用校区列表 |
| **3. 区域** | `districtid` | `querydistricts` | 校区内的分区 |
| **4. 楼栋** | `buildid` | `querybuilds` | 注意：嘉定楼栋 ID 12~22 |
| **5. 楼层** | `floorid` | `queryfloors` | 根据楼栋动态生成的自增 ID |
| **6. 房间** | `roomid` | `queryrooms` | 数据库全局唯一自增 ID |

> [!IMPORTANT]
> **ID 唯一性**: `floorid` 和 `roomid` 在数据库中是**全局唯一**的自增数字。例如，嘉定一号楼一层的 `floorid` 是 `79`，而非 `1`。

---

## 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `elcsysid` | string | ✅ | 系统ID | `"1"` |
| `areaid` | string | ✅ | 校区ID | `"103"` |
| `districtid` | string | ✅ | 区域ID | `"1"` |
| `buildid` | string | ✅ | 楼栋ID | `"12"` |
| `floorid` | string | ✅ | 楼层ID | `"79"` |
| `roomid` | string | ✅ | 房间ID | `"102"` |

---

## 系统ID对照表

| 系统名称 | elcsysid |
|----------|----------|
| 嘉定校区 | 1 |
| 宝山校内 | 2 |
| 宝山南区 | 3 |
| 宝山新世纪 | 4 |

---

## 请求示例

### 1. 嘉定校区 (嘉定一号楼 102)

```bash
curl -s -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
           "elcsysid": "1",
           "area_id": "103",
           "district_id": "1",
           "buildid": "12",
           "floorid": "79",
           "roomid": "102"
         }'
```

### 2. 宝山校内 (校内六号楼 101)

```bash
curl -s -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
           "elcsysid": "2",
           "area_id": "99",
           "district_id": "1",
           "buildid": "1",
           "floorid": "1",
           "roomid": "101"
         }'
```

### 3. 宝山南区 (南区四号楼 101)

```bash
curl -s -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
           "elcsysid": "3",
           "area_id": "101",
           "district_id": "1",
           "buildid": "9",
           "floorid": "61",
           "roomid": "101"
         }'
```

### 4. 宝山新世纪 (新世纪9号楼 101)

```bash
curl -s -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
           "elcsysid": "4",
           "area_id": "102",
           "district_id": "1",
           "buildid": "4",
           "floorid": "31",
           "roomid": "101"
         }'
```

---

## 友好查询示例 (服务端自动补全 ID)

```bash
# 例子：宝山南区四号楼 101
curl -X POST "http://localhost:8000/query/friendly" \
     -H "Content-Type: application/json" \
     -d '{"building": "南区四号楼", "room": "101"}'
```

---

## 返回结构

```json
{
  "retcode": "0",
  "retmsg": "成功",
  "data": {
    "retcode": 0,
    "retmsg": "success",
    "elcsysid": 1,
    "areaId": "103",
    "buiId": "12",
    "roomId": "102",
    "roomName": "102房间",
    "restElecDegree": 53.92,
    "rest": 0.0,
    "degreelist": null
  }
}
```

### 关键字段说明

| 字段 | 说明 |
|------|------|
| `restElecDegree` | 剩余电量（度） |
| `roomName` | 房间名称 |
| `areaId` | 校区ID |
| `buiId` | 楼栋ID |
| `roomId` | 房间ID |

---

## ID 查找流程

1. **准备 Token**: 确保 `sw-authorization: Bearer <TOKEN>` 有效
2. **确定 ID 链**: 从 `dorm-data.json` 中按路径提取：
   - 系统 → 校区 → 区域 → 楼栋 → 楼层 → 房间
3. **构造请求**: 使用完整的 6 个 ID 参数发起 POST

```
使用 scripts/search_dorm.py 可快速查找房间 ID：
python scripts/search_dorm.py "嘉定一号楼 102"
```

---

## 安全说明

> [!WARNING]
> **越权访问风险**: 经测试，只要 Token 有效，可通过修改 `roomid` 查询任意房间电量。学校后端未强制校验学号与房间绑定关系。
