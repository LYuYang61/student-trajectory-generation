import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
import pymysql
import sys
import logging
from spatiotemporal_analysis import SpatiotemporalAnalysis

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_data_from_db():
    """从数据库获取测试数据"""
    try:
        # 连接数据库
        conn = pymysql.connect(
            host='localhost',
            user='root',  # 修改为您的数据库用户名
            password='123456',  # 修改为您的数据库密码
            database='trajectory',
            charset='utf8mb4'
        )

        # 获取摄像头数据
        cameras_query = "SELECT camera_id, location_x, location_y, name FROM cameras"
        cameras_df = pd.read_sql(cameras_query, conn)

        # 获取学生记录数据
        records_query = """
        SELECT student_id, camera_id, timestamp, location_x, location_y, 
               has_backpack, has_umbrella, has_bicycle 
        FROM student_records
        """
        records_df = pd.read_sql(records_query, conn)

        conn.close()
        return cameras_df, records_df

    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        # 如果无法连接数据库，返回空的DataFrame
        return pd.DataFrame(), pd.DataFrame()


def test_spatiotemporal_analysis():
    """测试SpatiotemporalAnalysis类的各个功能"""
    # 获取数据
    cameras_df, records_df = fetch_data_from_db()

    if cameras_df.empty or records_df.empty:
        logger.error("无法获取数据，测试终止")
        return

    logger.info(f"获取到 {len(cameras_df)} 个摄像头记录和 {len(records_df)} 条学生记录")

    # 初始化分析器
    analyzer = SpatiotemporalAnalysis(walking_speed=1.4)  # 1.4m/s的步行速度

    # 构建校园地图
    # 创建简单的路径数据（实际应用中可能需要更详细的数据）
    path_data = [
        {'from': 1, 'to': 2, 'distance': 50},  # 教学楼A区入口 -> 教学楼B区入口
        {'from': 2, 'to': 3, 'distance': 70},  # 教学楼B区入口 -> 图书馆前广场
        {'from': 3, 'to': 9, 'distance': 55},  # 图书馆前广场 -> 校园中心广场
        {'from': 9, 'to': 4, 'distance': 50},  # 校园中心广场 -> 学生宿舍1号楼
        {'from': 4, 'to': 5, 'distance': 35},  # 学生宿舍1号楼 -> 学生宿舍2号楼
        {'from': 1, 'to': 6, 'distance': 130},  # 教学楼A区入口 -> 食堂入口
        {'from': 6, 'to': 3, 'distance': 80},  # 食堂入口 -> 图书馆前广场
        {'from': 9, 'to': 7, 'distance': 60},  # 校园中心广场 -> 运动场北侧
        {'from': 7, 'to': 8, 'distance': 40},  # 运动场北侧 -> 运动场南侧
        {'from': 9, 'to': 10, 'distance': 45},  # 校园中心广场 -> 实验楼入口
    ]
    campus_graph = analyzer.build_campus_graph_from_data(cameras_df, path_data)
    logger.info(f"校园图构建完成，包含 {len(campus_graph.nodes)} 个节点和 {len(campus_graph.edges)} 条边")

    # 1. 测试计算行走时间
    location1 = (cameras_df.iloc[0]['location_x'], cameras_df.iloc[0]['location_y'])  # 教学楼A区入口
    location2 = (cameras_df.iloc[5]['location_x'], cameras_df.iloc[5]['location_y'])  # 食堂入口
    travel_time = analyzer.calculate_travel_time(location1, location2)
    logger.info(f"从教学楼A区入口到食堂入口的估计行走时间: {travel_time:.2f}秒")

    # 2. 测试按学生ID筛选记录并分析轨迹
    students = records_df['student_id'].unique()
    logger.info(f"数据集中共有 {len(students)} 名学生")

    # 选择前5个学生进行分析
    for student_id in students[:5]:
        student_records = records_df[records_df['student_id'] == student_id].copy() # 复制数据以避免修改原始数据
        logger.info(f"学生 {student_id} 有 {len(student_records)} 条记录")

        # 进行时空约束过滤
        filtered_records = analyzer.filter_by_spatiotemporal_constraints(student_records)
        logger.info(f"过滤后剩余 {len(filtered_records)} 条记录")

        # 分析异常
        anomalies = analyzer.analyze_anomalies(student_records)
        if anomalies:
            logger.info(f"发现 {len(anomalies)} 个异常")
            for anomaly in anomalies:
                logger.info(f"异常类型: {anomaly['type']}, 速度比: {anomaly['speed_ratio']:.2f}")

        # 获取轨迹段
        segments = analyzer.get_trajectory_segments(student_records)
        logger.info(f"学生轨迹包含 {len(segments)} 个段")

        # 构建轨迹图
        trajectory_graph = analyzer.create_trajectory_graph(student_records)
        logger.info(f"轨迹图包含 {len(trajectory_graph.nodes)} 个节点和 {len(trajectory_graph.edges)} 条边")

        # 找出最可能的轨迹
        most_likely_trajectory = analyzer.find_most_likely_trajectory(student_records)
        logger.info(f"最可能的轨迹包含 {len(most_likely_trajectory)} 个记录")

        logger.info("-" * 50)


def get_sample_trajectory_visualization():
    """为一个样本学生的轨迹创建可视化"""
    # 获取数据
    cameras_df, records_df = fetch_data_from_db()

    if cameras_df.empty or records_df.empty:
        logger.error("无法获取数据，可视化终止")
        return

    # 选择一个有较多记录的学生
    student_counts = records_df['student_id'].value_counts()
    if len(student_counts) == 0:
        logger.error("没有找到学生记录")
        return

    sample_student = student_counts.index[0]
    student_records = records_df[records_df['student_id'] == sample_student].copy()
    logger.info(f"为学生 {sample_student} 生成轨迹可视化，共 {len(student_records)} 条记录")

    # 初始化分析器并构建校园图
    analyzer = SpatiotemporalAnalysis(walking_speed=1.4)

    # 获取轨迹段
    segments = analyzer.get_trajectory_segments(student_records)

    # 将轨迹段可视化为有向图
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 10))

    # 绘制摄像头位置
    for _, cam in cameras_df.iterrows():
        plt.scatter(cam['location_x'], cam['location_y'], c='blue', s=100)
        plt.text(cam['location_x'], cam['location_y'], f"CAM {cam['camera_id']}", fontsize=12)

    # 绘制学生轨迹
    sorted_records = student_records.sort_values(by='timestamp')
    plt.plot(sorted_records['location_x'], sorted_records['location_y'], 'r-', alpha=0.5)

    # 为每个记录添加时间标记
    for idx, record in sorted_records.iterrows():
        time_str = record['timestamp'].strftime('%H:%M')
        plt.text(record['location_x'], record['location_y'] + 2, time_str, fontsize=10)

    plt.title(f"学生 {sample_student} 的轨迹")
    plt.xlabel("X 坐标")
    plt.ylabel("Y 坐标")
    plt.grid(True)
    plt.tight_layout()

    # 保存图像
    output_file = f"student_{sample_student}_trajectory.png"
    plt.savefig(output_file)
    logger.info(f"轨迹图已保存为 {output_file}")
    plt.close()


if __name__ == "__main__":
    logger.info("开始测试SpatiotemporalAnalysis类...")
    test_spatiotemporal_analysis()

    logger.info("生成样本轨迹可视化...")
    try:
        get_sample_trajectory_visualization()
    except Exception as e:
        logger.error(f"生成可视化失败: {e}")

    logger.info("测试完成")