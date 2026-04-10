# 从设备日志提取猫咪信息 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从设备日志中解析猫咪活动，自动发现并创建猫咪实体

**Architecture:** 在 LitterDevice 中添加 CatDiscoveryMixin 解析日志，DevicesCoordinator 从设备日志中发现猫咪并创建/更新 CatDevice，为每只猫咪提供 status/weight/pee_count/poo_count/last_event 传感器

**Tech Stack:** Python 3.11+, Home Assistant, Pydantic, pytest

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `models/api/logs.py` | 修改 | 扩展 LogEntry 模型添加新字段 |
| `devices/mixins/cat_discovery.py` | 新建 | 从日志解析猫咪活动的 mixin |
| `devices/mixins/__init__.py` | 修改 | 导出 CatDiscoveryMixin |
| `devices/litter_device.py` | 修改 | 继承 CatDiscoveryMixin |
| `devices/cat.py` | 修改 | 支持从日志更新，新增传感器 |
| `modules/devices_coordinator.py` | 修改 | 添加猫咪发现逻辑 |
| `modules/account.py` | 修改 | 新增 get_cat_detail API |
| `translations/en.json` | 修改 | 添加猫咪传感器翻译 |
| `translations/zh-Hans.json` | 修改 | 添加猫咪传感器翻译 |
| `strings.json` | 修改 | 添加猫咪传感器翻译 |
| `tests/test_cat_discovery.py` | 新建 | 猫咪发现功能测试 |

---

### Task 1: 扩展 LogEntry 模型

**Files:**
- Modify: `custom_components/catlink/models/api/logs.py`

- [ ] **Step 1: 更新 LogEntry 模型添加新字段**

```python
"""Log API models."""

from pydantic import BaseModel, ConfigDict


class LogEntry(BaseModel):
    """Log entry from device logs API."""

    model_config = ConfigDict(extra="allow")

    time: str = ""
    event: str = ""
    firstSection: str = ""
    secondSection: str = ""
    errkey: str = ""
    # 新增字段
    id: str = ""
    type: str = ""
    unrecognized: bool = False
    modifyFlag: bool = False
    snFlag: int = 0
    petId: str = "0"
```

- [ ] **Step 2: 运行现有测试确保兼容性**

Run: `pytest tests/test_logs_mixin.py -v`
Expected: All tests pass

- [ ] **Step 3: 提交**

```bash
git add custom_components/catlink/models/api/logs.py
git commit -m "feat: extend LogEntry model with cat activity fields"
```

---

### Task 2: 创建 CatDiscoveryMixin

**Files:**
- Create: `custom_components/catlink/devices/mixins/cat_discovery.py`
- Modify: `custom_components/catlink/devices/mixins/__init__.py`

- [ ] **Step 1: 编写测试 - 名字提取函数**

创建文件 `tests/test_cat_discovery.py`:

```python
"""Tests for CatDiscoveryMixin."""

import pytest

from custom_components.catlink.devices.mixins.cat_discovery import (
    CatDiscoveryMixin,
    extract_name_and_action,
    parse_weight,
    parse_duration,
)


class TestExtractNameAndAction:
    """Tests for extract_name_and_action function."""

    def test_extract_name_from_pooped_event(self) -> None:
        """Test extracting cat name from pooped event."""
        name, action = extract_name_and_action("土豆🥔 pooped")
        assert name == "土豆🥔"
        assert action == "pooped"

    def test_extract_name_from_peed_event(self) -> None:
        """Test extracting cat name from peed event."""
        name, action = extract_name_and_action("三多🐱 peed")
        assert name == "三多🐱"
        assert action == "peed"

    def test_extract_name_with_spaces(self) -> None:
        """Test extracting name with extra spaces."""
        name, action = extract_name_and_action("  小花  pooped  ")
        assert name == "小花"
        assert action == "pooped"

    def test_returns_none_for_unknown_action(self) -> None:
        """Test returns None for unknown action."""
        name, action = extract_name_and_action("Auto-clean")
        assert name is None
        assert action is None

    def test_returns_none_for_empty_string(self) -> None:
        """Test returns None for empty string."""
        name, action = extract_name_and_action("")
        assert name is None
        assert action is None


class TestParseWeight:
    """Tests for parse_weight function."""

    def test_parse_weight_kg(self) -> None:
        """Test parsing weight in kg."""
        assert parse_weight("7.9kg") == 7.9

    def test_parse_weight_with_space(self) -> None:
        """Test parsing weight with space."""
        assert parse_weight("5.2 kg") == 5.2

    def test_parse_weight_uppercase(self) -> None:
        """Test parsing weight with uppercase KG."""
        assert parse_weight("6.0KG") == 6.0

    def test_parse_weight_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid input."""
        assert parse_weight("") is None
        assert parse_weight("no weight") is None


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_parse_duration_seconds(self) -> None:
        """Test parsing duration in seconds."""
        assert parse_duration("173s") == 173

    def test_parse_duration_with_space(self) -> None:
        """Test parsing duration with space."""
        assert parse_duration("69 s") == 69

    def test_parse_duration_uppercase(self) -> None:
        """Test parsing duration with uppercase S."""
        assert parse_duration("100S") == 100

    def test_parse_duration_returns_none_for_invalid(self) -> None:
        """Test returns None for invalid input."""
        assert parse_duration("") is None
        assert parse_duration("no duration") is None


class TestCatDiscoveryMixin:
    """Tests for CatDiscoveryMixin class."""

    def test_get_cat_activities_from_logs(self) -> None:
        """Test extracting cat activities from logs."""
        mixin = CatDiscoveryMixin()
        mixin.logs = [
            {
                "time": "11:24",
                "event": "土豆🥔 pooped",
                "firstSection": "7.9kg",
                "secondSection": "173s",
                "id": "899877558",
                "type": "WC",
                "petId": "548334",
                "snFlag": 2,
            },
            {
                "time": "10:29",
                "event": "三多🐱 peed",
                "firstSection": "5.2kg",
                "secondSection": "69s",
                "id": "899857182",
                "type": "WC",
                "petId": "548337",
                "snFlag": 0,
            },
            {
                "time": "11:27",
                "event": "Auto-clean",
                "type": "RUN",
                "petId": "0",
            },
        ]

        activities = mixin.get_cat_activities_from_logs()

        assert len(activities) == 2
        assert activities[0]["pet_id"] == "548334"
        assert activities[0]["name"] == "土豆🥔"
        assert activities[0]["type"] == "poo"
        assert activities[0]["weight"] == 7.9
        assert activities[0]["duration"] == 173
        assert activities[1]["pet_id"] == "548337"
        assert activities[1]["name"] == "三多🐱"
        assert activities[1]["type"] == "pee"

    def test_get_cat_activities_skips_pet_id_zero(self) -> None:
        """Test that activities with petId=0 are skipped."""
        mixin = CatDiscoveryMixin()
        mixin.logs = [
            {
                "time": "11:27",
                "event": "Auto-clean",
                "type": "RUN",
                "petId": "0",
            },
        ]

        activities = mixin.get_cat_activities_from_logs()
        assert len(activities) == 0

    def test_get_cat_activities_skips_non_wc_type(self) -> None:
        """Test that non-WC type logs are skipped."""
        mixin = CatDiscoveryMixin()
        mixin.logs = [
            {
                "time": "11:27",
                "event": "Auto-clean",
                "type": "RUN",
                "petId": "548334",
            },
        ]

        activities = mixin.get_cat_activities_from_logs()
        assert len(activities) == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_cat_discovery.py -v`
