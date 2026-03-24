FROM python:3.11-slim

WORKDIR /app

# Install dependencies (pinned to exact versions used in development)
RUN pip install --no-cache-dir \
    streamlit==1.55.0 \
    pandas==2.3.3 \
    plotly==6.6.0 \
    openpyxl==3.1.5

# Copy application and all data files
COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "syndicate_explorer.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
