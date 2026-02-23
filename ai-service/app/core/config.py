"""
应用配置管理
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # 应用信息
    app_name: str = Field(default="智能教育平台 AI 服务", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, description="监听端口")
    workers: int = Field(default=1, description="工作进程数")
    
    # OpenAI 配置
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI Base URL")
    openai_model: str = Field(default="gpt-4", description="默认模型")
    openai_temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    openai_max_tokens: int = Field(default=2000, ge=1, le=4000, description="最大Token数")
    
    # 备用模型配置
    azure_openai_api_key: Optional[str] = Field(default=None, description="Azure OpenAI API Key")
    azure_openai_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI Endpoint")
    azure_openai_deployment: Optional[str] = Field(default=None, description="Azure OpenAI Deployment")

    # Ollama 配置
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", description="Ollama Base URL")
    ollama_api_key: Optional[str] = Field(default=None, description="Ollama API Key（如不需要可为空）")
    ollama_embedding_model: str = Field(default="qwen3-embedding:4b", description="Ollama Embedding 模型")
    ollama_qwen_model: str = Field(default="qwen2.5:7b-instruct", description="Ollama Qwen 聊天模型")
    ollama_qwen_url: Optional[str] = Field(default=None, description="Ollama Qwen 服务地址（为空则使用 ollama_base_url）")
    
    # 向量数据库配置
    chroma_persist_directory: str = Field(default="./chroma_db", description="ChromaDB 持久化目录")
    chroma_collection_name: str = Field(default="edu_knowledge", description="ChromaDB 集合名称")
    
    # 知识库配置
    max_upload_file_size: int = Field(default=50 * 1024 * 1024, description="最大上传文件大小(字节)")
    allowed_extensions: List[str] = Field(default=["pdf", "txt", "docx", "md"], description="允许的文件扩展名")
    chunk_size: int = Field(default=1000, description="文本切分大小")
    chunk_overlap: int = Field(default=200, description="文本切分重叠大小")
    
    # 缓存配置
    redis_url: Optional[str] = Field(default=None, description="Redis URL")
    cache_ttl: int = Field(default=3600, description="缓存过期时间(秒)")
    
    # 限流配置
    rate_limit_per_minute: int = Field(default=60, description="每分钟请求限制")

    # LangSmith 配置
    langsmith_project_name: str = Field(default="智能教育平台-AI-Service", description="LangSmith Project 名称")

    # MongoDB 对话存储配置
    mongodb_enabled: bool = Field(default=True, description="是否启用 MongoDB 对话存储")
    mongodb_uri: str = Field(default="mongodb://127.0.0.1:27017", description="MongoDB 连接 URI")
    mongodb_database: str = Field(default="ai_service", description="MongoDB 数据库名")
    mongodb_chat_collection: str = Field(default="rag_chat_messages", description="MongoDB 对话集合名")
    mongodb_history_limit: int = Field(default=40, ge=1, le=200, description="从 Mongo 回填历史消息数量")
    
@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()


settings = get_settings()