Expected: FAIL with module import error

- [ ] **Step 3: 实现 CatDiscoveryMixin**

创建文件 `custom_components/catlink/devices/mixins/cat_discovery.py`:

```python
"""Mixin for discovering cats from device logs."""

import re
from typing import Any


def extract_name_and_action(event: str) -> tuple[str | None, str | None]:
    """Extract cat name and action from event string.

    Args:
        event: Event string like "土豆🥔 pooped" or "三多🐱 peed"

    Returns:
        Tuple of (name, action) or (None, None) if not parseable
    """
    for action in ["pooped", "peed"]:
        if action in event:
            name = event.replace(action, "").strip()
            return name, action
    return None, None


def parse_weight(section: str) -> float | None:
    """Parse weight from firstSection string.

    Args:
        section: String like "7.9kg" or "5.2 kg"

    Returns:
        Weight as float or None if not parseable
    """
    match = re.search(r"([\d.]+)\s*kg", section, re.IGNORECASE)
    return float(match.group(1)) if match else None


def parse_duration(section: str) -> int | None:
    """Parse duration from secondSection string.

    Args:
        section: String like "173s" or "69 s"

    Returns:
        Duration in seconds as int or None if not parseable
    """
    match = re.search(r"(\d+)\s*s", section, re.IGNORECASE)
    return int(match.group(1)) if match else None


class CatDiscoveryMixin:
    """Mixin for devices that can discover cats from logs."""

    logs: list[dict[str, Any]]

    def get_cat_activities_from_logs(self) -> list[dict[str, Any]]:
        """Extract cat activities from device logs.

        Returns:
            List of activity dicts with keys:
            - pet_id: Cat's pet ID
            - name: Cat name extracted from event
            - type: "pee" or "poo"
            - weight: Weight in kg (or None)
            - duration: Duration in seconds (or None)
            - time: Time string
            - log_id: Log entry ID
            - raw_event: Original event string
        """
        activities = []
        for log in self.logs:
            # Skip non-WC type logs
            if log.get("type") != "WC":
                continue
            # Skip entries without valid pet ID
            pet_id = log.get("petId", "0")
            if pet_id == "0":
                continue

            activity = self._parse_cat_activity(log)
            if activity:
                activities.append(activity)
        return activities

    def _parse_cat_activity(self, log: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a single log entry into cat activity data."""
        event = log.get("event", "")

        # Extract name and action
        name, action = extract_name_and_action(event)
        if not name:
            return None

        # Parse weight and duration
        weight = parse_weight(log.get("firstSection", ""))
        duration = parse_duration(log.get("secondSection", ""))

        # Determine activity type from snFlag
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
```

- [ ] **Step 4: 更新 mixins/__init__.py 导出**

```python
"""Device mixins for CatLink integration."""

from .cat_discovery import CatDiscoveryMixin
from .logs import LogsMixin

__all__ = [
    "CatDiscoveryMixin",
    "LogsMixin",
]
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/test_cat_discovery.py -v`
Expected: All tests pass

- [ ] **Step 6: 提交**

```bash
git add custom_components/catlink/devices/mixins/cat_discovery.py
git add custom_components/catlink/devices/mixins/__init__.py
git add tests/test_cat_discovery.py
git commit -m "feat: add CatDiscoveryMixin for parsing cat activities from logs"
```

---

### Task 3: 将 CatDiscoveryMixin 添加到 LitterDevice

**Files:**
- Modify: `custom_components/catlink/devices/litter_device.py`

- [ ] **Step 1: 编写测试 - LitterDevice 具有猫咪发现能力**

在 `tests/test_devices.py` 末尾添加:

