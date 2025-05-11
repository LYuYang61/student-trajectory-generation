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
    tracking_video_path VARCHAR(255), -- 目标跟踪结果视频路径
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

-- 创建 `student_trajectories` 表，用于存储学生轨迹数据
CREATE TABLE student_trajectories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT, -- 自增主键
    student_id VARCHAR(50), -- 学生学号
    trajectory_data BLOB, -- 轨迹数据（以二进制存储）
    timestamp DATETIME -- 时间戳
);

-- 创建 `students` 表，用于存储学生基本信息
CREATE TABLE students (
    student_id VARCHAR(50) PRIMARY KEY,     -- 学生学号，主键
    name VARCHAR(100) NOT NULL,             -- 姓名
    gender ENUM('男', '女', '其他') NOT NULL, -- 性别（可根据实际需求拓展）
    grade VARCHAR(10),                      -- 年级，例如 "2021"
    major VARCHAR(100),                     -- 专业名称
    phone VARCHAR(20),                      -- 联系电话
    email VARCHAR(100),                     -- 电子邮箱
    birth_date DATE,                        -- 出生日期
    enrollment_date DATE                    -- 入学日期
);

ALTER TABLE student_records
ADD CONSTRAINT fk_student
FOREIGN KEY (student_id) REFERENCES students(student_id)
ON DELETE CASCADE ON UPDATE CASCADE;

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,     -- 用户唯一 ID
    username VARCHAR(50) NOT NULL UNIQUE,       -- 用户名（唯一）
    password_hash VARCHAR(255) NOT NULL,        -- 密码哈希值
    role ENUM('admin', 'user') NOT NULL,        -- 用户角色：管理员 / 普通用户
    real_name VARCHAR(100),                     -- 真实姓名
    email VARCHAR(100),                         -- 邮箱地址
    phone VARCHAR(20),                          -- 电话
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 注册时间
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP -- 更新时间
);

-- 修改 `student_trajectories` 表，更好地存储学生轨迹数据
DROP TABLE IF EXISTS student_trajectories;
CREATE TABLE student_trajectories (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,     -- 自增主键
    student_id VARCHAR(50),                    -- 学生学号
    tracking_session_id VARCHAR(50),           -- 轨迹会话ID (用于分组同一次跟踪的记录)
    start_time DATETIME,                       -- 轨迹开始时间
    end_time DATETIME,                         -- 轨迹结束时间
    path_points JSON,                          -- 轨迹路径点 (存储格式: [{camera_id, timestamp, location_x, location_y, confidence},...])
    camera_sequence VARCHAR(255),              -- 摄像头序列 (例如: "1,3,5,2" 记录学生经过的摄像头顺序)
    total_distance DOUBLE,                     -- 总移动距离
    average_speed DOUBLE,                      -- 平均速度
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

ALTER TABLE cameras
ADD COLUMN ip_address VARCHAR(255) DEFAULT '' COMMENT '摄像头IP地址',
ADD COLUMN port INTEGER DEFAULT 554 COMMENT '摄像头端口号',
ADD COLUMN protocol VARCHAR(50) DEFAULT 'rtsp' COMMENT '访问协议(rtsp/http/rtmp等)',
ADD COLUMN username VARCHAR(255) DEFAULT '' COMMENT '摄像头访问用户名',
ADD COLUMN password VARCHAR(255) DEFAULT '' COMMENT '摄像头访问密码',
ADD COLUMN rtsp_url VARCHAR(512) DEFAULT '' COMMENT '完整的RTSP URL';


UPDATE cameras SET
ip_address = '192.168.1.100',
port = 554,
protocol = 'rtsp',
username = 'admin',
password = 'admin',
rtsp_url = 'rtsp://admin:admin@192.168.1.100:554/stream'
WHERE camera_id = 1;