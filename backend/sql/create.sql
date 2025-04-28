use trajectory;-- 创建 `student_records` 表，用于存储学生记录
CREATE TABLE student_records (
    id INTEGER PRIMARY KEY AUTO_INCREMENT, -- 自增主键
    student_id VARCHAR(50), -- 学生学号
    camera_id INTEGER, -- 摄像头ID
    timestamp DATETIME, -- 时间戳
    location_x DOUBLE(9, 6), -- X坐标
    location_y DOUBLE(9, 6), -- Y坐标
    has_backpack BOOLEAN, -- 是否背包
    has_umbrella BOOLEAN, -- 是否带雨伞
    has_bicycle BOOLEAN, -- 是否骑自行车
    feature_vector BLOB, -- 特征向量（以二进制存储）
    image_frame BLOB, -- 图像帧（以二进制存储）
    confidence_east FLOAT, -- 东方向置信度
    confidence_south FLOAT, -- 南方向置信度
    confidence_west FLOAT, -- 西方向置信度
    confidence_north FLOAT -- 北方向置信度
);

-- 创建 `cameras` 表，用于存储摄像头位置信息
CREATE TABLE cameras (
    camera_id INTEGER PRIMARY KEY, -- 摄像头ID
    location_x DOUBLE(9, 6), -- X坐标
    location_y DOUBLE(9, 6), -- Y坐标
    name VARCHAR(100) -- 摄像头名称
);

-- 创建 `camera_videos` 表，用于存储摄像头视频信息
CREATE TABLE camera_videos (
    id INTEGER PRIMARY KEY AUTO_INCREMENT, -- 自增主键
    camera_id INTEGER, -- 摄像头ID
    date DATE, -- 日期
    start_time TIME, -- 视频开始时间
    end_time TIME, -- 视频结束时间
    video_path VARCHAR(255), -- 视频文件路径
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

-- 创建 `student_trajectories` 表，用于存储学生轨迹数据
CREATE TABLE student_trajectories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT, -- 自增主键
    student_id VARCHAR(50), -- 学生学号
    trajectory_data BLOB, -- 轨迹数据（以二进制存储）
    timestamp DATETIME -- 时间戳
);