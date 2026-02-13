# -*- coding: utf-8 -*-
"""
模块名称: adapters/__init__.py
模块功能: 硬件采集适配器包初始化
依赖模块: 无
系统适配: 所有平台通用

说明:
    本包包含各平台专属的硬件采集模块：
    - win_collector: Windows硬件采集
    - linux_collector: Linux硬件采集（含国产Linux）
    - mac_collector: macOS硬件采集
"""

# 导出各平台采集器类（延迟导入，仅在需要时加载）
__all__ = [
    "WindowsCollector",  # Windows采集器
    "LinuxCollector",  # Linux采集器
    "MacCollector"  # macOS采集器
]
