# ZLMediaKit 流媒体服务器部署

> 从安装到配置 —— 打造无人机实时图传系统

---

## 一、ZLMediaKit 概述

### 1.1 什么是 ZLMediaKit

**ZLMediaKit** 是一个高性能的流媒体服务器，支持 RTMP/RTSP/HLS/WebRTC 等多种协议，由国人开发，开源免费。

**核心特点：**
- ✅ 高性能（C++11 开发，单核支持千路并发）
- ✅ 多协议（RTMP/RTSP/HLS/WebRTC/HTTP-FLV）
- ✅ 低延迟（WebRTC 延迟<500ms）
- ✅ 跨平台（Linux/Windows/macOS/ARM）
- ✅ 易集成（提供 C/C++/Java 接口）

### 1.2 无人机图传架构

```mermaid
graph LR
    A[无人机] --> B[机载编码器]
    B --> C[4G/5G 网络]
    C --> D[ZLMediaKit 服务器]
    D --> E[Web 端/客户端]
    D --> F[AI 分析系统]
    D --> G[云端存储]
```

### 1.3 应用场景

| 场景 | 协议 | 延迟要求 |
|------|------|---------|
| 实时监看 | WebRTC/RTMP | <1 秒 |
| 远程操控 | WebRTC | <500ms |
| 直播推流 | RTMP/HLS | 2-5 秒 |
| 录像存储 | RTMP | 不敏感 |

---

## 二、快速安装

### 2.1 Ubuntu/Debian 安装

**步骤 1：安装依赖**
```bash
sudo apt-get update
sudo apt-get install -y git cmake build-essential libssl-dev
```

**步骤 2：克隆源码**
```bash
git clone --depth 1 https://github.com/ZLMediaKit/ZLMediaKit.git
cd ZLMediaKit
```

**步骤 3：编译安装**
```bash
mkdir build && cd build
cmake ..
make -j4
sudo make install
```

**步骤 4：启动服务**
```bash
cd release/linux/Release/
./MediaServer
```

### 2.2 Docker 安装（推荐）

**拉取镜像：**
```bash
docker pull zlmediakit/zlmediakit:latest
```

**运行容器：**
```bash
docker run -d \
  --name zlmediakit \
  -p 1935:1935 \
  -p 8554:8554 \
  -p 8080:80 \
  -p 8443:443 \
  -p 10000:10000/udp \
  -v /opt/zlmediakit/config:/opt/ZLMediaKit/config \
  -v /opt/zlmediakit/www:/opt/ZLMediaKit/www \
  zlmediakit/zlmediakit:latest
```

**端口说明：**
| 端口 | 协议 | 用途 |
|------|------|------|
| 1935 | RTMP | 推流/拉流 |
| 8554 | RTSP | 拉流 |
| 8080 | HTTP | Web 界面/HLS |
| 8443 | HTTPS | 安全访问 |
| 10000/udp | WebRTC | 低延迟传输 |

### 2.3 macOS 安装

```bash
brew install cmake openssl
git clone --depth 1 https://github.com/ZLMediaKit/ZLMediaKit.git
cd ZLMediaKit
mkdir build && cd build
cmake ..
make -j4
./MediaServer
```

---

## 三、配置详解

### 3.1 配置文件位置

- Docker：`/opt/zlmediakit/config/config.ini`
- 源码编译：`config/config.ini`
- 运行时：`./config.ini`（当前目录）

### 3.2 核心配置项

```ini
# 服务器配置
[server]
port=1935              # RTMP 端口
http_port=80           # HTTP 端口
https_port=443         # HTTPS 端口
rtsp_port=554          # RTSP 端口
webrtc_port=10000      # WebRTC UDP 端口

# 协议配置
[protocol]
enable_rtmp=true       # 启用 RTMP
enable_rtsp=true       # 启用 RTSP
enable_hls=true        # 启用 HLS
enable_webrtc=true     # 启用 WebRTC
enable_http_flv=true   # 启用 HTTP-FLV

# 录制配置
[record]
enable=true            # 启用录制
file_path=/opt/record  # 录制文件路径
file_second=3600       # 单文件时长（秒）

# 转码配置
[transcode]
enable=false           # 启用转码（需 FFmpeg）
```