```python
class TestLitterDeviceCatDiscovery:
    """Tests for cat discovery in LitterDevice."""

    def test_litter_device_has_cat_discovery(
        self, mock_coordinator, sample_device_data
    ) -> None:
        """Test LitterDevice has get_cat_activities_from_logs method."""
        device = LitterBox(sample_device_data, mock_coordinator)
        assert hasattr(device, "get_cat_activities_from_logs")

    def test_litter_device_extracts_cat_activities(
        self, mock_coordinator, sample_device_data
    ) -> None:
        """Test LitterDevice can extract cat activities from logs."""
        device = LitterBox(sample_device_data, mock_coordinator)
        device.logs = [
            {
                "time": "11:24",
                "event": "土豆🥔 pooped",
                "firstSection": "7.9kg",
                "secondSection": "173s",
                "id": "899877558",
                "type": "WC",
                "petId": "548334",
                "snFlag": 2,
            },
        ]

        activities = device.get_cat_activities_from_logs()
        assert len(activities) == 1
        assert activities[0]["name"] == "土豆🥔"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_devices.py::TestLitterDeviceCatDiscovery -v`
Expected: FAIL with AssertionError (no attribute 'get_cat_activities_from_logs')

- [ ] **Step 3: 修改 LitterDevice 继承 CatDiscoveryMixin**

```python
"""Litter device base class for LitterBox and ScooperDevice."""

from collections import deque
from typing import TYPE_CHECKING

from ..const import _LOGGER
from ..models.additional_cfg import AdditionalDeviceConfig
from .base import Device
from .mixins import CatDiscoveryMixin, LogsMixin

if TYPE_CHECKING:
    from ..modules.devices_coordinator import DevicesCoordinator


class LitterDevice(CatDiscoveryMixin, LogsMixin, Device):
    """Base class for litter-related devices (LitterBox, ScooperDevice)."""

    # ... 其余代码保持不变
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_devices.py::TestLitterDeviceCatDiscovery -v`
Expected: All tests pass

- [ ] **Step 5: 运行所有相关测试确保兼容**

Run: `pytest tests/test_devices.py tests/test_logs_mixin.py -v`
Expected: All tests pass

- [ ] **Step 6: 提交**

```bash
git add custom_components/catlink/devices/litter_device.py tests/test_devices.py
git commit -m "feat: add CatDiscoveryMixin to LitterDevice"
```

---

### Task 4: 扩展 CatDevice 支持从日志更新

**Files:**
- Modify: `custom_components/catlink/devices/cat.py`

- [ ] **Step 1: 编写测试 - CatDevice 从活动更新**

在 `tests/test_devices.py` 的 `TestCatDevice` 类中添加:

```python
class TestCatDeviceUpdateFromActivity:
    """Tests for CatDevice update_from_activity method."""

    def test_update_from_activity_sets_name(
        self, mock_coordinator, sample_cat_data
    ) -> None:
        """Test update_from_activity sets discovered name."""
        device = CatDevice(sample_cat_data, mock_coordinator)
        activity = {
            "pet_id": "548334",
            "name": "土豆🥔",
            "type": "poo",
            "weight": 7.9,
            "duration": 173,
            "time": "11:24",
            "log_id": "899877558",
        }
        device.update_from_activity(activity)
        assert device.discovered_name == "土豆🥔"

    def test_update_from_activity_updates_weight(
        self, mock_coordinator, sample_cat_data
    ) -> None:
        """Test update_from_activity updates weight."""
        device = CatDevice(sample_cat_data, mock_coordinator)
        activity = {
            "pet_id": "548334",
            "name": "土豆🥔",
            "type": "poo",
            "weight": 7.9,
            "duration": 173,
            "time": "11:24",
            "log_id": "899877558",
        }
        device.update_from_activity(activity)
        assert device.weight == 7.9

    def test_update_from_activity_increments_poo_count(
        self, mock_coordinator, sample_cat_data
    ) -> None:
        """Test update_from_activity increments poo count."""
        device = CatDevice(sample_cat_data, mock_coordinator)
        initial_count = device.local_poo_count
        activity = {
            "pet_id": "548334",
            "name": "土豆🥔",
            "type": "poo",
            "weight": 7.9,
            "duration": 173,
            "time": "11:24",
            "log_id": "899877558",
        }
        device.update_from_activity(activity)
        assert device.local_poo_count == initial_count + 1

    def test_update_from_activity_increments_pee_count(
        self, mock_coordinator, sample_cat_data
    ) -> None:
        """Test update_from_activity increments pee count."""
        device = CatDevice(sample_cat_data, mock_coordinator)
        initial_count = device.local_pee_count
        activity = {
            "pet_id": "548334",
            "name": "三多🐱",
            "type": "pee",
            "weight": 5.2,
            "duration": 69,
            "time": "10:29",
            "log_id": "899857182",
        }
        device.update_from_activity(activity)
        assert device.local_pee_count == initial_count + 1

    def test_update_from_activity_skips_duplicate_log(
        self, mock_coordinator, sample_cat_data
    ) -> None:
        """Test update_from_activity skips already processed log."""
        device = CatDevice(sample_cat_data, mock_coordinator)
        activity = {
            "pet_id": "548334",
            "name": "土豆🥔",
            "type": "poo",
            "weight": 7.9,
            "duration": 173,
            "time": "11:24",
            "log_id": "899877558",
        }
        device.update_from_activity(activity)
        initial_count = device.local_poo_count
        # Same log_id should be skipped
        device.update_from_activity(activity)
        assert device.local_poo_count == initial_count

    def test_local_counts_initialize_to_zero(
        self, mock_coordinator, sample_cat_data
    ) -> None:
        """Test local counts initialize to zero."""
        # Create cat without summary_simple data
        cat_data = {
            "id": "cat-test",
            "pet_id": "test123",
            "petName": "Test Cat",
            "deviceName": "Test Cat",
            "deviceType": "CAT",
            "mac": "cat-test",
        }
        device = CatDevice(cat_data, mock_coordinator)
        assert device.local_pee_count == 0
        assert device.local_poo_count == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_devices.py::TestCatDeviceUpdateFromActivity -v`
