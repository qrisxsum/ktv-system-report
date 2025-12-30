"""
缓存文件清理服务

定期清理上传目录中的旧缓存文件
"""
import os
import glob
from datetime import datetime, timedelta
from typing import Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    IntervalTrigger = None

from app.config import get_settings

settings = get_settings()
scheduler: Optional[AsyncIOScheduler] = None


def cleanup_old_files(days: int = 7) -> dict:
    """
    清理上传目录中超过指定天数的文件
    
    参数:
    - days: 保留最近N天的文件，默认7天
    
    返回:
    - dict: 包含删除文件数量和释放空间的字典
    """
    upload_dir = settings.UPLOAD_DIR
    if not os.path.exists(upload_dir):
        return {
            "deleted_count": 0,
            "freed_space_mb": 0,
            "error": "上传目录不存在",
        }

    deleted_count = 0
    freed_space = 0
    cutoff_time = datetime.now() - timedelta(days=days)
    errors = []

    try:
        # 获取所有文件
        files = glob.glob(os.path.join(upload_dir, "*"))
        
        for file_path in files:
            if os.path.isfile(file_path):
                # 获取文件修改时间
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # 如果文件超过指定天数，则删除
                if file_mtime < cutoff_time:
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        freed_space += file_size
                    except Exception as e:
                        errors.append(f"删除文件失败 {file_path}: {e}")

        freed_space_mb = round(freed_space / (1024 * 1024), 2)
        
        return {
            "deleted_count": deleted_count,
            "freed_space_mb": freed_space_mb,
            "errors": errors if errors else None,
        }
    except Exception as e:
        return {
            "deleted_count": 0,
            "freed_space_mb": 0,
            "error": str(e),
        }


async def scheduled_cleanup():
    """定时清理任务"""
    result = cleanup_old_files(days=7)
    if result.get("deleted_count", 0) > 0:
        print(
            f"🧹 自动清理完成: 删除 {result['deleted_count']} 个文件，"
            f"释放 {result.get('freed_space_mb', 0)} MB 空间"
        )
    if result.get("errors"):
        print(f"⚠️ 清理过程中出现错误: {result['errors']}")


def start_scheduler():
    """启动定时清理任务"""
    global scheduler
    
    if not APSCHEDULER_AVAILABLE:
        print("⚠️ APScheduler 未安装，跳过定时清理任务启动")
        return None
    
    if scheduler is not None:
        return scheduler
    
    try:
        scheduler = AsyncIOScheduler()
        
        # 每24小时执行清理任务
        scheduler.add_job(
            scheduled_cleanup,
            trigger=IntervalTrigger(hours=24),
            id="cleanup_cache_files",
            name="清理缓存文件",
            replace_existing=True,
        )
        
        scheduler.start()
        print("✅ 缓存文件自动清理任务已启动（每24小时执行一次）")
        
        return scheduler
    except Exception as e:
        print(f"⚠️ 启动定时清理任务失败: {e}")
        scheduler = None
        return None


def stop_scheduler():
    """停止定时清理任务"""
    global scheduler
    
    if scheduler is not None:
        try:
            scheduler.shutdown()
            scheduler = None
            print("🛑 缓存文件自动清理任务已停止")
        except Exception as e:
            print(f"⚠️ 停止定时清理任务失败: {e}")
            scheduler = None

