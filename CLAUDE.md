# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CatLink is a Home Assistant custom integration for CatLINK smart pet devices (litter boxes, feeders, water fountains). It connects to the CatLink cloud API to monitor and control devices.

## Development Commands

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run all tests
pytest

# Run a single test file
pytest tests/test_devices.py

# Run a single test
pytest tests/test_devices.py::test_create_device
```

## Architecture

### Entry Points
- `__init__.py`: Sets up config entries, coordinators, and forwards platform setups
- `config_flow.py`: UI-based setup flow (phone/password authentication, device discovery)

### Core Components

**Account** (`modules/account.py`):
- Handles CatLink cloud API authentication
- Manages API requests with signed parameters
- Stores tokens in Home Assistant storage

**DevicesCoordinator** (`modules/devices_coordinator.py`):
- Extends `DataUpdateCoordinator` for periodic polling
- Fetches devices and cats from API
- Creates device instances and updates entities

**Device Classes** (`devices/`):
- `base.py`: Base `Device` class with common properties (state, mode, actions, sensors)
- `registry.py`: Maps `deviceType` strings to device classes
- Device types: `ScooperDevice`, `LitterBox`, `C08Device`, `FeederDevice`, `PureProDevice`, `CatDevice`

**Entity Classes** (`entities/`):
- `base.py`: `CatlinkEntity` extends `CoordinatorEntity`, handles state updates
- `registry.py`: Maps domain names to entity classes
- Platforms: `sensor`, `binary_sensor`, `switch`, `select`, `button`, `number`

### Device-Entity Pattern
Devices expose entities via `hass_*` properties (e.g., `hass_sensor`, `hass_switch`). Each returns a dict mapping entity keys to config dicts with `icon`, `state_attrs`, and platform-specific options.

### API Layer (`models/api/`)
- Pydantic models for parsing API responses (`DeviceInfoBase`, `LitterDeviceInfo`, etc.)
- `parse.py`: Response parsing utilities

### Adding a New Device Type
1. Create a class extending `Device` (or a specialized base like `LitterDevice`)
2. Register in `devices/registry.py` `DEVICE_TYPES` dict
3. Add `deviceType` to `SUPPORTED_DEVICE_TYPES` in `const.py` if fully supported

## Key Files

- `const.py`: Domain constants, API servers, configuration schema
- `helpers.py`: Utility functions (phone parsing, region discovery, error formatting)
- `manifest.json`: Integration metadata, dependencies (phonenumbers, pydantic)
