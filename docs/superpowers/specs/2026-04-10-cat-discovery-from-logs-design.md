# 从设备日志提取猫咪信息的设计文档

## 背景

当前 CatLink 集成通过 `get_cats` API 获取猫咪列表，但部分用户未在 App 中添加猫咪，导致该 API 返回空数组，无法创建猫咪实体。

然而，设备日志中包含猫咪活动记录，可以从中提取猫咪信息并动态创建猫咪实体。

## 目标

1. 从设备日志（如 C08 设备的 `scooperLogTop5`）中解析猫咪活动记录
2. 自动发现猫咪并创建对应的 `CatDevice` 实例
3. 为每只猫咪提供实用的 sensor 实体（体重、活动统计等）
4. 尝试通过 API 获取猫咪详细信息（如头像），同时支持用户手动配置

## 数据分析

### 设备日志结构

C08 设备的日志示例：

```json
{
  "time": "11:24",
  "event": "土豆🥔 pooped",
  "firstSection": "7.9kg",
  "secondSection": "173s",
  "errkey": "",
  "id": "899877558",
  "type": "WC",
  "unrecognized": false,
  "modifyFlag": true,
  "snFlag": 2,
  "petId": "548334"
}
```

关键字段：
- `type`: 事件类型，`"WC"` 表示如厕事件，`"RUN"` 表示设备运行（清洁等）
- `petId`: 猫咪 ID，`"0"` 表示无关联猫咪
- `event`: 事件描述，格式为 `"{猫咪名字} {动作}"`（如 "土豆🥔 pooped"、"三多🐱 peed"）
- `firstSection`: 体重信息（如 "7.9kg"）
- `secondSection`: 时长信息（如 "173s"）
- `snFlag`: 活动类型，`2` 表示拉臭臭，`0` 表示嘘嘘

### 猫咪名字提取规则

从 `event` 字段解析：
- "土豆🥔 pooped" → 名字 "土豆🥔"，动作 "pooped"
- "三多🐱 peed" → 名字 "三多🐱"，动作 "peed"

动作关键词：`pooped`, `peed`

## 架构设计

### 组件关系

```
DevicesCoordinator
    │
    ├── C08Device (设备)
    │   ├── logs[] (设备日志)
    │   └── update_logs() → 解析日志 → 发现猫咪活动
    │
    └── CatDevice (猫咪) - 从日志动态创建
        ├── sensor.cat_{name}_status
        ├── sensor.cat_{name}_weight
        ├── sensor.cat_{name}_pee_count
        ├── sensor.cat_{name}_poo_count
        └── sensor.cat_{name}_last_event
```

### 新增/修改文件

1. **`devices/mixins/cat_discovery.py`** (新建)
   - `CatDiscoveryMixin`: 从日志中解析猫咪活动的 mixin

2. **`devices/cat.py`** (修改)
   - 支持从日志创建和更新猫咪数据
   - 新增 `update_from_log()` 方法

3. **`modules/devices_coordinator.py`** (修改)
   - 在 `_async_update_data` 中处理猫咪发现逻辑
   - 从设备日志中提取猫咪信息，创建/更新 `CatDevice`

4. **`modules/account.py`** (修改)
   - 新增 `get_cat_detail(pet_id)` 方法，尝试获取猫咪详情

5. **`models/api/logs.py`** (修改)
   - 扩展 `LogEntry` 模型，添加新字段

## 详细设计

### 1. 日志解析 (CatDiscoveryMixin)

