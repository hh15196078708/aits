import schedule
import time
import threading
import logging
from core.authorize import AuthorizeManager

logger = logging.getLogger(__name__)

class Engine:
    """流量客户端核心控制引擎"""

    def __init__(self, settings):
        self.settings = settings
        self.auth_manager = AuthorizeManager()
        self.running = False
        self._thread = None

    def _heartbeat_job(self):
        """执行心跳检测任务"""
        logger.debug("Executing scheduled heartbeat check...")
        result = self.auth_manager.check_auth()
        if not result:
            logger.warning("Heartbeat check failed, auth manager will attempt re-registration.")

    def _run_scheduler(self):
        """调度器运行循环"""
        # 配置心跳周期
        interval = self.settings.heartbeat_interval
        schedule.every(interval).seconds.do(self._heartbeat_job)
        
        logger.info(f"Heartbeat task scheduled every {interval} seconds.")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        """启动引擎"""
        if self.running:
            return
            
        self.running = True
        # 先执行一次同步鉴权/注册
        if self.auth_manager.check_auth():
            logger.info("Initial authentication successful.")
        
        # 开启后台线程执行心跳调度
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        logger.info("Engine started successfully.")

    def stop(self):
        """停止引擎"""
        self.running = False
        schedule.clear()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Engine stopped.")