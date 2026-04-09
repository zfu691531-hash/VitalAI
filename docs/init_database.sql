-- ============================================================
-- 校园AI教务助手平台 - 数据库初始化脚本
-- 版本: 1.1.0
-- 数据库: MySQL 8.0+
-- 字符集: utf8mb4
-- 设计原则: 无外键约束，ID关联由业务层保证数据一致性
-- 变更记录:
--   v1.0.0 - 7张表基础结构
--   v1.1.0 - 新增 student.student_no / class.status / school_rule.category / ai_history.input_params
-- ============================================================

CREATE DATABASE IF NOT EXISTS `aistu` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `aistu`;

-- ------------------------------------------------------------
-- 1. 用户表 (user)
-- 存储所有用户的登录信息与基础身份信息
-- 密码使用 bcrypt 哈希存储(60字符)，禁止明文或MD5
-- ------------------------------------------------------------
CREATE TABLE `user` (
    `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `username`       VARCHAR(50)  NOT NULL                COMMENT '登录账号，唯一',
    `password_hash`  VARCHAR(255) NOT NULL                COMMENT '密码哈希(bcrypt, 60字符)',
    `role`           ENUM('student','teacher','admin') NOT NULL COMMENT '角色: student-学生, teacher-教师, admin-校务管理员',
    `name`           VARCHAR(50)  NOT NULL                COMMENT '真实姓名',
    `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. 班级表 (class)
-- 存储班级信息，current_count 由业务层维护
-- 注意: class 是 MySQL 保留字，所有引用须用反引号包裹
-- ------------------------------------------------------------
CREATE TABLE `class` (
    `id`              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `grade`           VARCHAR(20)  NOT NULL                COMMENT '年级（如：2024级）',
    `name`            VARCHAR(50)  NOT NULL                COMMENT '班级名称，唯一（如：2024级1班）',
    `head_teacher_id` BIGINT       DEFAULT NULL            COMMENT '班主任ID（关联teacher.id，无外键）',
    `max_count`       INT          NOT NULL DEFAULT 50      COMMENT '人数上限',
    `current_count`   INT          NOT NULL DEFAULT 0       COMMENT '当前人数（业务层维护）',
    `status`          TINYINT      NOT NULL DEFAULT 1       COMMENT '状态: 1-在读, 0-已毕业',
    `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_name` (`name`),
    KEY `idx_grade` (`grade`),
    KEY `idx_head_teacher_id` (`head_teacher_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班级表';

-- ------------------------------------------------------------
-- 3. 教师表 (teacher)
-- 存储教师详细信息
-- class_ids 使用逗号分隔字符串存储绑定班级（如 "1,3,5"）
-- 后端通过 Python split 后传给 SQLAlchemy .in_() 查询
-- 注意: 若班级绑定数 >20，考虑改为关联表 teacher_class
-- ------------------------------------------------------------
CREATE TABLE `teacher` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `name`        VARCHAR(50)  NOT NULL                COMMENT '姓名',
    `subject`     VARCHAR(50)  DEFAULT NULL            COMMENT '任教科目',
    `title`       ENUM('head_teacher','normal') NOT NULL DEFAULT 'normal' COMMENT '职务: head_teacher-班主任, normal-普通教师',
    `class_ids`   VARCHAR(500) DEFAULT NULL            COMMENT '绑定班级ID列表，逗号分隔（关联class.id，无外键）',
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师表';

-- ------------------------------------------------------------
-- 4. 学生表 (student)
-- 存储学生详细信息，标签使用逗号分隔（如 "留守儿童,学困生"）
-- ------------------------------------------------------------
CREATE TABLE `student` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `student_no`  VARCHAR(20)  NOT NULL                COMMENT '学号，唯一',
    `name`        VARCHAR(50)  NOT NULL                COMMENT '姓名',
    `gender`      ENUM('male','female') NOT NULL       COMMENT '性别: male-男, female-女',
    `age`         INT          DEFAULT NULL            COMMENT '年龄',
    `class_id`    BIGINT       DEFAULT NULL            COMMENT '所属班级ID（关联class.id，无外键）',
    `contact`     VARCHAR(20)  DEFAULT NULL            COMMENT '联系方式',
    `specialty`   VARCHAR(200) DEFAULT NULL            COMMENT '个人特长',
    `tags`        VARCHAR(500) DEFAULT NULL            COMMENT '标签，逗号分隔（如：留守儿童,学困生）',
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_student_no` (`student_no`),
    KEY `idx_class_id` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生表';

-- ------------------------------------------------------------
-- 5. 成绩表 (score)
-- 存储学生成绩信息，score 是 MySQL 保留字须用反引号包裹
-- ------------------------------------------------------------
CREATE TABLE `score` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `student_id`  BIGINT       NOT NULL                COMMENT '学生ID（关联student.id，无外键）',
    `class_id`    BIGINT       NOT NULL                COMMENT '班级ID（关联class.id，无外键）',
    `exam_batch`  VARCHAR(50)  NOT NULL                COMMENT '考试批次（如期中、期末）',
    `subject`     VARCHAR(50)  NOT NULL                COMMENT '科目',
    `score`       DECIMAL(5,2) NOT NULL                COMMENT '分数（0-100）',
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_student_id` (`student_id`),
    KEY `idx_class_id` (`class_id`),
    KEY `idx_exam_batch` (`exam_batch`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成绩表';

-- ------------------------------------------------------------
-- 6. AI 历史记录表 (ai_history)
-- 存储AI工具生成内容，支持查看/复用/删除
-- tool_type 枚举值: comment/discipline/notice/rule_qa/score_diag/meeting/interview/group
-- ------------------------------------------------------------
CREATE TABLE `ai_history` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `user_id`       BIGINT       NOT NULL                COMMENT '用户ID（关联user.id，无外键）',
    `tool_type`     VARCHAR(50)  NOT NULL                COMMENT '功能类型（comment/discipline/notice/rule_qa/score_diag/meeting/interview/group）',
    `input_params`  JSON         DEFAULT NULL            COMMENT '输入参数快照(JSON)，用于历史复用',
    `content`       TEXT         NOT NULL                COMMENT 'AI生成的内容',
    `student_id`    BIGINT       DEFAULT NULL            COMMENT '关联学生ID（可选）',
    `class_id`      BIGINT       DEFAULT NULL            COMMENT '关联班级ID（可选）',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_tool_type` (`tool_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI生成历史记录表';

-- ------------------------------------------------------------
-- 7. 校规表 (school_rule)
-- 校规问答机器人的知识库数据源，由校务管理员维护
-- ------------------------------------------------------------
CREATE TABLE `school_rule` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    `category`    VARCHAR(50)  NOT NULL DEFAULT '未分类' COMMENT '校规分类（如：考勤、行为规范、安全）',
    `title`       VARCHAR(200) NOT NULL                COMMENT '校规标题',
    `content`     TEXT         NOT NULL                COMMENT '校规正文',
    `updated_by`  BIGINT       DEFAULT NULL            COMMENT '最后更新人ID（关联user.id，无外键）',
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='校规表';

-- ============================================================
-- 初始化数据
-- ============================================================

-- 初始管理员账号（密码需在应用中通过 bcrypt 生成后填入）
-- 示例: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('admin123'))"
INSERT INTO `user` (`username`, `password_hash`, `role`, `name`) VALUES
('admin', '<bcrypt_hash_of_admin_password>', 'admin', '系统管理员');

-- 示例校规数据（校规问答机器人知识库）
INSERT INTO `school_rule` (`category`, `title`, `content`, `updated_by`) VALUES
('考勤', '考勤管理', '学生应按时到校上课，不得无故迟到、早退、旷课。迟到一次由班主任口头警告，迟到三次通知家长。旷课一天以上需家长到校说明情况。', 1),
('行为规范', '课堂纪律', '上课期间应保持安静，认真听讲，不得交头接耳、随意走动、使用手机等电子设备。违反课堂纪律者，视情节轻重给予口头警告、书面检查、请家长等处理。', 1),
('作业管理', '作业管理', '学生应按时完成各科作业，不得抄袭他人作业。未完成作业者需在规定时间内补交，多次未完成者由任课教师通知家长。', 1);