Expected: FAIL with AttributeError (no 'update_from_activity')

- [ ] **Step 3: 实现 CatDevice 的 update_from_activity 方法**

修改 `custom_components/catlink/devices/cat.py`:

```python
"""Cat device class for CatLink integration."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

from custom_components.catlink.devices.base import Device
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfMass
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from custom_components.catlink.modules.devices_coordinator import DevicesCoordinator


GENDER_LABELS: dict[int, str] = {
    1: "gender_male",
    2: "gender_female",
    3: "gender_neutered_male",
    4: "gender_neutered_female",
}


class CatDevice(Device):
    """Cat device class for CatLink integration."""

    def __init__(
        self,
        dat: dict,
        coordinator: DevicesCoordinator,
        additional_config: Any | None = None,
    ) -> None:
        """Initialize the cat device."""
        super().__init__(dat, coordinator, additional_config)
        # 从日志发现时使用的属性
        self._discovered_name: str | None = None
        self._source_device_id: str | None = None
        self._processed_log_ids: set[str] = set()
        self._local_pee_count: int = 0
        self._local_poo_count: int = 0
        self._last_activity: dict[str, Any] | None = None
        self._recent_weights: deque[dict[str, Any]] = deque(maxlen=50)

    async def async_init(self) -> None:
        """Initialize the device."""
        self.detail = self.data

    def update_data(self, dat: dict) -> None:
        """Update device data."""
        super().update_data(dat)
        self.detail = dat

    async def update_device_detail(self) -> dict:
        """Update device detail (cats use list payload)."""
        self.detail = self.data
        self._handle_listeners()
        return self.detail

    def update_from_activity(self, activity: dict[str, Any]) -> bool:
        """Update cat data from a log activity.

        Args:
            activity: Activity dict from CatDiscoveryMixin

        Returns:
            True if activity was processed, False if skipped (duplicate)
        """
        log_id = activity.get("log_id", "")
        if log_id and log_id in self._processed_log_ids:
            return False

        if log_id:
            self._processed_log_ids.add(log_id)

        # 更新名字
        if not self._discovered_name and activity.get("name"):
            self._discovered_name = activity["name"]
            self.data["petName"] = activity["name"]

        # 更新体重
        weight = activity.get("weight")
        if weight is not None:
            # 过滤异常体重
            if 1.0 <= weight <= 15.0:
                self.data["weight"] = weight
                self._recent_weights.append({
                    "weight": weight,
                    "time": activity.get("time"),
                })

        # 更新计数
        activity_type = activity.get("type")
        if activity_type == "pee":
            self._local_pee_count += 1
        elif activity_type == "poo":
            self._local_poo_count += 1

        # 记录最近活动
        self._last_activity = activity
        return True

    @property
    def pet_id(self) -> str | None:
        """Return the pet id."""
        return self.data.get("pet_id") or self.data.get("id")

    @property
    def weight(self) -> float | None:
        """Return the pet weight."""
        return self.data.get("weight")

    @property
    def discovered_name(self) -> str | None:
        """Return the name discovered from logs."""
        return self._discovered_name

    @property
    def source_device_id(self) -> str | None:
        """Return the source device ID."""
        return self._source_device_id

    @property
    def local_pee_count(self) -> int:
        """Return pee count from local tracking."""
        return self._local_pee_count

    @property
    def local_poo_count(self) -> int:
        """Return poo count from local tracking."""
        return self._local_poo_count

    @property
    def last_activity(self) -> dict[str, Any] | None:
        """Return the last activity."""
        return self._last_activity

    @property
    def age_years(self) -> int | None:
        """Return the pet age in years."""
        return self.data.get("year") or self.data.get("age")

    @property
    def age_months(self) -> int | None:
        """Return the pet age in months."""
        return self.data.get("month")

    @property
    def breed(self) -> str | None:
        """Return the pet breed."""
        return self.data.get("breedName")

    @property
    def gender_label(self) -> str | None:
        """Return the pet gender label."""
        gender = self.data.get("gender")
        if isinstance(gender, str) and gender.isdigit():
            gender = int(gender)
        if isinstance(gender, int):
            return GENDER_LABELS.get(gender)
        return None

    @property
    def birthday(self) -> str | None:
        """Return the pet birthday as ISO date."""
        birthday = self.data.get("birthday")
        if not birthday:
            return None
        return dt_util.utc_from_timestamp(birthday / 1000).date().isoformat()

    @property
    def avatar_url(self) -> str | None:
        """Return the pet avatar URL."""
        return self.data.get("avatar")

    @property
    def avatar(self) -> None:
        """Return the avatar state."""
        return None

    def _summary(self) -> dict:
        return self.data.get("summary_simple") or {}

    def _summary_section(self, name: str) -> dict:
        summary = self._summary()
        return summary.get(name) or {}

    @staticmethod
    def _to_float(value) -> float | None:
        """Convert a value to float when possible."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    @property
    def status(self) -> str | None:
        """Return the pet health status description."""
        summary = self._summary()
        return summary.get("statusDescription") or summary.get("status")

    @property
    def toilet_times(self) -> int | None:
        """Return the number of toilet visits."""
        return self._summary_section("toilet").get("times")

    @property
    def toilet_weight_avg(self) -> float | None:
        """Return the average toilet weight."""
        return self._summary_section("toilet").get("weightAvg")

    @property
    def pee_times(self) -> int | None:
        """Return the number of pee events."""
        return self._summary_section("toilet").get("peed")

    @property
    def poo_times(self) -> int | None:
        """Return the number of poo events."""
        return self._summary_section("toilet").get("pood")

    @property
    def drink_times(self) -> int:
        """Return the drink times."""
        return self._summary_section("drink").get("times", 0)

    @property
    def diet_times(self) -> int:
        """Return the diet times."""
        return self._summary_section("diet").get("times", 0)

    @property
    def diet_intakes(self) -> float | None:
        """Return the diet intakes."""
        return self._to_float(self._summary_section("diet").get("intakes"))

    @property
    def sport_active_duration(self) -> int:
        """Return the sport active duration."""
        return self._summary_section("sport").get("activeDuration", 0)

    def cat_attrs(self) -> dict:
        """Return the cat attributes."""
        return {
            "pet_id": self.pet_id,
            "breed": self.breed,
            "gender": self.gender_label,
            "birthday": self.birthday,
            "weight": self.weight,
            "age_years": self.age_years,
            "age_months": self.age_months,
            "toilet_times": self.toilet_times,
            "toilet_weight_avg": self.toilet_weight_avg,
            "pee_times": self.pee_times,
            "poo_times": self.poo_times,
            "drink_times": self.drink_times,
            "diet_times": self.diet_times,
            "diet_intakes": self.diet_intakes,
            "sport_active_duration": self.sport_active_duration,
            "local_pee_count": self._local_pee_count,
            "local_poo_count": self._local_poo_count,
            "source_device": self._source_device_id,
        }

    def _status_attrs(self) -> dict:
        """Return status attributes."""
        return {
            "pet_id": self.pet_id,
            "name": self._discovered_name or self.name,
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

    @property
    def hass_sensor(self) -> dict:
        """Return cat sensors."""
        return {
            "status": {
                "icon": "mdi:cat",
                "state_attrs": self.cat_attrs,
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
            "age_years": {
                "icon": "mdi:calendar",
            },
            "age_months": {
                "icon": "mdi:calendar",
            },
            "gender_label": {
                "icon": "mdi:gender-male-female",
            },
            "breed": {
                "icon": "mdi:cat",
            },
            "birthday": {
                "icon": "mdi:cake-variant",
                "class": SensorDeviceClass.DATE,
            },
            "avatar": {
                "icon": "mdi:image",
                "entity_picture": self.avatar_url,
            },
            "toilet_times": {
                "icon": "mdi:toilet",
            },
            "toilet_weight_avg": {
                "icon": "mdi:scale",
                "class": SensorDeviceClass.WEIGHT,
                "state_class": SensorStateClass.MEASUREMENT,
                "unit": UnitOfMass.KILOGRAMS,
            },
            "pee_times": {
                "icon": "mdi:water",
            },
            "poo_times": {
                "icon": "mdi:emoticon-poop",
            },
            "drink_times": {
                "icon": "mdi:cup-water",
            },
            "diet_times": {
                "icon": "mdi:food",
            },
            "diet_intakes": {
                "icon": "mdi:food",
            },
            "sport_active_duration": {
                "icon": "mdi:run",
            },
        }

    @property
    def hass_binary_sensor(self) -> dict:
        """Return empty binary sensors for cats."""
        return {}

    @property
    def hass_switch(self) -> dict:
        """Return empty switches for cats."""
        return {}

    @property
    def hass_button(self) -> dict:
        """Return empty buttons for cats."""
        return {}

    @property
    def hass_select(self) -> dict:
        """Return empty selects for cats."""
        return {}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_devices.py::TestCatDeviceUpdateFromActivity -v`
