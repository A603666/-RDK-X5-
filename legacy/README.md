# 原始模块目录 / Legacy Modules Directory

本目录包含系统重构前的原始模块，保留作为参考和向后兼容性支持。

## 目录结构

### 原始功能模块
- `传感器/` - 原始传感器模块
- `定位模块 copy/` - 原始定位模块
- `导航避障模块/` - 原始导航避障模块
- `电机驱动可以运行版本 copy/` - 原始电机控制模块
- `目标检测/` - 原始AI检测模块
- `前后端/` - 原始Web前后端模块

### 集成和测试文件
- `integration_main.py` - 原始集成主程序
- `项目.md` - 原始项目说明文档

## 重要说明

⚠️ **注意：这些是原始模块，仅供参考使用**

- 新的开发应该使用 `board/` 和 `pc/` 目录下的重构版本
- 这些模块可能包含过时的配置和依赖
- 保留这些文件是为了：
  - 向后兼容性
  - 功能参考
  - 调试和对比
  - 历史记录

## 迁移指南

如果需要从原始模块迁移到新架构：

### 板端模块迁移
- 原始模块 → 新架构
- `传感器/` → `board/modules/sensors/`
- `定位模块 copy/` → `board/modules/positioning/`
- `导航避障模块/` → `board/modules/navigation/`
- `电机驱动可以运行版本 copy/` → `board/modules/motor_control/`
- `目标检测/` → `board/modules/ai_detection/`

### PC端模块迁移
- `前后端/` → `pc/web/` 和 `pc/api/`
- 配置文件已整合到 `config/` 目录
- Web界面已优化并移动到 `pc/web/`

### 配置迁移
- 各模块的 `config.py` 已整合到 `config/global_config.py`
- MQTT配置已统一到 `config/mqtt_config.py`
- 日志配置已统一到 `config/system_logger.py`

## 使用建议

1. **新项目**：直接使用 `board/` 和 `pc/` 目录下的新架构
2. **现有项目**：逐步迁移到新架构，可以参考这些原始模块
3. **调试**：如果新架构出现问题，可以对比原始模块的实现
4. **学习**：了解系统演进过程和设计决策

## 维护状态

- ❌ 不再主动维护
- ❌ 不推荐用于新开发
- ✅ 保留用于参考
- ✅ 支持向后兼容性查询

---

# Legacy Modules Directory (English)

This directory contains the original modules before system refactoring, preserved for reference and backward compatibility support.

## Directory Structure

### Original Functional Modules
- `传感器/` - Original sensor module
- `定位模块 copy/` - Original positioning module
- `导航避障模块/` - Original navigation and obstacle avoidance module
- `电机驱动可以运行版本 copy/` - Original motor control module
- `目标检测/` - Original AI detection module
- `前后端/` - Original web frontend and backend module

### Integration and Test Files
- `integration_main.py` - Original integration main program
- `项目.md` - Original project documentation

## Important Notes

⚠️ **Note: These are legacy modules for reference only**

- New development should use the refactored versions in `board/` and `pc/` directories
- These modules may contain outdated configurations and dependencies
- These files are preserved for:
  - Backward compatibility
  - Functional reference
  - Debugging and comparison
  - Historical records

## Migration Guide

If you need to migrate from legacy modules to the new architecture:

### Board Module Migration
- Legacy Module → New Architecture
- `传感器/` → `board/modules/sensors/`
- `定位模块 copy/` → `board/modules/positioning/`
- `导航避障模块/` → `board/modules/navigation/`
- `电机驱动可以运行版本 copy/` → `board/modules/motor_control/`
- `目标检测/` → `board/modules/ai_detection/`

### PC Module Migration
- `前后端/` → `pc/web/` and `pc/api/`
- Configuration files integrated into `config/` directory
- Web interface optimized and moved to `pc/web/`

### Configuration Migration
- Individual module `config.py` files integrated into `config/global_config.py`
- MQTT configuration unified in `config/mqtt_config.py`
- Logging configuration unified in `config/system_logger.py`

## Usage Recommendations

1. **New Projects**: Use the new architecture in `board/` and `pc/` directories directly
2. **Existing Projects**: Gradually migrate to the new architecture, referencing these legacy modules
3. **Debugging**: Compare with legacy module implementations if issues arise in the new architecture
4. **Learning**: Understand system evolution and design decisions

## Maintenance Status

- ❌ No longer actively maintained
- ❌ Not recommended for new development
- ✅ Preserved for reference
- ✅ Supports backward compatibility queries