### 3.3 鉴权配置

**推流鉴权：**
```ini
[auth]
enable=true
secret=your_secret_key
publish_token=your_publish_token
```

**拉流鉴权：**
```ini
[auth]
play_token=your_play_token
```

---

## 四、推流与拉流

### 4.1 FFmpeg 推流

**推 RTMP 流：**
```bash
ffmpeg -re -i input.mp4 \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -c:a aac -ar 44100 \
  -f flv rtmp://your_server/live/stream_key
```

**参数说明：**
- `-re`：按帧率读取（模拟直播）
- `-preset ultrafast`：超低延迟编码
- `-tune zerolatency`：零延迟优化

**推 WebRTC 流：**
```bash
# 需要 SRT 或 WHIP 协议支持
ffmpeg -re -i input.mp4 \
  -c:v libx264 \
  -f srt srt://your_server:10000?streamid=stream_key
```

### 4.2 无人机机载推流

**使用 GStreamer：**
```bash
gst-launch-1.0 \
  v4l2src device=/dev/video0 ! \
  videoconvert ! \
  x264enc tune=zerolatency ! \
  rtmpsink location=rtmp://your_server/live/drone1
```

**使用 Python（OpenCV+FFmpeg）：**
```python
import cv2
import subprocess

# 启动 FFmpeg 进程
command = [
    'ffmpeg', '-re', '-i', 'pipe:0',
    '-c:v', 'libx264', '-preset', 'ultrafast',
    '-f', 'flv', 'rtmp://your_server/live/drone1'
]
process = subprocess.Popen(command, stdin=subprocess.PIPE)

# 读取摄像头并推流
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if ret:
        # 编码为 H264 并写入 stdin
        # （需要额外编码步骤）
        pass
```

### 4.3 拉流播放

**VLC 播放 RTMP：**
```
vlc rtmp://your_server/live/stream_key
```

**VLC 播放 WebRTC：**
```
打开 VLC → 媒体 → 打开网络串流 → 输入 WebRTC 地址
```

**Web 端播放（flv.js）：**
```html
<script src="https://cdn.bootcdn.net/ajax/libs/flv.js/1.6.2/flv.min.js"></script>
<video id="videoElement" controls></video>
<script>
  var flvPlayer = flvjs.createPlayer({
    type: 'flv',
    url: 'http://your_server/live/stream_key.flv'
  });
  flvPlayer.attachMediaElement(document.getElementById('videoElement'));
  flvPlayer.load();
  flvPlayer.play();
</script>
```

**Web 端播放（WebRTC）：**
```html
<video id="webrtc" autoplay playsinline></video>
<script>
  const pc = new RTCPeerConnection({
    iceServers: [{urls: 'stun:stun.l.google.com:19302'}]
  });
  
  pc.addTransceiver('video', {direction: 'recvonly'});
  
  fetch('http://your_server/index/api/webrtc?app=live&stream=stream_key&type=play')
    .then(res => res.json())
    .then(offer => pc.setRemoteDescription(offer))
    .then(() => pc.createAnswer())
    .then(answer => pc.setLocalDescription(answer))
    .then(() => {
      fetch('http://your_server/index/api/webrtc', {
        method: 'POST',
        body: JSON.stringify(pc.localDescription)
      });
    });
  
  pc.ontrack = (event) => {
    document.getElementById('webrtc').srcObject = event.streams[0];
  };
</script>
```

---

## 五、无人机图传实战

### 5.1 系统架构

