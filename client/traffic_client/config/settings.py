import json
import os
import logging

logger = logging.getLogger(__name__)


class Settings:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 获取当前脚本所在目录的绝对路径
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, 'config.json')
        self._config = self._load_config()
        self._initialized = True

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件未找到: {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件出错: {e}")
            return {}

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            logger.error(f"保存配置文件出错: {e}")

    @property
    def server_url(self):
        return self._config.get("server_url", "http://localhost:82")

    @property
    def heartbeat_interval(self):
        """获取心跳间隔，默认为 5 秒"""
        return self._config.get("heartbeat_interval", 5)

    @property
    def project_id(self):
        return self._config.get("project_id", "")

    @property
    def client_id(self):
        return self._config.get("client_id", "")

    @client_id.setter
    def client_id(self, value):
        self._config["client_id"] = value
        self.save_config()

    @property
    def client_secret(self):
        return self._config.get("client_secret", "")

    @client_secret.setter
    def client_secret(self, value):
        self._config["client_secret"] = value
        self.save_config()


# --- 修改处：将实例重命名为 client_settings ---
client_settings = Settings()