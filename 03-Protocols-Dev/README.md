# 03-Protocols-Dev：通讯协议与开发

> 💻 掌握 MAVLink、DJI SDK、ROS2 —— 无人机开发的核心技术栈

---

## 📌 模块定位

本模块面向**无人机软件开发工程师**，深度解析通讯协议原理、SDK 开发方法与系统集成技术。

---

## 🎯 目标读者

- 飞控开发工程师
- 地面站软件开发人员
- 无人机应用开发者
- ROS/ROS2 集成工程师

---

## 📚 内容导航

| 文档 | 预计耗时 | 核心内容 |
|------|---------|---------|
| [01-MAVLink 协议详解](./01-MAVLink 协议详解.md) | 40 分钟 | 消息结构、常用命令、解析实现 |
| [02-DJI SDK 对比](./02-DJI-SDK 对比.md) | 30 分钟 | Onboard/Mobile/Payload SDK 差异与选型 |
| [03-ROS2 无人机集成](./03-ROS2 无人机集成.md) | 40 分钟 | micro-ROS、px4_ros2、自定义消息 |
| [04-通信模版代码](./04-通信模版代码.md) | 20 分钟 | Python/Java 示例代码 |

---

## 💻 技术栈图谱

```mermaid
graph TB
    subgraph 底层协议
        A1[MAVLink 2.0] --> A2[UDP/TCP 传输]
        A2 --> A3[串口通信]
        A3 --> A4[CAN 总线]
    end
    
    subgraph 厂商 SDK
        B1[DJI Onboard SDK] --> B2[DJI Mobile SDK]
        B2 --> B3[DJI Payload SDK]
        B3 --> B4[DJI Cloud API]
    end
    
    subgraph 开源生态
        C1[PX4 Autopilot] --> C2[ArduPilot]
        C2 --> C3[micro-ROS]
        C3 --> C4[px4_ros2]
    end
    
    subgraph 应用开发
        D1[地面站开发] --> D2[航线规划]
        D2 --> D3[实时监控]
        D3 --> D4[数据分析]
    end
    
    底层协议 --> 厂商 SDK
    厂商 SDK --> 开源生态
    开源生态 --> 应用开发
```

---

## 🔗 相关模块

| 关联内容 | 推荐模块 |
|---------|---------|
| 硬件基础 | [02-Hardware-Systems/飞控系统](../02-Hardware-Systems/03-传感器详解.md) |
| 开源飞控 | [07-OpenSource-Awesome/开源飞控](../07-OpenSource-Awesome/01-开源飞控.md) |
| 地面站软件 | [07-OpenSource-Awesome/地面站软件](../07-OpenSource-Awesome/02-地面站软件.md) |

---

## 📅 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-04-05 | 模块初始化完成 |
| 每日 02:30 | 自动追踪协议更新与 SDK 版本 |

---

<div align="center">

**开始学习 →** [MAVLink 协议详解](./01-MAVLink 协议详解.md)

</div>
