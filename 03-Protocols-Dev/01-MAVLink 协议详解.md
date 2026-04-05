# MAVLink 协议详解

> 无人机最通用的通讯协议 —— 消息结构、常用命令、解析实现

---

## 一、协议概述

### 1.1 什么是 MAVLink

**MAVLink（Micro Air Vehicle Link）** 是无人机领域最通用的轻量级通讯协议，由 Lorenz Meier 于 2009 年创建，现由 PX4/ArduPilot 社区维护。

**核心特点：**
- ✅ 轻量级（消息头仅 10-14 字节）
- ✅ 开源免费（MIT 许可证）
- ✅ 可扩展（支持自定义消息）
- ✅ 多语言支持（C/C++/Python/Java 等）
- ✅ 多传输方式（串口/UDP/TCP/4G）

### 1.2 应用场景

| 场景 | 说明 |
|------|------|
| 飞控↔地面站 | 遥测数据、控制命令 |
| 飞控↔机载电脑 | 任务规划、AI 识别结果 |
| 飞控↔遥控器 | 控制指令、状态反馈 |
| 无人机↔云端 | 远程监控、数据上传 |

### 1.3 版本对比

| 特性 | MAVLink 1.0 | MAVLink 2.0 |
|------|------------|------------|
| 消息头 | 8 字节 | 10-14 字节 |
| 最大负载 | 255 字节 | 255 字节 |
| 签名安全 | ❌ | ✅ |
| 兼容模式 | - | 支持 1.0 兼容 |
| 推荐使用 | ❌ | ✅ |

---

## 二、消息结构

### 2.1 MAVLink 2.0 帧格式

```
┌─────────────────────────────────────────────────────────┐
│  帧头   │   负载   │  序列号  │  系统 ID  │  组件 ID  │  校验  │
│  2 字节  │  0-255 字节 │  1 字节  │  1 字节  │  1 字节  │  2 字节  │
└─────────────────────────────────────────────────────────┘
```

**详细说明：**

| 字段 | 长度 | 说明 |
|------|------|------|
| 帧头（Magic） | 2 字节 | 0xFD 0x01（MAVLink 2.0） |
| 负载长度 | 1 字节 | 0-255 |
| 序列号 | 1 字节 | 0-255 循环 |
| 系统 ID | 1 字节 | 1-255（区分不同无人机） |
| 组件 ID | 1 字节 | 1-255（区分飞控/GPS/相机等） |
| 消息 ID | 3 字节 | 标识消息类型 |
| 负载数据 | 0-255 字节 | 实际数据 |
| 校验码 | 2 字节 | CRC-16-CCITT |

### 2.2 常用消息类型

| 消息 ID | 消息名称 | 用途 | 发送频率 |
|--------|---------|------|---------|
| 0 | HEARTBEAT | 心跳包 | 1Hz |
| 30 | ATTITUDE | 姿态信息 | 10-50Hz |
| 33 | GLOBAL_POSITION_INT | 位置信息 | 1-10Hz |
| 76 | COMMAND_LONG | 控制命令 | 按需 |
| 147 | BATTERY_STATUS | 电池状态 | 1Hz |
| 231 | DEBUG_VECT | 调试数据 | 按需 |

### 2.3 HEARTBEAT 消息示例

```python
# MAVLink 2.0 HEARTBEAT 消息
# 系统类型：四旋翼（1）
# 自动驾驶仪：PX4（12）
# 组件：飞控（1）

帧结构：
FD 09 00 00 01 01 00 00 00 01 0C 01 00 00 00 00 00 00 00 00

解析：
FD          - 帧头
09          - 负载长度 9 字节
00          - 序列号 0
00          - 系统 ID 0（地面站）
01          - 组件 ID 1
00 00 00    - 消息 ID 0（HEARTBEAT）
01          - 自定义模式
0C          - 系统类型（四旋翼）
01          - 自动驾驶仪类型（PX4）
00 00 00 00 - 基础模式
00 00       - 校验码
```

---

## 三、常用命令

### 3.1 飞行控制命令

**起飞命令（MAV_CMD_NAV_TAKEOFF）：**
```python
command = 22  # MAV_CMD_NAV_TAKEOFF
param1 = 0    # 最小俯仰角
param2 = 0    # 保留
param3 = 0    # 偏航角（0=当前）
param4 = 0    # 保留
x = 0         # 纬度（0=当前位置）
y = 0         # 经度（0=当前位置）
z = 30        # 目标高度（米）
```

**降落命令（MAV_CMD_NAV_LAND）：**
```python
command = 21  # MAV_CMD_NAV_LAND
param1 = 0    # 下降模式
param2 = 0    # 保留
param3 = 0    # 偏航角
param4 = 0    # 保留
x = 0         # 纬度（0=当前位置）
y = 0         # 经度（0=当前位置）
z = 0         # 高度（0=地面）
```

**返航命令（MAV_CMD_NAV_RETURN_TO_LAUNCH）：**
```python
command = 20  # MAV_CMD_NAV_RETURN_TO_LAUNCH
# 无参数
```

### 3.2 模式切换命令

**设置飞行模式：**
```python
command = 176  # MAV_CMD_DO_SET_MODE
param1 = 1     # 基础模式（1=手动，3=自动）
param2 = 0     # 自定义模式
# Stabilize 模式：param1=1, param2=0
# Loiter 模式：param1=1, param2=5
# Auto 模式：param1=1, param2=4
```

### 3.3 航点任务命令

**添加航点：**
```python
command = 16  # MAV_CMD_NAV_WAYPOINT
param1 = 0    # 停留时间（秒）
param2 = 0    # 接受半径（米）
param3 = 0    # 通过角度
param4 = 0    # 偏航角
x = 30.1234   # 纬度
y = 120.5678  # 经度
z = 50        # 高度（米）
```

