# -*- coding: utf-8 -*-
"""
班级服务模块
============
- CRUD: 班级新增/查询/编辑/删除，支持年级、状态筛选
- 学生绑定: 班级与学生的关联/解绑操作
- 数据一致性: 删除班级时校验有无学生/成绩，新增时校验班主任角色
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.models.class_ import Class
from database.models.student import Student
from database.models.score import Score
from database.models.teacher import Teacher
from database.models.user import User
from core.response import success_response, error_response
from utils.logger import logger


def get_list(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    grade: Optional[str] = None,
    status: Optional[int] = 1,
) -> dict:
    """
    分页查询班级列表
    
    Args:
        db: 数据库会话
        current_user: 当前登录用户
        page: 页码
        page_size: 每页数量
        grade: 年级
        status: 状态（1-在读，0-毕业）
    
    Returns:
        dict: 班级列表和总数
    """
    query = db.query(Class)
    
    # 权限过滤
    if current_user.role == "teacher":
        # 教师仅查自己绑定的班级
        teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
        if not teacher or not teacher.class_ids:
            return success_response(data={"list": [], "total": 0})
        class_ids = [int(cid.strip()) for cid in teacher.class_ids.split(",") if cid.strip()]
        if not class_ids:
            return success_response(data={"list": [], "total": 0})
        query = query.filter(Class.id.in_(class_ids))
    # admin/student：admin查全量，student不做班级管理（但可能有查看需求）
    
    # 筛选条件
    if grade:
        query = query.filter(Class.grade == grade)
    if status is not None:
        query = query.filter(Class.status == status)
    
    # 统计总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    classes = query.order_by(Class.id.desc()).offset(offset).limit(page_size).all()
    
    # 查询班主任姓名
    teacher_ids = [c.head_teacher_id for c in classes if c.head_teacher_id]
    teacher_map = {}
    if teacher_ids:
        teachers = db.query(Teacher).filter(Teacher.id.in_(teacher_ids)).all()
        teacher_map = {t.id: t.name for t in teachers}
    
    # 构建响应数据
    list_data = []
    for c in classes:
        list_data.append({
            "id": c.id,
            "grade": c.grade,
            "name": c.name,
            "head_teacher_id": c.head_teacher_id,
            "head_teacher_name": teacher_map.get(c.head_teacher_id, ""),
            "max_count": c.max_count,
            "current_count": c.current_count,
            "status": c.status,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        })
    
    return success_response(data={"list": list_data, "total": total})


def get_all(
    db: Session,
    status: Optional[int] = 1,
) -> dict:
    """
    获取所有班级（下拉选择用）
    
    Args:
        db: 数据库会话
        status: 状态（1-在读，0-毕业）
    
    Returns:
        dict: 班级列表
    """
    query = db.query(Class)
    if status is not None:
        query = query.filter(Class.status == status)
    
    classes = query.order_by(Class.grade, Class.name).all()
    
    list_data = [{"id": c.id, "name": c.name, "grade": c.grade} for c in classes]
    
    return success_response(data=list_data)


def create(
    db: Session,
    grade: str,
    name: str,
    head_teacher_id: int,
    max_count: int,
    status: int = 1,
) -> dict:
    """
    新增班级（校验班主任角色、班级名唯一）
    
    Args:
        db: 数据库会话
        grade: 年级
        name: 班级名称
        head_teacher_id: 班主任ID
        max_count: 最大人数
        status: 状态
    
    Returns:
        dict: 操作结果
    """
    # 校验班级名唯一性
    existing = db.query(Class).filter(Class.name == name).first()
    if existing:
        return error_response(msg=f"班级名称 {name} 已存在")
    
    # 校验班主任是否存在
    teacher = db.query(Teacher).filter(Teacher.id == head_teacher_id).first()
    if not teacher:
        return error_response(msg=f"教师ID {head_teacher_id} 不存在")
    
    class_obj = Class(
        grade=grade,
        name=name,
        head_teacher_id=head_teacher_id,
        max_count=max_count,
        current_count=0,
        status=status,
    )
    db.add(class_obj)
    db.commit()
    db.refresh(class_obj)
    
    logger.info(f"创建班级成功: {name}")
    
    return success_response(msg="创建成功", data={"id": class_obj.id})


def update(
    db: Session,
    class_id: int,
    grade: Optional[str] = None,
    name: Optional[str] = None,
    head_teacher_id: Optional[int] = None,
    max_count: Optional[int] = None,
    status: Optional[int] = None,
) -> dict:
    """
    更新班级信息
    
    Args:
        db: 数据库会话
        class_id: 班级ID
        其他参数: 可选更新字段
    
    Returns:
        dict: 操作结果
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return error_response(msg="班级不存在")
    
    # 更新班级名（校验唯一性）
    if name is not None and name != class_obj.name:
        existing = db.query(Class).filter(Class.name == name).first()
        if existing:
            return error_response(msg=f"班级名称 {name} 已存在")
        class_obj.name = name
    
    # 更新班主任（校验教师是否存在）
    if head_teacher_id is not None:
        teacher = db.query(Teacher).filter(Teacher.id == head_teacher_id).first()
        if not teacher:
            return error_response(msg=f"教师ID {head_teacher_id} 不存在")
        class_obj.head_teacher_id = head_teacher_id
    
    if grade is not None:
        class_obj.grade = grade
    if max_count is not None:
        # 校验最大人数不小于当前人数
        if max_count < class_obj.current_count:
            return error_response(msg=f"最大人数不能小于当前人数 {class_obj.current_count}")
        class_obj.max_count = max_count
    if status is not None:
        class_obj.status = status
    
    db.commit()
    db.refresh(class_obj)
    
    logger.info(f"更新班级成功: {class_id}")
    
    return success_response(msg="更新成功")


