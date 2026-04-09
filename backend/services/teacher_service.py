# -*- coding: utf-8 -*-
"""
教师服务模块
============
- CRUD: 教师新增/查询/编辑/删除，支持学科、职务、班级筛选
- 权限过滤: 教师仅查自身，校务查全量
- 班级绑定: 教师与班级的绑定/解绑操作（通过class_ids关联）
- 数据一致性: 删除教师时校验是否为班级班主任
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.responses import StreamingResponse

from database.models.teacher import Teacher
from database.models.class_ import Class
from database.models.user import User
from core.response import success_response, error_response
from utils.logger import logger


def get_list(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict:
    """
    分页查询教师列表（权限过滤）
    
    Args:
        db: 数据库会话
        current_user: 当前登录用户
        page: 页码
        page_size: 每页数量
        keyword: 关键词（姓名）
        subject: 学科
    
    Returns:
        dict: 教师列表和总数
    """
    query = db.query(Teacher)
    
    # 权限过滤
    if current_user.role == "teacher":
        # 教师仅查自己：通过user.name匹配teacher.name
        query = query.filter(Teacher.name == current_user.name)
    # admin角色：全量查询
    
    # 筛选条件
    if keyword:
        query = query.filter(Teacher.name.contains(keyword))
    if subject:
        query = query.filter(Teacher.subject == subject)
    
    # 统计总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    teachers = query.order_by(Teacher.id.desc()).offset(offset).limit(page_size).all()
    
    # 查询班级名称
    list_data = []
    for t in teachers:
        class_names = ""
        if t.class_ids:
            class_ids = [int(cid.strip()) for cid in t.class_ids.split(",") if cid.strip()]
            if class_ids:
                classes = db.query(Class).filter(Class.id.in_(class_ids)).all()
                class_names = ",".join([c.name for c in classes])
        
        list_data.append({
            "id": t.id,
            "name": t.name,
            "subject": t.subject,
            "title": t.title,
            "class_ids": t.class_ids,
            "class_names": class_names,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        })
    
    return success_response(data={"list": list_data, "total": total})


def create(
    db: Session,
    name: str,
    subject: str,
    title: str,
    class_ids: Optional[str] = None,
) -> dict:
    """
    新增教师
    
    Args:
        db: 数据库会话
        name: 姓名
        subject: 学科
        title: 职称
        class_ids: 班级ID列表（逗号分隔）
    
    Returns:
        dict: 操作结果
    """
    # 校验职称
    if title not in ("head_teacher", "normal"):
        return error_response(msg="职称只能是 head_teacher 或 normal")
    
    # 校验班级ID是否存在
    if class_ids:
        cid_list = [int(cid.strip()) for cid in class_ids.split(",") if cid.strip()]
        if cid_list:
            existing_count = db.query(Class).filter(Class.id.in_(cid_list)).count()
            if existing_count != len(cid_list):
                return error_response(msg="部分班级ID不存在")
    
    teacher = Teacher(
        name=name,
        subject=subject,
        title=title,
        class_ids=class_ids,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    
    logger.info(f"创建教师成功: {name}")
    
    return success_response(msg="创建成功", data={"id": teacher.id})


def update(
    db: Session,
    teacher_id: int,
    name: Optional[str] = None,
    subject: Optional[str] = None,
    title: Optional[str] = None,
    class_ids: Optional[str] = None,
) -> dict:
    """
    更新教师信息
    
    Args:
        db: 数据库会话
        teacher_id: 教师ID
        其他参数: 可选更新字段
    
    Returns:
        dict: 操作结果
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return error_response(msg="教师不存在")
    
    if name is not None:
        teacher.name = name
    if subject is not None:
        teacher.subject = subject
    if title is not None:
        if title not in ("head_teacher", "normal"):
            return error_response(msg="职称只能是 head_teacher 或 normal")
        teacher.title = title
    if class_ids is not None:
        # 校验班级ID是否存在
        if class_ids:
            cid_list = [int(cid.strip()) for cid in class_ids.split(",") if cid.strip()]
            if cid_list:
                existing_count = db.query(Class).filter(Class.id.in_(cid_list)).count()
                if existing_count != len(cid_list):
                    return error_response(msg="部分班级ID不存在")
        teacher.class_ids = class_ids
    
    db.commit()
    db.refresh(teacher)
    
    logger.info(f"更新教师成功: {teacher_id}")
    
    return success_response(msg="更新成功")


def delete(db: Session, teacher_id: int) -> dict:
    """
    删除教师（校验是否为班主任）
    
    Args:
        db: 数据库会话
        teacher_id: 教师ID
    
    Returns:
        dict: 操作结果
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return error_response(msg="教师不存在")
    
    # 校验是否为某班班主任
    class_as_head = db.query(Class).filter(Class.head_teacher_id == teacher_id).first()
    if class_as_head:
        return error_response(msg=f"该教师是 {class_as_head.name} 的班主任，请先更换班主任")
    
    db.delete(teacher)
    db.commit()
    
    logger.info(f"删除教师成功: {teacher_id}")
    
    return success_response(msg="删除成功")


def bind_classes(
    db: Session,
    teacher_id: int,
    class_ids: List[int],
) -> dict:
    """
    绑定班级
    
    Args:
        db: 数据库会话
        teacher_id: 教师ID
        class_ids: 班级ID列表
    
    Returns:
        dict: 操作结果
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return error_response(msg="教师不存在")
    
    # 校验班级是否存在
    if class_ids:
        existing_classes = db.query(Class).filter(Class.id.in_(class_ids)).all()
        if len(existing_classes) != len(class_ids):
            return error_response(msg="部分班级不存在")
    
    # 合并现有班级和新班级
    existing_ids = set()
    if teacher.class_ids:
        existing_ids = {int(cid.strip()) for cid in teacher.class_ids.split(",") if cid.strip()}
    
    new_ids = existing_ids.union(set(class_ids))
    teacher.class_ids = ",".join(map(str, sorted(new_ids))) if new_ids else None
    
    db.commit()
    
    logger.info(f"教师 {teacher_id} 绑定班级: {class_ids}")
    
    return success_response(msg="绑定成功")


def unbind_classes(
    db: Session,
    teacher_id: int,
    class_ids: List[int],
) -> dict:
    """
    解绑班级
    
    Args:
        db: 数据库会话
        teacher_id: 教师ID
        class_ids: 班级ID列表
    
    Returns:
        dict: 操作结果
    """
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return error_response(msg="教师不存在")
    
    # 解绑班级
    existing_ids = set()
    if teacher.class_ids:
        existing_ids = {int(cid.strip()) for cid in teacher.class_ids.split(",") if cid.strip()}
    
    new_ids = existing_ids - set(class_ids)
    teacher.class_ids = ",".join(map(str, sorted(new_ids))) if new_ids else None
    
    db.commit()
    
    logger.info(f"教师 {teacher_id} 解绑班级: {class_ids}")
    
    return success_response(msg="解绑成功")
