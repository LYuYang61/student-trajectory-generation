import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import logging
from backend.dbInterface.db_interface import DatabaseInterface

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QueryFilter:
    """查询过滤模块，根据用户输入条件过滤数据库结果"""

    def __init__(self, db_interface: DatabaseInterface):
        """
        初始化查询过滤器

        Args:
            db_interface: 数据库接口实例
        """
        self.db = db_interface

    def filter_by_criteria(self,
                           student_id: Optional[str] = None,
                           features: Optional[Dict[str, bool]] = None,
                           time_range: Optional[Tuple[datetime, datetime]] = None,
                           camera_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """
        根据条件过滤学生记录

        Args:
            student_id: 学生学号，可选
            features: 特征字典，例如 {'has_backpack': True}，可选
            time_range: 时间范围元组 (start_time, end_time)，可选
            camera_ids: 摄像头ID列表，可选

        Returns:
            符合条件的学生记录DataFrame
        """
        logger.info(
            f"Filtering records with: student_id={student_id}, features={features}, time_range={time_range}, camera_ids={camera_ids}")

        # 将特征字典（如果提供）转换为数据库接口所需的格式
        db_features = None
        if features:
            db_features = {}
            for key, value in features.items():
                # 只包含布尔值的键值对
                if isinstance(value, bool):
                    db_features[key] = value

        # 查询数据库
        records = self.db.query_student_records(
            features=db_features,
            time_range=time_range,
            camera_ids=camera_ids
        )

        logger.info(f"Initial filter returned {len(records)} records")
        return records

    def get_records_by_ids(self, record_ids: List[int]) -> pd.DataFrame:
        """
        根据记录ID列表获取详细记录

        Args:
            record_ids: 记录ID列表

        Returns:
            包含指定ID记录的DataFrame
        """
        if not record_ids:
            return pd.DataFrame()

        try:
            # 将ID列表转换为逗号分隔的字符串
            id_str = ','.join(map(str, record_ids))

            # 构建SQL查询
            query = f"""
            SELECT * FROM student_appearances
            WHERE id IN ({id_str})
            """

            # 查询数据库
            records = self.db.execute_query(query)
            logger.info(f"查询到 {len(records)} 条记录，通过IDs: {id_str}")

            # 增强结果
            enhanced_records = self.enhance_filter_results(records)

            return enhanced_records

        except Exception as e:
            logger.error(f"通过ID获取记录失败: {str(e)}")
            return pd.DataFrame()

    def filter_by_appearance(self,
                             records: pd.DataFrame,
                             has_bicycle: Optional[bool] = None,
                             has_backpack: Optional[bool] = None,
                             has_umbrella: Optional[bool] = None) -> pd.DataFrame:
        """
        根据外观特征进一步过滤记录

        Args:
            records: 初步过滤的记录
            has_bicycle: 是否骑自行车，可选
            has_backpack: 是否背包，可选
            has_umbrella: 是否带雨伞，可选

        Returns:
            进一步过滤后的记录
        """
        filtered = records.copy()

        if has_bicycle is not None and 'has_bicycle' in filtered.columns:
            filtered = filtered[filtered['has_bicycle'] == has_bicycle]

        if has_backpack is not None and 'has_backpack' in filtered.columns:
            filtered = filtered[filtered['has_backpack'] == has_backpack]

        if has_umbrella is not None and 'has_umbrella' in filtered.columns:
            filtered = filtered[filtered['has_umbrella'] == has_umbrella]

        logger.info(f"Appearance filter returned {len(filtered)} of {len(records)} records")
        return filtered

    def enhance_filter_results(self, records: pd.DataFrame) -> pd.DataFrame:
        """
        增强过滤结果，添加额外的信息

        Args:
            records: 过滤后的记录

        Returns:
            增强的记录数据
        """
        if records.empty:
            return records

        # 获取摄像头位置信息
        cameras = self.db.get_camera_locations()

        # 合并摄像头位置信息到记录中
        if 'camera_id' in records.columns:
            enhanced = pd.merge(
                records,
                cameras[['camera_id', 'location_x', 'location_y', 'name']],
                on='camera_id',
                how='left'
            )
        else:
            enhanced = records

        logger.info(f"Enhanced {len(enhanced)} records with camera location data")
        return enhanced

    def sort_by_time(self, records: pd.DataFrame) -> pd.DataFrame:
        """
        按时间顺序排序记录

        Args:
            records: 记录DataFrame

        Returns:
            按时间排序的记录
        """
        if 'timestamp' in records.columns and not records.empty:
            sorted_records = records.sort_values(by='timestamp')
            return sorted_records
        return records

    def group_by_camera(self, records: pd.DataFrame) -> Dict[int, pd.DataFrame]:
        """
        将记录按摄像头分组

        Args:
            records: 记录DataFrame

        Returns:
            按摄像头ID分组的记录字典
        """
        if records.empty or 'camera_id' not in records.columns:
            return {}

        grouped = {}
        for camera_id, group in records.groupby('camera_id'):
            grouped[camera_id] = group.sort_values(by='timestamp')

        logger.info(f"Grouped records by {len(grouped)} cameras")
        return grouped

    def filter_process(self,
                       student_id: Optional[str] = None,
                       features: Optional[Dict[str, bool]] = None,
                       time_range: Optional[Tuple[datetime, datetime]] = None,
                       camera_ids: Optional[List[int]] = None,
                       has_bicycle: Optional[bool] = None,
                       has_backpack: Optional[bool] = None,
                       has_umbrella: Optional[bool] = None) -> Dict[str, Any]:
        # 整合所有特征条件
        all_features = features or {}
        if has_bicycle is not None:
            all_features['has_bicycle'] = has_bicycle
        if has_backpack is not None:
            all_features['has_backpack'] = has_backpack
        if has_umbrella is not None:
            all_features['has_umbrella'] = has_umbrella

        # 初步过滤
        filtered_records = self.filter_by_criteria(
            student_id=student_id,
            features=all_features,
            time_range=time_range,
            camera_ids=camera_ids
        )

        # 增强结果
        enhanced_records = self.enhance_filter_results(filtered_records)

        # 确保时间戳是日期时间类型
        if 'timestamp' in enhanced_records.columns:
            enhanced_records['timestamp'] = pd.to_datetime(enhanced_records['timestamp'])

        # 按时间排序
        sorted_records = self.sort_by_time(enhanced_records)

        # 按摄像头分组
        grouped_records = self.group_by_camera(sorted_records)

        # 打印调试信息
        logger.debug(f"Filtered records: {filtered_records}")
        logger.debug(f"Enhanced records: {enhanced_records}")
        logger.debug(f"Sorted records: {sorted_records}")
        logger.debug(f"Grouped records: {grouped_records}")

        return {
            'all_records': enhanced_records,
            'sorted_records': sorted_records,
            'camera_groups': grouped_records
        }