import logging
import os

# 创建日志目录
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{log_dir}/deid_assess.log"),
        logging.StreamHandler()
    ]
)

# 创建日志记录器
def get_logger(name):
    return logging.getLogger(name)
