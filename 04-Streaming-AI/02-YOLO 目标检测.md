# YOLO 目标检测实战

> 从训练到部署 —— 无人机航拍图像目标检测全流程

---

## 一、YOLO 概述

### 1.1 YOLO 发展历程

| 版本 | 发布时间 | 特点 | 适用场景 |
|------|---------|------|---------|
| YOLOv3 | 2018 | 经典版本、精度高 | 通用检测 |
| YOLOv4 | 2020 | 性能优化 | 实时检测 |
| YOLOv5 | 2020 | 工程化优化 | 工业应用 |
| YOLOv6 | 2022 | 效率提升 | 边缘部署 |
| YOLOv7 | 2022 | 精度提升 | 高精度需求 |
| YOLOv8 | 2023 | 多任务支持 | 检测/分割/姿态 |

### 1.2 无人机应用场景

**电力巡检：**
- 绝缘子破损检测
- 导线断股识别
- 杆塔锈蚀检测
- 异物识别

**安防监控：**
- 人员检测
- 车辆检测
- 异常行为识别

**农业监测：**
- 病虫害识别
- 作物长势分析
- 杂草检测

---

## 二、环境搭建

### 2.1 硬件要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| GPU | GTX 1060 6G | RTX 3080 10G |
| 内存 | 16GB | 32GB |
| 存储 | 100GB SSD | 500GB NVMe |
| CPU | 4 核 | 8 核以上 |

### 2.2 软件环境

**Ubuntu 20.04 安装：**
```bash
# 安装 NVIDIA 驱动
sudo apt install nvidia-driver-525

# 安装 CUDA 11.8
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-11-8

# 安装 cuDNN
# 从 NVIDIA 官网下载对应版本

# 安装 Python 环境
sudo apt install python3.8 python3-pip python3-venv
python3 -m venv yolo_env
source yolo_env/bin/activate

# 安装 PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装 YOLOv8
pip install ultralytics
```

### 2.3 Docker 部署（推荐）

**Dockerfile：**
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

RUN apt-get update && apt-get install -y \
    python3.8 python3-pip git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN pip3 install torch torchvision torchaudio \
    ultralytics opencv-python

CMD ["python3"]
```

**运行容器：**
```bash
docker run --gpus all -it \
  -v /data:/workspace/data \
  -v /models:/workspace/models \
  yolo-env
```

---

## 三、数据准备

### 3.1 数据标注

**标注工具：**
- LabelImg（矩形框标注）
- CVAT（在线标注）
- Roboflow（云端标注）

**标注格式（YOLO）：**
```
# 每行一个目标
<class_id> <x_center> <y_center> <width> <height>

# 示例（归一化坐标）
0 0.5 0.5 0.2 0.3  # 类别 0，中心 (0.5,0.5)，宽 0.2，高 0.3
```

### 3.2 数据集结构

```
dataset/
├── images/
│   ├── train/      # 训练图像
│   ├── val/        # 验证图像
│   └── test/       # 测试图像
├── labels/
│   ├── train/      # 训练标签
│   ├── val/        # 验证标签
│   └── test/       # 测试标签
└── data.yaml       # 数据配置文件
```

**data.yaml 配置：**
```yaml
train: ../dataset/images/train
val: ../dataset/images/val
test: ../dataset/images/test

nc: 5  # 类别数量
names: ['insulator', 'wire', 'tower', 'vehicle', 'person']  # 类别名称
```

### 3.3 数据增强

**常用增强方法：**
```python
from ultralytics import YOLO

# 训练时自动应用数据增强
model.train(
    data='data.yaml',
    augment=True,  # 启用数据增强
    hsv_h=0.015,   # 色调增强
    hsv_s=0.7,     # 饱和度增强
    hsv_v=0.4,     # 亮度增强
    flipud=0.0,    # 上下翻转概率
    fliplr=0.5,    # 左右翻转概率
    mosaic=1.0,    # mosaic 增强概率
    mixup=0.1,     # mixup 增强概率
)
```

---

## 四、模型训练

### 4.1 加载预训练模型

```python
from ultralytics import YOLO

# 加载 YOLOv8n 预训练模型
model = YOLO('yolov8n.pt')

# 或加载自定义模型
# model = YOLO('runs/detect/train/weights/best.pt')
```

### 4.2 训练配置

```python
# 开始训练
results = model.train(
    data='data.yaml',      # 数据配置
    epochs=100,            # 训练轮数
    imgsz=640,             # 输入图像尺寸
    batch=16,              # 批次大小
    device=0,              # GPU 设备（0 或'cpu'）
    workers=8,             # 数据加载线程数
    optimizer='SGD',       # 优化器
    lr0=0.01,              # 初始学习率
    patience=50,           # 早停耐心值
    save_period=10,        # 每 N 轮保存一次
    project='runs/detect', # 保存路径
    name='exp1',           # 实验名称
)
```

### 4.3 训练监控

**TensorBoard 监控：**
```bash
# 启动 TensorBoard
tensorboard --logdir=runs/detect
# 访问 http://localhost:6006
```

**关键指标：**
- mAP@50：IoU=0.5 时的平均精度
- mAP@50-95：不同 IoU 下的平均精度
- precision：查准率
- recall：召回率
- loss：损失函数值

---

## 五、模型推理

### 5.1 单张图像推理

```python
from ultralytics import YOLO
import cv2

