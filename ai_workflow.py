
"""
LangGraph + vLLM 로컬 H100 에이전트
http://192.168.0.84:8000 의 vLLM 서버를 사용합니다.
"""

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from typing import Annotated, TypedDict, Sequence
import operator
import json

# ============================================================================
# API 설정
# ============================================================================
base = "http://192.168.0.84:8000"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImM1NTlkOWM1LTk2OWQtNDk1MC05YTVhLWY3MGJlMTY1YTk1ZiIsImV4cCI6MTc3MTU3NTMzMywianRpIjoiMjgyYThkYWYtNzc4NS00MjliLWI1Y2ItMWIxYzFlNmMyZTA0MyJ9.VFDZueb-nRuU3ISLw4eDM6wKdOgGmaS1TjgExnErIY4"

headers = {
    "Authorization": token,
    "Content-Type": "application/json"
}

# ============================================================================
# 1. vLLM 로컬 LLM 설정
# ============================================================================
llm = ChatOpenAI(
    api_key=token,  # 토큰 기반 인증
    model="openai/gpt-oss-120b",  # H100에 올려진 모델
    base_url=f"{base}/v1",  # /v1 엔드포인트 추가
    temperature=0.7,
    top_p=0.9,
    max_tokens=1024,
)

# ============================================================================
# 2. State 정의
# ============================================================================
class AgentState(TypedDict):
    """에이전트의 상태"""
    messages: Annotated[Sequence, operator.add]
    step_count: int


# ============================================================================
# 3. Tools 정의
# ============================================================================
@tool
def calculator(expression: str) -> str:
    """
    수학 계산을 수행합니다.
    
    Args:
        expression: 계산할 수식 (예: "100 + 250 * 2")
    
    Returns:
        계산 결과
    """
    try:
        result = eval(expression)
        return f"계산 결과: {expression} = {result}"
    except Exception as e:
        return f"계산 오류: {str(e)}"


@tool
def weather_check(city: str) -> str:
    """
    특정 도시의 날씨 정보를 조회합니다.
    
    Args:
        city: 도시 이름 (예: "서울")
    
    Returns:
        날씨 정보
    """
    # 실제로는 API를 호출하지만, 여기서는 시뮬레이션
    weather_data = {
        "서울": "맑음, 기온 5°C, 습도 45%",
        "부산": "흐림, 기온 8°C, 습도 60%",
        "대구": "맑음, 기온 6°C, 습도 50%",
    }
    result = weather_data.get(city, f"{city}의 날씨 정보를 찾을 수 없습니다.")
    return result


@tool
def text_processor(text: str, operation: str) -> str:
    """
    텍스트를 처리합니다.
    
    Args:
        text: 처리할 텍스트
        operation: 처리 방식 ("uppercase", "lowercase", "reverse", "wordcount")
    
    Returns:
        처리된 텍스트
    """
    if operation == "uppercase":
        return text.upper()
    elif operation == "lowercase":
        return text.lower()
    elif operation == "reverse":
        return text[::-1]
    elif operation == "wordcount":
        return f"단어 개수: {len(text.split())}"
    else:
        return f"지원하지 않는 작업: {operation}"


@tool
def information_lookup(topic: str) -> str:
    """
    주제에 대한 정보를 조회합니다.
    
    Args:
        topic: 조회할 주제
    
    Returns:
        관련 정보
    """
    information_db = {
        "파이썬": "Python은 1991년 Guido van Rossum이 개발한 인터프리터 언어입니다.",
        "AI": "AI(Artificial Intelligence)는 인공지능으로, 기계가 인간처럼 학습하고 판단할 수 있도록 하는 기술입니다.",
        "LangGraph": "LangGraph는 LangChain에서 제공하는 상태 그래프 기반 에이전트 프레임워크입니다.",
    }
    return information_db.get(
        topic,
        f"{topic}에 대한 정보를 찾을 수 없습니다. 다른 주제를 시도해보세요."
    )


# ============================================================================
# 4. 에이전트 노드 - LLM이 tool 호출 여부를 결정
# ============================================================================
def agent_node(state: AgentState):
    """
    LLM을 실행하고 tool 호출 여부를 결정합니다.
    """
    tools = [calculator, weather_check, text_processor, information_lookup]
    
    # Tools를 LLM에 바인딩
    llm_with_tools = llm.bind_tools(tools)
    
    # LLM 실행
    response = llm_with_tools.invoke(state["messages"])
    
    # 상태 업데이트
    return {
        "messages": [response],
        "step_count": state["step_count"] + 1
    }