def delete(db: Session, class_id: int) -> dict:
    """
    删除班级（校验有无学生/成绩）
    
    Args:
        db: 数据库会话
        class_id: 班级ID
    
    Returns:
        dict: 操作结果
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return error_response(msg="班级不存在")
    
    # 校验是否有学生
    student_count = db.query(Student).filter(Student.class_id == class_id).count()
    if student_count > 0:
        return error_response(msg=f"该班级有 {student_count} 名学生，无法删除")
    
    # 校验是否有成绩记录
    score_count = db.query(Score).filter(Score.class_id == class_id).count()
    if score_count > 0:
        return error_response(msg=f"该班级有 {score_count} 条成绩记录，无法删除")
    
    db.delete(class_obj)
    db.commit()
    
    logger.info(f"删除班级成功: {class_id}")
    
    return success_response(msg="删除成功")


def bind_students(
    db: Session,
    class_id: int,
    student_ids: List[int],
) -> dict:
    """
    绑定学生到班级
    
    Args:
        db: 数据库会话
        class_id: 班级ID
        student_ids: 学生ID列表
    
    Returns:
        dict: 操作结果
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return error_response(msg="班级不存在")
    
    # 校验班级容量
    if class_obj.current_count + len(student_ids) > class_obj.max_count:
        return error_response(msg=f"班级容量不足，当前 {class_obj.current_count}/{class_obj.max_count}")
    
    # 校验学生是否存在
    students = db.query(Student).filter(Student.id.in_(student_ids)).all()
    if len(students) != len(student_ids):
        return error_response(msg="部分学生不存在")
    
    # 绑定学生
    bound_count = 0
    for student in students:
        if student.class_id != class_id:
            # 如果学生原班级存在，更新原班级人数
            if student.class_id:
                old_class = db.query(Class).filter(Class.id == student.class_id).first()
                if old_class:
                    old_class.current_count -= 1
            student.class_id = class_id
            student.grade = class_obj.grade
            bound_count += 1
    
    class_obj.current_count += bound_count
    db.commit()
    
    logger.info(f"班级 {class_id} 绑定学生: {bound_count} 名")
    
    return success_response(msg=f"成功绑定 {bound_count} 名学生")


def unbind_students(
    db: Session,
    class_id: int,
    student_ids: List[int],
) -> dict:
    """
    从班级解绑学生
    
    Args:
        db: 数据库会话
        class_id: 班级ID
        student_ids: 学生ID列表
    
    Returns:
        dict: 操作结果
    """
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return error_response(msg="班级不存在")
    
    # 解绑学生
    unbound_count = 0
    for student_id in student_ids:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student and student.class_id == class_id:
            student.class_id = None
            unbound_count += 1
    
    class_obj.current_count -= unbound_count
    db.commit()
    
    logger.info(f"班级 {class_id} 解绑学生: {unbound_count} 名")
    
    return success_response(msg=f"成功解绑 {unbound_count} 名学生")