```
┌─────────────┐      4G/5G      ┌─────────────┐
│   无人机    │ ───────────────> │ ZLMediaKit  │
│  (OBS/FFmpeg)│                │   服务器    │
└─────────────┘                └──────┬──────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
              ┌─────▼─────┐   ┌──────▼──────┐  ┌──────▼──────┐
              │ Web 监看  │   │ AI 分析系统 │  │  录像存储   │
              └───────────┘   └─────────────┘  └─────────────┘
```

### 5.2 低延迟优化

**编码器设置：**
```bash
ffmpeg -i input \
  -c:v libx264 \
  -preset ultrafast \
  -tune zerolatency \
  -x264-params keyint=30:min-keyint=30:no-scenecut \
  -b:v 2000k \
  -maxrate 2500k \
  -bufsize 2000k \
  -c:a aac \
  -f flv rtmp://server/live/stream
```

**关键参数：**
- `preset ultrafast`：最快编码速度
- `tune zerolatency`：零延迟模式
- `keyint=30`：关键帧间隔（GOP）
- `no-scenecut`：禁用场景切换

**网络优化：**
- 使用 5G 网络（低延迟）
- 启用 QoS（优先级）
- 使用 UDP 而非 TCP（WebRTC）

### 5.3 多路复用

**一机多推（备份）：**
```bash
# 主路
ffmpeg -i input -f flv rtmp://server1/live/stream
# 备路
ffmpeg -i input -f flv rtmp://server2/live/stream
```

**服务器转发：**
```ini
# config.ini
[forward]
enable=true
url=rtmp://backup_server/live/stream
```

---

## 六、运维管理

### 6.1 监控指标

| 指标 | 说明 | 阈值 |
|------|------|------|
| CPU 使用率 | 服务器负载 | <80% |
| 内存使用 | 并发路数相关 | <90% |
| 网络带宽 | 上行带宽 | <80% 带宽 |
| 推流数 | 当前推流数量 | 视服务器性能 |
| 拉流数 | 当前拉流数量 | 视服务器性能 |

### 6.2 日志管理

**日志位置：**
- Docker：`docker logs zlmediakit`
- 源码：`./logs/` 目录

**日志级别：**
```ini
[log]
level=2  # 0=调试，1=信息，2=警告，3=错误
```

### 6.3 故障排查

**问题 1：推流失败**
- 检查网络连通性
- 检查推流地址
- 检查鉴权 token
- 检查防火墙

**问题 2：延迟过高**
- 检查 GOP 设置
- 检查网络质量
- 检查服务器负载
- 启用 WebRTC 协议

**问题 3：画面卡顿**
- 检查带宽
- 降低码率
- 检查编码器性能
- 启用硬件编码

---

## 七、进阶功能

### 7.1 集群部署

**多服务器负载均衡：**
```
         ┌─────────────┐
         │   Nginx LB  │
         └──────┬──────┘
                │
    ┌───────────┼───────────┐
    │           │           │
┌───▼───┐  ┌───▼───┐  ┌───▼───┐
│Server1│  │Server2│  │Server3│
└───────┘  └───────┘  └───────┘
```

### 7.2 API 接口

**获取流列表：**
```bash
curl http://your_server/index/api/getMediaList?secret=your_secret
```

**踢流：**
```bash
curl http://your_server/index/api/kick?secret=your_secret&schema=rtmp&app=live&stream=stream_key
```

### 7.3 二次开发

**C++ 接口：**
```cpp
#include "Util/logger.h"
#include "Network/TcpServer.h"

int main() {
    // 初始化日志
    Logger::Instance().add(std::make_shared<ConsoleChannel>());
    
    // 启动服务器
    TcpServer::Ptr server(new TcpServer());
    server->start<Session>(1935);
    
    return 0;
}
```

---

<div align="center">

**继续学习 →** [02-YOLO 目标检测](./02-YOLO 目标检测.md)

**最后更新**: 2026-04-05

</div>
