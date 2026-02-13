import platform
import psutil
from logger import logger  # 日志管理器

class HardwareCollector:

    def collect_all(self):
        """
        采集特定的7个硬件指标：
        1. 操作系统信息 (os_info)
        2. CPU配置 (cpu_config)
        3. CPU占有率 (cpu_usage)
        4. 内存大小 (memory_size)
        5. 内存占有率 (memory_usage)
        6. 硬盘大小 (disk_size)
        7. 硬盘使用率 (disk_usage)
        """
        try:
            # ---------------- 1. 操作系统信息 ----------------
            os_info = platform.platform()

            # ---------------- 2. CPU配置 ----------------
            processor_name = platform.processor()
            if not processor_name:
                processor_name = platform.machine()  # 如果获取不到详细名称，使用机器类型作为备选

            physical_cores = psutil.cpu_count(logical=False)  # 物理核心
            logical_cores = psutil.cpu_count(logical=True)  # 逻辑核心

            # 格式化输出，例如: Intel64 Family 6 Model 158 [4 Cores / 8 Threads]
            cpu_config = f"{processor_name} [{physical_cores} Cores / {logical_cores} Threads]"

            # ---------------- 3. CPU占有率 ----------------
            # interval=1 会阻塞1秒钟以计算准确的CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)

            # ---------------- 4. 内存大小 & 5. 内存占有率 ----------------
            mem = psutil.virtual_memory()
            # 将字节转换为GB，保留2位小数
            memory_total_gb = round(mem.total / (1024 ** 3), 2)
            memory_size = f"{memory_total_gb} GB"
            memory_usage = mem.percent

            # ---------------- 6. 硬盘大小 & 7. 硬盘使用率 ----------------
            # 自动判断操作系统来选择监控的根路径
            if platform.system() == 'Windows':
                disk_path = 'C:\\'
            else:
                disk_path = '/'

            disk_info = psutil.disk_usage(disk_path)

            disk_total_gb = round(disk_info.total / (1024 ** 3), 2)
            disk_size = f"{disk_total_gb} GB"
            disk_usage = disk_info.percent

            # 组装结果字典
            result = {
                "os_info": os_info,  # 操作系统信息
                "cpu_config": cpu_config,  # CPU配置
                "cpu_usage": cpu_usage,  # CPU占有率 (%)
                "memory_size": memory_size,  # 内存大小 (GB)
                "memory_usage": memory_usage,  # 内存占有率 (%)
                "disk_size": disk_size,  # 硬盘大小 (GB)
                "disk_usage": disk_usage  # 硬盘使用率 (%)
            }

            logger.info(f"Collected hardware metrics: {result}")
            return result

        except Exception as e:
            logger.error(f"Error collecting hardware metrics: {e}")
            # 发生错误时返回带默认值的字典，防止程序崩溃
            return {
                "os_info": "Unknown",
                "cpu_config": "Unknown",
                "cpu_usage": 0,
                "memory_size": "0 GB",
                "memory_usage": 0,
                "disk_size": "0 GB",
                "disk_usage": 0
            }


if __name__ == "__main__":
    # 本地测试代码
    collector = HardwareCollector()
    print(collector.collect_all())