import json
import os
import random
import time
import traceback

import numpy as np
import cv2
import torch
from PIL import Image
from torchvision import transforms
from scipy.spatial.distance import cosine
import sys
import logging
import datetime
from datetime import datetime, timedelta
import pandas as pd

# 配置全局日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ReIDProcessor:
    def __init__(self, db_interface=None):
        """
        初始化重识别处理器

        Args:
            db_interface: 数据库接口实例，用于查询视频和摄像头信息
        """
        logger.info("初始化 ReIDProcessor")
        self.models = {}
        # 为不同模型创建不同的transform
        self.transforms = {
            'mgn': transforms.Compose([
                transforms.Resize((384, 128)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ]),
            'agw': transforms.Compose([
                transforms.Resize((256, 128)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ]),
            'sbs': transforms.Compose([
                transforms.Resize((256, 128)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        }

        # 兼容原有代码的默认transform
        self.transform = self.transforms['mgn']
        self.db_interface = db_interface
        logger.info("ReIDProcessor 初始化完成，图像转换器已设置")

    def _load_model(self, algorithm):
        """加载指定的重识别模型"""
        logger.info(f"尝试加载 {algorithm} 模型")

        if algorithm in self.models:
            logger.info(f"{algorithm} 模型已加载，直接返回缓存模型")
            return self.models[algorithm]

        try:
            if algorithm == 'agw':
                logger.info("开始加载 FastReID AGW 模型")
                from fastreid.config import get_cfg
                from fastreid.modeling.meta_arch import build_model
                from fastreid.utils.checkpoint import Checkpointer
                import torch

                # 创建默认配置
                cfg = get_cfg()

                # 重要：设置为CPU设备
                cfg.MODEL.DEVICE = "cpu"

                # 加载配置文件
                config_path = os.path.join(os.path.dirname(__file__), '../resources/configs/agw.yml')
                logger.info(f"AGW 配置文件路径: {config_path}")

                if os.path.exists(config_path):
                    cfg.merge_from_file(config_path)
                    logger.info("成功加载AGW配置文件")
                else:
                    logger.warning(f"配置文件不存在，使用默认设置: {config_path}")
                    # 手动设置关键配置
                    cfg.MODEL.META_ARCHITECTURE = "Baseline"
                    cfg.MODEL.BACKBONE.NAME = "build_resnet_backbone"
                    cfg.MODEL.BACKBONE.DEPTH = "50x"
                    cfg.MODEL.HEADS.NAME = "EmbeddingHead"
                    cfg.MODEL.HEADS.EMBEDDING_DIM = 512
                    cfg.MODEL.HEADS.NECK_FEAT = "after"
                    cfg.MODEL.HEADS.POOL_LAYER = "GeneralizedMeanPooling"
                    cfg.MODEL.DEVICE = "cpu"

                # 创建模型
                model = build_model(cfg)
                model_path = os.path.join(os.path.dirname(__file__), '../resources/models/agw_model.pth')
                logger.info(f"AGW 模型路径: {model_path}")

                # 加载权重
                if os.path.exists(model_path):
                    Checkpointer(model).load(model_path)
                    logger.info("AGW模型权重加载成功")
                else:
                    logger.warning(f"AGW模型权重文件不存在: {model_path}")

                model.eval()
                self.models[algorithm] = model
                logger.info("AGW 模型加载成功并设置为评估模式")
                return model

            elif algorithm == 'sbs':
                logger.info("开始加载 FastReID SBS 模型")
                from fastreid.config import get_cfg
                from fastreid.modeling.meta_arch import build_model
                from fastreid.utils.checkpoint import Checkpointer
                import torch

                # 创建默认配置
                cfg = get_cfg()

                # 设置为CPU设备
                cfg.MODEL.DEVICE = "cpu"

                # 加载配置文件
                config_path = os.path.join(os.path.dirname(__file__), '../resources/configs/sbs.yml')
                logger.info(f"SBS 配置文件路径: {config_path}")

                if os.path.exists(config_path):
                    cfg.merge_from_file(config_path)
                    logger.info("成功加载SBS配置文件")
                else:
                    logger.warning(f"配置文件不存在，使用默认设置: {config_path}")
                    # 手动设置关键配置
                    cfg.MODEL.META_ARCHITECTURE = "Baseline"
                    cfg.MODEL.BACKBONE.NAME = "build_resnet_backbone"
                    cfg.MODEL.BACKBONE.DEPTH = "50x"
                    cfg.MODEL.HEADS.NAME = "EmbeddingHead"
                    cfg.MODEL.HEADS.EMBEDDING_DIM = 512
                    cfg.MODEL.HEADS.NECK_FEAT = "after"
                    cfg.MODEL.HEADS.POOL_LAYER = "GeneralizedMeanPoolingP"
                    cfg.MODEL.DEVICE = "cpu"

                # 创建模型
                model = build_model(cfg)
                model_path = os.path.join(os.path.dirname(__file__), '../resources/models/sbs_model.pth')
                logger.info(f"SBS 模型路径: {model_path}")

                # 加载权重
                if os.path.exists(model_path):
                    Checkpointer(model).load(model_path)
                    logger.info("SBS模型权重加载成功")
                else:
                    logger.warning(f"SBS模型权重文件不存在: {model_path}")

                model.eval()
                self.models[algorithm] = model
                logger.info("SBS 模型加载成功并设置为评估模式")
                return model

            elif algorithm == 'mgn':
                # MGN模型加载代码保持不变
                logger.info("开始加载 MGN 模型")
                # 添加项目根目录到搜索路径
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                logger.info(f"添加路径: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}")

                # 直接导入MGN类
                from backend.resources.models.mgn.mgn import MGN
                import torch

                # 初始化模型参数
                class Args:
                    def __init__(self):
                        self.num_classes = 751
                        self.feats = 256
                        self.pool = 'max'

                args = Args()
                logger.info("正在初始化 MGN 模型")
                model = MGN(args)

                # 加载权重
                model_path = os.path.join(os.path.dirname(__file__),
                                          '../resources/models/mgn/model/model_best.pt')
                logger.info(f"MGN模型路径: {model_path}")

                if os.path.exists(model_path):
                    model.load_state_dict(torch.load(model_path, map_location='cpu'))
                    logger.info("MGN模型权重加载成功")
                else:
                    logger.warning(f"MGN模型权重文件不存在: {model_path}")

                model.eval()
                self.models[algorithm] = model
                logger.info("MGN模型加载成功并设置为评估模式")
                return model

            else:
                logger.error(f"不支持的算法: {algorithm}")
                raise ValueError(f"不支持的算法: {algorithm}")

        except Exception as e:
            logger.error(f"加载 {algorithm} 模型失败: {str(e)}", exc_info=True)
            # 出错时返回一个默认模型，防止整个程序崩溃
            if algorithm != 'mgn':  # 仅对新增模型生效
                logger.info(f"加载失败，改为加载MGN模型")
                return self._load_model('mgn')
            raise

    def _extract_feature_vector(self, image_data, algorithm='mgn'):
        """从图像中提取特征向量"""
        logger.info(f"开始使用 {algorithm} 算法提取特征向量")
        try:
            # 加载模型
            model = self._load_model(algorithm)

            # 预处理图像
            if isinstance(image_data, np.ndarray):
                image = Image.fromarray(cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB))
            else:
                logger.error("不支持的图像数据格式")
                return None

            # 使用对应模型的transform
            if algorithm in self.transforms:
                transform = self.transforms[algorithm]
            else:
                transform = self.transform  # 使用默认transform

            # 转换图像
            image_tensor = transform(image).unsqueeze(0)

            # 提取特征
            with torch.no_grad():
                if algorithm == 'mgn':
                    features, *_ = model(image_tensor)
                    feature_vector = features.cpu().numpy()[0]
                    # 确保特征向量维度是2048
                    if len(feature_vector) != 2048:
                        logger.warning(f"MGN特征向量维度为{len(feature_vector)}，调整为2048")
                        if len(feature_vector) < 2048:
                            # 填充
                            padded = np.zeros(2048)
                            padded[:len(feature_vector)] = feature_vector
                            feature_vector = padded
                        else:
                            # 截断
                            feature_vector = feature_vector[:2048]
                elif algorithm in ['agw', 'sbs']:
                    # FastReID模型特征提取
                    features = model(image_tensor)
                    # SBS和AGW模型的特征提取方式
                    feature_vector = features.cpu().numpy()[0]
                    logger.info(f"FastReID {algorithm} 特征形状: {feature_vector.shape}")
                else:
                    logger.error(f"不支持的算法: {algorithm}")
                    return None

            logger.info(f"特征提取完成，维度: {len(feature_vector)}")
            return feature_vector

        except Exception as e:
            logger.error(f"特征提取失败: {str(e)}", exc_info=True)
            return None

    def _download_video_from_url(self, url, local_cache_dir="./resources/videos", original_filename=None):
        """
        从URL(如阿里云OSS)下载视频到本地缓存目录，保留原始文件名

        Args:
            url: 视频URL
            local_cache_dir: 本地缓存目录
            original_filename: 可选的原始文件名，如果提供则使用此文件名

        Returns:
            本地视频文件路径
        """
        import requests
        import os
        import hashlib
        from urllib.parse import urlparse, unquote

        logger.info(f"从URL下载视频: {url}")

        # 创建缓存目录
        os.makedirs(local_cache_dir, exist_ok=True)

        # 确定文件名
        video_name = None

        # 如果提供了原始文件名，优先使用它
        if original_filename:
            video_name = original_filename
            logger.info(f"使用提供的原始文件名: {video_name}")
        else:
            # 尝试从URL中提取文件名
            try:
                parsed_url = urlparse(url)
                path = unquote(parsed_url.path)

                # 从路径中获取文件名
                path_filename = os.path.basename(path)

                # 检查是否是有效的文件名
                if path_filename and '.' in path_filename:
                    video_name = path_filename
                    logger.info(f"从URL路径提取文件名: {video_name}")

                # 如果无法从路径获取有效文件名，检查查询参数
                if not video_name:
                    from urllib.parse import parse_qs
                    query_params = parse_qs(parsed_url.query)

                    # 阿里云OSS通常会有filename参数
                    if 'filename' in query_params:
                        video_name = query_params['filename'][0]
                        logger.info(f"从URL查询参数提取文件名: {video_name}")
            except Exception as e:
                logger.warning(f"从URL提取文件名失败: {str(e)}")

        # 如果仍然无法获取文件名，使用URL的哈希值
        if not video_name:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            video_name = f"{url_hash}.mp4"
            logger.info(f"无法获取原始文件名，使用URL哈希值作为文件名: {video_name}")

        # 确保文件名是安全的，处理非法字符
        import re
        video_name = re.sub(r'[\\/*?:"<>|]', '_', video_name)  # 替换Windows不支持的文件名字符

        local_path = os.path.join(local_cache_dir, video_name)

        # 如果缓存中已有该视频，直接返回
        if os.path.exists(local_path):
            logger.info(f"视频已存在于本地缓存中: {local_path}")
            return local_path

        try:
            # 下载视频
            logger.info(f"开始下载视频: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # 尝试从响应头中获取文件名(如果有Content-Disposition)
            if not original_filename and 'Content-Disposition' in response.headers:
                import re
                content_disposition = response.headers['Content-Disposition']
                filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if filename_match:
                    new_video_name = filename_match.group(1)
                    new_video_name = re.sub(r'[\\/*?:"<>|]', '_', new_video_name)  # 安全处理

                    # 只有当文件名看起来有效时才使用它
                    if new_video_name and '.' in new_video_name:
                        video_name = new_video_name
                        local_path = os.path.join(local_cache_dir, video_name)
                        logger.info(f"从响应头获取新文件名: {video_name}")

            # 保存视频到本地
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"视频下载完成，保存至: {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"下载视频时出错: {str(e)}", exc_info=True)
            return None

    def _get_video_paths(self, records):
        """
        根据记录信息获取对应的视频路径

        Args:
            records: 包含时间和摄像头ID的记录列表

        Returns:
            带有视频路径的记录列表
        """
        logger.info("开始获取视频路径")

        # 导入时间类
        from datetime import time as datetime_time

        if not self.db_interface:
            logger.warning("数据库接口未初始化，无法获取视频路径")
            return records

        for record in records:
            # 跳过查询记录，因为它已经有图像数据
            if record.get('id') == 'query':
                logger.info("跳过查询记录的视频路径获取")
                continue

            try:
                camera_id = record.get('camera_id')
                timestamp_str = record.get('timestamp')

                if not camera_id or not timestamp_str:
                    logger.warning(f"记录缺少摄像头ID或时间戳: {record}")
                    continue

                # 解析时间戳
                if isinstance(timestamp_str, str):
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = timestamp_str

                date = timestamp.date()
                time = timestamp.time()

                # 查询视频信息
                query = f"""
                SELECT video_path, start_time, end_time
                FROM camera_videos
                WHERE camera_id = {camera_id}
                  AND date = '{date}'
                  AND start_time <= '{time}'
                  AND end_time >= '{time}'
                """
                logger.info(f"执行SQL查询: {query}")

                # 执行查询
                video_info = self.db_interface.execute_query(query)

                if video_info and len(video_info) > 0:
                    video_path = video_info[0]['video_path']
                    start_time = video_info[0]['start_time']
                    end_time = video_info[0]['end_time']

                    logger.info(f"找到视频路径: {video_path}, 开始时间: {start_time}, 结束时间: {end_time}")

                    record['video_path'] = video_path

                    # 确保 start_time 和 end_time 是 datetime.time 类型
                    if isinstance(start_time, timedelta):
                        # 转换 timedelta 为 time 类型
                        seconds = start_time.total_seconds()
                        hours = int(seconds // 3600)
                        minutes = int((seconds % 3600) // 60)
                        seconds = int(seconds % 60)
                        start_time_obj = datetime_time(hours, minutes, seconds)
                    elif not isinstance(start_time, datetime_time):
                        # 尝试将字符串转换为 time 对象
                        try:
                            if isinstance(start_time, str):
                                start_time_obj = datetime.strptime(start_time, "%H:%M:%S").time()
                            else:
                                start_time_obj = datetime_time(0, 0, 0)  # 默认值
                        except Exception as e:
                            logger.warning(f"无法解析开始时间: {e}")
                            start_time_obj = datetime_time(0, 0, 0)  # 默认值
                    else:
                        start_time_obj = start_time

                    if isinstance(end_time, timedelta):
                        # 转换 timedelta 为 time 类型
                        seconds = end_time.total_seconds()
                        hours = int(seconds // 3600)
                        minutes = int((seconds % 3600) // 60)
                        seconds = int(seconds % 60)
                        end_time_obj = datetime_time(hours, minutes, seconds)
                    elif not isinstance(end_time, datetime_time):
                        # 尝试将字符串转换为 time 对象
                        try:
                            if isinstance(end_time, str):
                                end_time_obj = datetime.strptime(end_time, "%H:%M:%S").time()
                            else:
                                end_time_obj = datetime_time(23, 59, 59)  # 默认值
                        except Exception as e:
                            logger.warning(f"无法解析结束时间: {e}")
                            end_time_obj = datetime_time(23, 59, 59)  # 默认值
                    else:
                        end_time_obj = end_time

                    # 现在使用正确类型的时间对象来组合
                    record['video_start_time'] = datetime.combine(date, start_time_obj).strftime("%Y-%m-%d %H:%M:%S")
                    record['video_end_time'] = datetime.combine(date, end_time_obj).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    logger.warning(f"未找到对应的视频: 摄像头ID={camera_id}, 日期={date}, 时间={time}")
                    record['video_path'] = ""
                    record['video_start_time'] = timestamp_str
                    record['video_end_time'] = timestamp_str

            except Exception as e:
                logger.error(f"获取视频路径时发生错误: {str(e)}", exc_info=True)
                record['video_path'] = ""
                record['video_start_time'] = timestamp_str if isinstance(timestamp_str,
                                                                         str) else timestamp_str.strftime(
                    "%Y-%m-%d %H:%M:%S")
                record['video_end_time'] = timestamp_str if isinstance(timestamp_str, str) else timestamp_str.strftime(
                    "%Y-%m-%d %H:%M:%S")

        logger.info("视频路径获取完成")
        return records

    def _extract_frames_from_video(self, video_path, timestamp_str, window_seconds=10):
        """
        从视频中提取指定时间点附近的帧

        Args:
            video_path: 视频文件路径
            timestamp_str: 时间戳字符串
            window_seconds: 时间窗口大小（秒）

        Returns:
            提取的帧列表
        """
        logger.info(f"开始从视频中提取帧: {video_path}, 时间点: {timestamp_str}")

        # 检查是否是URL
        if video_path.startswith('http'):
            logger.info("检测到URL视频路径，开始下载")
            local_video_path = self._download_video_from_url(video_path)
            if not local_video_path:
                logger.error("下载视频失败")
                return []
            video_path = local_video_path

        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return []

        try:
            # 解析时间戳
            if isinstance(timestamp_str, str):
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            else:
                timestamp = timestamp_str

            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"无法打开视频文件: {video_path}")
                return []

            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_duration = total_frames / fps  # 视频总时长（秒）

            logger.info(f"视频信息: FPS={fps}, 总帧数={total_frames}, 时长={video_duration}秒")

            # 提取视频文件名中的日期和时间信息（假设格式为 camera_X_YYYY-MM-DD_HH-MM-SS.mp4）
            video_filename = os.path.basename(video_path)
            video_timestamp = None

            # 尝试从文件名解析时间
            try:
                parts = video_filename.split('_')
                date_part = parts[-2]
                time_part = parts[-1].split('.')[0]

                date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                time_obj = datetime.strptime(time_part, "%H-%M-%S").time()

                video_timestamp = datetime.combine(date_obj.date(), time_obj)
                logger.info(f"从文件名解析出视频开始时间: {video_timestamp}")
            except Exception as e:
                logger.warning(f"无法从文件名解析时间: {str(e)}")
                video_timestamp = None

            # 计算目标时间点对应的帧位置
            target_frame = None

            if video_timestamp:
                # 计算时间差（秒）
                time_diff = (timestamp - video_timestamp).total_seconds()

                if 0 <= time_diff <= video_duration:
                    target_frame = int(time_diff * fps)
                    logger.info(f"计算得到目标帧位置: {target_frame}")
                else:
                    logger.warning(f"目标时间点不在视频范围内: 时间差={time_diff}秒, 视频时长={video_duration}秒")

            # 如果无法计算目标帧，则使用视频中间位置
            if target_frame is None:
                target_frame = total_frames // 2
                logger.info(f"使用视频中间位置作为目标帧: {target_frame}")

            # 计算提取帧的范围
            start_frame = max(0, target_frame - int(window_seconds * fps / 2))
            end_frame = min(total_frames - 1, target_frame + int(window_seconds * fps / 2))

            logger.info(f"提取帧范围: {start_frame} 到 {end_frame}")

            # 提取帧
            frames = []
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            # 每秒提取1帧
            step = int(fps)
            for frame_idx in range(start_frame, end_frame + 1, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
                    logger.info(f"成功提取帧: {frame_idx}, 形状: {frame.shape}")
                else:
                    logger.warning(f"无法读取帧: {frame_idx}")

            cap.release()
            logger.info(f"完成帧提取，共提取 {len(frames)} 帧")
            return frames

        except Exception as e:
            logger.error(f"提取帧时发生错误: {str(e)}", exc_info=True)
            return []

    def _detect_person_in_frames(self, frames, save_dir=None):
        """
        在帧中检测人物并可选择保存到本地

        Args:
            frames: 视频帧列表
            save_dir: 保存检测结果的目录路径，如不提供则不保存

        Returns:
            检测到的人物图像列表
        """
        logger.info(f"开始在 {len(frames)} 帧中检测人物")

        try:
            # 加载人物检测模型（此处使用简单的HOG检测器作为示例）
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

            person_images = []

            # 创建保存目录
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                logger.info(f"行人图像将保存到: {save_dir}")

            # 当前时间戳用于文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for i, frame in enumerate(frames):
                # 检测人物
                boxes, weights = hog.detectMultiScale(frame, winStride=(8, 8), padding=(4, 4), scale=1.05)

                # 处理每个检测到的人物
                for j, (x, y, w, h) in enumerate(boxes):
                    # 调整边界框，确保不超出图像范围
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, frame.shape[1] - x)
                    h = min(h, frame.shape[0] - y)

                    if w > 0 and h > 0:
                        # 提取人物图像
                        person_img = frame[y:y + h, x:x + w]
                        person_images.append(person_img)

                        # 保存到本地
                        if save_dir:
                            filename = f"person_{timestamp}_frame{i}_det{j}.jpg"
                            filepath = os.path.join(save_dir, filename)
                            cv2.imwrite(filepath, person_img)
                            logger.info(f"已保存行人图像: {filepath}")

            logger.info(f"人物检测完成，共提取 {len(person_images)} 个人物图像")
            return person_images

        except Exception as e:
            logger.error(f"人物检测失败: {str(e)}", exc_info=True)
            return []

    def extract_features(self, records, algorithm='mgn', callback=None, save_dir=None):
        """
        提取特征向量，并返回匹配到的图像帧

        参数:
            records: 包含图像信息的记录列表
            algorithm: 使用的特征提取算法，默认为'mgn'
            callback: 进度回调函数
            save_dir: 保存检测结果的目录路径

        返回:
            添加了特征向量和图像数据的记录列表
        """
        logger.info(f"开始批量特征提取，使用算法: {algorithm}，记录数量: {len(records)}")
        try:
            if not records:
                logger.warning("没有提供记录，返回空列表")
                return []

            # 检查并打印输入记录的结构
            logger.info(f"特征提取输入记录示例: {records[0] if records else 'No records'}")

            # 如果当前实例没有数据库接口，使用默认的数据库接口
            if not hasattr(self, 'db_interface') or self.db_interface is None:
                logger.info("数据库接口未初始化，尝试导入默认数据库接口")
                try:
                    from backend.dbInterface.db_interface import DatabaseInterface
                    db_config = {
                        'type': 'mysql',
                        'host': 'localhost',
                        'port': 3306,
                        'user': 'root',
                        'password': '123456',
                        'database': 'trajectory',
                    }
                    self.db_interface = DatabaseInterface(db_config)
                    logger.info("成功初始化默认数据库接口")
                except Exception as e:
                    logger.error(f"初始化数据库接口失败: {str(e)}")

            # 获取视频路径
            if hasattr(self, 'db_interface') and self.db_interface:
                logger.info("开始获取视频路径")
                records = self._get_video_paths(records)
                logger.info("视频路径获取完成")
            else:
                logger.warning("无法获取视频路径，数据库接口未初始化")

            features_records = []
            # 新增: 保存所有帧的特征向量，按照摄像头ID组织
            all_frames_features = {}
            query_feature = None

            total_records = len(records)
            logger.info(f"总记录数: {total_records}")

            for idx, record in enumerate(records):
                logger.info(f"处理第 {idx + 1}/{total_records} 条记录")

                # 检查记录是否包含必要字段
                if 'id' not in record:
                    logger.warning(f"记录缺少id字段: {record}")
                    record['id'] = idx  # 使用索引作为临时ID
                    logger.info(f"为记录分配临时ID: {idx}")

                logger.info(f"处理记录ID: {record['id']}")

                # 初始化帧特征数组
                record_frames_features = []

                # 尝试获取图像数据
                image_data = None

                # 检查记录中是否包含图像数据
                if 'image' in record:
                    logger.info("使用直接提供的图像数据")
                    image_data = record['image']
                elif 'image_base64' in record:
                    logger.info("检测到base64编码的图像数据")
                    import base64
                    # 从base64解码图像
                    try:
                        # 检查是否包含data:image前缀
                        image_str = record['image_base64']
                        if ',' in image_str:
                            logger.info("检测到data:image前缀，进行分割处理")
                            image_str = image_str.split(',', 1)[1]

                        logger.info("解码base64图像数据")
                        image_bytes = base64.b64decode(image_str)
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        image_data = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if image_data is not None:
                            logger.info(f"成功从base64解码图像，形状: {image_data.shape}")
                        else:
                            logger.error("从base64解码图像失败，结果为None")
                    except Exception as e:
                        logger.error(f"解码base64图像时出错: {e}", exc_info=True)

                # 如果记录中没有图像数据，尝试从image_path加载
                if image_data is None and 'image_path' in record:
                    logger.info(f"尝试从路径加载图像: {record['image_path']}")
                    try:
                        image_data = cv2.imread(record['image_path'])
                        if image_data is not None:
                            logger.info(f"成功从路径加载图像，形状: {image_data.shape}")
                        else:
                            logger.error(f"从路径加载图像失败，结果为None: {record['image_path']}")
                    except Exception as e:
                        logger.error(f"从路径加载图像时出错: {e}", exc_info=True)

                # 如果记录中没有图像数据，尝试从视频中提取
                extracted_person_images = []
                if image_data is None and 'video_path' in record and record['video_path']:
                    logger.info(f"尝试从视频中提取图像: {record['video_path']}")
                    try:
                        # 从视频中提取帧
                        frames = self._extract_frames_from_video(
                            record['video_path'],
                            record.get('timestamp', '')
                        )

                        if frames:
                            # 从帧中检测人物
                            person_images = self._detect_person_in_frames(frames, save_dir=save_dir)
                            extracted_person_images = person_images  # 保存所有检测到的人物图像

                            if person_images:
                                # 使用第一个检测到的人物图像作为主要图像
                                image_data = person_images[0]
                                logger.info(f"成功从视频中提取人物图像，形状: {image_data.shape}")
                            else:
                                logger.warning("未在视频帧中检测到人物")
                        else:
                            logger.warning("未能从视频中提取帧")
                    except Exception as e:
                        logger.error(f"从视频中提取图像时出错: {e}", exc_info=True)

                # 保存提取到的所有图像帧
                if extracted_person_images:
                    record['extracted_frames'] = extracted_person_images
                    logger.info(f"为记录 {record['id']} 添加了 {len(extracted_person_images)} 个提取的图像帧")

                # 如果成功获取到图像数据，保存到记录中
                if image_data is not None:
                    record['processed_image'] = image_data.copy()
                    logger.info(f"为记录 {record['id']} 添加了处理后的图像数据")

                # 如果没有图像数据，使用一个默认图像
                if image_data is None:
                    logger.warning(f"记录 {record['id']} 没有图像数据，使用随机特征")
                    # 生成一个随机特征向量作为占位符
                    feature_vector = np.random.rand(256).astype(np.float32)
                    record['feature_vector'] = feature_vector.tolist()
                    features_records.append(record)
                    logger.info(f"为记录 {record['id']} 添加了随机特征向量")
                    continue

                # 为主图像提取特征向量
                logger.info(f"为记录 {record['id']} 提取特征向量，使用算法: {algorithm}")
                feature_vector = self._extract_feature_vector(image_data, algorithm)

                # 将特征向量添加到记录中
                record['feature_vector'] = feature_vector.tolist()

                # 如果是查询记录，保存其特征向量
                if record['id'] == 'query':
                    query_feature = feature_vector
                    logger.info("保存查询特征向量")

                # 提取所有检测到的人物图像的特征
                if extracted_person_images:
                    logger.info(f"开始为记录 {record['id']} 的所有 {len(extracted_person_images)} 个检测图像提取特征")
                    camera_id = record.get('camera_id', 'unknown')

                    # 为每个检测到的人物图像提取特征
                    for i, person_img in enumerate(extracted_person_images):
                        try:
                            person_feature = self._extract_feature_vector(person_img, algorithm)
                            if person_feature is not None:
                                frame_info = {
                                    'frame_index': i,
                                    'feature_vector': person_feature.tolist(),
                                    'record_id': record['id'],
                                    'camera_id': camera_id,
                                    'timestamp': record.get('timestamp', '')
                                }
                                record_frames_features.append(frame_info)
                                logger.info(f"成功为记录 {record['id']} 的第 {i + 1} 个人物图像提取特征")
                            else:
                                logger.warning(f"记录 {record['id']} 的第 {i + 1} 个人物图像特征提取失败")
                        except Exception as e:
                            logger.error(f"为记录 {record['id']} 的第 {i + 1} 个人物图像提取特征时出错: {str(e)}")

                # 将帧特征按摄像头ID组织
                if record_frames_features:
                    camera_id = record.get('camera_id', 'unknown')
                    if camera_id not in all_frames_features:
                        all_frames_features[camera_id] = []
                    all_frames_features[camera_id].extend(record_frames_features)
                    logger.info(f"为摄像头 {camera_id} 添加了 {len(record_frames_features)} 个帧特征")

                features_records.append(record)
                logger.info(f"记录 {record['id']} 特征提取完成")

                # 更新进度
                if callback:
                    progress = int((idx + 1) / total_records * 100)
                    logger.info(f"特征提取进度: {progress}%")
                    callback('featureMatching', progress // 2)  # 前半部分进度

            # 处理可序列化性
            for record in features_records:
                if 'feature_vector' in record and isinstance(record['feature_vector'], np.ndarray):
                    record['feature_vector'] = record['feature_vector'].tolist()

                # 删除无法序列化的图像数据
                for key in ['image', 'processed_image', 'extracted_frames']:
                    if key in record:
                        del record[key]

            # 添加所有帧的特征结果到返回值
            result = {
                'records': features_records,
                'all_frames_features': all_frames_features,
                'query_feature': query_feature.tolist() if query_feature is not None else None
            }

            logger.info(f"特征提取完成，处理了 {len(features_records)} 条记录")
            logger.info(
                f"共收集了 {sum(len(frames) for frames in all_frames_features.values())} 个帧特征，来自 {len(all_frames_features)} 个摄像头")

            return result

        except Exception as e:
            import traceback
            logger.error(f"特征提取过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"记录缺少必要的字段或提取特征时出错: {str(e)}")

    def match_features(self, records, threshold=0.6, callback=None, save_dir=None):
        """
        对特征向量进行相似度匹配，并保存匹配结果图像

        Args:
            records: 包含特征向量的记录列表和帧特征数据
            threshold: 相似度阈值，低于此值的匹配将被忽略
            callback: 进度回调函数
            save_dir: 保存匹配结果图像的目录路径

        Returns:
            匹配结果列表
        """
        try:
            logger.info(f"开始特征匹配")
            import cv2

            # 解析输入数据
            features_records = records.get('records', [])
            all_frames_features = records.get('all_frames_features', {})
            query_feature = records.get('query_feature')

            logger.info(f"特征匹配输入: {len(features_records)} 条记录, {len(all_frames_features)} 个摄像头")
            if query_feature is None:
                logger.warning("没有提供查询特征向量，将从记录中查找")

            # 创建保存目录
            if save_dir is None:
                save_dir = os.path.join("matching_results", datetime.now().strftime("%Y%m%d_%H%M%S"))

            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                logger.info(f"匹配结果将保存到: {save_dir}")

            # 查找查询记录的特征向量和图像
            query_image = None
            if query_feature is None:
                for record in features_records:
                    if record.get('id') == 'query' and 'feature_vector' in record:
                        query_feature = record['feature_vector']
                        # 如果有图像数据，保存查询图像
                        if 'image' in record and record['image'] is not None:
                            query_image = record['image']
                            if isinstance(query_image, str) and query_image.startswith('data:image'):
                                # 处理base64编码的图像
                                import base64
                                query_image = query_image.split(',')[1]
                                query_image = base64.b64decode(query_image)
                                query_image = np.frombuffer(query_image, dtype=np.uint8)
                                query_image = cv2.imdecode(query_image, cv2.IMREAD_COLOR)

                            query_image_path = os.path.join(save_dir, "query_image.jpg")
                            cv2.imwrite(query_image_path, query_image)
                            logger.info(f"保存查询图像: {query_image_path}")

                        logger.info("从记录中找到查询特征向量")
                        break

            if query_feature is None:
                logger.error("未找到查询特征向量，无法进行匹配")
                return []

            # 将查询特征转换为numpy数组
            if isinstance(query_feature, list):
                query_feature = np.array(query_feature)

            # 匹配主记录
            logger.info("开始匹配主记录")
            main_matches = []
            total_records = len(features_records)

            for i, record in enumerate(features_records):
                if record.get('id') == 'query':
                    continue  # 跳过查询记录

                try:
                    if 'feature_vector' in record:
                        feature_vector = record['feature_vector']
                        if isinstance(feature_vector, list):
                            feature_vector = np.array(feature_vector)

                        # 计算相似度
                        similarity = 1 - cosine(query_feature, feature_vector)

                        if similarity > threshold:
                            match_info = {
                                'id': record.get('id'),
                                'camera_id': record.get('camera_id', 'unknown'),
                                'timestamp': record.get('timestamp', ''),
                                'student_id': record.get('student_id', ''),
                                'name': record.get('name', ''),
                                'location_x': record.get('location_x', 0),
                                'location_y': record.get('location_y', 0),
                                'confidence': float(similarity),
                                'video_path': record.get('video_path', ''),
                                'video_start_time': record.get('video_start_time', ''),
                                'video_end_time': record.get('video_end_time', ''),
                                'matched_frames': []  # 用于存储匹配的帧信息
                            }
                            main_matches.append(match_info)
                            logger.info(f"找到主记录匹配: ID={record.get('id')}, 相似度={similarity}")

                            # 保存主记录图像(如果有)
                            if 'processed_image' in record and record['processed_image'] is not None:
                                record_image = record['processed_image']
                                if isinstance(record_image, np.ndarray):
                                    # 添加标注信息
                                    img_with_info = record_image.copy()
                                    text = f"ID: {record.get('id')}, 相似度: {similarity:.2f}"
                                    cv2.putText(img_with_info, text, (10, 30),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                                    # 保存图像（添加相似度到文件名）
                                    record_img_path = os.path.join(save_dir,
                                                                   f"record_{record.get('id')}_sim_{similarity:.4f}.jpg")
                                    cv2.imwrite(record_img_path, img_with_info)
                                    logger.info(f"保存匹配记录图像: {record_img_path}")
                            elif 'image' in record and record['image'] is not None:
                                record_image = record['image']
                                if isinstance(record_image, np.ndarray):
                                    # 添加标注信息
                                    img_with_info = record_image.copy()
                                    text = f"ID: {record.get('id')}, 相似度: {similarity:.2f}"
                                    cv2.putText(img_with_info, text, (10, 30),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                                    # 保存图像（添加相似度到文件名）
                                    record_img_path = os.path.join(save_dir,
                                                                   f"record_{record.get('id')}_sim_{similarity:.4f}.jpg")
                                    cv2.imwrite(record_img_path, img_with_info)
                                    logger.info(f"保存匹配记录图像: {record_img_path}")
                except Exception as e:
                    logger.error(f"匹配记录 {record.get('id')} 时出错: {str(e)}")

                # 更新进度
                if callback:
                    progress = int((i + 1) / total_records * 100)
                    callback('featureMatching', 50 + progress // 2)  # 后半部分进度

            # 匹配帧级特征
            logger.info(f"开始匹配各摄像头的帧级特征，共 {len(all_frames_features)} 个摄像头")

            for camera_id, frames in all_frames_features.items():
                logger.info(f"处理摄像头 {camera_id} 的 {len(frames)} 个帧特征")

                # 为该摄像头创建单独的保存目录
                camera_save_dir = os.path.join(save_dir, f"camera_{camera_id}")
                os.makedirs(camera_save_dir, exist_ok=True)

                # 为每个帧计算与查询特征的相似度
                for frame_info in frames:
                    try:
                        frame_feature = frame_info.get('feature_vector')
                        if frame_feature:
                            if isinstance(frame_feature, list):
                                frame_feature = np.array(frame_feature)

                            # 计算相似度
                            similarity = 1 - cosine(query_feature, frame_feature)

                            if similarity > threshold:
                                # 找到对应的主记录
                                record_id = frame_info.get('record_id')
                                matched_record = next((r for r in main_matches if r.get('id') == record_id), None)

                                # 如果找不到对应的主记录，可能是因为主记录相似度低于阈值
                                # 在这种情况下，我们仍然保留高相似度的帧
                                if matched_record is None:
                                    # 查找原始记录
                                    original_record = next((r for r in features_records if r.get('id') == record_id),
                                                           None)

                                    if original_record:
                                        # 创建一个新的主匹配记录
                                        matched_record = {
                                            'id': record_id,
                                            'camera_id': camera_id,
                                            'timestamp': original_record.get('timestamp',
                                                                             frame_info.get('timestamp', '')),
                                            'student_id': original_record.get('student_id', ''),
                                            'name': original_record.get('name', ''),
                                            'location_x': original_record.get('location_x', 0),
                                            'location_y': original_record.get('location_y', 0),
                                            'confidence': float(similarity),  # 使用这个帧的相似度
                                            'video_path': original_record.get('video_path', ''),
                                            'video_start_time': original_record.get('video_start_time', ''),
                                            'video_end_time': original_record.get('video_end_time', ''),
                                            'matched_frames': []  # 用于存储匹配的帧信息
                                        }
                                        main_matches.append(matched_record)
                                        logger.info(f"基于帧匹配创建新的主记录: ID={record_id}, 相似度={similarity}")

                                # 添加匹配的帧信息
                                if matched_record:
                                    frame_match = {
                                        'frame_index': frame_info.get('frame_index', 0),
                                        'similarity': float(similarity),
                                        'camera_id': camera_id,
                                        'timestamp': frame_info.get('timestamp', '')
                                    }
                                    matched_record['matched_frames'].append(frame_match)
                                    logger.info(
                                        f"添加帧匹配: 记录ID={record_id}, 帧索引={frame_info.get('frame_index')}, 相似度={similarity}")

                                    # 保存匹配的帧图像
                                    if 'image' in frame_info and frame_info['image'] is not None:
                                        frame_image = frame_info['image']
                                        if isinstance(frame_image, np.ndarray):
                                            # 添加标注信息
                                            img_with_info = frame_image.copy()
                                            text = f"ID: {record_id}, 帧: {frame_info.get('frame_index')}, 相似度: {similarity:.2f}"
                                            cv2.putText(img_with_info, text, (10, 30),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                                            # 绘制矩形框，如果有边界框信息
                                            if 'bbox' in frame_info and len(frame_info['bbox']) == 4:
                                                x, y, w, h = frame_info['bbox']
                                                cv2.rectangle(img_with_info, (x, y), (x + w, y + h), (0, 255, 0), 2)

                                            # 保存图像（添加相似度到文件名）
                                            frame_img_path = os.path.join(
                                                camera_save_dir,
                                                f"match_{record_id}_frame_{frame_info.get('frame_index')}_sim_{similarity:.4f}.jpg"
                                            )
                                            cv2.imwrite(frame_img_path, img_with_info)
                                            logger.info(f"保存匹配帧图像: {frame_img_path}")
                    except Exception as e:
                        import traceback
                        logger.error(f"匹配帧特征时出错: {str(e)}")
                        logger.error(traceback.format_exc())

            # 对匹配结果按相似度排序
            main_matches.sort(key=lambda x: x['confidence'], reverse=True)

            # 对每个记录中的帧匹配也按相似度排序
            for match in main_matches:
                if 'matched_frames' in match and match['matched_frames']:
                    match['matched_frames'].sort(key=lambda x: x['similarity'], reverse=True)

            logger.info(f"特征匹配完成，共找到 {len(main_matches)} 条主记录匹配")

            # 生成简单的匹配结果网页，方便查看
            if main_matches and save_dir:
                html_path = os.path.join(save_dir, "matching_results.html")
                try:
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write("<html><head><title>匹配结果</title>")
                        f.write("<style>body{font-family:sans-serif;} table{border-collapse:collapse;width:100%}")
                        f.write(
                            "td,th{border:1px solid #ddd;padding:8px;} tr:nth-child(even){background-color:#f2f2f2}")
                        f.write("</style></head><body>")
                        f.write(f"<h1>匹配结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>")
                        f.write(
                            "<table><tr><th>ID</th><th>相似度</th><th>摄像头</th><th>时间</th><th>匹配帧数</th></tr>")

                        for match in main_matches:
                            f.write(f"<tr><td>{match.get('id')}</td>")
                            f.write(f"<td>{match.get('confidence', 0):.4f}</td>")
                            f.write(f"<td>{match.get('camera_id', 'unknown')}</td>")
                            f.write(f"<td>{match.get('timestamp', '')}</td>")
                            f.write(f"<td>{len(match.get('matched_frames', []))}</td></tr>")

                        f.write("</table></body></html>")
                    logger.info(f"生成匹配结果网页: {html_path}")
                except Exception as e:
                    logger.error(f"生成匹配结果网页失败: {str(e)}")

            return main_matches

        except Exception as e:
            import traceback
            logger.error(f"特征匹配过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    def save_trajectory_to_database(self, trajectory_data, db_interface):
        """
        将学生轨迹信息保存到数据库

        参数:
            trajectory_data: 包含轨迹信息的字典，包括学号、时间区间、经过摄像头、轨迹长度、总用时等
            db_interface: 数据库接口对象

        返回:
            成功返回轨迹记录ID，失败返回None
        """
        try:
            # 确保数据库连接有效
            if db_interface.conn.open is False:
                db_interface.reconnect()

            cursor = db_interface.conn.cursor()

            # 从轨迹数据中提取信息
            student_id = trajectory_data.get('studentId')
            time_range = trajectory_data.get('timeRange', [])
            start_time = time_range[0] if len(time_range) > 0 else None
            end_time = time_range[1] if len(time_range) > 1 else None
            camera_sequence = trajectory_data.get('traversedCameras', [])
            total_distance = trajectory_data.get('trajectoryLength', 0)
            total_duration = trajectory_data.get('totalTime', '0分钟')

            # 生成轨迹会话ID (可以用时间戳加随机数)
            tracking_session_id = f"track_{int(time.time())}_{random.randint(1000, 9999)}"

            # 处理路径点数据
            path_points = []
            for point in trajectory_data.get('trajectoryPoints', []):
                if point.get('type') == 'camera':  # 只保存摄像头点作为关键点
                    path_points.append({
                        'camera_id': point.get('cameraId'),
                        'camera_name': point.get('name', f"摄像头{point.get('cameraId')}"),
                        'timestamp': point.get('timestamp'),
                        'location_x': point.get('position', [0, 0])[0],
                        'location_y': point.get('position', [0, 0])[1],
                        'confidence': point.get('confidence', 1.0)
                    })

            # 将路径点转换为JSON字符串
            path_points_json = json.dumps(path_points)

            # 将摄像头序列连接为字符串，包含摄像头名称
            camera_sequence_str = ','.join([f"{cam['id']}({cam.get('name', '')})" for cam in
                                            trajectory_data.get('cameras',
                                                                [])]) if 'cameras' in trajectory_data else ','.join(
                camera_sequence)

            # 计算平均速度
            # 解析总用时为分钟数
            duration_minutes = 0
            if '小时' in total_duration:
                parts = total_duration.split('小时')
                hours = int(parts[0])
                minutes_part = parts[1].replace('分钟', '').strip()
                minutes = int(minutes_part) if minutes_part else 0
                duration_minutes = hours * 60 + minutes
            else:
                duration_minutes = int(total_duration.replace('分钟', '').strip())

            # 计算平均速度 (米/分钟)
            average_speed = total_distance / duration_minutes if duration_minutes > 0 else 0

            # 插入轨迹记录
            insert_sql = """
            INSERT INTO student_trajectories 
            (student_id, tracking_session_id, start_time, end_time, path_points, 
             camera_sequence, total_distance, average_speed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(insert_sql, (
                student_id,
                tracking_session_id,
                start_time,
                end_time,
                path_points_json,
                camera_sequence_str,
                total_distance,
                average_speed
            ))

            db_interface.conn.commit()
            trajectory_id = cursor.lastrowid

            logger.info(f"已保存学生轨迹: ID={trajectory_id}, 学号={student_id}, 会话ID={tracking_session_id}")
            logger.info(f"轨迹摄像头序列: {camera_sequence_str}")
            logger.info(f"轨迹长度: {total_distance}米, 用时: {total_duration}, 平均速度: {average_speed:.2f}米/分钟")

            return trajectory_id

        except Exception as e:
            logger.error(f"保存轨迹数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()

    def get(self, param):
        """
        获取指定参数的值

        Args:
            param: 参数名称

        Returns:
            参数值
        """
        if hasattr(self, param):
            return getattr(self, param)
        else:
            logger.warning(f"参数 {param} 不存在")
            return None