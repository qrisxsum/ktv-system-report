# ========================================
# KTV 报表系统 - 前端 Dockerfile
# ========================================

# 基础镜像
FROM node:20-alpine as base

# 设置工作目录
WORKDIR /app

# 设置 npm 镜像（加速下载）
RUN npm config set registry https://registry.npmmirror.com

# ========================================
# 开发环境
# ========================================
FROM base as development

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 5173

# 启动开发服务器 - Vite 热重载
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ========================================
# 构建阶段
# ========================================
FROM base as builder

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ========================================
# 生产环境 - Nginx 静态服务
# ========================================
FROM nginx:alpine as production

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

