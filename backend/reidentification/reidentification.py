import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
import logging
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import io
from scipy.spatial.distance import cosine
import torchreid
from torchreid.reid.utils import FeatureExtractor  as TorchreidExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FeatureExtractor:
    """特征提取器，从图像中提取人物特征，使用Torchreid框架"""

    def __init__(self, model_name: str = 'osnet_x1_0', model_path: Optional[str] = None):
        """
        初始化特征提取器

        Args:
            model_name: Torchreid模型名称，默认使用osnet_x1_0
            model_path: 自定义模型权重路径，如果为None则使用预训练权重
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 初始化Torchreid特征提取器
        model_kwargs = {'model_name': model_name}
        if model_path:
            model_kwargs['model_path'] = model_path

        self.extractor = TorchreidExtractor(
            **model_kwargs,
            device=self.device
        )

        logger.info(f"Feature extractor initialized with model {model_name} on device: {self.device}")

    def extract_features(self, image_data: bytes) -> np.ndarray:
        """
        从图像数据提取特征向量

        Args:
            image_data: 图像二进制数据

        Returns:
            特征向量
        """
        try:
            # 转换图像数据为PIL图像
            image = Image.open(io.BytesIO(image_data))

            # Torchreid需要图像路径或PIL图像
            features = self.extractor(image)

            # 转换为numpy数组并展平
            return features.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"Failed to extract features: {e}")
            # 根据模型输出特征维度设置默认值
            return np.zeros(512)  # osnet_x1_0的特征维度为512


class ReidentificationModel:
    """重识别模型，用于跨摄像头识别同一个学生"""

    def __init__(self, feature_extractor: FeatureExtractor, distance_threshold: float = 0.3):
        """
        初始化重识别模型

        Args:
            feature_extractor: 特征提取器实例
            distance_threshold: 距离阈值，小于该值表示匹配
        """
        self.feature_extractor = feature_extractor
        self.distance_threshold = distance_threshold

    def compute_distance(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """
        计算两个特征向量的距离

        Args:
            feature1: 第一个特征向量
            feature2: 第二个特征向量

        Returns:
            特征向量之间的距离
        """
        return cosine(feature1, feature2)

    def match_features(self,
                       query_feature: np.ndarray,
                       gallery_features: List[np.ndarray]) -> Tuple[int, float]:
        """
        查询特征在特征库中的最佳匹配

        Args:
            query_feature: 查询特征向量
            gallery_features: 特征库列表

        Returns:
            (最佳匹配索引, 距离值)
        """
        if not gallery_features:
            return -1, float('inf')

        distances = [self.compute_distance(query_feature, gf) for gf in gallery_features]
        min_idx = np.argmin(distances)
        min_dist = distances[min_idx]

        # 如果距离小于阈值，认为匹配成功
        if min_dist < self.distance_threshold:
            return min_idx, min_dist
        else:
            return -1, min_dist

    def batch_reidentification(self,
                               db_interface,
                               query_records: pd.DataFrame,
                               gallery_records: pd.DataFrame) -> Dict[int, int]:
        """
        批量重识别

        Args:
            db_interface: 数据库接口实例
            query_records: 查询记录DataFrame
            gallery_records: 库记录DataFrame

        Returns:
            匹配字典 {查询记录索引: 库记录索引}
        """
        matches = {}

        # 提取库特征
        gallery_features = []
        gallery_indices = []

        for idx, record in gallery_records.iterrows():
            # 如果已经有特征向量，直接使用
            if 'feature_vector' in record and record['feature_vector'] is not None:
                gallery_features.append(record['feature_vector'])
                gallery_indices.append(idx)
            else:
                # 否则，从图像提取特征
                image_data = db_interface.get_image_frame(record.name)
                if image_data:
                    feature = self.feature_extractor.extract_features(image_data)
                    gallery_features.append(feature)
                    gallery_indices.append(idx)

        logger.info(f"Extracted {len(gallery_features)} gallery features")

        # 对每个查询记录进行匹配
        for idx, record in query_records.iterrows():
            # 如果已经有特征向量，直接使用
            if 'feature_vector' in record and record['feature_vector'] is not None:
                query_feature = record['feature_vector']
            else:
                # 否则，从图像提取特征
                image_data = db_interface.get_image_frame(record.name)
                if not image_data:
                    continue
                query_feature = self.feature_extractor.extract_features(image_data)

            # 匹配特征
            match_idx, match_dist = self.match_features(query_feature, gallery_features)

            if match_idx >= 0:
                matches[idx] = gallery_indices[match_idx]
                logger.info(
                    f"Record {idx} matched with gallery record {gallery_indices[match_idx]} (distance: {match_dist:.4f})")

        return matches

    def identify_student(self,
                         db_interface,
                         records: pd.DataFrame,
                         student_id_records: pd.DataFrame) -> Dict[int, str]:
        """
        识别学生身份

        Args:
            db_interface: 数据库接口实例
            records: 待识别记录DataFrame
            student_id_records: 已知学生ID的记录DataFrame

        Returns:
            识别结果字典 {记录索引: 学生ID}
        """
        # 按学生ID分组已知记录
        student_groups = student_id_records.groupby('student_id')
        student_features = {}

        # 为每个学生提取特征
        for student_id, group in student_groups:
            features = []
            for idx, record in group.iterrows():
                if 'feature_vector' in record and record['feature_vector'] is not None:
                    features.append(record['feature_vector'])
                else:
                    image_data = db_interface.get_image_frame(record.name)
                    if image_data:
                        feature = self.feature_extractor.extract_features(image_data)
                        features.append(feature)

            if features:
                student_features[student_id] = features

        logger.info(f"Extracted features for {len(student_features)} students")

        # 对每条待识别记录进行匹配
        identifications = {}

        for idx, record in records.iterrows():
            # 提取特征
            if 'feature_vector' in record and record['feature_vector'] is not None:
                query_feature = record['feature_vector']
            else:
                image_data = db_interface.get_image_frame(record.name)
                if not image_data:
                    continue
                query_feature = self.feature_extractor.extract_features(image_data)

            # 计算与每个学生的最小距离
            min_dist = float('inf')
            best_student_id = None

            for student_id, features in student_features.items():
                for feature in features:
                    dist = self.compute_distance(query_feature, feature)
                    if dist < min_dist:
                        min_dist = dist
                        best_student_id = student_id

            # 如果找到匹配且距离小于阈值
            if best_student_id and min_dist < self.distance_threshold:
                identifications[idx] = best_student_id
                logger.info(f"Record {idx} identified as student {best_student_id} (distance: {min_dist:.4f})")

        return identifications

    def generate_reid_features(self, db_interface, records: pd.DataFrame) -> Dict[int, np.ndarray]:
        """
        为记录生成重识别特征

        Args:
            db_interface: 数据库接口实例
            records: 记录DataFrame

        Returns:
            特征字典 {记录索引: 特征向量}
        """
        features = {}

        for idx, record in records.iterrows():
            # 如果已经有特征向量，直接使用
            if 'feature_vector' in record and record['feature_vector'] is not None:
                features[idx] = record['feature_vector']
            else:
                # 否则，从图像提取特征
                image_data = db_interface.get_image_frame(record.name)
                if image_data:
                    feature = self.feature_extractor.extract_features(image_data)
                    features[idx] = feature

        logger.info(f"Generated features for {len(features)} records")
        return features


def create_reidentification_model(model_name: str = 'osnet_x1_0',
                                  model_path: Optional[str] = None,
                                  distance_threshold: float = 0.3) -> ReidentificationModel:
    """
    创建重识别模型的工厂函数

    Args:
        model_name: Torchreid模型名称
        model_path: 自定义模型权重路径
        distance_threshold: 匹配距离阈值

    Returns:
        初始化好的ReidentificationModel实例
    """
    # 初始化特征提取器
    feature_extractor = FeatureExtractor(model_name=model_name, model_path=model_path)

    # 初始化重识别模型
    reid_model = ReidentificationModel(feature_extractor, distance_threshold=distance_threshold)

    return reid_model


# 使用示例
if __name__ == "__main__":
    # 创建一个重识别模型
    reid_model = create_reidentification_model(model_name='osnet_x1_0')

    # 这里可以添加你的测试代码
    logger.info("ReID model created successfully.")