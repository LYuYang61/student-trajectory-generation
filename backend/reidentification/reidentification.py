import os
import numpy as np
import cv2
import torch
from PIL import Image
from torchvision import transforms
import sys
import logging
import datetime
from datetime import datetime, timedelta, time
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
        self.transform = transforms.Compose([
            transforms.Resize((384, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self.db_interface = db_interface
        logger.info("ReIDProcessor 初始化完成，图像转换器已设置")

    def _load_model(self, algorithm):
        """加载指定的重识别模型"""
        logger.info(f"尝试加载 {algorithm} 模型")

        if algorithm in self.models:
            logger.info(f"{algorithm} 模型已加载，直接返回缓存模型")
            return self.models[algorithm]

        try:
            if algorithm == 'osnet':
                logger.info("开始加载 OSNet 模型")
                # 实现OSNet模型加载
                from torchreid.reid.models.osnet import osnet_x1_0
                model = osnet_x1_0(name='osnet', num_classes=751)
                model_path = os.path.join(os.path.dirname(__file__), '../resources/models/osnet_x1_0.pth')
                logger.info(f"OSNet 模型路径: {model_path}")

                logger.info("正在加载 OSNet 模型权重")
                model.load_state_dict(torch.load(model_path, map_location='cpu'))
                model.eval()
                self.models[algorithm] = model
                logger.info("OSNet 模型加载成功并设置为评估模式")
                return model

            elif algorithm == 'mgn':
                logger.info("开始加载 MGN 模型")
                # 添加项目根目录到搜索路径
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                logger.info(f"添加路径: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}")

                # 直接导入MGN类
                from backend.resources.models.mgn.mgn import MGN

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
                                          '../resources/models/mgn/model_best.pt')
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

            elif algorithm == 'transformer':
                logger.info("开始加载 TransReID 模型")
                # 实现TransReID模型加载
                from backend.resources.models.transreid import build_transformer_model
                logger.info("正在构建 TransReID 模型结构")
                model = build_transformer_model()
                model_path = os.path.join(os.path.dirname(__file__), '../resources/models/transreid.pth')
                logger.info(f"TransReID 模型路径: {model_path}")

                logger.info("正在加载 TransReID 模型权重")
                model.load_state_dict(torch.load(model_path, map_location='cpu'))
                model.eval()
                self.models[algorithm] = model
                logger.info("TransReID 模型加载成功并设置为评估模式")
                return model

            else:
                logger.error(f"不支持的算法: {algorithm}")
                raise ValueError(f"不支持的算法: {algorithm}")

        except Exception as e:
            logger.error(f"加载 {algorithm} 模型失败: {str(e)}", exc_info=True)
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

            # 转换图像
            image_tensor = self.transform(image).unsqueeze(0)

            # 提取特征
            with torch.no_grad():
                if algorithm == 'osnet':
                    features = model(image_tensor)
                    feature_vector = features.cpu().numpy()[0]
                elif algorithm == 'mgn':
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
                else:
                    # 其他模型处理...
                    pass

            logger.info(f"特征提取完成，维度: {len(feature_vector)}")
            return feature_vector

        except Exception as e:
            logger.error(f"特征提取失败: {str(e)}", exc_info=True)
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
                                # 使用第一个检测到的人物图像
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

                # 根据所选算法提取特征
                logger.info(f"为记录 {record['id']} 提取特征向量，使用算法: {algorithm}")
                feature_vector = self._extract_feature_vector(image_data, algorithm)

                # 将特征向量添加到记录中
                record['feature_vector'] = feature_vector.tolist()
                features_records.append(record)
                logger.info(f"记录 {record['id']} 特征提取完成")

                # 更新进度
                if callback:
                    progress = int((idx + 1) / total_records * 100)
                    logger.info(f"特征提取进度: {progress}%")
                    callback('featureMatching', progress // 2)  # 前半部分进度

            logger.info(f"特征提取完成，处理了 {len(features_records)} 条记录")
            return features_records

        except Exception as e:
            import traceback
            logger.error(f"特征提取过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"记录缺少必要的字段或提取特征时出错: {str(e)}")

    def match_features(self, records, threshold=0.6, callback=None, save_dir=None):
        """
        对特征向量进行相似度匹配，并保存匹配结果图像

        Args:
            records: 包含特征向量的记录列表
            threshold: 相似度阈值，低于此值的匹配将被忽略
            callback: 进度回调函数
            save_dir: 保存匹配结果图像的目录路径

        Returns:
            匹配结果列表
        """
        try:
            from scipy.spatial.distance import cosine
            import traceback
            import os
            import cv2

            logger.info(f"开始特征匹配，记录数量: {len(records)}")

            # 创建保存目录
            if save_dir is None:
                save_dir = os.path.join("matching_results", datetime.now().strftime("%Y%m%d_%H%M%S"))

            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                logger.info(f"匹配结果将保存到: {save_dir}")

            # 提取所有有效的特征向量
            logger.info("提取所有特征向量")
            feature_vectors = []
            valid_indices = []
            record_ids = []
            expected_dim = 2048  # 统一使用2048维特征向量

            for i, record in enumerate(records):
                if 'feature_vector' in record and record['feature_vector'] is not None:
                    feature_vector = record['feature_vector']
                    # 统一特征向量维度
                    if len(feature_vector) != expected_dim:
                        logger.warning(
                            f"记录 {record['id']} 的特征向量维度为 {len(feature_vector)}，需要调整为 {expected_dim}")
                        if len(feature_vector) < expected_dim:
                            # 如果维度不足，填充零
                            padded_vector = np.zeros(expected_dim)
                            padded_vector[:len(feature_vector)] = feature_vector
                            feature_vector = padded_vector
                        else:
                            # 如果维度过大，截断
                            feature_vector = feature_vector[:expected_dim]

                    feature_vectors.append(feature_vector)
                    valid_indices.append(i)
                    record_ids.append(record['id'])

            logger.info(f"提取了 {len(feature_vectors)} 个特征向量")

            if len(feature_vectors) == 0:
                return []

            # 计算距离矩阵
            logger.info("计算特征向量距离矩阵")
            matches = []

            for i in range(len(feature_vectors)):
                # 如果是query记录，则与其他所有记录比较
                if record_ids[i] == 'query':
                    query_idx = i
                    query_record = records[valid_indices[i]]

                    # 确保查询图像可用
                    query_image = None
                    if 'processed_image' in query_record:
                        query_image = query_record['processed_image']

                    # 总比较数量用于计算进度
                    total_comparisons = len(feature_vectors) - 1

                    for j in range(len(feature_vectors)):
                        if i != j:  # 不与自身比较
                            try:
                                # 计算余弦距离
                                dist = cosine(feature_vectors[i], feature_vectors[j])
                                similarity = 1 - dist  # 转换为相似度

                                # 仅当相似度高于阈值时，保存匹配信息和图像
                                if similarity > threshold:
                                    match_record = records[valid_indices[j]]
                                    match_info = {
                                        'query_id': record_ids[i],
                                        'match_id': record_ids[j],
                                        'similarity': float(similarity),
                                        'camera_id': match_record.get('camera_id', 'unknown'),
                                        'timestamp': match_record.get('timestamp', ''),
                                        'video_path': match_record.get('video_path', ''),
                                        'location_x': match_record.get('location_x', 0),
                                        'location_y': match_record.get('location_y', 0),
                                    }

                                    # 添加所有其他字段（除了大型数据）
                                    for k, v in match_record.items():
                                        if k not in ['feature_vector', 'image', 'processed_image', 'extracted_frames']:
                                            match_info[k] = v

                                    # 保存匹配图像到指定目录
                                    if save_dir:
                                        # 保存主要匹配图像
                                        match_image = None
                                        if 'processed_image' in match_record:
                                            match_image = match_record['processed_image']
                                        elif 'extracted_frames' in match_record and match_record['extracted_frames']:
                                            match_image = match_record['extracted_frames'][0]

                                        if match_image is not None:
                                            # 为匹配图像创建文件名
                                            match_filename = f"match_{record_ids[j]}_sim{similarity:.4f}.jpg"
                                            match_path = os.path.join(save_dir, match_filename)

                                            # 保存图像
                                            cv2.imwrite(match_path, match_image)
                                            logger.info(f"保存匹配图像: {match_path}, 相似度: {similarity:.4f}")
                                            match_info['match_image_path'] = match_path

                                        # 如果有提取的帧，仅保存匹配度高的图像帧
                                        if 'extracted_frames' in match_record and match_record['extracted_frames']:
                                            saved_frames = []
                                            # 为每个帧创建单独的特征向量并计算相似度
                                            for frame_idx, frame in enumerate(match_record['extracted_frames']):
                                                # 使用已加载的模型为每个帧提取特征
                                                try:
                                                    frame_feature = self._extract_feature_vector(frame, 'mgn')
                                                    if frame_feature is not None:
                                                        # 计算与查询特征的相似度
                                                        frame_dist = cosine(feature_vectors[i], frame_feature)
                                                        frame_similarity = 1 - frame_dist

                                                        # 只保存相似度高于阈值的帧
                                                        if frame_similarity > threshold:
                                                            frame_filename = f"match_{record_ids[j]}_frame{frame_idx}_sim{frame_similarity:.4f}.jpg"
                                                            frame_path = os.path.join(save_dir, frame_filename)
                                                            cv2.imwrite(frame_path, frame)
                                                            saved_frames.append({
                                                                'path': frame_path,
                                                                'similarity': float(frame_similarity)
                                                            })
                                                            logger.info(
                                                                f"保存匹配帧: {frame_path}, 相似度: {frame_similarity:.4f}")
                                                except Exception as fe:
                                                    logger.warning(f"为帧 {frame_idx} 提取特征时出错: {str(fe)}")
                                                    continue

                                            if saved_frames:
                                                match_info['matched_frames'] = saved_frames
                                                logger.info(
                                                    f"为匹配 {record_ids[j]} 保存了 {len(saved_frames)} 个相似帧")

                                    matches.append(match_info)
                                    logger.info(f"找到匹配: ID={match_record.get('id')}, 相似度={similarity:.4f}")

                                # 更新进度
                                if callback and total_comparisons > 0:
                                    progress = int((j + (1 if j > i else 0)) / total_comparisons * 100)
                                    callback("特征匹配", progress)
                                    logger.info(f"特征匹配: {progress}%")

                            except Exception as e:
                                logger.error(f"计算记录 {record_ids[i]} 和 {record_ids[j]} 的相似度时出错: {str(e)}")
                                logger.error(traceback.format_exc())

            # 按相似度从高到低排序
            matches.sort(key=lambda x: x['similarity'], reverse=True)

            # 打印匹配结果
            logger.info(f"特征匹配完成，找到 {len(matches)} 个匹配")
            for idx, match in enumerate(matches):
                logger.info(f"匹配 #{idx + 1}:")
                logger.info(f"  摄像头ID: {match['camera_id']}")
                logger.info(f"  时间戳: {match['timestamp']}")
                logger.info(f"  视频路径: {match['video_path']}")
                logger.info(f"  相似度: {match['similarity']:.4f}")
                if 'match_image_path' in match:
                    logger.info(f"  匹配图像保存路径: {match['match_image_path']}")
                if 'matched_frames' in match:
                    logger.info(f"  匹配帧数量: {len(match['matched_frames'])}")
                logger.info("---")

            return matches

        except Exception as e:
            logger.error(f"特征匹配过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"特征匹配时出错: {str(e)}")

def load_image_safe(image_path_or_data):
    """安全加载图像，支持路径字符串或直接的图像数据"""
    try:
        if isinstance(image_path_or_data, str):
            # 如果是路径字符串，从文件加载
            if os.path.exists(image_path_or_data):
                img = cv2.imread(image_path_or_data)
                if img is not None:
                    logger.info(f"图像加载成功: {image_path_or_data}, 形状: {img.shape}")
                    return img, True
                else:
                    logger.warning(f"无法加载图像: {image_path_or_data}")
                    return None, False
            else:
                logger.warning(f"图像路径不存在: {image_path_or_data}")
                return None, False
        elif isinstance(image_path_or_data, np.ndarray):
            # 如果已经是图像数据，直接返回
            logger.info(f"使用已提供的图像数据，形状: {image_path_or_data.shape}")
            return image_path_or_data, True
        else:
            # 不支持的类型
            logger.warning(f"不支持的图像数据类型: {type(image_path_or_data)}")
            return None, False
    except Exception as e:
        logger.warning(f"图像加载异常: {e}")
        return None, False


def main():
    """主函数，用于演示ReIDProcessor的使用"""
    logger.info("开始演示ReIDProcessor")

    # 初始化ReIDProcessor
    processor = ReIDProcessor()
    image_path = "D:/lyycode02/student-trajectory-generation/frontend/public/2.jpg"

    # 加载测试图像
    query_image, success = load_image_safe(image_path)
    if not success:
        logger.warning(f"无法加载图像: {image_path}，使用默认图像")
        query_image = np.ones((384, 128, 3), dtype=np.uint8) * 200
    else:
        logger.info(f"成功加载查询图像，形状: {query_image.shape}")

    # 创建测试记录
    test_records = []
    for i in range(5):
        record = {
            'id': f'test_{i}',
            'camera_id': i + 1,
            'timestamp': datetime.now() - timedelta(minutes=i * 10),
            'location_x': 100 + i * 10,
            'location_y': 200 + i * 5
        }
        test_records.append(record)

    try:
        logger.info("开始提取特征")
        query_record = {'id': 'query', 'image': query_image}  # 明确设置image字段

        features_records = processor.extract_features(
            [query_record] + test_records,
            algorithm='mgn',
            callback=lambda stage, progress: logger.info(f"{stage}: {progress:.1f}%"),
            save_dir = os.path.join("detecting_results", datetime.now().strftime("%Y%m%d_%H%M%S"))
        )

        # 检查特征向量维度
        for record in features_records:
            if 'feature_vector' in record and record['feature_vector'] is not None:
                logger.info(f"记录 {record['id']} 的特征向量维度: {len(record['feature_vector'])}")

        # 匹配特征
        logger.info("开始特征匹配")
        matched_records = processor.match_features(
            features_records,
            threshold=0.8,
            callback=lambda stage, progress: logger.info(f"{stage}: {progress:.1f}%")
        )

        logger.info(f"匹配结果数量: {len(matched_records)}")

    except Exception as e:
        logger.error(f"演示过程中出错: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()