import platform

import cv2
import os
import torch
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from collections import defaultdict


class PersonTracker:
    def __init__(self, model_path="yolov8m.pt",
                 tracker_config="botsort.yaml",
                 conf=0.5, device='cpu', iou=0.5, img_size=(1280, 720)):
        """
        初始化行人跟踪器

        参数:
            model_path: YOLO模型路径
            tracker_config: 跟踪器配置文件
            conf: 检测置信度阈值
            device: 运行设备 ('cpu' 或 'cuda')
            iou: IoU阈值
            img_size: 处理图像大小
        """
        self.model = YOLO(model_path)
        self.tracker_config = tracker_config
        self.conf = conf
        self.device = device
        self.iou = iou
        self.img_size = img_size
        self.tracks = defaultdict(list)
        self.colors = {}

        # 确保输出目录存在
        os.makedirs('./results/images', exist_ok=True)
        os.makedirs('./results/videos', exist_ok=True)

    def _get_color(self, idx):
        """为每个轨迹ID生成唯一颜色"""
        if idx not in self.colors:
            self.colors[idx] = (
                np.random.randint(0, 255),
                np.random.randint(0, 255),
                np.random.randint(0, 255)
            )
        return self.colors[idx]

    # 添加停止方法
    def stop_tracking(self):
        self.is_running = False

    def track_people(self, source=0, show=True, max_trace_length=30, save_dir=None):
        """
        跟踪视频中的行人

        参数:
            source: 视频源(可以是文件路径或摄像头索引)
            show: 是否显示跟踪结果
            max_trace_length: 轨迹最大长度
            save_dir: 保存结果的目录

        返回:
            处理后的视频路径
        """
        # 确定保存路径
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            video_path = os.path.join(save_dir, 'results.mp4')
        else:
            video_path = './results/videos/results.mp4'

        # 视频预处理
        if isinstance(source, str) and not os.path.exists(source):
            print(f"错误: 无法找到视频文件 {source}")
            return None

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"错误: 无法打开视频源 {source}")
            return None

        # 获取视频属性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 设置输出视频编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        # 显示进度条的帧率间隔
        progress_interval = max(1, int(total_frames / 100))

        # 跟踪器参数
        model_kwargs = {
            'conf': self.conf,
            'iou': self.iou,
            'tracker': self.tracker_config,
            'device': self.device,
            'classes': 0,  # 仅跟踪类别0(行人)
            'agnostic_nms': True  # 添加这一行，使用 YOLOv8 自带的 NMS
        }

        # 从第一帧开始读取
        frame_idx = 0
        self.tracks.clear()  # 清除之前的轨迹
        self.colors.clear()  # 清除之前的颜色映射

        print(f"开始处理视频，总帧数: {total_frames}")
        self.is_running = True  # 重置运行状态

        while cap.isOpened() and self.is_running:  # 添加运行状态检查
            # 在每次循环开始检查是否应该继续
            if not self.is_running:
                print("接收到停止信号，中断处理")
                break

            ret, frame = cap.read()

            # 检查是否成功读取帧
            if not ret:
                print("视频帧读取结束或出错")
                break

            # 调整图像大小进行处理
            process_frame = cv2.resize(frame, (self.img_size[0], self.img_size[1]))

            # 运行YOLO检测和跟踪
            results = self.model.track(process_frame, persist=True, **model_kwargs)

            # 获取跟踪结果
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.int().cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()

                # 创建注释器
                annotator = Annotator(frame)

                # 处理每个跟踪目标
                for box, track_id, conf in zip(boxes, track_ids, confs):
                    x1, y1, x2, y2 = box

                    # 调整回原始图像尺寸
                    x1 = int(x1 * width / self.img_size[0])
                    y1 = int(y1 * height / self.img_size[1])
                    x2 = int(x2 * width / self.img_size[0])
                    y2 = int(y2 * height / self.img_size[1])

                    # 计算中心点
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)

                    # 获取该ID的唯一颜色
                    color = self._get_color(track_id)

                    # 添加到轨迹
                    self.tracks[track_id].append((center_x, center_y))

                    # 限制轨迹长度
                    if len(self.tracks[track_id]) > max_trace_length:
                        self.tracks[track_id] = self.tracks[track_id][-max_trace_length:]

                    # 绘制边界框
                    annotator.box_label([x1, y1, x2, y2], f"ID:{track_id} {conf:.2f}", color=color)

                    # 绘制轨迹
                    points = self.tracks[track_id]
                    for i in range(1, len(points)):
                        cv2.line(frame, points[i - 1], points[i], color, 2)

            # 添加帧计数
            cv2.putText(frame, f"Frame: {frame_idx}/{total_frames}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示处理进度
            if frame_idx % progress_interval == 0 or frame_idx == total_frames - 1:
                progress = (frame_idx + 1) / total_frames * 100
                print(f"进度: {progress:.1f}% ({frame_idx + 1}/{total_frames})")

            # 写入输出视频
            out.write(frame)

            # 显示结果
            if show:
                try:
                    cv2.imshow("Tracking", frame)
                    cv2.waitKey(1)
                except cv2.error:
                    # 如果 imshow 失败，可以保存帧到临时文件
                    if not hasattr(self, 'frame_count'):
                        self.frame_count = 0
                    # 每隔几帧保存一次，避免保存太多图片
                    if self.frame_count % 5 == 0:
                        cv2.imwrite(f"temp_frame_{self.frame_count}.jpg", frame)
                    self.frame_count += 1

            frame_idx += 1

        # 保存最后一帧作为结果图像
        cv2.imwrite('./results/images/results.jpg', frame)

        # 释放资源
        cap.release()
        out.release()
        cv2.destroyAllWindows()

        print(f"视频处理完成，结果已保存到 {video_path}")
        return video_path