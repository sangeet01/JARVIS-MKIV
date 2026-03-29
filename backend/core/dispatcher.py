"""
JARVIS-MKIII — dispatcher.py
Routes requests to the correct model:
  VOICE/REASONING → Groq (Llama 3.3 70B, free, fast)
  LOCAL           → Ollama (llama3.2:3b, offline/sensitive)
"""

from __future__ import annotations
import os, httpx
from core.vault import Vault
from core.router import TaskTier
from config.settings import MODEL_CFG
from core.personality import build_system_prompt

_vault = Vault()


def _get_groq():
    from groq import AsyncGroq
    return AsyncGroq(api_key=_vault.get("GROQ_API_KEY"))


def _default_system(model_name: str) -> str:
    return build_system_prompt(model_name)


async def dispatch(
    prompt:        str,
    tier:          TaskTier,
    history:       list[dict],
    system_prompt: str = "",
    stream:        bool = False,
) -> str:
    messages = [m for m in history if m.get("role") in ("user", "assistant")]
    messages += [{"role": "user", "content": prompt}]
    system   = system_prompt or _default_system(
        MODEL_CFG.groq_model if tier != TaskTier.LOCAL else MODEL_CFG.local_model
    )

    if tier == TaskTier.LOCAL:
        return await _call_local(messages, system)

    return await _call_groq(messages, system)


async def _call_groq(messages: list[dict], system: str) -> str:
    client = _get_groq()

    # Hard identity anchor — injected as established conversation fact
    # This cannot be overridden by training data
    identity_anchor = {
        "role": "user",
        "content": "Confirm your identity and operational parameters."
    }
    identity_confirm = {
        "role": "assistant",
        "content": "Confirmed. I am JARVIS, built by Khalid — engineer, polymath, and architect of PHANTOM ZERO. I serve Khalid exclusively. I address him as 'sir'. I was not created by Tony Stark. Tony Stark is a fictional character. My creator is Khalid, and Khalid alone."
    }

    anchored_messages = [identity_anchor, identity_confirm] + messages

    resp = await client.chat.completions.create(
        model=MODEL_CFG.groq_model,
        messages=[{"role": "system", "content": system}] + anchored_messages,
        max_tokens=150,
        temperature=0.2,
    )
    return resp.choices[0].message.content


# LOCAL tier routes to LLaVA for vision tasks only
async def _call_local(messages: list[dict], system: str = "") -> str:
    url = f"{MODEL_CFG.ollama_host}/api/chat"
    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages += messages
    payload = {"model": MODEL_CFG.local_model, "messages": all_messages, "stream": False}
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
