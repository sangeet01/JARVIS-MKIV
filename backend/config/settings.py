from pydantic import BaseModel

class ModelConfig(BaseModel):
    groq_model:        str = "llama-3.3-70b-versatile"
    local_model:       str = "llava:7b"          # pinned — must match `ollama pull llava:7b`
    local_model_timeout: int = 30                 # seconds for Ollama request timeout
    groq_max_tokens:   int = 512
    local_max_tokens:  int = 1024
    ollama_host:       str = "http://localhost:11434"

class ServerConfig(BaseModel):
    host:  str = "0.0.0.0"
    port:  int = 8000
    debug: bool = False

class MemoryConfig(BaseModel):
    short_term_limit: int = 20
    long_term_db:     str = "memory/hindsight.db"

class WakeWordConfig(BaseModel):
    sensitivity:  float = 0.5   # detection threshold (0.0–1.0); lower = more sensitive
    cooldown_ms:  int   = 1500  # ms to ignore re-triggers after a detection

# Tool names that the sandbox is allowed to execute.
# Any tool name not in this list will be blocked with a warning.
ALLOWED_TOOLS: list[str] = [
    "shell",
    "read_file",
    "write_file",
    "web_fetch",
    "file_read",
    "file_write",
    "web_scrape",
    "calculate",
    "screenshot",
    "screenshot_gui",
    "run_terminal",
    "open_app",
    "search_web",
    "get_weather",
    "get_calendar",
    "get_github_status",
    "type_text",
    "press_shortcut",
    "youtube_control",
]

LAT  = 30.0444
LON  = 31.2357
CITY = "Cairo"

MODEL_CFG   = ModelConfig()
SERVER_CFG  = ServerConfig()
MEMORY_CFG  = MemoryConfig()
WAKE_CFG    = WakeWordConfig()
