import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount, CardAction, ActionTypes

from src.ai.llm_client import get_gemini_client
from src.ai.rag_handler import get_rag_handler
from config import get_config

logger = logging.getLogger(__name__)

class MyBot(ActivityHandler):
    """최적화된 봇 활동 핸들러"""
    
    def __init__(self):
        self.config = get_config()
        self.ai_client = get_gemini_client()
        self.rag_handler = get_rag_handler()
        
        # 데이터 로딩
        self.jargon_data = self._load_json_data("jargon.json")
        self.initial_questions = self._load_json_data("initial_questions.json")

    @lru_cache(maxsize=32)
    def _load_json_data(self, filename: str) -> Dict[str, Any]:
        """JSON 데이터 로딩 및 캐싱"""
        try:
            file_path = Path("data") / filename
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}

    def _is_feedback_text(self, text: str) -> bool:
        """텍스트가 피드백 JSON인지 확인"""
        try:
            if text.startswith('{"type": "feedback"'):
                data = json.loads(text)
                return data.get("type") == "feedback"
        except:
            pass
        return False

    async def _send_response_without_feedback(self, turn_context: TurnContext, text_response: str):
        """피드백 없이 응답 전송 (외부 AI 검색용)"""
        logger.info("Sending response without feedback")
        await turn_context.send_activity(MessageFactory.text(text_response))

    async def _send_response_with_feedback(self, turn_context: TurnContext, 
                                         text_response: str, original_query: str = None, 
                                         retrieved_docs_metadata: list = None):
        """피드백과 함께 응답 전송 (내부 문서 검색용)"""
        logger.info(f"Sending response with feedback for query: '{original_query}'")
        await turn_context.send_activity(MessageFactory.text(text_response))

        if not original_query:
            logger.info("No original query provided, skipping feedback buttons")
            return

        # 피드백 버튼 생성
        feedback_payload = {
            "type": "feedback",
            "query": original_query,
            "answer": text_response,
            "docs": retrieved_docs_metadata or []
        }

        feedback_actions = [
            CardAction(
                type=ActionTypes.post_back,
                title="👍 도움이 되었어요",
                value=json.dumps({**feedback_payload, "feedback_type": "good"}, ensure_ascii=False)
            ),
            CardAction(
                type=ActionTypes.post_back,
                title="👎 도움이 되지 않았어요",
                value=json.dumps({**feedback_payload, "feedback_type": "bad"}, ensure_ascii=False)
            ),
            CardAction(
                type=ActionTypes.post_back,
                title="❓ 관련 없는 답변이에요",
                value=json.dumps({**feedback_payload, "feedback_type": "irrelevant"}, ensure_ascii=False)
            )
        ]

        feedback_reply = MessageFactory.suggested_actions(
            feedback_actions, 
            "답변이 어떠셨나요? 피드백을 남겨주세요."
        )
        await turn_context.send_activity(feedback_reply)
        logger.info("Feedback buttons sent successfully")

    async def _handle_feedback(self, turn_context: TurnContext, payload: Dict[str, Any]):
        """피드백 처리 - 개선된 버전"""
        try:
            feedback_type = payload.get("feedback_type")
            original_query = payload.get("query")
            answer = payload.get("answer")
            retrieved_docs_metadata = payload.get("docs", [])

            logger.info(f"Processing feedback: type='{feedback_type}', query='{original_query}'")

            # 피드백 기록
            await self.rag_handler.record_feedback(
                original_query, answer, feedback_type, retrieved_docs_metadata
            )
            
            feedback_messages = {
                "good": "👍 좋은 피드백 감사합니다!",
                "bad": "👎 피드백 감사합니다. 더 나은 답변을 위해 개선하겠습니다.",
                "irrelevant": "❓ 피드백 감사합니다. 더 관련성 높은 답변을 제공하도록 하겠습니다."
            }
            
            message = feedback_messages.get(feedback_type, "피드백 감사합니다!")
            await turn_context.send_activity(MessageFactory.text(message))
            logger.info(f"Feedback acknowledgment sent: '{message}'")
            
            # 부정적 피드백인 경우 추가 옵션 제공
            if feedback_type in ["bad", "irrelevant"]:
                logger.info(f"Providing additional options for negative feedback: {feedback_type}")
                actions = [
                    CardAction(
                        type=ActionTypes.im_back, 
                        value=f"EXTERNAL_SEARCH:{original_query}", 
                        title="외부 AI로 다시 검색"
                    ),
                    CardAction(
                        type=ActionTypes.im_back, 
                        value="담당자_안내", 
                        title="담당자에게 문의"
                    ),
                    CardAction(
                        type=ActionTypes.im_back, 
                        value="메인메뉴", 
                        title="메인 메뉴로"
                    )
                ]
                
                follow_up_reply = MessageFactory.suggested_actions(
                    actions, 
                    "다른 방법으로 도움을 드릴까요?"
                )
                await turn_context.send_activity(follow_up_reply)
                logger.info("Additional options provided for negative feedback")
            
        except Exception as e:
            logger.error(f"Error handling feedback: {e}", exc_info=True)
            await turn_context.send_activity(MessageFactory.text("피드백 처리 중 오류가 발생했습니다."))

    async def _handle_rag_search(self, turn_context: TurnContext, query: str):
        """RAG 검색 처리 (피드백 포함)"""
        try:
            logger.info(f"Starting RAG search for query: '{query}'")
            rag_result = await self.rag_handler.get_rag_answer(query)
            
            if rag_result and rag_result[0]:
                answer, metadata = rag_result
                logger.info(f"RAG search successful, found answer with {len(metadata)} metadata items")
                await self._send_response_with_feedback(
                    turn_context, 
                    f"내부 문서 검색 결과입니다.\n\n{answer}",
                    original_query=query,
                    retrieved_docs_metadata=metadata
                )
                return True
            
            logger.info("RAG search failed, trying jargon dictionary")
            # 용어 사전 검색 시도
            for term, data in self.jargon_data.items():
                if term.upper() in query.upper():
                    definition = data.get("definition", "설명이 없습니다.")
                    link = data.get("link", "")
                    
                    response = f"'{term}'에 대해 질문하셨군요!\n\n{definition}"
                    if link:
                        response += f"\n\n더 자세한 정보: {link}"
                    
                    logger.info(f"Found jargon match for term: '{term}'")
                    await self._send_response_with_feedback(
                        turn_context, response, original_query=query
                    )
                    return True
            
            logger.info("No matches found in RAG or jargon dictionary")
            return False
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}", exc_info=True)
            return False

    async def _handle_external_search(self, turn_context: TurnContext, query: str):
        """외부 AI 검색 처리 (피드백 없음)"""
        try:
            logger.info(f"Starting external AI search for query: '{query}'")
            await turn_context.send_activity(
                MessageFactory.text(f"외부 AI를 통해 '{query}'에 대한 정보를 검색 중입니다...")
            )
            
            ai_answer = await self.ai_client.generate_answer_async(query)
            logger.info("External AI search completed successfully")
            await self._send_response_without_feedback(
                turn_context,
                f"'{query}'에 대한 AI 답변입니다.\n\n{ai_answer}"
            )
            
        except Exception as e:
            logger.error(f"Error in external search: {e}", exc_info=True)
            await turn_context.send_activity(
                MessageFactory.text("외부 검색 중 오류가 발생했습니다.")
            )

    async def _handle_json_flow(self, turn_context: TurnContext, user_message: str):
        """JSON 기반 대화 흐름 처리"""
        json_path = Path("data") / f"{user_message}.json"
        
        if not json_path.exists():
            logger.debug(f"JSON file not found: {json_path}")
            return False
        
        try:
            logger.info(f"Processing JSON flow for: '{user_message}'")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 질문 목록이 있는 경우
            if data.get("questions"):
                logger.info(f"Found {len(data['questions'])} questions in JSON")
                actions = [
                    CardAction(type=ActionTypes.im_back, value=q["value"], title=q["title"])
                    for q in data["questions"]
                ]
                reply = MessageFactory.suggested_actions(
                    actions, 
                    data.get("title", "무엇을 도와드릴까요?")
                )
                await turn_context.send_activity(reply)
                return True
            
            # 답변이 있는 경우 (내부 데이터이므로 피드백 포함)
            if data.get("answer"):
                logger.info("Found direct answer in JSON")
                await self._send_response_with_feedback(
                    turn_context, 
                    data["answer"], 
                    original_query=user_message
                )
                return True
            
            # 답변이 없는 경우 대안 제시
            logger.info("No answer found in JSON, providing alternatives")
            actions = [
                CardAction(type=ActionTypes.im_back, value="담당자_안내", title="담당자 안내"),
                CardAction(type=ActionTypes.im_back, value=f"RAG_SEARCH:{user_message}", title="내부 데이터 검색")
            ]
            reply = MessageFactory.suggested_actions(
                actions, 
                "요청하신 정보가 등록되어 있지 않습니다. 어떻게 도와드릴까요?"
            )
            await turn_context.send_activity(reply)
            return True
            
        except Exception as e:
            logger.error(f"Error handling JSON flow for {user_message}: {e}", exc_info=True)
            return False

    async def on_message_activity(self, turn_context: TurnContext):
        """메시지 활동 처리 - 최적화된 버전"""
        user_message = turn_context.activity.text.strip() if turn_context.activity.text else ""
        activity_value = turn_context.activity.value

        logger.info(f"Received message activity - text: '{user_message}', has_value: {activity_value is not None}")

        # 텍스트가 피드백 JSON인지 먼저 확인
        if user_message and self._is_feedback_text(user_message):
            logger.info("Detected feedback in text field, processing as feedback")
            try:
                payload = json.loads(user_message)
                await self._handle_feedback(turn_context, payload)
                return
            except Exception as e:
                logger.error(f"Error parsing feedback text: {e}")

        # 피드백 처리 (activity_value)
        if activity_value:
            logger.info(f"Processing activity value: {type(activity_value)}")
            try:
                if isinstance(activity_value, str):
                    payload = json.loads(activity_value)
                elif isinstance(activity_value, dict):
                    payload = activity_value
                else:
                    logger.warning(f"Unexpected activity_value type: {type(activity_value)}")
                    payload = None

                if payload and payload.get("type") == "feedback":
                    logger.info("Detected feedback payload, processing feedback")
                    await self._handle_feedback(turn_context, payload)
                    return
                else:
                    logger.info(f"Activity value is not feedback type: {payload.get('type') if payload else 'None'}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse activity value as JSON: {e}")
            except Exception as e:
                logger.error(f"Error processing activity value: {e}", exc_info=True)

        # 메인 메뉴 처리
        if user_message == "메인메뉴":
            logger.info("Processing main menu request")
            if self.initial_questions.get("questions"):
                actions = [
                    CardAction(type=ActionTypes.im_back, value=q["value"], title=q["title"])
                    for q in self.initial_questions["questions"]
                ]
                reply = MessageFactory.suggested_actions(actions, "메인 메뉴입니다. 무엇을 도와드릴까요?")
                await turn_context.send_activity(reply)
            return

        # 특별 명령어 처리
        if user_message.startswith("EXTERNAL_SEARCH:"):
            query = user_message.replace("EXTERNAL_SEARCH:", "").strip()
            logger.info(f"Processing external search command for: '{query}'")
            await self._handle_external_search(turn_context, query)
            return

        if user_message.startswith("RAG_SEARCH:"):
            query = user_message.replace("RAG_SEARCH:", "").strip()
            logger.info(f"Processing RAG search command for: '{query}'")
            if await self._handle_rag_search(turn_context, query):
                return

        # 취소 명령어
        if user_message == "취소":
            logger.info("Processing cancel command")
            await turn_context.send_activity(
                MessageFactory.text("알겠습니다. 다른 질문이 있으시면 언제든지 말씀해 주세요.")
            )
            return

        # JSON 기반 흐름 처리
        if await self._handle_json_flow(turn_context, user_message):
            return

        # 자유 텍스트 처리 (RAG 검색)
        logger.info(f"Processing free text query: '{user_message}'")
        if await self._handle_rag_search(turn_context, user_message):
            return

        # 외부 검색 제안
        logger.info("No matches found, suggesting external search")
        actions = [
            CardAction(type=ActionTypes.im_back, value=f"EXTERNAL_SEARCH:{user_message}", title="예"),
            CardAction(type=ActionTypes.im_back, value="취소", title="아니요"),
        ]
        reply = MessageFactory.suggested_actions(
            actions, 
            f"내부 정보에서 '{user_message}'에 대한 답변을 찾지 못했습니다. 외부 AI를 통해 검색할까요?"
        )
        await turn_context.send_activity(reply)

    async def on_members_added_activity(self, members_added: list[ChannelAccount], 
                                      turn_context: TurnContext):
        """새 멤버 추가 시 환영 메시지"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                logger.info(f"New member added: {member.name}")
                welcome_text = f"안녕하세요 {member.name}님! 교보DTS 온보딩 멘토 봇입니다."
                
                if self.initial_questions.get("questions"):
                    actions = [
                        CardAction(type=ActionTypes.im_back, value=q["value"], title=q["title"])
                        for q in self.initial_questions["questions"]
                    ]
                    reply = MessageFactory.suggested_actions(actions, welcome_text)
                else:
                    reply = MessageFactory.text(welcome_text)
                
                await turn_context.send_activity(reply)

    async def cleanup(self):
        """리소스 정리"""
        logger.info("Bot cleanup completed")