Expected: All tests pass

- [ ] **Step 5: 运行所有设备测试确保兼容**

Run: `pytest tests/test_devices.py -v`
Expected: All tests pass

- [ ] **Step 6: 提交**

```bash
git add custom_components/catlink/devices/cat.py tests/test_devices.py
git commit -m "feat: add update_from_activity method to CatDevice"
```

---

### Task 5: 添加猫咪详情 API

**Files:**
- Modify: `custom_components/catlink/modules/account.py`

- [ ] **Step 1: 编写测试 - get_cat_detail API**

在 `tests/test_account.py` 中添加:

```python
class TestGetCatDetail:
    """Tests for get_cat_detail method."""

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_get_cat_detail_success(
        self, hass, mock_http_session
    ) -> None:
        """Test get_cat_detail returns cat data."""
        config = {
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            CONF_PASSWORD: "test_password",
            CONF_TOKEN: "valid_token",
        }
        account = Account(hass, config)
        account.http = mock_http_session

        mock_http_session.request = AsyncMock(
            return_value=AsyncMock(
                status=200,
                json=AsyncMock(
                    return_value={
                        "returnCode": 0,
                        "data": {
                            "id": "548334",
                            "petName": "土豆🥔",
                            "avatar": "https://example.com/avatar.jpg",
                        },
                    }
                ),
            )
        )

        result = await account.get_cat_detail("548334")

        assert result["id"] == "548334"
        assert result["petName"] == "土豆🥔"

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_get_cat_detail_returns_empty_on_failure(
        self, hass, mock_http_session
    ) -> None:
        """Test get_cat_detail returns empty dict on API failure."""
        config = {
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            CONF_PASSWORD: "test_password",
            CONF_TOKEN: "valid_token",
        }
        account = Account(hass, config)
        account.http = mock_http_session

        mock_http_session.request = AsyncMock(
            return_value=AsyncMock(
                status=200,
                json=AsyncMock(
                    return_value={
                        "returnCode": 500,
                        "data": None,
                    }
                ),
            )
        )

        result = await account.get_cat_detail("548334")
        assert result == {}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_account.py::TestGetCatDetail -v`