# 加载模型
model = YOLO('runs/detect/exp1/weights/best.pt')

# 推理
results = model('image.jpg')

# 处理结果
for result in results:
    boxes = result.boxes  # 边界框
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()  # 坐标
        cls = int(box.cls[0])                   # 类别
        conf = float(box.conf[0])               # 置信度
        
        print(f'检测到：{result.names[cls]}, 置信度：{conf:.2f}')
        
        # 绘制边界框
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
```

### 5.2 批量推理

```python
# 批量处理文件夹
results = model(source='data/images/', save=True)

# 视频推理
results = model(source='video.mp4', stream=True)

for result in results:
    # 处理每一帧
    pass
```

### 5.3 实时检测

```python
import cv2
from ultralytics import YOLO

model = YOLO('best.pt')
cap = cv2.VideoCapture(0)  # 摄像头

while True:
    ret, frame = cap.read()
    results = model(frame)
    
    # 绘制结果
    annotated = results[0].plot()
    
    cv2.imshow('YOLO Detection', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 六、模型部署

### 6.1 导出模型

```python
from ultralytics import YOLO

model = YOLO('best.pt')

# 导出为 ONNX
model.export(format='onnx')

# 导出为 TensorRT
model.export(format='engine', device=0)

# 导出为 OpenVINO
model.export(format='openvino')
```

### 6.2 边缘部署（Jetson）

**TensorRT 部署：**
```python
import torch
import cv2

# 加载 TensorRT 模型
model = torch.jit.load('best.engine')

# 推理
img = cv2.imread('test.jpg')
img = cv2.resize(img, (640, 640))
img = img.transpose(2, 0, 1) / 255.0
img = torch.from_numpy(img).unsqueeze(0).cuda()

with torch.no_grad():
    pred = model(img)
```

### 6.3 性能优化

**优化技巧：**
- 使用更小模型（YOLOv8n/vs）
- 降低输入分辨率（640→416）
- 量化（FP32→FP16→INT8）
- 批处理（batch inference）

**性能对比：**
| 模型 | 输入 | GPU | FPS | mAP |
|------|------|-----|-----|-----|
| YOLOv8n | 640 | RTX 3080 | 120 | 37.3 |
| YOLOv8s | 640 | RTX 3080 | 85 | 44.9 |
| YOLOv8m | 640 | RTX 3080 | 50 | 50.2 |
| YOLOv8n | 640 | Jetson Orin | 45 | 37.3 |

---

## 七、无人机巡检实战

### 7.1 绝缘子破损检测

**数据集：**
- 图像数量：5000 张
- 类别：insulator_ok, insulator_broken
- 标注工具：LabelImg

**训练配置：**
```yaml
train: ../insulator/images/train
val: ../insulator/images/val

nc: 2
names: ['insulator_ok', 'insulator_broken']
```

**训练命令：**
```bash
yolo detect train data=insulator.yaml model=yolov8n.pt epochs=100 imgsz=640 batch=16
```

**推理结果：**
```python
results = model('tower_image.jpg')

for result in results:
    for box in result.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        
        if cls == 1 and conf > 0.8:  # 破损且置信度高
            print('发现破损绝缘子！')
            # 发送告警
```

### 7.2 导线异物检测

**难点：**
- 目标小（导线宽度<10 像素）
- 背景复杂（天空、树木）
- 光照变化

**解决方案：**
- 使用高分辨率输入（1280×1280）
- 增加小目标检测层
- 数据增强（Mosaic、MixUp）
- 使用注意力机制

---

## 八、常见问题

### Q1：训练 loss 不下降怎么办？

**答：** 
- 检查学习率（可能太大）
- 检查数据标注（可能有错误）
- 增加训练轮数
- 检查类别平衡

### Q2：mAP 很低怎么办？

**答：**
- 增加训练数据
- 改进数据质量
- 调整模型大小
- 延长训练时间

### Q3：推理速度慢怎么办？

**答：**
- 使用更小模型
- 降低输入分辨率
- 模型量化
- TensorRT 加速

### Q4：小目标检测效果差怎么办？

**答：**
- 增加输入分辨率
- 使用 P2 特征层
- 增加小目标样本
- 使用切片推理

---

<div align="center">

**继续学习 →** [03-边缘计算方案](./03-边缘计算方案.md)

**最后更新**: 2026-04-05

</div>
