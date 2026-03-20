#!/usr/bin/env python3
"""
RAG 服务测试脚本

使用方法:
1. 在桌面创建"法律法规大全"文件夹
2. 放入 PDF/Word/TXT 法律文档
3. 运行: python test_rag.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rag_service import RagService


async def main():
    """测试 RAG 服务"""
    
    print("=" * 60)
    print("法律法规 RAG 服务测试")
    print("=" * 60)
    
    # 初始化服务
    print("\n1. 初始化 RAG 服务...")
    service = RagService()
    print(f"   桌面路径: {service.get_desktop_path()}")
    
    # 加载文档
    print("\n2. 加载法律法规文档...")
    try:
        stats = service.load_from_desktop("法律法规大全")
        print(f"   总文件数: {stats['total_files']}")
        print(f"   成功加载: {stats['loaded_files']}")
        print(f"   失败文件: {stats['failed_files']}")
        print(f"   总切片数: {stats['total_chunks']}")
        
        if stats['documents']:
            print("\n   已加载文档:")
            for doc in stats['documents'][:5]:  # 只显示前5个
                print(f"     - {doc['file']} ({doc['chunks']} chunks)")
    except FileNotFoundError as e:
        print(f"   错误: {e}")
        print("\n   请先在桌面创建'法律法规大全'文件夹并放入法律文档")
        return
    
    # 搜索测试
    print("\n3. 搜索测试...")
    test_queries = [
        "劳动合同法关于试用期的规定",
        "劳动合同解除的条件",
        "工资支付相关规定",
    ]
    
    for query in test_queries:
        print(f"\n   查询: {query}")
        results = service.search(query, top_k=3)
        
        if results:
            print(f"   找到 {len(results)} 条结果:")
            for i, r in enumerate(results, 1):
                print(f"\n   [{i}] {r['file_name']} (相似度: {r['score']:.3f})")
                # 只显示前100字
                content = r['content'][:100].replace('\n', ' ')
                print(f"       {content}...")
        else:
            print("   未找到相关结果")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
