# 上海大学宿舍电费查询 API

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)

## 项目简介

本项目逆向分析并封装了上海大学电费查询 API，提供更加人性化的API查询服务。服务端持有合法学号密码或 HMAC 签名用户即可通过 API 直接获取任何宿舍的电费信息。

## 特性

- ✅ **友好查询接口** - 使用中文楼栋名+房间号查询，无需记住 ID
- ✅ **Web API 服务** - 基于 FastAPI 的 RESTful 接口
- ✅ **凭证热更新** - 每次查询实时读取环境变量，支持运行时切换
- ✅ **双认证方式** - 支持账号密码和 HMAC 签名两种方式

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 设置环境变量

```bash
# 方式一：账号密码认证
export SHU_STUEMPNO=你的学号
export SHU_CUSTNAME=你的姓名
export SHU_PASSWORD=你的校园卡密码(明文) 身份证号后六位或者666666 除非你修改过

# 方式二：HMAC签名认证（优先）
export SHU_STUEMPNO=你的学号
export SHU_HMAC_SIGN=你的HMAC签名
export SHU_HMAC_TIMESTAMP=时间戳
```

### 3. 启动服务

```bash
uvicorn api.main:app --reload
```

---

## API 接口

详细的 API 接口定义、请求参数及示例请参考：
📖 **[API 完整文档](./docs/API.md)**

### 主要功能概览
- **[友好查询](./docs/API.md#22-友好查询-推荐)**: 支持中文楼栋名直接查询 (e.g., `嘉定一号楼 102`)
- **[模糊搜索](./docs/API.md#23-模糊搜索)**: 查找不确定的楼栋或房间
- **[原始查询](./docs/API.md#24-原始查询-raw-id)**: 支持 6 级 ID 精确查询 (兼容四个校区系统)

---

## 项目结构

```
ShuDormPowerApiWrapper/
├── shu_power/           # 核心库
│   ├── client.py        # API 客户端
│   ├── auth.py          # 认证模块
│   ├── crypto.py        # SM4 加密
│   ├── dorm_lookup.py   # 🆕 房间查找服务 (中文名 -> ID链)
│   ├── models.py        # 数据模型
│   └── exceptions.py    # 异常定义
├── api/                 # Web API (FastAPI)
│   ├── main.py          # 服务入口
│   └── schemas.py       # Pydantic 模型
├── dorm-data.json       # 🆕 宿舍 ID 映射全集
└── ShuIDCard-LoginInfo/ # 原始逆向分析文档
```

## 参考文档

- [电费查询元数据](./docs/dorm-metadata.md) - API 参数结构说明
- [ShuIDCard-LoginInfo](./ShuIDCard-LoginInfo/README.md) - 原始逆向分析

## 免责声明

本项目仅供技术研究和教育交流使用。使用本项目产生的任何后果由用户自行承担。