```python
class CatDiscoveryMixin:
    """Mixin for devices that can discover cats from logs."""

    def get_cat_activities_from_logs(self) -> list[dict]:
        """Extract cat activities from device logs."""
        activities = []
        for log in self.logs:
            if log.get("type") != "WC":
                continue
            pet_id = log.get("petId", "0")
            if pet_id == "0":
                continue

            activity = self._parse_cat_activity(log)
            if activity:
                activities.append(activity)
        return activities

    def _parse_cat_activity(self, log: dict) -> dict | None:
        """Parse a single log entry into cat activity data."""
        event = log.get("event", "")

        # 解析名字和动作
        name, action = self._extract_name_and_action(event)
        if not name:
            return None

        # 解析体重
        weight = self._parse_weight(log.get("firstSection", ""))

        # 解析时长
        duration = self._parse_duration(log.get("secondSection", ""))

        # 确定活动类型
        sn_flag = log.get("snFlag", 0)
        activity_type = "poo" if sn_flag == 2 else "pee"

        return {
            "pet_id": log.get("petId"),
            "name": name,
            "type": activity_type,
            "weight": weight,
            "duration": duration,
            "time": log.get("time"),
            "log_id": log.get("id"),
            "raw_event": event,
        }

    def _extract_name_and_action(self, event: str) -> tuple[str | None, str | None]:
        """Extract cat name and action from event string."""
        for action in ["pooped", "peed"]:
            if action in event:
                name = event.replace(action, "").strip()
                return name, action
        return None, None

    def _parse_weight(self, section: str) -> float | None:
        """Parse weight from firstSection (e.g., '7.9kg' -> 7.9)."""
        import re
        match = re.search(r"([\d.]+)\s*kg", section, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def _parse_duration(self, section: str) -> int | None:
        """Parse duration from secondSection (e.g., '173s' -> 173)."""
        import re
        match = re.search(r"(\d+)\s*s", section, re.IGNORECASE)
        return int(match.group(1)) if match else None
```

### 2. CatDevice 扩展

```python
class CatDevice(Device):
    # 现有代码...

    # 新增：从日志创建时使用的属性
    _discovered_name: str | None = None
    _source_device_id: str | None = None

    def update_from_activity(self, activity: dict) -> None:
        """Update cat data from a log activity."""
        # 更新名字（如果之前没有）
        if not self._discovered_name and activity.get("name"):
            self._discovered_name = activity["name"]
            self.data["petName"] = activity["name"]

        # 更新体重
        if activity.get("weight"):
            self.data["weight"] = activity["weight"]
            self._recent_weights.append({
                "weight": activity["weight"],
                "time": activity["time"],
            })

        # 更新计数
        if activity["type"] == "pee":
            self._local_pee_count += 1
        elif activity["type"] == "poo":
            self._local_poo_count += 1

        # 记录最近活动
        self._last_activity = activity

    @property
    def discovered_name(self) -> str | None:
        """Return the name discovered from logs."""
        return self._discovered_name

    @property
    def local_pee_count(self) -> int:
        """Return pee count from local tracking."""
        return self._local_pee_count

    @property
    def local_poo_count(self) -> int:
        """Return poo count from local tracking."""
        return self._local_poo_count
```

### 3. DevicesCoordinator 猫咪发现逻辑

```python
async def _async_update_data(self) -> dict:
    # 现有设备更新逻辑...

    # 从设备日志发现猫咪
    await self._discover_cats_from_device_logs()

    # 尝试获取猫咪 summary（如果 API 支持）
    await self._update_cat_summaries()

    return self.hass.data[DOMAIN][CONF_DEVICES]

async def _discover_cats_from_device_logs(self) -> None:
    """Discover cats from device logs and create/update CatDevice instances."""
    discovered_cats: dict[str, dict] = {}  # pet_id -> activity list

    # 从所有设备收集猫咪活动
    for device in self.hass.data[DOMAIN][CONF_DEVICES].values():
        if not hasattr(device, "get_cat_activities_from_logs"):
            continue
        activities = device.get_cat_activities_from_logs()
        for activity in activities:
            pet_id = activity["pet_id"]
            if pet_id not in discovered_cats:
                discovered_cats[pet_id] = {
                    "activities": [],
                    "source_device": device.id,
                }
            discovered_cats[pet_id]["activities"].append(activity)

    # 创建或更新猫咪设备
    for pet_id, data in discovered_cats.items():
        cat_device_id = f"cat-{pet_id}"

        # 按时间排序活动（最新的在前）
        activities = sorted(
            data["activities"],
            key=lambda x: x.get("time", ""),
            reverse=True
        )
        latest_activity = activities[0] if activities else None

        if not latest_activity:
            continue

        existing = self.hass.data[DOMAIN][CONF_DEVICES].get(cat_device_id)
        if existing:
            # 更新现有猫咪
            existing.update_from_activity(latest_activity)
        else:
            # 创建新猫咪
            cat_data = {
                "id": cat_device_id,
                "pet_id": pet_id,
                "petName": latest_activity.get("name"),
                "weight": latest_activity.get("weight"),
                "deviceType": "CAT",
                "mac": f"cat-{pet_id}",
                "model": "Cat",
                "deviceName": latest_activity.get("name") or f"Cat {pet_id}",
            }
            cat_device = create_device(cat_data, self, None)
            cat_device._source_device_id = data["source_device"]
            self.hass.data[DOMAIN][CONF_DEVICES][cat_device_id] = cat_device
            await cat_device.async_init()
```

