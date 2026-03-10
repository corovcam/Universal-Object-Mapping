import logging
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="UOM Orchestrator API",
    description="LLM-based iterative translation (LangGraph) for Universal Object Mapping",
    version="0.1.0"
)

# --- LangGraph State Definition ---
class TranslationState(TypedDict):
    source_code: str
    source_language: str
    target_language: str
    translated_code: str
    error_feedback: str
    current_step: str
    iterations: int

# --- Helper Nodes (Mock implementations for now) ---
async def extract_schema_context(state: TranslationState) -> TranslationState:
    logger.info("Extracting schema context...")
    state["current_step"] = "translate"
    return state

async def generate_translation(state: TranslationState) -> TranslationState:
    logger.info(f"Generating translation from {state['source_language']} to {state['target_language']}...")
    # Mock LLM generation
    state["translated_code"] = f"// Translated to {state['target_language']}\n{state['source_code']}"
    state["current_step"] = "verify"
    state["iterations"] += 1
    return state

async def verify_compilation(state: TranslationState) -> TranslationState:
    logger.info("Verifying compilation with backend services...")
    # Mock compilation check
    # In reality, this would call .NET or Java services via HTTP
    state["error_feedback"] = ""
    state["current_step"] = "compile_success"
    return state

def route_translation(state: TranslationState) -> Literal["compile_success", "translate"]:
    """Router based on error feedback."""
    if state["error_feedback"] and state["iterations"] < 3:
        return "translate"
    return "compile_success"

# --- Building the Graph ---
builder = StateGraph(TranslationState)
builder.add_node("extract_context", extract_schema_context)
builder.add_node("translate", generate_translation)
builder.add_node("verify", verify_compilation)

builder.add_edge(START, "extract_context")
builder.add_edge("extract_context", "translate")
builder.add_edge("translate", "verify")
builder.add_conditional_edges("verify", route_translation, {
    "translate": "translate",
    "compile_success": END
})

# Compile the graph
translation_workflow = builder.compile()

# --- API Endpoints ---
class TranslationRequest(BaseModel):
    source_code: str
    source_language: str
    target_language: str
    schema_context: str | None = None

class TranslationResponse(BaseModel):
    translated_code: str
    status: str
    iterations: int

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/translate", response_model=TranslationResponse)
async def translate_query(request: TranslationRequest):
    try:
        initial_state: TranslationState = {
            "source_code": request.source_code,
            "source_language": request.source_language,
            "target_language": request.target_language,
            "translated_code": "",
            "error_feedback": "",
            "current_step": "start",
            "iterations": 0
        }
        
        # Execute workflow
        result = await translation_workflow.ainvoke(initial_state)
        
        return TranslationResponse(
            translated_code=result["translated_code"],
            status="success" if not result["error_feedback"] else "error",
            iterations=result["iterations"]
        )
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
