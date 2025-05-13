create table cameras
(
    camera_id  int                         not null
        primary key,
    location_x double(9, 6)                null,
    location_y double(9, 6)                null,
    name       varchar(100)                null,
    ip_address varchar(255) default ''     null comment '摄像头IP地址',
    port       int          default 554    null comment '摄像头端口号',
    protocol   varchar(50)  default 'rtsp' null comment '访问协议(rtsp/http/rtmp等)',
    username   varchar(255) default ''     null comment '摄像头访问用户名',
    password   varchar(255) default ''     null comment '摄像头访问密码',
    rtsp_url   varchar(512) default ''     null comment '完整的RTSP URL'
);

create table camera_videos
(
    id                  int auto_increment
        primary key,
    camera_id           int          null,
    date                date         null,
    start_time          time         null,
    end_time            time         null,
    video_path          varchar(255) null,
    tracking_video_path varchar(255) null,
    constraint camera_videos_ibfk_1
        foreign key (camera_id) references cameras (camera_id)
);

create index camera_id
    on camera_videos (camera_id);

create table students
(
    student_id      varchar(50)               not null
        primary key,
    name            varchar(100)              not null,
    gender          enum ('男', '女', '其他') not null,
    grade           varchar(10)               null,
    major           varchar(100)              null,
    phone           varchar(20)               null,
    email           varchar(100)              null,
    birth_date      date                      null,
    enrollment_date date                      null
);

create table student_records
(
    id               int auto_increment
        primary key,
    student_id       varchar(50)            null,
    camera_id        int                    null,
    timestamp        datetime               null,
    location_x       double(9, 6)           null,
    location_y       double(9, 6)           null,
    has_backpack     tinyint(1)             null,
    has_umbrella     tinyint(1)             null,
    has_bicycle      tinyint(1)             null,
    feature_vector   blob                   null,
    image_frame      blob                   null,
    confidence_east  float                  null,
    confidence_south float                  null,
    confidence_west  float                  null,
    confidence_north float                  null,
    clothing_color   varchar(50) default '' null comment '学生衣服颜色',
    constraint fk_student
        foreign key (student_id) references students (student_id)
            on update cascade on delete cascade
);

create table student_trajectories
(
    id                  int auto_increment
        primary key,
    student_id          varchar(50)                        null,
    tracking_session_id varchar(50)                        null,
    start_time          datetime                           null,
    end_time            datetime                           null,
    path_points         json                               null,
    camera_sequence     varchar(255)                       null,
    total_distance      double                             null,
    average_speed       double                             null,
    created_at          datetime default CURRENT_TIMESTAMP null,
    constraint student_trajectories_ibfk_1
        foreign key (student_id) references students (student_id)
            on delete cascade
);

create index student_id
    on student_trajectories (student_id);

create table users
(
    user_id       int auto_increment
        primary key,
    username      varchar(50)                        not null,
    password_hash varchar(255)                       not null,
    role          enum ('admin', 'user')             not null,
    real_name     varchar(100)                       null,
    email         varchar(100)                       null,
    phone         varchar(20)                        null,
    created_at    datetime default CURRENT_TIMESTAMP null,
    updated_at    datetime default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP,
    constraint username
        unique (username)
);