---

## 四、Python 实现示例

### 4.1 环境准备

```bash
pip install pymavlink
```

### 4.2 连接飞控

```python
from pymavlink import mavutil

# 通过串口连接
master = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)

# 或通过 UDP 连接
# master = mavutil.mavlink_connection('udpin:127.0.0.1:14550')

# 等待心跳包
master.wait_heartbeat()
print(f"连接成功：系统={master.target_system}, 组件={master.target_component}")
```

### 4.3 接收遥测数据

```python
# 持续接收消息
while True:
    msg = master.recv_match(type=['GLOBAL_POSITION_INT', 'ATTITUDE'], blocking=True)
    
    if msg.get_type() == 'GLOBAL_POSITION_INT':
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        alt = msg.alt / 1000.0
        print(f"位置：{lat}, {lon}, 高度：{alt}m")
    
    elif msg.get_type() == 'ATTITUDE':
        roll = msg.roll
        pitch = msg.pitch
        yaw = msg.yaw
        print(f"姿态：横滚={roll:.2f}, 俯仰={pitch:.2f}, 偏航={yaw:.2f}")
```

### 4.4 发送控制命令

```python
# 解锁无人机
master.arducopter_arm()
print("已解锁")

# 起飞到 10 米高度
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0, 0, 0, 0, 0, 0, 0, 10
)
print("起飞命令已发送")

# 设置模式为 Loiter
master.set_mode(5)  # 5=Loiter
print("已切换到 Loiter 模式")
```

### 4.5 航点任务规划

```python
# 创建航点列表
waypoints = [
    (30.1234, 120.5678, 50),  # 航点 1
    (30.1245, 120.5689, 50),  # 航点 2
    (30.1256, 120.5700, 50),  # 航点 3
]

# 上传航点
for i, (lat, lon, alt) in enumerate(waypoints):
    master.mav.mission_item_int_send(
        master.target_system,
        master.target_component,
        i,  # 序号
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        2, 0, 0, 0, 0, 0,
        int(lat * 1e7),
        int(lon * 1e7),
        alt
    )

# 开始任务
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_MISSION_START,
    0, 0, 0, 0, 0, 0, 0, 0
)
```

---

## 五、Java 实现示例

### 5.1 Maven 依赖

```xml
<dependency>
    <groupId>org.mavlink</groupId>
    <artifactId>javamavlink</artifactId>
    <version>2.0</version>
</dependency>
```

### 5.2 连接与通信

```java
import com.MAVLink.MAVLinkPacket;
import com.MAVLink.Messages.MAVLinkMessage;
import com.MAVLink.Messages.ardupilotmega.msg_heartbeat;
import com.MAVLink.Messages.ardupilotmega.msg_global_position_int;

// 通过 UDP 连接
DatagramSocket socket = new DatagramSocket(14550);

// 接收消息
byte[] buffer = new byte[1024];
DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
socket.receive(packet);

// 解析 MAVLink 消息
MAVLinkPacket mavPacket = MAVLinkPacket.decode(packet.getData());
if (mavPacket != null) {
    MAVLinkMessage msg = mavPacket.unpack();
    if (msg.msgid == 0) {  // HEARTBEAT
        msg_heartbeat heartbeat = (msg_heartbeat) msg;
        System.out.println("收到心跳包");
    } else if (msg.msgid == 33) {  // GLOBAL_POSITION_INT
        msg_global_position_int pos = (msg_global_position_int) msg;
        double lat = pos.lat / 1e7;
        double lon = pos.lon / 1e7;
        System.out.println("位置：" + lat + ", " + lon);
    }
}
```

---

## 六、调试技巧

### 6.1 常用工具

| 工具 | 用途 | 平台 |
|------|------|------|
| QGroundControl | 地面站、日志查看 | 全平台 |
| Mission Planner | 地面站、参数配置 | Windows |
| MAVLink Inspector | 消息监控 | 全平台 |
| Wireshark | 网络抓包 | 全平台 |

### 6.2 日志分析

**下载飞控日志：**
```python
# 使用 pymavlink 下载日志
master.mav.log_request_list_send(
    master.target_system,
    master.target_component,
    0,  # 起始日志 ID
    10  # 数量
)
```

**分析日志：**
- 使用 Flight Review（https://review.px4.io）
- 上传.ulg 日志文件
- 查看飞行状态、传感器数据

### 6.3 常见问题

**问题 1：连接失败**
- 检查串口号/端口号
- 检查波特率（通常 57600 或 115200）
- 检查防火墙设置

**问题 2：消息乱码**
- 确认 MAVLink 版本（1.0/2.0）
- 检查字节序（大小端）
- 确认消息 ID 映射

**问题 3：控制无响应**
- 确认已解锁
- 确认模式正确
- 检查安全开关

---

## 七、进阶主题

### 7.1 自定义消息

**添加自定义消息：**
1. 修改 common.xml（消息定义文件）
2. 添加消息 ID（>10000 为保留区）
3. 重新生成代码（使用 mavgen.py）

### 7.2 安全签名

**MAVLink 2.0 签名：**
- 防止重放攻击
- 需要共享密钥
- 启用后所有消息带签名

### 7.3 高性能优化

**优化技巧：**
- 使用二进制协议（非文本）
- 批量发送消息
- 使用 UDP 而非 TCP
- 启用消息流控制

---

<div align="center">

**继续学习 →** [02-DJI SDK 对比](./02-DJI-SDK 对比.md)

**最后更新**: 2026-04-05

</div>
