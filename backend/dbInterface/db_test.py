import unittest
import os
import sys
import datetime
import pandas as pd
import numpy as np
import pickle
from typing import Dict, Any
import logging
import pymysql


# 导入要测试的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_interface import DatabaseInterface

# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_db_interface")


class TestDatabaseInterface(unittest.TestCase):
    """测试DatabaseInterface类的各项功能"""

    @classmethod
    def setUpClass(cls):
        """测试前设置 - 连接数据库"""
        cls.db_config = {
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'root',  # 根据实际情况修改用户名
            'password': '123456',  # 根据实际情况修改密码
            'database': 'trajectory'
        }
        try:
            cls.db = DatabaseInterface(cls.db_config)
            logger.info("Database connection established for testing")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @classmethod
    def tearDownClass(cls):
        """测试后清理 - 关闭数据库连接"""
        if hasattr(cls, 'db') and cls.db.conn:
            cls.db.disconnect()
            logger.info("Database connection closed after testing")

    def test_connection(self):
        """测试数据库连接是否成功"""
        self.assertIsNotNone(self.db.conn, "Database connection should be established")

        # 尝试执行一个简单查询来验证连接
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()

        self.assertEqual(result[0], 1, "Should be able to execute a simple query")

    def test_get_camera_locations(self):
        """测试获取摄像头位置信息"""
        camera_df = self.db.get_camera_locations()  # 获取摄像头位置信息

        # 验证返回的数据框结构
        self.assertIsInstance(camera_df, pd.DataFrame, "Should return a DataFrame")
        self.assertGreater(len(camera_df), 0, "Should return at least one camera")

        # 验证必要的列是否存在
        required_columns = ['camera_id', 'location_x', 'location_y', 'name']
        for col in required_columns:
            self.assertIn(col, camera_df.columns, f"Column {col} should be present")

        # 打印摄像头位置信息
        logger.info("Camera locations:")
        for index, row in camera_df.iterrows():
            logger.info(f"Camera ID: {row['camera_id']}, Location: ({row['location_x']}, {row['location_y']}), Name: {row['name']}")

    def test_query_student_records_all(self):
        """测试查询所有学生记录"""
        records_df = self.db.query_student_records()

        # 验证返回的数据框结构
        self.assertIsInstance(records_df, pd.DataFrame, "Should return a DataFrame")
        self.assertGreater(len(records_df), 0, "Should return at least one record")

        # 验证必要的列是否存在
        required_columns = ['id', 'student_id', 'camera_id', 'timestamp',
                            'location_x', 'location_y']
        for col in required_columns:
            self.assertIn(col, records_df.columns, f"Column {col} should be present")

        # 打印查询结果
        logger.info("Student records:")
        for index, row in records_df.iterrows():
            logger.info(f"Record ID: {row['id']}, Student ID: {row['student_id']}, "
                        f"Camera ID: {row['camera_id']}, Timestamp: {row['timestamp']}, "
                        f"Location: ({row['location_x']}, {row['location_y']})")


    def test_query_student_records_by_id(self):
        """测试按学生ID查询记录"""
        # 先获取一个存在的学生ID
        all_records = self.db.query_student_records()
        if len(all_records) == 0:
            self.skipTest("No student records in database")

        student_id = all_records['student_id'].iloc[0] # 获取第一个学生ID
        records_df = self.db.query_student_records(student_id=student_id)

        # 验证筛选结果
        self.assertGreater(len(records_df), 0, f"Should find records for student {student_id}")
        self.assertTrue((records_df['student_id'] == student_id).all(),
                        "All records should be for the specified student")

        # 打印查询结果
        logger.info(f"Records for student {student_id}:")
        for index, row in records_df.iterrows():
            logger.info(f"Record ID: {row['id']}, Camera ID: {row['camera_id']}, "
                        f"Timestamp: {row['timestamp']}, Location: ({row['location_x']}, {row['location_y']})")

    def test_query_student_records_by_features(self):
        """测试按特征查询记录"""
        # 测试查询带背包的学生
        features = {'has_backpack': True}
        records_df = self.db.query_student_records(features=features)

        # 验证筛选结果
        if len(records_df) > 0:
            self.assertTrue((records_df['has_backpack'] == True).all(),
                            "All records should have has_backpack=True")

        # 打印查询结果
        logger.info("Records with has_backpack=True:")
        for index, row in records_df.iterrows():
            logger.info(f"Record ID: {row['id']}, Student ID: {row['student_id']}, "
                        f"Camera ID: {row['camera_id']}, Timestamp: {row['timestamp']}, "
                        f"Location: ({row['location_x']}, {row['location_y']})")

    def test_query_student_records_by_time_range(self):
        """测试按时间范围查询记录"""
        # 设置一个测试时间范围 - 上午7点到9点
        start_time = datetime.datetime(2025, 4, 10, 7, 0, 0)
        end_time = datetime.datetime(2025, 4, 10, 9, 0, 0)
        time_range = (start_time, end_time)

        records_df = self.db.query_student_records(time_range=time_range)

        # 验证筛选结果
        if len(records_df) > 0:
            # 确保所有时间戳都在范围内
            # 将时间戳列转换为datetime类型
            records_df['timestamp'] = pd.to_datetime(records_df['timestamp'])
            self.assertTrue((records_df['timestamp'] >= start_time).all() and
                            (records_df['timestamp'] <= end_time).all(),
                            "All records should be within the specified time range")
        # 打印查询结果
        logger.info(f"Records between {start_time} and {end_time}:")
        for index, row in records_df.iterrows():
            logger.info(f"Record ID: {row['id']}, Student ID: {row['student_id']}, "
                        f"Camera ID: {row['camera_id']}, Timestamp: {row['timestamp']}, "
                        f"Location: ({row['location_x']}, {row['location_y']})")

    def test_query_student_records_by_camera(self):
        """测试按摄像头ID查询记录"""
        # 先获取一个存在的摄像头ID
        cameras = self.db.get_camera_locations()
        if len(cameras) == 0:
            self.skipTest("No cameras in database")

        camera_id = cameras['camera_id'].iloc[0]
        records_df = self.db.query_student_records(camera_ids=[camera_id])

        # 验证筛选结果
        if len(records_df) > 0:
            self.assertTrue((records_df['camera_id'] == camera_id).all(),
                            f"All records should be from camera {camera_id}")
        # 打印查询结果
        logger.info(f"Records from camera {camera_id}:")
        for index, row in records_df.iterrows():
            logger.info(f"Record ID: {row['id']}, Student ID: {row['student_id']}, "
                        f"Timestamp: {row['timestamp']}, Location: ({row['location_x']}, {row['location_y']})")

    def test_get_image_frame(self):
        """测试获取图像帧"""
        # 先获取一个存在的记录ID
        all_records = self.db.query_student_records()
        if len(all_records) == 0:
            self.skipTest("No student records in database")

        record_id = all_records['id'].iloc[0]
        image_frame = self.db.get_image_frame(record_id)

        # 验证返回的图像帧
        self.assertIsNotNone(image_frame, f"Should return image frame for record {record_id}")
        self.assertIsInstance(image_frame, bytes, "Image frame should be binary data")

        # 打印图像帧的大小
        logger.info(f"Image frame size for record {record_id}: {len(image_frame)} bytes")

    def test_get_video_path(self):
        """测试获取视频路径"""
        # 先获取一个存在的记录
        all_records = self.db.query_student_records()
        if len(all_records) == 0:
            self.skipTest("No student records in database")

        camera_id = all_records['camera_id'].iloc[0]
        timestamp = datetime.datetime.strptime(str(all_records['timestamp'].iloc[0]),
                                               '%Y-%m-%d %H:%M:%S')

        video_path = self.db.get_video_path(camera_id, timestamp)

        # 视频路径可能为None（如果没有找到匹配的视频）
        if video_path:
            self.assertIsInstance(video_path, str, "Video path should be a string")
            self.assertTrue(video_path.startswith('/videos/'),
                            "Video path should start with '/videos/'")

    def test_update_student_id(self):
        """测试更新学生ID"""
        # 先获取一个存在的记录ID
        all_records = self.db.query_student_records()
        if len(all_records) == 0:
            self.skipTest("No student records in database")

        record_id = all_records['id'].iloc[0]
        original_student_id = all_records['student_id'].iloc[0]
        test_student_id = "TEST123"

        # 更新学生ID
        success = self.db.update_student_id(record_id, test_student_id)
        self.assertTrue(success, "Should successfully update student ID")

        # 验证更新是否成功
        updated_record = self.db.query_student_records()
        updated_record = updated_record[updated_record['id'] == record_id]
        self.assertEqual(updated_record['student_id'].iloc[0], test_student_id,
                         "Student ID should be updated in database")

        # 恢复原始学生ID
        self.db.update_student_id(record_id, original_student_id)

    def test_save_trajectory(self):
        """测试保存轨迹数据"""
        student_id = "2021001"
        trajectory_data = {
            "path": [(120.35, 67.82), (190.56, 155.23), (246.34, 79.45)],
            "timestamps": [
                datetime.datetime(2025, 4, 10, 7, 15, 23),
                datetime.datetime(2025, 4, 10, 10, 35, 34),
                datetime.datetime(2025, 4, 10, 12, 15, 23)
            ],
            "features": {
                "morning": {"has_backpack": True},
                "noon": {"has_backpack": True},
                "evening": {"has_backpack": False}
            }
        }

        # 保存轨迹
        trajectory_id = self.db.save_trajectory(student_id, trajectory_data)
        self.assertGreater(trajectory_id, 0, "Should return a valid trajectory ID")

        # 验证轨迹是否已保存到数据库
        # (这需要额外的查询方法，不在当前接口中)
        query = "SELECT * FROM student_trajectories WHERE id = %s"
        cursor = self.db.conn.cursor()
        cursor.execute(query, (trajectory_id,))
        result = cursor.fetchone()
        cursor.close()

        self.assertIsNotNone(result, f"Trajectory with ID {trajectory_id} should exist")
        self.assertEqual(result[1], student_id, "Student ID should match")

        # 清理 - 删除测试创建的轨迹
        cleanup_query = "DELETE FROM student_trajectories WHERE id = %s"
        cursor = self.db.conn.cursor()
        cursor.execute(cleanup_query, (trajectory_id,))
        self.db.conn.commit()
        cursor.close()


class TestDatabasePerformance(unittest.TestCase):
    """测试数据库查询性能"""

    @classmethod
    def setUpClass(cls):
        """测试前设置 - 连接数据库"""
        cls.db_config = {
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'root',  # 根据实际情况修改用户名
            'password': 'password',  # 根据实际情况修改密码
            'database': 'trajectory'
        }
        try:
            cls.db = DatabaseInterface(cls.db_config)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @classmethod
    def tearDownClass(cls):
        """测试后清理 - 关闭数据库连接"""
        if hasattr(cls, 'db') and cls.db.conn:
            cls.db.disconnect()

    def test_query_performance(self):
        """测试查询性能 - 查询所有记录应该在合理时间内完成"""
        import time

        start_time = time.time()
        records_df = self.db.query_student_records()
        end_time = time.time()

        query_time = end_time - start_time
        logger.info(f"Query completed in {query_time:.4f} seconds, returned {len(records_df)} records")

        # 查询应该在1秒内完成（可根据数据量和环境调整）
        self.assertLess(query_time, 1.0, "Query should complete in reasonable time")


if __name__ == "__main__":
    unittest.main()