from tortoise import Model, fields
from datetime import datetime


class Task(Model):
    """Task model"""
    id = fields.UUIDField(pk=True)
    task_id = fields.CharField(max_length=255, unique=True)
    user_id = fields.CharField(max_length=255)
    user_name = fields.CharField(max_length=255)
    intent = fields.CharField(max_length=255)
    status = fields.CharField(max_length=50, default="pending")  # pending, running, completed, failed
    input_data = fields.JSONField()
    output_data = fields.JSONField(null=True)
    execution_strategy = fields.CharField(max_length=50, null=True)  # api, rpa, api_then_rpa_verify
    platform = fields.CharField(max_length=50, null=True)  # woocommerce, odoo, chatwoot
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class TaskLog(Model):
    """Task log model"""
    id = fields.UUIDField(pk=True)
    task = fields.ForeignKeyField("models.Task", related_name="logs")
    step = fields.CharField(max_length=255)
    message = fields.TextField()
    level = fields.CharField(max_length=50)  # info, warning, error
    created_at = fields.DatetimeField(auto_now_add=True)


class User(Model):
    """User model"""
    id = fields.UUIDField(pk=True)
    feishu_user_id = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255)
    role = fields.CharField(max_length=50)  # product, warehouse, customer_service, finance
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Workflow(Model):
    """Workflow model"""
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    description = fields.TextField()
    definition = fields.JSONField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)