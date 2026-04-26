# 使用 Streamlit 官方基础镜像
FROM streamlit/streamlit:latest

# 切换到 root 用户以安装系统依赖
USER root

# 安装 libzbar0 (pyzbar 的系统依赖) 和清理缓存以减小体积
RUN apt-get update && \
    apt-get install -y libzbar0 && \
    rm -rf /var/lib/apt/lists/*

# 切回 streamlit 用户 (安全最佳实践)
USER streamlit

# 复制项目文件
COPY . /app

# 设置工作目录
WORKDIR /app

# 启动命令 (Streamlit Cloud 通常会自动检测，但显式写出更稳妥)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]