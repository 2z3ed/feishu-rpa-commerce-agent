#!/usr/bin/env python3
"""
飞书长连接启动器
用于在后台启动飞书长连接监听器

用法:
    python -m app.services.feishu.runner
"""

import time
import os
from app.services.feishu.longconn import longconn_listener
from app.core.logging import logger


def main():
    # 打印启动信息以便确认版本
    logger.info("==========================================")
    logger.info("Starting Feishu Long Connection Listener")
    logger.info("Working dir: %s", os.getcwd())
    logger.info("Parser path: app/services/feishu/parser.py")
    logger.info("Client path: app/services/feishu/client.py")
    logger.info("==========================================")
    
    longconn_listener.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        longconn_listener.stop()


if __name__ == "__main__":
    main()