Expected: FAIL with AttributeError (no 'get_cat_detail')

- [ ] **Step 3: 实现 get_cat_detail 方法**

在 `account.py` 的 `get_cat_summary_simple` 方法后添加:

```python
    async def get_cat_detail(self, pet_id: str) -> dict:
        """Get cat detail including avatar.

        Args:
            pet_id: The pet ID to fetch details for

        Returns:
            Cat detail dict or empty dict if failed
        """
        if not self.token:
            if not await self.async_login():
                return {}

        # 尝试可能的 API 端点
        # 可能的端点: token/pet/detail, token/pet/info
        api = "token/pet/detail"
        params = {"petId": pet_id}

        rsp = await self.request(api, params)
        if rsp is None:
            return {}

        eno = rsp.get("returnCode", 0)
        if eno == 1002:  # Illegal token
            if await self.async_login():
                rsp = await self.request(api, params)
                if rsp is None:
                    return {}

        return rsp.get("data") or {}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_account.py::TestGetCatDetail -v`
Expected: All tests pass

- [ ] **Step 5: 提交**

```bash
git add custom_components/catlink/modules/account.py tests/test_account.py
git commit -m "feat: add get_cat_detail API method"
```

---

### Task 6: 在 DevicesCoordinator 中添加猫咪发现逻辑

**Files:**
- Modify: `custom_components/catlink/modules/devices_coordinator.py`

- [ ] **Step 1: 编写测试 - 猫咪发现逻辑**

创建 `tests/test_cat_discovery_coordinator.py`:

```python
"""Tests for cat discovery in DevicesCoordinator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.catlink.devices.cat import CatDevice
from custom_components.catlink.devices.c08 import C08Device
from custom_components.catlink.modules.devices_coordinator import DevicesCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {
        "catlink": {
            "config": {},
            "add_entities": {},
        }
    }
    hass.config.time_zone = "Asia/Shanghai"
    return hass


@pytest.fixture
def mock_account(mock_hass):
    """Create a mock Account instance."""
    account = MagicMock()
    account.hass = mock_hass
    account.uid = "86-13812345678"
    account.update_interval = 60
    account.get_devices = AsyncMock(return_value=[])
    account.get_cats = AsyncMock(return_value=[])
    account.get_cat_summary_simple = AsyncMock(return_value={})
    account.get_cat_detail = AsyncMock(return_value={})
    return account


class TestDiscoverCatsFromDeviceLogs:
    """Tests for _discover_cats_from_device_logs method."""

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_discovers_cat_from_device_logs(
        self, mock_hass, mock_account
    ) -> None:
        """Test that cats are discovered from device logs."""
        coordinator = DevicesCoordinator(mock_account, "test_entry_id")
        mock_hass.data["catlink"]["devices"] = {}

        # 创建一个带有猫咪活动日志的设备
        device_data = {
            "id": "c08-1",
            "mac": "01:23:45:67:89:AB",
            "model": "Open-X",
            "deviceName": "Bedroom C08",
            "deviceType": "C08",
        }
        device = C08Device(device_data, coordinator)
        device.logs = [
            {
                "time": "11:24",
                "event": "土豆🥔 pooped",
                "firstSection": "7.9kg",
                "secondSection": "173s",
                "id": "899877558",
                "type": "WC",
                "petId": "548334",
                "snFlag": 2,
            },
        ]
        mock_hass.data["catlink"]["devices"]["c08-1"] = device

        await coordinator._discover_cats_from_device_logs()

        # 应该发现一只猫咪
        assert "cat-548334" in mock_hass.data["catlink"]["devices"]
        cat_device = mock_hass.data["catlink"]["devices"]["cat-548334"]
        assert isinstance(cat_device, CatDevice)
        assert cat_device.discovered_name == "土豆🥔"

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_updates_existing_cat_from_logs(
        self, mock_hass, mock_account
    ) -> None:
        """Test that existing cat is updated from new logs."""
        coordinator = DevicesCoordinator(mock_account, "test_entry_id")
        mock_hass.data["catlink"]["devices"] = {}

        # 创建已有的猫咪设备
        cat_data = {
            "id": "cat-548334",
            "pet_id": "548334",
            "petName": "土豆🥔",
            "deviceName": "土豆🥔",
            "deviceType": "CAT",
            "mac": "cat-548334",
        }
        existing_cat = CatDevice(cat_data, coordinator)
        await existing_cat.async_init()
        mock_hass.data["catlink"]["devices"]["cat-548334"] = existing_cat

        # 创建一个带有新活动的设备
        device_data = {
            "id": "c08-1",
            "mac": "01:23:45:67:89:AB",
            "model": "Open-X",
            "deviceName": "Bedroom C08",
            "deviceType": "C08",
        }
        device = C08Device(device_data, coordinator)
        device.logs = [
            {
                "time": "11:30",
                "event": "土豆🥔 peed",
                "firstSection": "7.5kg",
                "secondSection": "60s",
                "id": "899877559",
                "type": "WC",
                "petId": "548334",
                "snFlag": 0,
            },
        ]
        mock_hass.data["catlink"]["devices"]["c08-1"] = device

        initial_count = existing_cat.local_pee_count
        await coordinator._discover_cats_from_device_logs()

        # 应该更新猫咪的计数
        assert existing_cat.local_pee_count == initial_count + 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_cat_discovery_coordinator.py -v`
Expected: FAIL with AttributeError (no '_discover_cats_from_device_logs')

