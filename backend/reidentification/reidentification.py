import pandas as pd
import time
import numpy as np
import cv2
import os
import torch
from sqlalchemy import create_engine, text
from tqdm import tqdm
from PIL import Image
from torchvision import transforms
from torch.nn import functional as F


class ReIDProcessor:
    def __init__(self, db_url='mysql+pymysql://root:123456@localhost/trajectory',
                 models_path="D:/lyycode02/student-trajectory-generation/backend/resources/models", device=None):
        """
        初始化重识别处理器

        Args:
            db_url: 数据库连接URL
            models_path: 模型文件存放路径
            device: 运行设备，默认为自动选择GPU或CPU
        """
        self.db_engine = create_engine(db_url)
        self.models_path = models_path
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"使用设备: {self.device}")

        # 初始化变换
        self.transform = transforms.Compose([
            transforms.Resize((256, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        # 各种ReID模型
        self.models = {
            'osnet': self._init_osnet_model(),
            'mgn': self._init_mgn_model(),
            'transformer': self._init_transformer_model()
        }

        # 当前选择的模型
        self.current_model = None
        self.model_name = None

    def _init_osnet_model(self):
        """初始化OSNet模型"""
        try:
            from torchreid.reid.models import build_model

            print("初始化OSNet模型...")
            model_path = os.path.join(self.models_path, 'osnet_x1_0_market.pth')

            # 检查模型文件是否存在
            if not os.path.exists(model_path):
                print(f"警告: 模型文件不存在: {model_path}")
                return None

            # 构建OSNet模型
            model = build_model(
                name='osnet_x1_0',
                num_classes=751,  # Market-1501数据集类别数
                pretrained=False
            )

            # 加载预训练权重
            checkpoint = torch.load(model_path, map_location=self.device)
            model.load_state_dict(checkpoint)
            model.to(self.device)
            model.eval()

            print("OSNet模型加载成功")
            return model

        except Exception as e:
            print(f"OSNet模型初始化失败: {e}")
            return None

    def _init_mgn_model(self):
        """初始化MGN模型"""
        try:
            # 导入MGN模型所需的类和函数
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from backend.resources.models.mgn import Model
            from backend.resources.models.mgn.mgn import make_model

            print("初始化MGN模型...")

            # 使用相对路径，更具可移植性
            model_path = os.path.join(self.models_path, 'mgn')

            # 检查模型目录是否存在
            if not os.path.exists(model_path):
                print(f"警告: 模型目录不存在: {model_path}")
                return None

            # 创建一个类似于args的对象，包含MGN模型所需的参数
            class Args:
                def __init__(self):
                    self.model = 'MGN'
                    self.num_classes = 751  # Market-1501数据集类别数
                    self.feats = 256  # 特征维度
                    self.pool = 'avg'  # 池化方式
                    self.cpu = self.device == 'cpu'
                    self.nGPU = 0 if self.cpu else 1
                    self.save_models = False
                    self.pre_train = ''
                    self.resume = -1

            # 创建ckpt对象
            class Ckpt:
                def __init__(self):
                    self.dir = model_path

            args = Args()
            ckpt = Ckpt()

            # 构建MGN模型
            model = Model(args, ckpt)
            model.eval()

            print("MGN模型加载成功")
            return model

        except Exception as e:
            print(f"MGN模型初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _init_transformer_model(self):
        """初始化TransformerReID模型"""
        try:
            from backend.resources import models

            print("初始化TransformerReID模型...")
            model_path = os.path.join(self.models_path, 'transformer_reid_market.pth')

            # 检查模型文件是否存在
            if not os.path.exists(model_path):
                print(f"警告: 模型文件不存在: {model_path}")
                return None

            # 构建TransformerReID模型
            model = models(num_classes=751)  # Market-1501数据集类别数

            # 加载预训练权重
            checkpoint = torch.load(model_path, map_location=self.device)
            model.load_state_dict(checkpoint)
            model.to(self.device)
            model.eval()

            print("TransformerReID模型加载成功")
            return model

        except Exception as e:
            print(f"TransformerReID模型初始化失败: {e}")
            return None

    def set_model(self, algorithm='mgn'):
        """
        设置要使用的重识别模型

        Args:
            algorithm: 模型名称，可选值：'osnet', 'mgn', 'transformer'

        Returns:
            bool: 是否成功设置模型
        """
        if algorithm not in self.models:
            print(f"错误: 不支持的算法 '{algorithm}'")
            return False

        if self.models[algorithm] is None:
            print(f"错误: 模型 '{algorithm}' 未能正确加载")
            return False

        self.current_model = self.models[algorithm]
        self.model_name = algorithm
        print(f"已设置模型: {algorithm}")
        return True

    def extract_feature(self, img_path):
        """
        从图像中提取特征向量

        Args:
            img_path: 图像路径

        Returns:
            torch.Tensor: 特征向量
        """
        if self.current_model is None:
            print("错误: 未设置模型")
            return None

        try:
            # 加载图像
            img = Image.open(img_path).convert('RGB')
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)

            # 提取特征
            with torch.no_grad():
                if self.model_name == 'mgn':
                    # MGN模型特殊处理
                    _, _, features = self.current_model(img_tensor)
                    feature = torch.cat(features, dim=1)
                else:
                    # 其他模型通用处理
                    feature = self.current_model(img_tensor)

                # 归一化特征向量
                feature = F.normalize(feature, p=2, dim=1)

            return feature.cpu()

        except Exception as e:
            print(f"特征提取失败: {e}")
            return None

    def calculate_similarity(self, feature1, feature2):
        """
        计算两个特征向量之间的相似度

        Args:
            feature1: 第一个特征向量
            feature2: 第二个特征向量

        Returns:
            float: 相似度得分 (0-1)
        """
        # 使用余弦相似度
        similarity = torch.cosine_similarity(feature1, feature2).item()
        return max(0, similarity)  # 确保相似度在0-1之间

    def extract_frames_from_video(self, video_path, start_time=None, end_time=None, interval=1):
        """
        从视频中提取行人帧

        Args:
            video_path: 视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            interval: 提取帧的间隔（秒）

        Returns:
            list: 提取的帧图像列表
        """
        if not os.path.exists(video_path):
            print(f"错误: 视频文件不存在: {video_path}")
            return []

        try:
            # 打开视频
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"错误: 无法打开视频: {video_path}")
                return []

            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps

            # 设置开始和结束帧
            start_frame = 0
            if start_time is not None:
                start_frame = int(start_time * fps)

            end_frame = total_frames
            if end_time is not None:
                end_frame = min(int(end_time * fps), total_frames)

            # 设置提取帧的间隔
            frame_interval = int(interval * fps)

            # 提取帧
            frames = []
            current_frame = start_frame

            print(f"从视频中提取帧: {video_path}")
            print(f"FPS: {fps}, 总帧数: {total_frames}, 持续时间: {duration:.2f}秒")
            print(f"开始帧: {start_frame}, 结束帧: {end_frame}, 间隔: {frame_interval}")

            # 设置当前帧位置
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            # 使用tqdm显示进度
            for current_pos in tqdm(range(start_frame, end_frame, frame_interval), desc="提取帧"):
                # 设置当前帧位置
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

                # 读取帧
                ret, frame = cap.read()
                if not ret:
                    break

                # 转换为RGB格式并添加到列表
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)

            cap.release()
            print(f"成功提取了 {len(frames)} 帧")
            return frames

        except Exception as e:
            print(f"提取帧失败: {e}")
            return []

    def detect_pedestrians(self, frame):
        """
        从帧中检测行人

        Args:
            frame: 图像帧

        Returns:
            list: 行人图像列表
        """
        # 这里使用简单的行人检测器进行示例
        # 实际应用中，您可能需要使用更高级的检测器如YOLOv8、Faster R-CNN等
        try:
            # 创建HOG行人检测器
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

            # 检测行人
            boxes, weights = hog.detectMultiScale(
                frame,
                winStride=(8, 8),
                padding=(4, 4),
                scale=1.05
            )

            pedestrians = []
            for i, (x, y, w, h) in enumerate(boxes):
                # 提取行人图像
                person_img = frame[max(0, y):y + h, max(0, x):x + w]
                pedestrians.append({
                    'image': person_img,
                    'box': (x, y, w, h),
                    'confidence': weights[i]
                })

            return pedestrians

        except Exception as e:
            print(f"行人检测失败: {e}")
            return []

    def process(self, query_image_path, records=None, algorithm='mgn',
                threshold=0.7, callback=None, fetch_records=True):
        """
        执行重识别处理

        Args:
            query_image_path: 查询图像路径
            records: 包含学生记录的DataFrame，如果为None则从数据库获取
            algorithm: 使用的重识别算法
            threshold: 匹配阈值
            callback: 进度回调函数
            fetch_records: 是否从数据库获取记录

        Returns:
            处理后的DataFrame，包含视频路径等信息
        """
        print(f"使用{algorithm}算法进行重识别处理，阈值：{threshold}")

        # 设置模型
        if not self.set_model(algorithm):
            print("模型设置失败，无法继续处理")
            return pd.DataFrame()

        # 提取查询图像特征
        query_feature = self.extract_feature(query_image_path)
        if query_feature is None:
            print("无法从查询图像中提取特征")
            return pd.DataFrame()

        # 如果需要从数据库获取记录
        if fetch_records and records is None:
            records = self._fetch_records_from_db()

        if records is None or records.empty:
            print("没有记录需要处理")
            return pd.DataFrame()

        # 确保数据框有必要的列
        required_columns = ['id', 'student_id', 'camera_id', 'timestamp', 'location_x', 'location_y']
        missing_cols = [col for col in required_columns if col not in records.columns]
        if missing_cols:
            print(f"数据缺少必要的列: {missing_cols}")
            return pd.DataFrame()

        # 按时间排序
        sorted_records = records.sort_values(by='timestamp').reset_index(drop=True)

        # 进度跟踪
        total_records = len(sorted_records)

        # 阶段1: 准备视频路径和时间信息
        if callback:
            callback('preparing', 10)
        print("准备视频路径和时间信息...")

        # 添加视频路径
        records_with_video = self._add_video_paths(sorted_records)
        # 过滤掉没有视频的记录
        valid_records = records_with_video[records_with_video['video_path'].notna()].reset_index(drop=True)
        print(f"有效记录数: {len(valid_records)}/{total_records}")

        # 阶段2: 处理每条记录
        if callback:
            callback('processing', 20)

        # 创建结果DataFrame
        result_records = pd.DataFrame()

        # 处理记录
        for idx, record in tqdm(valid_records.iterrows(), total=len(valid_records), desc="处理记录"):
            try:
                # 获取视频路径和时间信息
                video_path = record['video_path']
                camera_id = record['camera_id']
                timestamp = pd.to_datetime(record['timestamp'])

                # 计算视频中的时间点（秒）
                video_start_time = pd.to_datetime(record['video_start_time'])
                time_diff = (timestamp - video_start_time).total_seconds()

                # 在时间点前后提取帧（5秒窗口）
                start_time = max(0, time_diff - 2.5)
                end_time = time_diff + 2.5

                # 提取帧
                frames = self.extract_frames_from_video(
                    video_path,
                    start_time=start_time,
                    end_time=end_time,
                    interval=0.5  # 每0.5秒提取一帧
                )

                if not frames:
                    print(f"从视频 {video_path} 中没有提取到帧")
                    continue

                # 在每一帧中检测行人
                max_similarity = 0
                best_match = None

                for frame_idx, frame in enumerate(frames):
                    pedestrians = self.detect_pedestrians(frame)

                    for ped_idx, pedestrian in enumerate(pedestrians):
                        # 将行人图像转换为PIL Image
                        ped_img = Image.fromarray(pedestrian['image'])

                        # 暂存行人图像以提取特征
                        temp_path = f"temp_pedestrian_{idx}_{frame_idx}_{ped_idx}.jpg"
                        ped_img.save(temp_path)

                        # 提取特征
                        ped_feature = self.extract_feature(temp_path)

                        # 删除临时文件
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                        if ped_feature is None:
                            continue

                        # 计算相似度
                        similarity = self.calculate_similarity(query_feature, ped_feature)

                        # 更新最佳匹配
                        if similarity > max_similarity:
                            max_similarity = similarity
                            best_match = pedestrian.copy()
                            best_match['similarity'] = similarity
                            best_match['frame_time'] = start_time + frame_idx * 0.5

                # 检查最佳匹配是否超过阈值
                if max_similarity >= threshold:
                    # 创建匹配记录
                    match_record = record.copy()
                    match_record['confidence'] = max_similarity
                    match_record['frame_time'] = best_match['frame_time']

                    # 添加到结果
                    result_records = pd.concat([result_records, pd.DataFrame([match_record])], ignore_index=True)

                    print(f"找到匹配: 记录ID={record['id']}, 相似度={max_similarity:.4f}, 时间={timestamp}")

            except Exception as e:
                print(f"处理记录 {idx} 时出错: {e}")

            # 更新进度
            if callback:
                progress = 20 + int(80 * (idx + 1) / len(valid_records))
                callback('processing', min(99, progress))

        # 最终阶段完成
        if callback:
            callback('completed', 100)

        # 排序并重置索引
        if not result_records.empty:
            result_records = result_records.sort_values(by=['confidence', 'timestamp'],
                                                        ascending=[False, True]).reset_index(drop=True)
            print(f"重识别处理完成，找到 {len(result_records)} 条匹配记录")
            if not result_records.empty:
                print("最佳匹配示例:")
                print(result_records.head(1)[['id', 'camera_id', 'timestamp', 'confidence', 'video_path']])
        else:
            print("未找到匹配记录")

        return result_records

    def _fetch_records_from_db(self, days=7):
        """
        从数据库获取最近的记录

        Args:
            days: 获取最近几天的记录

        Returns:
            DataFrame: 记录数据框
        """
        try:
            print(f"从数据库获取最近 {days} 天的记录...")

            query = text("""
            SELECT id, student_id, camera_id, timestamp, location_x, location_y
            FROM student_appearances
            WHERE timestamp >= DATE_SUB(CURRENT_DATE(), INTERVAL :days DAY)
            ORDER BY timestamp DESC
            """)

            with self.db_engine.connect() as conn:
                result = conn.execute(query, {"days": days})
                records = pd.DataFrame(result.fetchall())
                if not records.empty:
                    records.columns = result.keys()

            if records.empty:
                print("没有找到记录")
                return pd.DataFrame()

            print(f"从数据库获取了 {len(records)} 条记录")
            return records

        except Exception as e:
            print(f"从数据库获取记录失败: {e}")
            return pd.DataFrame()

    def _add_video_paths(self, records):
        """
        为每条记录添加对应的视频路径

        Args:
            records: 记录DataFrame

        Returns:
            添加了视频路径的DataFrame
        """
        print("正在从数据库获取视频路径信息...")

        # 初始化视频路径列
        result_records = records.copy()
        result_records['video_path'] = None
        result_records['video_start_time'] = None
        result_records['video_end_time'] = None

        try:
            # 为每条记录查询对应的视频信息
            for idx, record in tqdm(records.iterrows(), total=len(records), desc="查询视频路径"):
                camera_id = record['camera_id']
                record_time = pd.to_datetime(record['timestamp'])
                record_date = record_time.date()
                record_time_only = record_time.time()

                # 构造SQL查询
                query = text("""
                SELECT video_path, start_time, end_time 
                FROM camera_videos 
                WHERE camera_id = :camera_id 
                AND DATE(start_time) = :record_date 
                AND start_time <= :record_time 
                AND end_time >= :record_time
                """)

                with self.db_engine.connect() as conn:
                    result = conn.execute(
                        query,
                        {
                            "camera_id": camera_id,
                            "record_date": record_date,
                            "record_time": record_time
                        }
                    ).fetchone()

                    if result:
                        result_records.at[idx, 'video_path'] = result[0]
                        result_records.at[idx, 'video_start_time'] = result[1]
                        result_records.at[idx, 'video_end_time'] = result[2]

        except Exception as e:
            print(f"获取视频路径时出错: {e}")

        # 打印结果
        video_count = result_records['video_path'].notna().sum()
        print(f"共找到 {video_count}/{len(records)} 条记录的视频")

        return result_records


def demo_usage():
    """演示如何使用ReIDProcessor"""
    # 初始化处理器
    processor = ReIDProcessor(db_url='mysql+pymysql://root:123456@localhost/trajectory')

    # 查询图像路径
    query_image = "path/to/query_person.jpg"

    # 进度回调函数
    def progress_callback(stage, percent):
        print(f"处理阶段: {stage}, 进度: {percent}%")

    # 执行处理
    results = processor.process(
        query_image_path=query_image,
        algorithm='mgn',  # 使用MGN模型
        threshold=0.7,  # 设置匹配阈值
        callback=progress_callback
    )

    # 输出结果
    if not results.empty:
        print(f"\n找到 {len(results)} 条匹配记录:")
        for idx, result in results.iterrows():
            print(f"{idx + 1}. 相机: {result['camera_id']}, 时间: {result['timestamp']}, "
                  f"位置: ({result['location_x']}, {result['location_y']}), "
                  f"相似度: {result['confidence']:.4f}")
    else:
        print("未找到匹配记录")


if __name__ == "__main__":
    demo_usage()