# ============================================================================
# 5. Tool 실행 노드
# ============================================================================
def tool_node(state: AgentState):
    """
    LLM이 요청한 tool을 실행합니다.
    """
    last_message = state["messages"][-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {"messages": []}
    
    tool_results = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["input"]
        
        print(f"\n🔧 Tool 실행: {tool_name}")
        print(f"   입력: {tool_input}")
        
        # Tool 실행
        if tool_name == "calculator":
            result = calculator.invoke(tool_input)
        elif tool_name == "weather_check":
            result = weather_check.invoke(tool_input)
        elif tool_name == "text_processor":
            result = text_processor.invoke(tool_input)
        elif tool_name == "information_lookup":
            result = information_lookup.invoke(tool_input)
        else:
            result = f"Unknown tool: {tool_name}"
        
        print(f"   결과: {result}")
        
        # Tool 결과를 메시지에 추가
        tool_results.append(
            ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
                name=tool_name
            )
        )
    
    return {"messages": tool_results}


# ============================================================================
# 6. 조건부 라우팅 - tool 호출 여부 판단
# ============================================================================
def should_continue(state: AgentState) -> str:
    """
    마지막 메시지에 tool_calls가 있으면 tool 실행, 없으면 종료
    """
    last_message = state["messages"][-1]
    
    # Tool calls가 있으면 tools 노드로, 없으면 END로
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


# ============================================================================
# 7. 그래프 구성 및 컴파일
# ============================================================================
def create_agent_graph():
    """
    LangGraph 에이전트 그래프를 생성합니다.
    """
    graph_builder = StateGraph(AgentState)
    
    # 노드 추가
    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", tool_node)
    
    # 엣지 추가
    graph_builder.add_edge(START, "agent")  # 시작 -> agent
    
    # 조건부 엣지: agent -> (tools or end)
    graph_builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    
    graph_builder.add_edge("tools", "agent")  # tools 실행 후 다시 agent로
    
    # 그래프 컴파일
    return graph_builder.compile()


# ============================================================================
# 8. 메인 실행 함수
# ============================================================================
def run_agent(user_query: str):
    """
    에이전트를 실행합니다.
    
    Args:
        user_query: 사용자 쿼리
    """
    print("=" * 70)
    print("🤖 LangGraph + vLLM 에이전트 시작")
    print("=" * 70)
    print(f"🔍 사용자 쿼리: {user_query}\n")
    
    # 그래프 생성
    agent_graph = create_agent_graph()
    
    # 초기 상태
    initial_state = {
        "messages": [HumanMessage(content=user_query)],
        "step_count": 0
    }
    
    print("-" * 70)
    print("📊 에이전트 실행 중...\n")
    
    # 에이전트 실행
    try:
        final_state = agent_graph.invoke(initial_state)
        
        print("\n" + "-" * 70)
        print("✅ 에이전트 완료\n")
        
        # 최종 응답 출력
        last_message = final_state["messages"][-1]
        
        print("=" * 70)
        print("🎯 최종 답변:")
        print("=" * 70)
        if hasattr(last_message, "content"):
            print(last_message.content)
        else:
            print(str(last_message))
        
        print("\n" + "=" * 70)
        print(f"총 단계: {final_state['step_count']}")
        print("=" * 70)
        
        return final_state
        
    except Exception as e:
        print(f"\n❌ 에러 발생: {str(e)}")
        print(f"   vLLM 서버 주소: {base}")
        print(f"   API 엔드포인트: {base}/v1/chat/completions")
        print(f"\n   디버깅 팁:")
        print(f"   1. 서버 상태 확인: curl -H 'Authorization: {token[:20]}...' {base}/v1/models")
        print(f"   2. 토큰 유효성 확인")
        print(f"   3. 모델명 확인: {llm.model}")
        return None


# ============================================================================
# 9. 테스트 케이스
# ============================================================================
if __name__ == "__main__":
    # 테스트 쿼리들
    test_queries = [
        
        "서울의 날씨는 어때?",
        "LangGraph에 대해 알려줘",
        '"안녕하세요! 반갑습니다"를 대문자로 변환해줄 수 있어?',
    ]
    
    # 첫 번째 쿼리 실행
    run_agent(test_queries[0])