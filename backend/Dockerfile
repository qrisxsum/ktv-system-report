# ========================================
# KTV 报表系统 - 后端 Dockerfile
# ========================================

# 基础镜像
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    # 安装 LibreOffice 核心和表格组件（用于 Excel 修复转换）
    libreoffice-calc \
    libreoffice-java-common \
    # 中文字体支持，确保转换过程不乱码
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# ========================================
# 开发环境
# ========================================
FROM base as development

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令 - 开发模式带热重载
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]

# ========================================
# 生产环境
# ========================================
FROM base as production

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# 复制应用代码
COPY --chown=appuser:appuser . .

# 暴露端口
EXPOSE 8000

# 启动命令 - 生产模式
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