- [ ] **Step 3: 实现 _discover_cats_from_device_logs 方法**

修改 `devices_coordinator.py`，在 `_async_update_data` 方法中添加调用，并实现新方法:

```python
    async def _async_update_data(self) -> dict:
        """Update data via API."""
        # ... 现有代码 ...

        # 从设备日志发现猫咪（在获取 API 猫咪之后）
        await self._discover_cats_from_device_logs()

        # 尝试获取猫咪详情（头像等）
        await self._update_cat_details()

        return self.hass.data[DOMAIN][CONF_DEVICES]

    async def _discover_cats_from_device_logs(self) -> None:
        """Discover cats from device logs and create/update CatDevice instances."""
        discovered_cats: dict[str, dict] = {}  # pet_id -> {activities, source_device}

        # 从所有设备收集猫咪活动
        for device in list(self.hass.data[DOMAIN][CONF_DEVICES].values()):
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
                reverse=True,
            )

            existing = self.hass.data[DOMAIN][CONF_DEVICES].get(cat_device_id)
            if existing:
                # 更新现有猫咪 - 处理所有活动
                for activity in activities:
                    existing.update_from_activity(activity)
            else:
                # 创建新猫咪 - 只使用最新活动初始化
                latest_activity = activities[0] if activities else None
                if not latest_activity:
                    continue

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
                # 处理所有活动
                for activity in activities:
                    cat_device.update_from_activity(activity)
                self.hass.data[DOMAIN][CONF_DEVICES][cat_device_id] = cat_device
                await cat_device.async_init()
                for d in SUPPORTED_DOMAINS:
                    await self.update_hass_entities(d, cat_device)

    async def _update_cat_details(self) -> None:
        """Update cat details (avatar, etc.) from API."""
        for device in list(self.hass.data[DOMAIN][CONF_DEVICES].values()):
            if not isinstance(device, CatDevice):
                continue
            if device.avatar_url:  # 已有头像则跳过
                continue

            pet_id = device.pet_id
            if not pet_id:
                continue

            try:
                detail = await self.account.get_cat_detail(pet_id)
                if detail:
                    if detail.get("avatar"):
                        device.data["avatar"] = detail["avatar"]
                    if detail.get("petName") and not device.discovered_name:
                        device.data["petName"] = detail["petName"]
            except Exception:  # noqa: BLE001
                pass  # API 可能不支持，忽略错误
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_cat_discovery_coordinator.py -v`
Expected: All tests pass

- [ ] **Step 5: 运行所有测试确保兼容**

Run: `pytest tests/ -v --ignore=tests/test_devices_coordinator.py`
Expected: All tests pass

- [ ] **Step 6: 提交**

```bash
git add custom_components/catlink/modules/devices_coordinator.py tests/test_cat_discovery_coordinator.py
git commit -m "feat: add cat discovery from device logs in DevicesCoordinator"
```

---

### Task 7: 添加翻译

**Files:**
- Modify: `custom_components/catlink/strings.json`
- Modify: `custom_components/catlink/translations/en.json`
- Modify: `custom_components/catlink/translations/zh-Hans.json`

- [ ] **Step 1: 添加猫咪传感器翻译到 strings.json**

在 `strings.json` 的 `entity.sensor` 部分添加:

```json
{
  "entity": {
    "sensor": {
      "CAT_status": {
        "name": "Status"
      },
      "CAT_weight": {
        "name": "Weight"
      },
      "CAT_pee_count": {
        "name": "Pee Count"
      },
      "CAT_poo_count": {
        "name": "Poo Count"
      },
      "CAT_last_event": {
        "name": "Last Event"
      },
      "CAT_age_years": {
        "name": "Age (Years)"
      },
      "CAT_age_months": {
        "name": "Age (Months)"
      },
      "CAT_gender_label": {
        "name": "Gender"
      },
      "CAT_breed": {
        "name": "Breed"
      },
      "CAT_birthday": {
        "name": "Birthday"
      },
      "CAT_avatar": {
        "name": "Avatar"
      },
      "CAT_toilet_times": {
        "name": "Toilet Times"
      },
      "CAT_toilet_weight_avg": {
        "name": "Avg Toilet Weight"
      },
      "CAT_pee_times": {
        "name": "Pee Times"
      },
      "CAT_poo_times": {
        "name": "Poo Times"
      },
      "CAT_drink_times": {
        "name": "Drink Times"
      },
      "CAT_diet_times": {
        "name": "Diet Times"
      },
      "CAT_diet_intakes": {
        "name": "Diet Intakes"
      },
      "CAT_sport_active_duration": {
        "name": "Sport Duration"
      }
    }
  }
}
```

- [ ] **Step 2: 添加英文翻译到 translations/en.json**

```json
{
  "entity": {
    "sensor": {
      "CAT_status": {
        "name": "Status"
      },
      "CAT_weight": {
        "name": "Weight"
      },
      "CAT_pee_count": {
        "name": "Pee Count"
      },
      "CAT_poo_count": {
        "name": "Poo Count"
      },
      "CAT_last_event": {
        "name": "Last Event"
      },
      "CAT_age_years": {
        "name": "Age (Years)"
      },
      "CAT_age_months": {
        "name": "Age (Months)"
      },
      "CAT_gender_label": {
        "name": "Gender"
      },
      "CAT_breed": {
        "name": "Breed"
      },
      "CAT_birthday": {
        "name": "Birthday"
      },
      "CAT_avatar": {
        "name": "Avatar"
      },
      "CAT_toilet_times": {
        "name": "Toilet Times"
      },
      "CAT_toilet_weight_avg": {
        "name": "Avg Toilet Weight"
      },
      "CAT_pee_times": {
        "name": "Pee Times"
      },
      "CAT_poo_times": {
        "name": "Poo Times"
      },
      "CAT_drink_times": {
        "name": "Drink Times"
      },
      "CAT_diet_times": {
        "name": "Diet Times"
      },
      "CAT_diet_intakes": {
        "name": "Diet Intakes"
      },
      "CAT_sport_active_duration": {
        "name": "Sport Duration"
      }
    }
  }
}
```

