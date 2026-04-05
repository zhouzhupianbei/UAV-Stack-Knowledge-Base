# 04-Streaming-AI：流媒体与人工智能

> 🤖 ZLMediaKit + YOLO + 边缘计算 —— 打造智能无人机视觉系统

---

## 📌 模块定位

本模块面向**算法工程师、边缘计算开发者、AI 应用集成人员**，解析无人机视频流处理与智能识别技术。

---

## 🎯 目标读者

- 计算机视觉算法工程师
- 边缘计算部署人员
- 流媒体系统开发人员
- AI 巡检方案设计师

---

## 📚 内容导航

| 文档 | 预计耗时 | 核心内容 |
|------|---------|---------|
| [01-ZLMediaKit 部署](./01-ZLMediaKit 部署.md) | 30 分钟 | 流媒体服务器搭建、SRT/RTMP/HLS/WebRTC |
| [02-YOLO 目标检测](./02-YOLO 目标检测.md) | 40 分钟 | 模型训练、TensorRT 部署、小目标优化 |
| [03-边缘计算方案](./03-边缘计算方案.md) | 25 分钟 | Jetson/树莓派/国产边缘设备选型 |
| [04-SLAM 入门](./04-SLAM 入门.md) | 35 分钟 | ORB-SLAM、VINS、视觉定位原理 |

---

## 🤖 技术架构

```mermaid
graph TB
    subgraph 视频采集
        A1[机载相机] --> A2[图传接收]
        A2 --> A3[RTSP 拉流]
    end
    
    subgraph 流媒体处理
        B1[ZLMediaKit] --> B2[转码分发]
        B2 --> B3[多协议输出]
        B3 --> B4[低延迟优化]
    end
    
    subgraph AI 推理
        C1[YOLO 检测] --> C2[多目标跟踪]
        C2 --> C3[异常识别]
        C3 --> C4[结果标注]
    end
    
    subgraph 边缘部署
        D1[Jetson Orin] --> D2[Jetson Nano]
        D2 --> D3[树莓派 5]
        D3 --> D4[国产边缘盒]
    end
    
    subgraph 应用输出
        E1[实时告警] --> E2[结果存储]
        E2 --> E3[可视化展示]
        E3 --> E4[报告生成]
    end
    
    视频采集 --> 流媒体处理
    流媒体处理 --> AI 推理
    AI 推理 --> 边缘部署
    边缘部署 --> 应用输出
```

---

## 🔗 相关模块

| 关联内容 | 推荐模块 |
|---------|---------|
| 图传硬件 | [02-Hardware-Systems/图传系统](../02-Hardware-Systems/04-图传系统.md) |
| 电力巡检应用 | [06-Industry-Solutions/电力巡检](../06-Industry-Solutions/01-电力巡检方案.md) |
| 安防监控应用 | [06-Industry-Solutions/安防监控](../06-Industry-Solutions/03-安防监控方案.md) |

---

## 📅 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-04-05 | 模块初始化完成 |
| 每日 02:30 | 自动追踪 AI 模型与边缘设备进展 |

---

<div align="center">

**开始学习 →** [ZLMediaKit 部署](./01-ZLMediaKit 部署.md)

</div>
