# -*- coding: utf-8 -*-
"""
@模块名称: 服务自启动管理 (core/service_manager.py)
@功能描述:
    1. Windows: 实现 pywin32 服务类，处理 Start/Stop/SvcDoRun 逻辑。
    2. Linux: 生成 .service 文件并调用 systemctl 命令进行注册。
@性能约束: 服务轮询间隔需配合CPU占用要求。
"""

import sys
import time
import os
import socket
from pathlib import Path

# 引入项目工具
# 假设在项目根目录运行或已设置PYTHONPATH，实际部署会处理路径问题
try:
    from utils.system_tools import SystemUtils
except ImportError:
    # 兼容直接运行此脚本的情况，临时添加路径
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.system_tools import SystemUtils

# -----------------------------------------------------------
# Windows 服务实现区域
# -----------------------------------------------------------
if SystemUtils.is_windows():
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class TrafficAnalysisService(win32serviceutil.ServiceFramework):
        # 服务名和显示名称
        _svc_name_ = "TrafficAnalysisClient"
        _svc_display_name_ = "Traffic Analysis Client Service"
        _svc_description_ = "Traffic Analysis Software Client (Python) - Background Monitor"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.is_alive = True

        def SvcStop(self):
            """服务停止信号回调"""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)
            self.is_alive = False
            # 这里可以添加停止业务逻辑，如关闭抓包线程

        def SvcDoRun(self):
            """服务主运行逻辑"""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.main()

        def main(self):
            """
            主入口：这里将调用 client_main.py 的核心逻辑
            注意：服务环境中，工作目录可能为 System32，需切换到脚本所在目录
            """
            project_root = SystemUtils.get_root_path()
            os.chdir(project_root)

            # --- 模拟启动主程序 ---
            # 实际集成时，这里会 import client_main 并调用 client_main.run()
            # 为了防止服务脚本报错导致系统服务崩溃，必须包裹 Try-Catch
            try:
                # 模拟导入主逻辑
                # from client_main import ClientApp
                # app = ClientApp()
                # app.start()

                # 占位符：保持服务运行
                while self.is_alive:
                    # 检查停止信号，超时时间即为循环间隔
                    rc = win32event.WaitForSingleObject(self.hWaitStop, 3000) # 3秒心跳
                    if rc == win32event.WAIT_OBJECT_0:
                        break

                    # 这里执行周期性检查任务
                    pass

            except Exception as e:
                servicemanager.LogErrorMsg(f"Service Exception: {str(e)}")

# -----------------------------------------------------------
# Linux Systemd 实现区域
# -----------------------------------------------------------
class LinuxServiceManager:
    SERVICE_NAME = "traffic_client.service"
    SYSTEMD_PATH = "/etc/systemd/system/"

    @staticmethod
    def generate_service_file(python_path: str, script_path: str):
        """生成 systemd 配置文件内容"""

        # 必须使用绝对路径
        work_dir = str(Path(script_path).parent)

        content = f"""[Unit]
Description=Traffic Analysis Client Service
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory={work_dir}
# 启动命令：使用指定的Python解释器运行主程序
ExecStart={python_path} {script_path}
# 进程守护：异常退出后3秒重启
Restart=always
RestartSec=3
# 资源限制（可选，systemd层面的兜底）
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""
        return content

    @staticmethod
    def install():
        """安装并启动服务"""
        if not SystemUtils.get_os_type() == 'linux':
            print("Error: This function is for Linux only.")
            return

        python_exec = sys.executable
        # 假设入口是 client_main.py
        main_script = SystemUtils.resolve_path("client_main.py")
        service_file_path = os.path.join(LinuxServiceManager.SYSTEMD_PATH, LinuxServiceManager.SERVICE_NAME)

        print(f"Creating service file at: {service_file_path}")
        content = LinuxServiceManager.generate_service_file(python_exec, main_script)

        try:
            with open(service_file_path, 'w') as f:
                f.write(content)

            # 重新加载配置并启动
            SystemUtils.execute_cmd("systemctl daemon-reload")
            SystemUtils.execute_cmd(f"systemctl enable {LinuxServiceManager.SERVICE_NAME}")
            SystemUtils.execute_cmd(f"systemctl start {LinuxServiceManager.SERVICE_NAME}")
            print("Service installed and started successfully.")

        except PermissionError:
            print("Error: Permission denied. Please run as root (sudo).")
        except Exception as e:
            print(f"Error installing service: {str(e)}")

    @staticmethod
    def uninstall():
        """停止并移除服务"""
        try:
            SystemUtils.execute_cmd(f"systemctl stop {LinuxServiceManager.SERVICE_NAME}")
            SystemUtils.execute_cmd(f"systemctl disable {LinuxServiceManager.SERVICE_NAME}")

            service_file_path = os.path.join(LinuxServiceManager.SYSTEMD_PATH, LinuxServiceManager.SERVICE_NAME)
            if os.path.exists(service_file_path):
                os.remove(service_file_path)
                print("Service file removed.")

            SystemUtils.execute_cmd("systemctl daemon-reload")
            print("Service uninstalled successfully.")
        except Exception as e:
            print(f"Error uninstalling service: {str(e)}")

# -----------------------------------------------------------
# 命令行入口
# -----------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python service_manager.py [install|start|stop|remove]")
        sys.exit(1)

    action = sys.argv[1]

    if SystemUtils.is_windows():
        # Windows直接调用 pywin32 的处理逻辑
        win32serviceutil.HandleCommandLine(TrafficAnalysisService)
    else:
        # Linux 手动分发
        if action == "install":
            LinuxServiceManager.install()
        elif action == "remove" or action == "uninstall":
            LinuxServiceManager.uninstall()
        elif action == "start":
            SystemUtils.execute_cmd(f"systemctl start {LinuxServiceManager.SERVICE_NAME}")
        elif action == "stop":
            SystemUtils.execute_cmd(f"systemctl stop {LinuxServiceManager.SERVICE_NAME}")
        elif action == "status":
            ok, out = SystemUtils.execute_cmd(f"systemctl status {LinuxServiceManager.SERVICE_NAME}")
            print(out)
        else:
            print("Unknown command for Linux. Use: install, remove, start, stop, status")


