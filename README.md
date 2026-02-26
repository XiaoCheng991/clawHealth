# clawHealth

个人健康数据管理系统 - Apple Watch 数据接入、食物分析、健康仪表盘

## 功能概览

| 模块 | 功能 |
|------|------|
| **健康仪表盘** | 汇总关键指标（步数、心率、卡路里、睡眠、血氧），并展示 7/14/30 天趋势图 |
| **Apple Watch 数据接入** | REST API 接收手表健康数据（批量或单条），表格展示最近记录 |
| **食物分析** | 按日记录饮食、三大营养素环形图、近 7 天热量趋势柱状图 |
| **目标设置** | 自定义每日步数、热量摄入/消耗、睡眠时长、运动时间目标 |

## 技术栈

- **后端**: Python · Flask · Flask-SQLAlchemy · SQLite
- **前端**: Bootstrap 5 · Bootstrap Icons · Chart.js
- **测试**: pytest

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用（首次运行自动建库）
python app.py

# 3. 浏览器访问
open http://127.0.0.1:5000
```

## API 文档

### 健康数据（Apple Watch）

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/health/sync` | 同步健康记录（单条或数组） |
| GET  | `/api/health/data` | 获取历史记录（支持 start/end/limit 参数） |
| GET  | `/api/health/summary` | 获取聚合摘要（?days=7） |
| GET  | `/api/health/trend` | 获取逐日趋势（?days=7） |

**示例 - 同步一条 Apple Watch 记录：**

```bash
curl -X POST http://127.0.0.1:5000/api/health/sync \
  -H "Content-Type: application/json" \
  -d '{
    "recorded_at": "2026-02-26T08:00:00",
    "steps": 9500,
    "heart_rate": 71,
    "calories_burned": 480,
    "active_minutes": 42,
    "sleep_hours": 7.9,
    "blood_oxygen": 98,
    "workout_type": "跑步",
    "workout_duration": 30
  }'
```

### 食物分析

| 方法 | 路由 | 说明 |
|------|------|------|
| GET  | `/api/food/entries` | 获取指定日期饮食记录（?date=YYYY-MM-DD） |
| POST | `/api/food/entries` | 添加饮食记录 |
| DELETE | `/api/food/entries/<id>` | 删除饮食记录 |
| GET  | `/api/food/analysis` | 获取每日营养分析 |
| GET  | `/api/food/trend` | 获取逐日热量摄入趋势 |

### 目标设置

| 方法 | 路由 | 说明 |
|------|------|------|
| GET  | `/api/goals` | 获取当前目标 |
| PUT  | `/api/goals` | 更新目标 |

## 运行测试

```bash
python -m pytest tests/test_app.py -v
```

