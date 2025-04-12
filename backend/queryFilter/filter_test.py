import pandas as pd
from datetime import datetime, timedelta
import logging
from query_filter import QueryFilter
from backend.dbInterface.db_interface import DatabaseInterface
import matplotlib.pyplot as plt
import seaborn as sns

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """演示QueryFilter的使用方法"""
    # 实例化数据库接口
    db = DatabaseInterface({
        'type': 'mysql',
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'trajectory'
    })

    # 实例化查询过滤器
    query_filter = QueryFilter(db)

    # 示例1: 按学号查询学生记录
    print("\n==== 示例1: 按学号查询学生记录 ====")
    student_results = query_filter.filter_process(student_id='2021001')
    print(f"找到记录数: {len(student_results['all_records'])}")

    if not student_results['all_records'].empty:
        # 显示学生活动时间轴
        print("\n学生2021001的活动时间线:")
        timeline = student_results['sorted_records'][['timestamp', 'camera_id', 'name']]
        print(timeline.head())

    # 示例2: 按时间范围和位置查询
    print("\n==== 示例2: 按时间范围和位置查询 ====")
    # 查询早上7点到9点之间，在教学楼附近的学生
    morning_time = (datetime(2025, 4, 10, 7, 0), datetime(2025, 4, 10, 9, 0))
    teaching_cameras = [1, 2]

    morning_results = query_filter.filter_process(
        time_range=morning_time,
        camera_ids=teaching_cameras
    )

    print(f"找到记录数: {len(morning_results['all_records'])}")

    if not morning_results['all_records'].empty:
        # 按摄像头显示统计
        camera_counts = morning_results['all_records']['camera_id'].value_counts()
        print("\n各摄像头捕获的学生数量:")
        for camera_id, count in camera_counts.items():
            camera_name = morning_results['all_records'][
                morning_results['all_records']['camera_id'] == camera_id
                ]['name'].iloc[0]
            print(f"摄像头 {camera_id} ({camera_name}): {count} 人次")

    # 示例3: 按外观特征查询
    print("\n==== 示例3: 按外观特征查询 ====")
    # 查询带雨伞的学生
    umbrella_results = query_filter.filter_process(has_umbrella=True)

    print(f"找到记录数: {len(umbrella_results['all_records'])}")

    if not umbrella_results['all_records'].empty:
        print("\n带雨伞的学生记录:")
        print(umbrella_results['sorted_records'][['student_id', 'timestamp', 'name']].head())

    # 示例4: 复杂条件组合查询
    print("\n==== 示例4: 复杂条件组合查询 ====")
    # 查询下午3点到5点，在运动场附近，骑自行车的学生
    afternoon_time = (datetime(2025, 4, 10, 15, 0), datetime(2025, 4, 10, 17, 0))
    playground_cameras = [7, 8]

    bicycle_results = query_filter.filter_process(
        time_range=afternoon_time,
        camera_ids=playground_cameras,
        has_bicycle=True
    )

    print(f"找到记录数: {len(bicycle_results['all_records'])}")

    if not bicycle_results['all_records'].empty:
        print("\n下午在运动场骑自行车的学生:")
        print(bicycle_results['sorted_records'][
                  ['student_id', 'timestamp', 'camera_id', 'name']
              ].head())

    # 示例5: 可视化学生轨迹
    visualization_demo(query_filter)


def visualization_demo(query_filter):
    """演示如何使用查询结果进行可视化"""
    print("\n==== 示例5: 可视化学生轨迹 ====")

    # 获取所有相机位置以创建校园地图基础
    cameras = query_filter.db.get_camera_locations()

    # 查询特定学生的全天活动
    student_id = '2021001'
    day_time = (datetime(2025, 4, 10, 0, 0), datetime(2025, 4, 10, 23, 59, 59))

    student_results = query_filter.filter_process(
        student_id=student_id,
        time_range=day_time
    )

    if not student_results['all_records'].empty:
        print(f"学生 {student_id} 的一天活动轨迹，共 {len(student_results['all_records'])} 条记录")

        # 这里只是演示，实际可视化代码需要matplotlib等库
        print("\n可视化轨迹代码示例:")
        print("1. 绘制校园地图，标记摄像头位置")
        print("2. 根据时间顺序连接学生在不同摄像头的出现位置")
        print("3. 使用颜色或标记区分不同时段的活动")

        # 此处添加可视化代码（实际项目中实现）
        try:
            # 创建简单的可视化图表，展示学生一天的移动路径
            plt.figure(figsize=(10, 8))

            # 绘制摄像头位置
            plt.scatter(cameras['location_x'], cameras['location_y'], c='blue', s=100,
                        marker='^', label='摄像头')

            # 为每个摄像头添加标签
            for _, camera in cameras.iterrows():
                plt.annotate(f"{camera['camera_id']}: {camera['name']}",
                             (camera['location_x'], camera['location_y']),
                             textcoords="offset points",
                             xytext=(0, 10),
                             ha='center')

            # 绘制学生轨迹
            student_data = student_results['sorted_records']
            plt.scatter(student_data['location_x'], student_data['location_y'],
                        c='red', s=80, label='学生位置')

            # 连接轨迹点
            plt.plot(student_data['location_x'], student_data['location_y'],
                     'r--', alpha=0.7)

            # 标记时间点
            for _, record in student_data.iterrows():
                time_str = record['timestamp'].strftime('%H:%M')
                plt.annotate(time_str,
                             (record['location_x'], record['location_y']),
                             textcoords="offset points",
                             xytext=(5, 5),
                             color='darkred')

            plt.title(f"学生 {student_id} 的活动轨迹 ({day_time[0].date()})")
            plt.xlabel('X 坐标')
            plt.ylabel('Y 坐标')
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.7)

            # 保存图像
            plt.savefig(f"student_{student_id}_trajectory.png")
            print(f"轨迹图已保存为 student_{student_id}_trajectory.png")

        except Exception as e:
            print(f"无法创建可视化图表: {e}")
            print("请确保已安装matplotlib和seaborn库")


if __name__ == "__main__":
    main()