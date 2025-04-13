import torch
from ultralytics import YOLO
import cv2
import numpy as np
from collections import defaultdict


class PersonTracker:
    def __init__(self,
                 model_path='yolov8m.pt',
                 tracker_config="botsort.yaml",
                 conf=0.5,
                 device='cpu',
                 iou=0.5,
                 img_size=(640, 640),
                 max_trace_length=50):  # 最大轨迹保留长度

        self.model = YOLO(model_path)
        self.tracker_config = tracker_config
        self.conf = conf
        self.device = device
        self.iou = iou
        self.img_size = img_size
        self.trajectories = defaultdict(list)  # 存储轨迹数据 {id: [(x1,y1), (x2,y2)...]}
        self.max_trace_length = max_trace_length
        self.colors = {}  # 存储每个ID对应的颜色

    def get_color(self, track_id):
        """为每个ID生成固定颜色"""
        if track_id not in self.colors:
            # 使用HSV颜色空间生成可区分的颜色
            hue = (180 * track_id // 10) % 180  # 每10个ID循环一次颜色
            color = cv2.cvtColor(np.uint8([[[hue, 255, 220]]]), cv2.COLOR_HSV2BGR)[0][0]
            self.colors[track_id] = (int(color[0]), int(color[1]), int(color[2]))
        return self.colors[track_id]

    def draw_trajectories(self, frame):
        """在帧上绘制轨迹"""
        for track_id, points in self.trajectories.items():
            if len(points) > 1:
                # 将浮点坐标转换为整数
                pts = np.array(points, dtype=np.int32)
                # 绘制光滑轨迹线
                cv2.polylines(frame, [pts], isClosed=False, color=self.get_color(track_id),
                              thickness=2, lineType=cv2.LINE_AA)

                # 在最新位置绘制ID标签
                last_point = points[-1]
                cv2.putText(frame, f"ID:{track_id}", (int(last_point[0]) + 10, int(last_point[1])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.get_color(track_id), 2)
        return frame

    def track_people(self, source=0, show=True):
        """
        执行实时跟踪
        :param source: 视频源，可以是摄像头设备号、视频文件路径或RTSP流地址
        :param show: 是否显示实时画面
        """
        results = self.model.track(
            source=source,
            stream=True,
            persist=True,  # 保持跟踪状态
            tracker=self.tracker_config,
            conf=self.conf,
            device=self.device,
            iou=self.iou,
            classes=[0],  # 只检测person类
            imgsz=self.img_size,
            verbose=False
        )

        for result in results:
            frame = result.plot()  # 获取绘制了检测框的原始帧
            if result.boxes.id is not None:
                # 提取跟踪信息
                track_ids = result.boxes.id.int().tolist()
                boxes = result.boxes.xywh.cpu().numpy()

                # 更新轨迹数据
                for track_id, box in zip(track_ids, boxes):
                    x, y = box[0], box[1]  # 获取中心点坐标
                    self.trajectories[track_id].append((x, y))

                    # 限制轨迹长度
                    if len(self.trajectories[track_id]) > self.max_trace_length:
                        self.trajectories[track_id].pop(0)

            # 绘制轨迹
            frame_with_traces = self.draw_trajectories(frame)

            # 显示结果
            if show:
                cv2.imshow('Person Tracking', frame_with_traces)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    # 使用示例
    tracker = PersonTracker(
        model_path='D:/lyycode02/student-trajectory-generation/backend/resources/models/yolov8m.pt',  # 模型文件路径
        device='cuda:0' if torch.cuda.is_available() else 'cpu',  # 自动选择设备
        conf=0.6,  # 置信度阈值
        iou=0.6,  # IoU阈值
        img_size=(1280, 720),  # 处理分辨率
        max_trace_length=30  # 轨迹保留长度
    )

    # 从摄像头捕获（0表示默认摄像头）
    # tracker.track_people(source=0)

    # 从视频文件捕获
    tracker.track_people(source="D:/lyycode02/student-trajectory-generation/backend/resources/videos/MOT17-04-FRCNN-raw.webm")