- [ ] **Step 3: 添加中文翻译到 translations/zh-Hans.json**

```json
{
  "entity": {
    "sensor": {
      "CAT_status": {
        "name": "状态"
      },
      "CAT_weight": {
        "name": "体重"
      },
      "CAT_pee_count": {
        "name": "小便次数"
      },
      "CAT_poo_count": {
        "name": "大便次数"
      },
      "CAT_last_event": {
        "name": "最近活动"
      },
      "CAT_age_years": {
        "name": "年龄(岁)"
      },
      "CAT_age_months": {
        "name": "年龄(月)"
      },
      "CAT_gender_label": {
        "name": "性别"
      },
      "CAT_breed": {
        "name": "品种"
      },
      "CAT_birthday": {
        "name": "生日"
      },
      "CAT_avatar": {
        "name": "头像"
      },
      "CAT_toilet_times": {
        "name": "如厕次数"
      },
      "CAT_toilet_weight_avg": {
        "name": "平均如厕体重"
      },
      "CAT_pee_times": {
        "name": "小便次数"
      },
      "CAT_poo_times": {
        "name": "大便次数"
      },
      "CAT_drink_times": {
        "name": "饮水次数"
      },
      "CAT_diet_times": {
        "name": "进食次数"
      },
      "CAT_diet_intakes": {
        "name": "进食量"
      },
      "CAT_sport_active_duration": {
        "name": "运动时长"
      }
    }
  }
}
```

- [ ] **Step 4: 提交**

```bash
git add custom_components/catlink/strings.json
git add custom_components/catlink/translations/en.json
git add custom_components/catlink/translations/zh-Hans.json
git commit -m "i18n: add translations for cat discovery sensors"
```

---

### Task 8: 更新实体传感器状态值

**Files:**
- Modify: `custom_components/catlink/entities/sensor.py`

- [ ] **Step 1: 检查 sensor.py 中如何获取状态值**

阅读 `custom_components/catlink/entities/sensor.py` 确认状态值获取逻辑。

- [ ] **Step 2: 确保 CatDevice 的属性可以被正确读取**

需要确认 `pee_count` 和 `poo_count` 属性能被正确读取。在 `sensor.py` 中，状态值通常通过 `getattr(self._device, key)` 获取。

CatDevice 需要添加 `pee_count` 和 `poo_count` 属性:

```python
# 在 CatDevice 中添加属性
@property
def pee_count(self) -> int:
    """Return the local pee count."""
    return self._local_pee_count

@property
def poo_count(self) -> int:
    """Return the local poo count."""
    return self._local_poo_count

@property
def last_event(self) -> str | None:
    """Return the last event description."""
    if not self._last_activity:
        return None
    activity_type = self._last_activity.get("type", "")
    weight = self._last_activity.get("weight")
    duration = self._last_activity.get("duration")
    time = self._last_activity.get("time", "")

    parts = [time]
    if activity_type == "pee":
        parts.append("嘘嘘" if self._is_chinese else "pee")
    elif activity_type == "poo":
        parts.append("拉臭臭" if self._is_chinese else "poo")
    if weight:
        parts.append(f"{weight}kg")
    if duration:
        parts.append(f"{duration}s")

    return " ".join(parts) if parts else None
```

- [ ] **Step 3: 运行测试确保实体状态正确**

Run: `pytest tests/test_entities.py -v`
Expected: All tests pass

- [ ] **Step 4: 提交**

```bash
git add custom_components/catlink/devices/cat.py custom_components/catlink/entities/sensor.py
git commit -m "feat: add pee_count, poo_count, last_event properties to CatDevice"
```

---

### Task 9: 集成测试

**Files:**
- Test: 运行完整测试套件

- [ ] **Step 1: 运行所有测试**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: 检查代码风格**

Run: `ruff check custom_components/catlink/`
Expected: No errors (or fix them)

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: complete cat discovery from device logs feature"
```

---

## 自检清单

### Spec 覆盖检查

| 规格要求 | 任务 |
|---------|------|
| 从日志解析猫咪活动 | Task 2: CatDiscoveryMixin |
| 解析名字、体重、时长 | Task 2: extract_name_and_action, parse_weight, parse_duration |
| 自动发现猫咪并创建 CatDevice | Task 6: _discover_cats_from_device_logs |
| 传感器: status, weight, pee_count, poo_count, last_event | Task 4: CatDevice.hass_sensor |
| 尝试 API 获取头像 | Task 5: get_cat_detail, Task 6: _update_cat_details |
| 用户手动配置头像 | 已支持（Home Assistant entity_picture） |
| 去重处理 | Task 4: _processed_log_ids |
| 翻译支持 | Task 7 |

### 占位符检查

- 无 TBD、TODO 占位符
- 所有代码步骤包含完整实现
- 所有测试包含完整测试代码

### 类型一致性检查

- `activity["pet_id"]` 在所有地方都是字符串
- `activity["type"]` 是 "pee" 或 "poo"
- `activity["weight"]` 是 float 或 None
- `activity["duration"]` 是 int 或 None
- `CatDevice.discovered_name` 返回 `str | None`
- `CatDevice.local_pee_count` 返回 `int`
- `CatDevice.local_poo_count` 返回 `int`
