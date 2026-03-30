"""E2E test for Supervisor Multi-Agent with local Ollama."""
import asyncio
import os
import sys
import time

# Set env vars before any imports
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["MONGODB_ENABLED"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
# Clear proxy vars to prevent Ollama routing through system proxies
for var in ["http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(var, None)

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


async def test_e2e():
    from app.agents.supervisor_agent import create_supervisor_plan_agent
    from langchain_core.messages import HumanMessage

    print("=== E2E Test: Supervisor Agent with Ollama ===", flush=True)
    agent = create_supervisor_plan_agent()

    # Use small week count to keep inference fast
    query = (
        "请生成一份整学期教案规划。\n"
        "学科：劳动法\n年级：大学三年级\n学期周数：4\n"
        "每周课时：2\n班级人数：40\n请严格按结构化字段输出。"
    )

    start = time.time()
    print("Starting agent.ainvoke...", flush=True)
    result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.1f}s", flush=True)

    assert "structured_response" in result, "Missing structured_response"
    assert "agent_meta" in result, "Missing agent_meta"

    sr = result["structured_response"]
    meta = result["agent_meta"]

    print(f"semester_title: {sr.semester_title}", flush=True)
    print(f"subject: {sr.subject}", flush=True)
    print(f"weekly_plans count: {len(sr.weekly_plans)}", flush=True)

    for skill_name, status in meta["skill_status"].items():
        print(f"  {skill_name}: {status}", flush=True)

    print(f"data_gaps: {meta['data_gaps']}", flush=True)
    print(f"conflicts: {meta['conflicts']}", flush=True)
    print(f"total_time_ms: {meta['total_time_ms']}", flush=True)

    success_count = sum(1 for s in meta["skill_status"].values() if s == "success")
    print(f"成功 skills: {success_count}/4", flush=True)
    assert success_count >= 2, f"至少2个 skill 应成功，实际 {success_count}"

    print("=== E2E Test PASSED ===", flush=True)


if __name__ == "__main__":
    asyncio.run(test_e2e())