### 4. 获取猫咪详情 API

尝试获取猫咪头像等信息：

```python
# account.py
async def get_cat_detail(self, pet_id: str) -> dict:
    """Get cat detail including avatar."""
    if not self.token:
        if not await self.async_login():
            return {}

    api = "token/pet/detail"  # 假设的 API 端点
    params = {"petId": pet_id}

    rsp = await self.request(api, params)
    if rsp is None:
        return {}

    return rsp.get("data") or {}
```

如果 API 不存在或返回空，则猫咪头像由用户通过 Home Assistant 的 `entity_picture` 配置。

### 5. 猫咪实体定义

```python
# cat.py
@property
def hass_sensor(self) -> dict:
    """Return cat sensors."""
    return {
        "status": {
            "icon": "mdi:cat",
            "state_attrs": self._status_attrs,
        },
        "weight": {
            "icon": "mdi:scale",
            "class": SensorDeviceClass.WEIGHT,
            "state_class": SensorStateClass.MEASUREMENT,
            "unit": UnitOfMass.KILOGRAMS,
        },
        "pee_count": {
            "icon": "mdi:water",
            "state_class": SensorStateClass.TOTAL_INCREASING,
        },
        "poo_count": {
            "icon": "mdi:emoticon-poop",
            "state_class": SensorStateClass.TOTAL_INCREASING,
        },
        "last_event": {
            "icon": "mdi:history",
            "state_attrs": self._last_event_attrs,
        },
    }

def _status_attrs(self) -> dict:
    """Return status attributes."""
    return {
        "pet_id": self.pet_id,
        "name": self.discovered_name or self.name,
        "source_device": self._source_device_id,
    }

def _last_event_attrs(self) -> dict:
    """Return last event attributes."""
    if not self._last_activity:
        return {}
    return {
        "time": self._last_activity.get("time"),
        "type": self._last_activity.get("type"),
        "weight": self._last_activity.get("weight"),
        "duration": self._last_activity.get("duration"),
    }
```

## 实现步骤

1. **扩展 LogEntry 模型**
   - 添加 `type`, `petId`, `snFlag` 等字段

2. **创建 CatDiscoveryMixin**
   - 实现日志解析逻辑
   - 提取猫咪活动信息

3. **修改 LitterDevice**
   - 继承 `CatDiscoveryMixin`

4. **扩展 CatDevice**
   - 添加从日志更新的能力
   - 实现新的 sensor 定义

5. **修改 DevicesCoordinator**
   - 添加猫咪发现逻辑
   - 处理猫咪创建和更新

6. **添加猫咪详情 API** (可选)
   - 尝试获取猫咪头像等信息

7. **添加翻译**
   - 为新的 sensor 添加翻译 key

## 边界情况处理

1. **重复活动**：通过 `log_id` 去重，避免重复计数
2. **名字变化**：使用最新的名字，但保留首次发现的名字作为标识
3. **体重异常**：过滤掉不合理的体重值（如 < 1kg 或 > 15kg）
4. **API 失败**：如果 `get_cat_summary_simple` 或 `get_cat_detail` 失败，使用本地统计数据
5. **重启后数据丢失**：今日计数在重启后重置，历史由 Home Assistant 记录

## 测试计划

1. 单元测试：日志解析函数
2. 单元测试：名字提取逻辑
3. 集成测试：从模拟日志创建猫咪设备
4. 集成测试：猫咪活动更新流程
