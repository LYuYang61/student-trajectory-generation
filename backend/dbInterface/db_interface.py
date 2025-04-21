import sqlite3
import pymysql
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
import os
import logging
import numpy as np
import pickle
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseInterface:
    """数据库接口类，处理与数据库的所有交互"""

    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化数据库连接

        Args:
            db_config: 数据库配置信息
                {
                    'type': 'sqlite' or 'mysql',
                    'sqlite_path': 路径 (仅sqlite),
                    'host': 主机名 (仅mysql),
                    'port': 端口 (仅mysql),
                    'user': 用户名 (仅mysql),
                    'password': 密码 (仅mysql),
                    'database': 数据库名 (仅mysql)
                }
        """
        self.db_config = db_config
        self.conn = None
        self.connect()

    def connect(self):
        """建立数据库连接"""
        try:
            if self.db_config['type'].lower() == 'sqlite':
                self.conn = sqlite3.connect(self.db_config['sqlite_path'])
                logger.info(f"Connected to SQLite database at {self.db_config['sqlite_path']}")
            elif self.db_config['type'].lower() == 'mysql':
                self.conn = pymysql.connect(
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    user=self.db_config['user'],
                    password=self.db_config['password'],
                    database=self.db_config['database'],
                    charset='utf8mb4'
                )
                logger.info(f"Connected to MySQL database at {self.db_config['host']}")
            else:
                raise ValueError(f"Unsupported database type: {self.db_config['type']}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


    def query_student_records(self,
                              student_id: Optional[str] = None,
                              features: Optional[Dict[str, bool]] = None,
                              time_range: Optional[Tuple[datetime, datetime]] = None,
                              camera_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """
        查询学生记录

        Args:
            student_id: 学生学号，可选
            features: 特征字典，如 {'has_backpack': True, 'has_umbrella': False}，可选
            time_range: 时间范围(开始时间, 结束时间)，可选
            camera_ids: 摄像头ID列表，可选

        Returns:
            包含学生记录的DataFrame
        """
        try:
            query_parts = ["SELECT * FROM student_records WHERE 1=1"]
            params = []

            # 添加过滤条件
            if student_id:
                query_parts.append("AND student_id = %s")
                params.append(student_id)

            # 特征过滤
            if features:
                for feature, value in features.items():
                    query_parts.append(f"AND {feature} = %s")
                    params.append(value)

            # 时间范围过滤
            if time_range:
                query_parts.append("AND timestamp BETWEEN %s AND %s")
                params.extend([time_range[0], time_range[1]])

            # 摄像头ID过滤
            if camera_ids:
                placeholders = ', '.join(['%s'] * len(camera_ids))
                query_parts.append(f"AND camera_id IN ({placeholders})")
                params.extend(camera_ids)

            # 组装最终查询语句
            query = " ".join(query_parts)

            # 执行查询
            if self.db_config['type'].lower() == 'sqlite':
                # SQLite 使用 ? 作为参数占位符，而不是 %s
                query = query.replace("%s", "?")

            df = pd.read_sql(query, self.conn, params=params)

            def safe_unpickle(x):
                try:
                    if x is not None and len(x) > 0:
                        return pickle.loads(x)
                    else:
                        return None
                except Exception as e:
                    logger.warning(f"Failed to unpickle feature_vector: {e}")
                    return None  # 失败时返回None而不是抛出异常

            # 处理特征数据
            if 'feature_vector' in df.columns:
                # 假设特征向量是以二进制格式存储的
                df['feature_vector'] = df['feature_vector'].apply(safe_unpickle)

            logger.info(f"Retrieved {len(df)} records from database")
            return df

        except Exception as e:
            logger.error(f"Error querying student records: {e}")
            raise

    def get_camera_locations(self) -> pd.DataFrame:
        """
        获取所有摄像头位置信息

        Returns:
            包含摄像头ID、位置坐标的DataFrame
        """
        try:
            query = "SELECT camera_id, location_x, location_y, name FROM cameras"
            df = pd.read_sql(query, self.conn)
            logger.info(f"Retrieved {len(df)} camera locations")
            return df
        except Exception as e:
            logger.error(f"Error retrieving camera locations: {e}")
            raise

    def get_image_frame(self, record_id: int) -> bytes:
        """
        获取特定记录的图像帧

        Args:
            record_id: 记录ID

        Returns:
            图像二进制数据
        """
        try:
            query = "SELECT image_frame FROM student_records WHERE id = %s"
            if self.db_config['type'].lower() == 'sqlite':
                query = query.replace("%s", "?")

            cursor = self.conn.cursor()
            cursor.execute(query, (record_id,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                return result[0]  # 图像二进制数据
            else:
                logger.warning(f"No image frame found for record ID {record_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving image frame: {e}")
            raise

    def get_video_path(self, camera_id: int, timestamp: datetime) -> str:
        """
        获取与特定摄像头和时间相关的视频路径

        Args:
            camera_id: 摄像头ID
            timestamp: 时间戳

        Returns:
            视频文件路径
        """
        try:
            # 格式化日期和时间
            date_str = timestamp.strftime('%Y%m%d')

            # 查询视频文件信息
            query = """
            SELECT video_path FROM camera_videos 
            WHERE camera_id = %s AND date = %s 
            AND start_time <= %s AND end_time >= %s 
            LIMIT 1
            """

            if self.db_config['type'].lower() == 'sqlite':
                query = query.replace("%s", "?")

            cursor = self.conn.cursor()
            cursor.execute(query, (camera_id, date_str, timestamp, timestamp))
            result = cursor.fetchone()
            cursor.close()

            if result:
                return result[0]  # 视频路径
            else:
                logger.warning(f"No video found for camera {camera_id} at {timestamp}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving video path: {e}")
            raise

    def update_student_id(self, record_id: int, student_id: str) -> bool:
        """
        更新记录的学号信息

        Args:
            record_id: 记录ID
            student_id: 学生学号

        Returns:
            更新是否成功
        """
        try:
            query = "UPDATE student_records SET student_id = %s WHERE id = %s"
            if self.db_config['type'].lower() == 'sqlite':
                query = query.replace("%s", "?")

            cursor = self.conn.cursor()
            cursor.execute(query, (student_id, record_id))
            self.conn.commit()
            cursor.close()

            logger.info(f"Updated student_id to {student_id} for record {record_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating student ID: {e}")
            self.conn.rollback()
            return False

    def save_trajectory(self, student_id: str, trajectory_data: Dict[str, Any]) -> int:
        """
        保存学生轨迹数据

        Args:
            student_id: 学生学号
            trajectory_data: 轨迹数据字典

        Returns:
            新保存的轨迹ID
        """
        try:
            trajectory_json = pickle.dumps(trajectory_data)
            timestamp = datetime.now()

            query = """
            INSERT INTO student_trajectories 
            (student_id, trajectory_data, timestamp) 
            VALUES (%s, %s, %s)
            """

            if self.db_config['type'].lower() == 'sqlite':
                query = query.replace("%s", "?")

            cursor = self.conn.cursor()
            cursor.execute(query, (student_id, trajectory_json, timestamp))

            if self.db_config['type'].lower() == 'sqlite':
                trajectory_id = cursor.lastrowid
            else:  # MySQL
                trajectory_id = cursor.lastrowid

            self.conn.commit()
            cursor.close()

            logger.info(f"Saved trajectory for student {student_id}, ID: {trajectory_id}")
            return trajectory_id
        except Exception as e:
            logger.error(f"Error saving trajectory: {e}")
            self.conn.rollback()
            return -1

