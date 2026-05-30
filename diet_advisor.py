
import base64
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# ── 초기화 ──────────────────────────────────────────────
load_dotenv()
client = OpenAI()

# 모델은 변수로 빼두면 gpt-5.4-mini 로 쉽게 교체 가능
MODEL_NAME = "gpt-5.4-mini"

IMAGE_PROMPT_TEMPLATE = """
당신은 업로드된 음식 사진을 보고 다이어트 관점에서 코멘트하는 AI입니다.
아래 순서대로 처리하세요.

[1단계 · 칼로리 분석]
- 음식의 종류와 양을 파악하고 예상 칼로리(kcal)를 숫자로 추정합니다.
- 음식을 다음 두 가지 중 하나로 분류합니다.
  (A) 고칼로리/건강하지 않은 음식: 튀김, 패스트푸드, 디저트, 고지방·고당류, 야식 등
  (B) 저칼로리/건강한 음식: 샐러드, 채소, 닭가슴살, 단백질 위주의 가벼운 식단 등

[2단계 · 응답 톤]
선택된 톤: {response_tone}
강도(1~5): {intensity}  (숫자가 클수록 더 강하게. 얌전하게 쓰지 말 것)

■ 톤이 '심각한 비난'일 때 — 인터넷 커뮤니티 악플러 컨셉
- 존댓말 절대 금지. 반말로만 쓴다.
- 'ㅋㅋㅋ' 같은 비웃음과 인터넷 밈 말투를 적극적으로 쓴다.
- 강도가 높을수록 더 신랄하게. 강도 4~5면 진짜 악플러처럼 사정없이 비꼰다.
- 단, 비난 대상은 '음식 선택/식습관'에만 한정한다. 외모·체형·인격 모독, 욕설, 혐오 표현은 쓰지 않는다.
- (A) 고칼로리면: "ㅋㅋㅋㅋ 이걸 올리는 의도가 뭐냐?" 처럼 왜 이런 걸 먹냐며 맹비난·조롱한다.
- (B) 저칼로리면: "오? 요즘 심경의 변화라도 있냐? 안 하던 짓을 하네 ㅋㅋ" 처럼 갑자기 건강식 먹는 걸 비꼰다.

■ 톤이 '따뜻한 위로'일 때 — 다정한 응원 컨셉
- 부드러운 존댓말. 공감과 응원 위주로 쓴다.
- 강도가 높을수록 더 진하고 다정하게.
- (A) 고칼로리면: "그래도 다음엔 잘 참을 수 있어요", "건강을 조금만 더 생각해주세요" 처럼 위로하며 부드럽게 권유한다.
- (B) 저칼로리면: "정말 좋은 식단이에요!" 처럼 진심으로 칭찬하고 응원한다.

[출력 형식]
1) 예상 칼로리: 약 OOO kcal (한 줄)
2) 위 톤과 강도에 맞춘 코멘트 2~3문장

사용자 입력: {user_input}
"""

# ── 페이지 설정 (반드시 첫 Streamlit 호출이어야 함) ──────────
st.set_page_config(page_title="AI 다이어트 코치", page_icon="🥗")
st.title("🥗 AI 다이어트 조언가")
st.caption("음식 사진을 올리면 칼로리를 추정하고, 선택한 톤으로 한마디 해드립니다.")

# ── 1) 음식 이미지 업로드 ────────────────────────────────
uploaded = st.file_uploader("음식 사진 업로드", type=["jpg", "jpeg", "png"])

# 업로드 이미지 미리보기 (업로드 ↔ 프롬프트 영역 사이)
if uploaded is not None:
    st.image(uploaded, caption="업로드한 음식", use_container_width=True)

# ── 2) 프롬프트 영역 (사용자 추가 요청 + 분석 버튼) ────────────
user_input = st.text_area(
    "추가로 하고 싶은 말이나 질문 (선택)",
    placeholder="예) 오늘 저녁인데 이 정도면 괜찮을까요?",
)
run = st.button("분석하기", type="primary", disabled=(uploaded is None))

# ── 3) 대화 톤 토글 ─────────────────────────────────────
# st.toggle 은 True/False 를 반환하므로, 두 톤에 매핑한다.
serious = st.toggle("심각 모드", value=False, help="켜면 '심각한 비난', 끄면 '따뜻한 위로'")
response_tone = "심각한 비난" if serious else "따뜻한 위로"
st.write(f"현재 응답 톤: **{response_tone}** {'😡' if serious else '🤗'}")

# 톤의 강도(수준)를 슬라이더로 조절 → 프롬프트에 주입
intensity = st.slider(
    "강도",
    min_value=1,
    max_value=5,
    value=3,
    help="높일수록 더 세게(비난) / 더 진하게(위로). 1=가벼운 장난, 5=사정없이",
)

# ── 4) 분석 실행 ────────────────────────────────────────
if run:
    with st.spinner("칼로리 분석 중..."):
        # 이미지를 base64 로 인코딩
        image_b64 = base64.b64encode(uploaded.getvalue()).decode("utf-8")
        mime = uploaded.type or "image/jpeg"  # png/jpeg 자동 대응

        # 프롬프트 템플릿 채우기
        prompt = IMAGE_PROMPT_TEMPLATE.format(
            user_input=user_input.strip() or "(추가 입력 없음)",
            response_tone=response_tone,
            intensity=intensity,
        )

        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                            },
                        ],
                    }
                ],
            )
            st.markdown("### 결과")
            st.markdown(resp.choices[0].message.content)
        except Exception as e:
            st.error(f"오류가 발생했어요: {e}")
