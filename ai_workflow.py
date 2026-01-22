"""
LangGraph + LangChain + Agent 통합 예제
파일 하나로: ReAct Agent with Web Search Tool
"""

import os
from typing import Annotated
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# .env 파일에서 OPENAI_API_KEY 로드 (없으면 설정 필요)
load_dotenv()

# ============ TOOL 정의 ============
@tool
def search_web(query: str) -> str:
    """
    간단한 웹 검색 시뮬레이션
    실제로는 requests + BeautifulSoup 또는 serper.dev API 사용
    """
    # 실제 구현: google search API, bing, serper 등
    results = {
        "파이썬": "파이썬은 1991년 귀도 반로섬이 만든 프로그래밍 언어입니다.",
        "langgraph": "LangGraph는 LangChain 위에서 agent를 그래프로 관리하는 라이브러리입니다.",
        "agent": "Agent는 도구를 사용해 자율적으로 작업하는 AI 시스템입니다.",
    }
    return results.get(query.lower(), f"'{query}' 검색 결과를 찾을 수 없습니다.")

@tool
def calculate(expression: str) -> str:
    """간단한 계산 도구"""
    try:
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"계산 오류: {e}"

# ============ STATE 정의 ============
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ============ AGENT 함수 ============
def should_continue(state: AgentState) -> str:
    """
    마지막 메시지가 tool call인지 확인
    tool call이면 "tools"로, 아니면 "end"로 라우팅
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # tool_calls가 있으면 tools 노드로
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    else:
        return "end"

def call_model(state: AgentState) -> dict:
    """LLM에 메시지 전달"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [search_web, calculate]
    llm_with_tools = llm.bind_tools(tools)
    
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

def process_tool_call(state: AgentState) -> dict:
    """Tool 실행 후 결과를 메시지에 추가"""
    from langchain_core.messages import ToolMessage
    
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_results = []
    
    # 각 tool call 실행
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        
        if tool_name == "search_web":
            result = search_web.invoke(tool_input["query"])
        elif tool_name == "calculate":
            result = calculate.invoke(tool_input["expression"])
        else:
            result = "알 수 없는 도구"
        
        # ToolMessage로 결과 추가
        tool_results.append(
            ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
                name=tool_name
            )
        )
    
    return {"messages": tool_results}

# ============ GRAPH 구성 ============
graph_builder = StateGraph(AgentState)

# 노드 추가
graph_builder.add_node("agent", call_model)
graph_builder.add_node("tools", process_tool_call)

# 엣지 추가
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END,
    },
)
graph_builder.add_edge("tools", "agent")

# 그래프 컴파일
graph = graph_builder.compile()

# ============ 실행 ============
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    
    # 사용자 질문
    user_input = "파이썬이 뭐야? 그리고 10 + 5 계산해줘"
    print(f"\n👤 사용자: {user_input}")
    print("-" * 60)
    
    # Agent 실행
    result = graph.invoke({"messages": [HumanMessage(content=user_input)]})
    
    # 최종 응답 출력
    final_message = result["messages"][-1]
    print(f"🤖 Agent: {final_message.content}")
    print("-" * 60)
    
    # 모든 메시지 확인 (디버깅용)
    print("\n📋 전체 대화 흐름:")
    for i, msg in enumerate(result["messages"]):
        if hasattr(msg, "content"):
            print(f"  [{i}] {msg.__class__.__name__}: {msg.content[:100]}...")
