import os

import networkx as nx
import pandas as pd
from flask_socketio import SocketIO
import flask
from flask import Flask, request, jsonify

from backend.queryFilter.query_filter import QueryFilter
from backend.reidentification.reidentification import ReIDProcessor
from backend.spatiotemporalAnalysis.spatiotemporal_analysis import SpatiotemporalAnalysis
from backend.track.pipeline import run_pipeline
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, supports_credentials=True, resource={r'/*': {'origins': '*'}})
socketio = SocketIO(app)
detection_running = True

# 初始化各模块
query_filter = QueryFilter()
reid_processor = ReIDProcessor()
campus_map = nx.Graph()  # 可以从文件或数据库加载校园地图
spatiotemporal_analyzer = SpatiotemporalAnalysis(campus_map)

# Paths for saving result images and videos
image_result_path = "./results/images/results.jpg"
video_result_path = "./results/videos/results.mp4"

@app.route('/')
def hello_world():
    return 'Hello World'

@app.route('/stopDetection', methods=['POST'])
def stop_detection():
    global detection_running
    detection_running = False
    socketio.emit('detection_stopped', {'status': 'stopped'})
    return 'Detection stopped', 200

@app.route('/trackByVideo', methods=['POST'])
def track_by_video():
    file = request.files.get('file')
    if file:
        video_path = os.path.join('uploads', file.filename)
        file.save(video_path)
        run_pipeline(video_path)
        # Returns the video for inline display
        return flask.send_file(video_result_path, mimetype='video/mp4')
    return 'No file uploaded', 400


@app.route('/api/filter', methods=['POST'])
def filter_records():
    """根据条件过滤记录"""
    data = request.json
    student_id = data.get('studentId')
    start_time = data.get('startTime')
    end_time = data.get('endTime')
    attributes = data.get('attributes', [])
    reference_image = data.get('referenceImage')

    # 调用查询过滤模块
    filtered_records = query_filter.filter_records(
        student_id=student_id,
        time_range=(start_time, end_time),
        attributes=attributes,
        reference_image=reference_image
    )

    return jsonify({
        'status': 'success',
        'data': filtered_records.to_dict('records')
    })


@app.route('/api/spatiotemporal', methods=['POST'])
def analyze_spatiotemporal():
    """进行时空约束分析"""
    data = request.json
    records = pd.DataFrame(data.get('records'))

    # 调用时空约束分析
    filtered_records = spatiotemporal_analyzer.filter_by_spatiotemporal_constraints(records)

    # 返回时空约束过滤后的结果
    return jsonify({
        'status': 'success',
        'data': filtered_records.to_dict('records')
    })


@app.route('/api/reid', methods=['POST'])
def perform_reid():
    """执行ReID重识别处理"""
    data = request.json
    records = pd.DataFrame(data.get('records'))
    algorithm = data.get('algorithm', 'osnet')
    threshold = data.get('threshold', 70)

    # 进度通知函数
    def progress_callback(stage, percentage):
        socketio.emit('reid_progress', {
            'stage': stage,
            'percentage': percentage
        })

    print(f"开始执行ReID处理，算法: {algorithm}, 阈值: {threshold}")

    # 调用ReID处理
    reid_results = reid_processor.process(
        records,
        algorithm=algorithm,
        threshold=threshold / 100,
        callback=progress_callback
    )

    # 构建轨迹
    trajectory = spatiotemporal_analyzer.find_most_likely_trajectory(reid_results)

    # 格式化结果，确保所有字段都是JSON可序列化的
    reid_dict = reid_results.to_dict('records')

    # 打印重要信息
    print("====== ReID 处理结果 ======")
    print(f"处理记录数: {len(reid_results)}")
    print(f"找到轨迹点数: {len(trajectory)}")

    for record in reid_dict[:5]:  # 只打印前5条记录的详细信息
        print(f"记录ID: {record.get('id')}, 摄像头: {record.get('camera_id')}, "
              f"时间: {record.get('timestamp')}, 置信度: {record.get('confidence'):.2f}, "
              f"视频路径: {record.get('video_path')}")

    # 返回重识别和轨迹结果
    return jsonify({
        'status': 'success',
        'reid_results': reid_dict,
        'trajectory': trajectory
    })


@app.route('/api/trajectory', methods=['POST'])
def get_trajectory():
    """获取完整的轨迹数据"""
    data = request.json
    record_ids = data.get('recordIds', [])

    # 根据记录ID获取详细信息
    trajectory_data = query_filter.get_records_by_ids(record_ids)

    # 获取轨迹段
    segments = spatiotemporal_analyzer.get_trajectory_segments(trajectory_data)

    # 获取异常点
    anomalies = spatiotemporal_analyzer.analyze_anomalies(trajectory_data)

    return jsonify({
        'status': 'success',
        'trajectory_data': trajectory_data.to_dict('records'),
        'segments': segments,
        'anomalies': anomalies
    })

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", debug=True, port=5000, allow_unsafe_werkzeug=True)