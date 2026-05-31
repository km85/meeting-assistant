import asyncio
import time
from typing import Optional

import openai
from config import get_settings
from session_manager import Session

settings = get_settings()
client = openai.AsyncOpenAI(api_key=settings.openai_api_key)


class LLMHandler:
    """Generate responses using OpenAI GPT-4o-mini."""
    
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
        
        prompt = f"""Based on this meeting transcript, provide a concise recap:

Transcript:
{transcript}

Provide:
1. Short meeting summary (1-2 sentences)
2. Key points discussed (3-5 bullet points)
3. Open questions or unresolved items
4. Recommended next step

Keep it executive-friendly and actionable."""

        return await LLMHandler._call_llm(prompt)
    
    @staticmethod
    async def generate_say(session: Session) -> str:
        """Generate suggested answer to latest question."""
        question = session.get_latest_question()
        transcript = session.get_recent_transcript(minutes=10)
        
        if not question:
            # No clear question - provide talking point based on latest discussion
            prompt = f"""Based on the latest discussion in this meeting, suggest a useful talking point or response:

Recent transcript:
{transcript}

Provide:
- Latest discussion point
- Suggested response or angle
- Confidence: Low (no clear question detected)"""
        else:
            prompt = f"""Answer this question from the meeting:

Question: {question}

Meeting context:
{transcript}

Provide:
- Latest question detected
- Suggested concise answer (3-5 sentences)
- Confidence: High/Medium/Low based on context clarity

Use tradeoff framing when appropriate."""
        
        return await LLMHandler._call_llm(prompt)
    
    @staticmethod
    async def generate_followup(session: Session) -> str:
        """Generate follow-up questions."""
        transcript = session.get_recent_transcript(minutes=15)
        
        if not transcript.strip():
            return "No recent discussion found. Start the meeting first."
        
        prompt = f"""Based on this meeting discussion, suggest 3-5 smart follow-up questions:

Transcript:
{transcript}

Requirements:
- Practical and concise
- Executive-friendly language
- Help uncover risks, dependencies, or decisions needed
- Focus on next steps and accountability"""

        return await LLMHandler._call_llm(prompt)
    
    @staticmethod
    async def generate_assist(session: Session) -> str:
        """Generate general real-time assistance."""
        transcript = session.get_recent_transcript(minutes=10)
        
        if not transcript.strip():
            return "No recent context available. The meeting may have just started."
        
        prompt = f"""Provide real-time meeting assistance based on this context:

Recent transcript:
{transcript}

Provide:
1. Current situation (what's happening now)
2. Recommended angle (how to approach it)
3. Suggested response (what to say)

Keep it practical and actionable."""

        return await LLMHandler._call_llm(prompt)
    
    @staticmethod
    async def _call_llm(prompt: str) -> str:
        """Call OpenAI API with retry logic."""
        max_retries = 2
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
                print(f"LLM response generated in {latency:.2f}s")
                
                return response.choices[0].message.content
                
            except Exception as e:
                if attempt == max_retries:
                    return f"Error generating response: {str(e)}"
                await asyncio.sleep(1)


# Global instance
llm_handler = LLMHandler()
