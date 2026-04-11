"""
Test LangGraph with real database
"""
from app.graph.builder import graph as lang_graph
from app.db.session import SessionLocal
from app.db.models import TaskRecord
from datetime import datetime

# Create a test task record
db = SessionLocal()
try:
    test_task_id = "TEST-LANGGRAPH-001"
    test_chat_id = "test_chat_001"
    test_message_id = "test_msg_001"
    test_open_id = "test_user_001"
    test_text = "查询 SKU A001 状态"
    
    # Create task record
    task_record = TaskRecord(
        task_id=test_task_id,
        source_message_id=test_message_id,
        chat_id=test_chat_id,
        user_open_id=test_open_id,
        intent_text=test_text,
        status="processing",
        created_at=datetime.now()
    )
    db.add(task_record)
    db.commit()
    
    print(f"Created test task: {test_task_id}")
    
    # Execute LangGraph
    initial_state = {
        "task_id": test_task_id,
        "source_message_id": test_message_id,
        "source_chat_id": test_chat_id,
        "user_open_id": test_open_id,
        "raw_text": test_text,
    }
    
    print("=== LANGGRAPH EXECUTION START ===")
    result = lang_graph.invoke(initial_state)
    print("=== LANGGRAPH EXECUTION END ===")
    
    print(f"\nResult:")
    print(f"  status: {result.get('status')}")
    print(f"  intent_code: {result.get('intent_code')}")
    print(f"  result_summary: {result.get('result_summary')}")
    print(f"  slots: {result.get('slots')}")
    
    # Check task record
    db.refresh(task_record)
    print(f"\nTask record after execution:")
    print(f"  status: {task_record.status}")
    print(f"  intent_code: {task_record.intent_code}")
    print(f"  result_summary: {task_record.result_summary}")
    
finally:
    db.close()
