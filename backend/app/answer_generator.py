import asyncio
import time
from typing import Optional

from app.config import get_settings
from app.session_manager import Session
from app.security import log_audit
from app.knowledge_base import knowledge_base

settings = get_settings()

# Mock mode untuk testing tanpa API key
MOCK_LLM = False

class LLMHandler:
    """Generate responses using OpenAI GPT-4o-mini atau mock untuk testing."""
    
    SYSTEM_PROMPT = """You are a professional meeting assistant. Your role is to help the user navigate meetings effectively.

Rules:
- Keep answers short: 3-6 sentences max
- Use calm, executive, practical tone
- When suggesting responses, use tradeoff framing:
  1. Acknowledge concern
  2. Explain risk or implication
  3. Suggest practical next step
- Do not fabricate project-specific facts
- If context is weak, say confidence is Low
- If no clear question found, respond with best suggested talking point

Language: Respond in the same language as the user's command or the meeting transcript."""

    @staticmethod
    async def generate_recap(session: Session) -> str:
        """Generate meeting recap from transcript."""
        transcript = session.get_recent_transcript(minutes=60)
        
        if not transcript.strip():
            return "No transcript available yet. The meeting may have just started or no speech was detected."
        
        if MOCK_LLM:
            return LLMHandler._mock_recap(session)
        
        # Add project context if available
        project_context = ""
        if session.active_project_id:
            project_context = f"\nActive project: {session.active_project_id}\nUse project knowledge if relevant."
        
        prompt = f"""Based on this meeting transcript, provide a concise recap:

Transcript:
{transcript}
{project_context}

Provide:
1. Short meeting summary (1-2 sentences)
2. Key points discussed (3-5 bullet points)
3. Open questions or unresolved items
4. Recommended next step

Keep it executive-friendly and actionable."""

        return await LLMHandler._call_llm(prompt, session.session_id)
    
    @staticmethod
    async def generate_say(session: Session) -> str:
        """Generate suggested answer to latest question."""
        question = session.get_latest_question()
        transcript = session.get_recent_transcript(minutes=10)
        
        if MOCK_LLM:
            return LLMHandler._mock_say(session, question, transcript)
        
        # Add project context from knowledge base
        project_context = ""
        if session.active_project_id:
            # Search knowledge base for relevant context
            kb_results = knowledge_base.search(
                project_id=session.active_project_id,
                query=question or transcript[:100],
                limit=3,
            )
            
            if kb_results:
                kb_text = "\n".join([r["text"] for r in kb_results])
                project_context = f"""\nRelevant project knowledge:\n{kb_text}\n"""
            else:
                project_context = f"\nActive project: {session.active_project_id}\nNo specific knowledge found for this query."
        
        if not question:
            prompt = f"""Based on the latest discussion in this meeting, suggest a useful talking point or response:

Recent transcript:
{transcript}
{project_context}

Provide:
- Latest discussion point
- Suggested response or angle
- Confidence: Low (no clear question detected)"""
        else:
            prompt = f"""Answer this question from the meeting:

Question: {question}

Meeting context:
{transcript}
{project_context}

Provide:
- Latest question detected
- Suggested concise answer (3-5 sentences)
- Confidence: High/Medium/Low based on context clarity

Use tradeoff framing when appropriate."""
        
        return await LLMHandler._call_llm(prompt, session.session_id)
    
    @staticmethod
    async def generate_followup(session: Session) -> str:
        """Generate follow-up questions."""
        transcript = session.get_recent_transcript(minutes=15)
        
        if not transcript.strip():
            return "No recent discussion found. Start the meeting first."
        
        if MOCK_LLM:
            return LLMHandler._mock_followup(transcript)
        
        # Add project context if available
        project_context = ""
        if session.active_project_id:
            project_context = f"\nActive project: {session.active_project_id}\nUse project knowledge if relevant."
        
        prompt = f"""Based on this meeting discussion, suggest 3-5 smart follow-up questions:

Transcript:
{transcript}
{project_context}

Requirements:
- Practical and concise
- Executive-friendly language
- Help uncover risks, dependencies, or decisions needed
- Focus on next steps and accountability"""

        return await LLMHandler._call_llm(prompt, session.session_id)
    
    @staticmethod
    async def generate_assist(session: Session) -> str:
        """Generate general real-time assistance."""
        transcript = session.get_recent_transcript(minutes=10)
        
        if not transcript.strip():
            return "No recent context available. The meeting may have just started."
        
        if MOCK_LLM:
            return LLMHandler._mock_assist(session, transcript)
        
        # Add project context from knowledge base
        project_context = ""
        if session.active_project_id:
            # Search knowledge base for relevant context
            kb_results = knowledge_base.search(
                project_id=session.active_project_id,
                query=transcript[:200],
                limit=3,
            )
            
            if kb_results:
                kb_text = "\n".join([r["text"] for r in kb_results])
                project_context = f"""\nRelevant project knowledge:\n{kb_text}\n"""
            else:
                project_context = f"\nActive project: {session.active_project_id}\nNo specific knowledge found for this query."
        
        prompt = f"""Provide real-time meeting assistance based on this context:

Recent transcript:
{transcript}
{project_context}

Provide:
1. Current situation (what's happening now)
2. Recommended angle (how to approach it)
3. Suggested response (what to say)

Keep it practical and actionable."""
        
        return await LLMHandler._call_llm(prompt, session.session_id)
    
    # --- Mock Methods ---
    
    @staticmethod
    def _mock_recap(session: Session) -> str:
        """Mock recap response."""
        transcript = session.get_recent_transcript(minutes=60)
        lines = transcript.strip().split('\n')
        
        return f"""📊 Meeting Recap (MOCK MODE)

**Summary:**
Meeting discussed project topics with {len(lines)} key points.

**Key Points:**
""" + "\n".join([f"• {line[:80]}" for line in lines[:5]]) + """

**Open Questions:**
• Next steps to be defined
• Timeline confirmation needed

**Recommended Next Step:**
Schedule follow-up to finalize action items.

_(Note: Running in mock mode - connect OpenAI API key for real responses)_"""
    
    @staticmethod
    def _mock_say(session: Session, question: Optional[str], transcript: str) -> str:
        """Mock say response with project context."""
        kb_context = ""
        if session.active_project_id:
            kb_results = knowledge_base.search(
                project_id=session.active_project_id,
                query=question or transcript[:100],
                limit=2,
            )
            if kb_results:
                kb_context = "\n**Project Context:**\n" + "\n".join([f"• {r['text'][:100]}..." for r in kb_results])
        
        if question:
            return f"""🗣️ Suggested Response (MOCK MODE)

**Latest Question:**
{question}

**Suggested Answer:**
Based on the discussion, I'd recommend acknowledging the concern and suggesting a practical approach. Consider the tradeoffs between speed and thoroughness, then propose a concrete next step with clear ownership.
{kb_context}

**Confidence:** Medium

_(Note: Running in mock mode - connect OpenAI API key for real responses)_"""
        else:
            return f"""💡 Talking Point (MOCK MODE)

**Latest Discussion:**
{transcript[:200]}...

**Suggested Angle:**
Frame the conversation around actionable outcomes. Identify the decision maker, clarify constraints, and propose 2-3 options with clear pros/cons.
{kb_context}

**Confidence:** Low (no clear question detected)

_(Note: Running in mock mode - connect OpenAI API key for real responses)_"""
    
    @staticmethod
    def _mock_followup(transcript: str) -> str:
        """Mock followup questions."""
        return """❓ Follow-up Questions (MOCK MODE)

1. What are the specific deliverables and deadlines for each team member?
2. Have we identified the key risks and mitigation strategies?
3. Who has final decision authority on budget and timeline changes?
4. What dependencies could block progress in the next 2 weeks?
5. When should we schedule the next check-in to review progress?

_(Note: Running in mock mode - connect OpenAI API key for real responses)_"""
    
    @staticmethod
    def _mock_assist(session: Session, transcript: str) -> str:
        """Mock assist response with project context."""
        kb_context = ""
        if session.active_project_id:
            kb_results = knowledge_base.search(
                project_id=session.active_project_id,
                query=transcript[:200],
                limit=2,
            )
            if kb_results:
                kb_context = "\n**Relevant Project Info:**\n" + "\n".join([f"• {r['text'][:120]}..." for r in kb_results])
        
        return f"""💡 Real-Time Assistance (MOCK MODE)

**Current Situation:**
The meeting is discussing project topics. Recent focus: {transcript[:150]}...

**Recommended Angle:**
Listen for decision points and constraints. When you hear a question or concern, acknowledge it and reframe around actionable next steps.

**Suggested Response:**
"That's a valid point. Let's identify the specific constraint, then explore 2-3 practical options with clear tradeoffs. Who can own the next step?"
{kb_context}

_(Note: Running in mock mode - connect OpenAI API key for real responses)_"""
    
    @staticmethod
    async def _call_llm(prompt: str, session_id: str) -> str:
        """Call LLM API (OpenAI atau Kimi) dengan retry logic."""
        max_retries = 2
        
        # Coba OpenAI dulu (sekarang ada credit)
        if settings.openai_api_key and len(settings.openai_api_key) > 50:
            return await LLMHandler._call_openai(prompt, session_id, max_retries)
        
        # Fallback ke Kimi
        if settings.kimi_api_key and len(settings.kimi_api_key) > 20:
            return await LLMHandler._call_kimi(prompt, session_id, max_retries)
        
        return "Error: No valid LLM API key configured"
    
    @staticmethod
    async def _call_kimi(prompt: str, session_id: str, max_retries: int) -> str:
        """Call Kimi API."""
        import openai
        
        # Kimi pakai OpenAI-compatible API
        client = openai.AsyncOpenAI(
            api_key=settings.kimi_api_key,
            base_url="https://api.moonshot.cn/v1",
        )
        
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                response = await client.chat.completions.create(
                    model=settings.kimi_model,
                    messages=[
                        {"role": "system", "content": LLMHandler.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )
                
                latency = time.time() - start_time
                log_audit("llm_response_generated", session_id, {"latency": latency, "provider": "kimi"})
                
                result = response.choices[0].message.content
                return result.encode('utf-8').decode('utf-8')
                
            except Exception as e:
                if attempt == max_retries:
                    log_audit("llm_error", session_id, {"error": str(e), "provider": "kimi"})
                    return f"Error generating response: {str(e)}"
                await asyncio.sleep(1)
    
    @staticmethod
    async def _call_openai(prompt: str, session_id: str, max_retries: int) -> str:
        """Call OpenAI API."""
        import openai
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                response = await client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": LLMHandler.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )
                
                latency = time.time() - start_time
                log_audit("llm_response_generated", session_id, {"latency": latency, "provider": "openai"})
                
                result = response.choices[0].message.content
                return result.encode('utf-8').decode('utf-8')
                
            except Exception as e:
                if attempt == max_retries:
                    log_audit("llm_error", session_id, {"error": str(e), "provider": "openai"})
                    return f"Error generating response: {str(e)}"
                await asyncio.sleep(1)


# Global instance
llm_handler = LLMHandler()
