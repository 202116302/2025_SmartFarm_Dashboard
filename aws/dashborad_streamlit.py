import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import base64
import io
from PIL import Image
import random

# Streamlit 페이지 설정 - 이 부분은 반드시 다른 streamlit 명령어보다 먼저 와야 합니다
st.set_page_config(
    page_title="스마트팜 모니터링 대시보드",
    page_icon="🌱",
    layout="wide",  # 전체 화면 너비를 사용합니다
    initial_sidebar_state="expanded"  # 사이드바를 기본적으로 열어둡니다
)

# 사용자 정의 CSS로 더 예쁘게 만들어봅시다
st.markdown("""
<style>
    /* 메인 타이틀의 스타일을 꾸며줍니다 */
    .main-title {
        text-align: center;
        color: #2E8B57;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }

    /* 센서 카드들의 스타일입니다 */
    .sensor-card {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* 메트릭 값들을 더 눈에 띄게 만듭니다 */
    .metric-container {
        text-align: center;
        padding: 1rem;
    }

    /* 게시글 카드 스타일 */
    .post-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2E8B57;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* 게시글 제목 스타일 */
    .post-title {
        color: #2E8B57;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }

    /* 게시글 메타 정보 스타일 */
    .post-meta {
        color: #6c757d;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }

    /* 게시글 내용 스타일 */
    .post-content {
        color: #333;
        line-height: 1.5;
    }

    /* 반 구분 헤더 스타일 */
    .class-header {
        background: linear-gradient(90deg, #2E8B57, #32CD32);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 1rem 0;
        font-size: 1.5rem;
        font-weight: bold;
    }

    /* 게시글 이미지 스타일 */
    .post-image {
        max-width: 100%;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# API 서버 주소 설정 - 여기서 localhost는 같은 서버 내의 Flask 앱을 의미합니다
API_BASE_URL = "http://localhost:5000"

# 게시글 데이터를 세션 상태에 저장 (실제 환경에서는 데이터베이스를 사용하세요)
if 'posts' not in st.session_state:
    st.session_state.posts = []

# 스마트팜 장치 그룹 정의
SMARTFARM_GROUPS = {
    1: {
        'name': '2반 (smartfarm01~04)',
        'devices': ['smartfarm_01', 'smartfarm_02', 'smartfarm_03', 'smartfarm_04'],
        'team_name': ['잘자라조(1조)', '순창고추갱(2조)', '도겸공주와4왕자(3조)', '생태보스 야르~(4조)'],
        'emoji': '🌱'
    },
    2: {
        'name': '4반 (smartfarm05~08)',
        'devices': ['smartfarm05', 'smartfarm06', 'smartfarm07', 'smartfarm08'],
        'emoji': '🌿'
    }
}


def get_current_class():
    """
    URL 파라미터나 세션 상태에서 현재 선택된 반을 가져옵니다.
    URL에 ?class=1 또는 ?class=2 가 있으면 해당 반을 선택합니다.
    """
    # URL 파라미터 확인
    query_params = st.query_params

    if 'class' in query_params:
        try:
            class_num = int(query_params['class'])
            if class_num in [1, 2]:
                st.session_state.selected_class = class_num
                return class_num
        except ValueError:
            pass

    # 세션 상태에서 가져오기 (기본값은 1반)
    if 'selected_class' not in st.session_state:
        st.session_state.selected_class = 1

    return st.session_state.selected_class


def set_class_url(class_num):
    """
    URL을 업데이트하여 반 정보를 포함시킵니다.
    """
    st.query_params['class'] = str(class_num)


def generate_dummy_soil_data(devices):
    """
    API가 연결되지 않을 때 사용할 더미 토양수분 데이터를 생성합니다.
    """
    sensors = []
    for device_id in devices:
        # 각 장치별로 랜덤한 토양수분 값 생성 (실제로는 데이터베이스에서 가져와야 함)
        moisture_level = random.randint(20, 90)
        sensors.append({
            'device_id': device_id,
            'soil_moisture': moisture_level,
            'last_updated': datetime.now().isoformat()
        })

    return {'sensors': sensors}


def fetch_api_data(endpoint, device_filter=None):
    """
    Flask API에서 데이터를 가져오는 함수입니다.
    device_filter가 있으면 해당 장치들만 필터링합니다.
    API가 연결되지 않으면 더미 데이터를 반환합니다.
    """
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            data = response.json()

            # 장치 필터링이 필요한 경우
            if device_filter and isinstance(data, dict) and 'sensors' in data:
                filtered_sensors = [
                    sensor for sensor in data['sensors']
                    if sensor.get('device_id') in device_filter
                ]
                data['sensors'] = filtered_sensors

            return data
        else:
            # API 호출 실패 시 더미 데이터 반환
            if endpoint == "/api/soil/all" and device_filter:
                return generate_dummy_soil_data(device_filter)
            return None
    except requests.exceptions.RequestException:
        # 네트워크 오류 시 더미 데이터 반환
        if endpoint == "/api/soil/all" and device_filter:
            return generate_dummy_soil_data(device_filter)
        elif endpoint == "/api/weather":
            return {
                'temperature': random.randint(18, 28),
                'humidity': random.randint(40, 80),
                'rain_status': random.choice(['rain', 'no_rain']),
                'last_updated': datetime.now().isoformat()
            }
        return None
    except Exception as e:
        st.error(f"예상치 못한 오류가 발생했습니다: {str(e)}")
        return None


def image_to_base64(image):
    """
    PIL Image를 base64 문자열로 변환합니다.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str


def display_weather_data(class_num):
    """
    선택된 반의 날씨 센서 데이터를 표시합니다.
    """
    group_info = SMARTFARM_GROUPS[class_num]

    # 반 헤더 표시
    st.markdown(f"""
    <div class="class-header">
        {group_info['emoji']} {group_info['name']} - 날씨 센서 데이터
    </div>
    """, unsafe_allow_html=True)

    # 실제 API에서는 장치별로 날씨 데이터를 가져와야 하지만,
    # 여기서는 예시로 전체 날씨 데이터를 표시하고 반 정보를 함께 보여줍니다
    weather_data = fetch_api_data("/api/weather")

    if weather_data:
        # 3개의 열로 나누어 각 센서 값을 표시합니다
        col1, col2, col3 = st.columns(3)

        with col1:
            temp_value = weather_data.get('temperature')
            if temp_value is not None:
                if temp_value >= 30:
                    temp_color = "🔥"
                elif temp_value >= 20:
                    temp_color = "🌡️"
                else:
                    temp_color = "❄️"

                st.metric(
                    label=f"{temp_color} 온도",
                    value=f"{temp_value}°C",
                    delta=f"{group_info['name']}"
                )
            else:
                st.metric(label="🌡️ 온도", value="데이터 없음")

        with col2:
            humidity_value = weather_data.get('humidity')
            if humidity_value is not None:
                if humidity_value >= 70:
                    humidity_icon = "💧"
                elif humidity_value >= 40:
                    humidity_icon = "💨"
                else:
                    humidity_icon = "🏜️"

                st.metric(
                    label=f"{humidity_icon} 습도",
                    value=f"{humidity_value}%",
                    delta=None
                )
            else:
                st.metric(label="💨 습도", value="데이터 없음")

        with col3:
            rain_status = weather_data.get('rain_status', 'unknown')
            if rain_status == 'rain':
                st.metric(label="🌧️ 강우", value="비 내림", delta=None)
            elif rain_status == 'no_rain':
                st.metric(label="☀️ 강우", value="맑음", delta=None)
            else:
                st.metric(label="🌫️ 강우", value="데이터 없음", delta=None)

        if 'last_updated' in weather_data:
            try:
                update_time = datetime.fromisoformat(weather_data['last_updated'].replace('Z', '+00:00'))
                st.caption(f"📅 마지막 업데이트: {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                st.caption(f"📅 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning(f"{group_info['name']} 날씨 데이터를 불러올 수 없습니다.")


def display_soil_data(class_num):
    """
    선택된 반의 토양수분 센서 데이터를 표시합니다.
    """
    group_info = SMARTFARM_GROUPS[class_num]

    # 반 헤더 표시
    st.markdown(f"""
    <div class="class-header">
        {group_info['emoji']} {group_info['name']} - 토양수분 센서 데이터
    </div>
    """, unsafe_allow_html=True)

    # 해당 반의 장치들만 필터링해서 데이터 가져오기
    soil_data = fetch_api_data("/api/soil/all", device_filter=group_info['devices'])

    if soil_data and soil_data.get('sensors'):
        sensors = soil_data['sensors']

        if not sensors:
            st.info(f"{group_info['name']}에 해당하는 센서 데이터가 없습니다.")
            return

        # 센서가 여러 개인 경우 열로 나누어 표시합니다
        cols = st.columns(len(sensors) if len(sensors) <= 4 else 4)

        sensor_names = []
        moisture_values = []
        device_colors = []

        for i, sensor in enumerate(sensors):
            col_index = i % len(cols)

            with cols[col_index]:
                moisture_level = sensor['soil_moisture']
                device_id = sensor['team_name'] if 'team_name' in sensor else sensor['device_id']

                # 토양수분 레벨에 따른 상태 판단
                if moisture_level >= 70:
                    status_text = "습함 💧"
                    device_color = '#2E8B57'  # 녹색
                elif moisture_level >= 40:
                    status_text = "적당 🌿"
                    device_color = '#32CD32'  # 연녹색
                elif moisture_level >= 20:
                    status_text = "건조 ⚠️"
                    device_color = '#FFA500'  # 주황색
                else:
                    status_text = "매우건조 🚨"
                    device_color = '#FF4500'  # 빨간색

                st.metric(
                    label=f"🏷️ {device_id}",
                    value=f"{moisture_level}%",
                    delta=status_text
                )

                sensor_names.append(device_id)
                moisture_values.append(moisture_level)
                device_colors.append(device_color)

        # 토양수분 데이터를 막대 차트로 시각화
        if sensor_names and moisture_values:
            st.subheader(f"📊 {group_info['name']} 토양수분 비교 차트")

            fig = go.Figure(data=[
                go.Bar(
                    x=sensor_names,
                    y=moisture_values,
                    marker_color=device_colors,
                    text=[f'{val}%' for val in moisture_values],
                    textposition='auto',
                )
            ])

            fig.update_layout(
                title=f"{group_info['name']} 토양수분 센서별 비교",
                xaxis_title="센서 ID",
                yaxis_title="수분량 (%)",
                yaxis=dict(range=[0, 100]),
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"{group_info['name']} 토양수분 데이터를 불러올 수 없습니다.")


def display_system_status():
    """
    시스템 전체 상태를 확인하는 함수입니다.
    """
    st.subheader("🔧 시스템 상태")

    health_data = fetch_api_data("/health")

    if health_data:
        col1, col2 = st.columns(2)

        with col1:
            st.success("✅ Flask 서버 연결 정상")
            st.info(f"🕐 서버 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        with col2:
            if 'services' in health_data:
                st.write("**활성 서비스:**")
                for service, description in health_data['services'].items():
                    st.write(f"• {description}")
    else:
        st.warning("⚠️ Flask 서버에 연결할 수 없어 더미 데이터로 동작 중입니다")
        st.info(f"🕐 로컬 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 반별 장치 상태 표시
    st.markdown("---")
    st.subheader("📱 반별 장치 현황")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌱 1반")
        for device in SMARTFARM_GROUPS[1]['devices']:
            status = "✅ 연결됨" if health_data else "⚠️ 더미 데이터"
            st.write(f"• {device}: {status}")

    with col2:
        st.markdown("### 🌿 2반")
        for device in SMARTFARM_GROUPS[2]['devices']:
            status = "✅ 연결됨" if health_data else "⚠️ 더미 데이터"
            st.write(f"• {device}: {status}")


def display_bulletin_board():
    """
    게시판 기능을 표시하는 함수입니다.
    사진 업로드 기능이 포함되어 있습니다.
    """
    st.subheader("📝 스마트팜 커뮤니티 게시판")

    # 게시글 작성 폼
    st.write("### ✍️ 새 게시글 작성")

    with st.form("post_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])

        with col1:
            author_name = st.text_input("👤 작성자 이름", placeholder="이름을 입력하세요")

        with col2:
            post_category = st.selectbox("📁 카테고리",
                                         ["🌱 1반 재배정보", "🌿 2반 재배정보", "🔧 기술 문의",
                                          "📊 데이터 분석", "💡 아이디어 제안", "🗨️ 자유 게시"])

        post_title = st.text_input("📌 제목", placeholder="게시글 제목을 입력하세요")
        post_content = st.text_area("📄 내용", placeholder="게시글 내용을 입력하세요...", height=150)

        # 이미지 업로드 기능 추가
        st.write("📸 **사진 첨부 (선택사항)**")
        uploaded_file = st.file_uploader(
            "이미지 파일을 선택하세요",
            type=['png', 'jpg', 'jpeg', 'gif'],
            help="PNG, JPG, JPEG, GIF 파일을 업로드할 수 있습니다."
        )

        # 업로드된 이미지 미리보기
        uploaded_image_data = None
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                # 이미지 크기 조정 (너무 큰 이미지는 리사이즈)
                max_size = (800, 600)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

                st.image(image, caption="업로드된 이미지 미리보기", width=300)

                # 이미지를 base64로 인코딩하여 세션에 저장할 준비
                uploaded_image_data = image_to_base64(image)

            except Exception as e:
                st.error(f"이미지 처리 중 오류가 발생했습니다: {str(e)}")

        submitted = st.form_submit_button("📤 게시글 등록", use_container_width=True)

        if submitted:
            if author_name and post_title and post_content:
                new_post = {
                    "id": len(st.session_state.posts) + 1,
                    "author": author_name,
                    "category": post_category,
                    "title": post_title,
                    "content": post_content,
                    "timestamp": datetime.now(),
                    "likes": 0,
                    "image": uploaded_image_data  # 이미지 데이터 추가
                }
                st.session_state.posts.insert(0, new_post)
                st.success("✅ 게시글이 성공적으로 등록되었습니다!")
                st.rerun()
            else:
                st.error("❌ 작성자 이름, 제목, 내용을 모두 입력해주세요!")

    st.markdown("---")

    # 게시글 목록 표시
    st.write("### 📋 게시글 목록")

    if st.session_state.posts:
        # 게시글 통계 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📝 총 게시글", len(st.session_state.posts))
        with col2:
            total_likes = sum(post['likes'] for post in st.session_state.posts)
            st.metric("👍 총 좋아요", total_likes)
        with col3:
            unique_authors = len(set(post['author'] for post in st.session_state.posts))
            st.metric("👥 참여 인원", unique_authors)
        with col4:
            posts_with_images = len([post for post in st.session_state.posts if post.get('image')])
            st.metric("📸 사진 게시글", posts_with_images)

        st.markdown("---")

        # 각 게시글을 카드 형태로 표시
        for post in st.session_state.posts:
            time_ago = datetime.now() - post['timestamp']
            if time_ago.days > 0:
                time_str = f"{time_ago.days}일 전"
            elif time_ago.seconds > 3600:
                hours = time_ago.seconds // 3600
                time_str = f"{hours}시간 전"
            elif time_ago.seconds > 60:
                minutes = time_ago.seconds // 60
                time_str = f"{minutes}분 전"
            else:
                time_str = "방금 전"

            with st.container():
                # 게시글 헤더 정보
                image_indicator = " 📸" if post.get('image') else ""
                st.markdown(f"""
                <div class="post-card">
                    <div class="post-title">{post['category']} {post['title']}{image_indicator}</div>
                    <div class="post-meta">👤 {post['author']} • 🕒 {time_str} • 👍 {post['likes']}개</div>
                    <div class="post-content">{post['content']}</div>
                </div>
                """, unsafe_allow_html=True)

                # 첨부된 이미지가 있으면 표시
                if post.get('image'):
                    try:
                        # base64 이미지를 다시 디코딩해서 표시
                        image_data = base64.b64decode(post['image'])
                        image = Image.open(io.BytesIO(image_data))

                        # 이미지를 중앙 정렬하여 표시
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(image, use_column_width=True, caption="첨부된 사진")

                    except Exception as e:
                        st.error("이미지를 불러올 수 없습니다.")

                # 좋아요 및 댓글 버튼
                col1, col2, col3 = st.columns([1, 1, 8])
                with col1:
                    if st.button("👍", key=f"like_{post['id']}", help="좋아요"):
                        for i, p in enumerate(st.session_state.posts):
                            if p['id'] == post['id']:
                                st.session_state.posts[i]['likes'] += 1
                                break
                        st.rerun()

                with col2:
                    if st.button("💬", key=f"comment_{post['id']}", help="댓글"):
                        st.info("댓글 기능은 향후 업데이트 예정입니다!")

                st.markdown("---")

    else:
        st.info("📭 아직 작성된 게시글이 없습니다. 첫 번째 게시글을 작성해보세요!")
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background-color: #f8f9fa; border-radius: 8px; margin: 1rem 0;">
            <h3>🌱 스마트팜 커뮤니티에 오신 것을 환영합니다!</h3>
            <p>농업 기술, 재배 정보, 데이터 분석 등 다양한 주제로 소통해보세요.</p>
            <p>📸 사진과 함께 여러분의 경험과 지식을 공유하면 모두에게 도움이 됩니다! 💚</p>
        </div>
        """, unsafe_allow_html=True)


# 메인 애플리케이션 시작
def main():
    """
    Streamlit 앱의 메인 함수입니다.
    """
    # 현재 선택된 반 가져오기
    current_class = get_current_class()
    group_info = SMARTFARM_GROUPS[current_class]

    # 페이지 제목에 현재 반 정보 포함
    st.markdown(
        f'<h1 class="main-title">🌱 스마트팜 모니터링 대시보드<br><small>{group_info["emoji"]} {group_info["name"]}</small></h1>',
        unsafe_allow_html=True)

    # 사이드바에 반 선택 컨트롤 추가
    with st.sidebar:
        st.header("🎛️ 제어판")

        # 반 선택
        st.subheader("🏫 반 선택")

        # URL 링크 버튼들
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🌱 1반", key="class1_btn",
                         type="primary" if current_class == 1 else "secondary"):
                set_class_url(1)
                st.session_state.selected_class = 1
                st.rerun()

        with col2:
            if st.button("🌿 2반", key="class2_btn",
                         type="primary" if current_class == 2 else "secondary"):
                set_class_url(2)
                st.session_state.selected_class = 2
                st.rerun()

        # URL 정보 표시
        st.markdown("**🔗 직접 접속 링크:**")
        st.markdown(f"• [1반 대시보드](?class=1)")
        st.markdown(f"• [2반 대시보드](?class=2)")

        st.markdown("---")

        # 자동 새로고침 설정
        auto_refresh = st.checkbox("자동 새로고침 (30초)", value=False)

        if st.button("🔄 수동 새로고침"):
            st.rerun()

        st.markdown("---")

        # 연결 정보 표시
        st.subheader("🔗 연결 정보")
        st.write(f"**Flask API:** {API_BASE_URL}")
        st.write(f"**현재 시간:** {datetime.now().strftime('%H:%M:%S')}")
        st.write(f"**선택된 반:** {group_info['name']}")

        # 현재 반의 장치 목록
        st.markdown("---")
        st.subheader(f"📱 {group_info['name']} 장치")
        for device in group_info['devices']:
            st.write(f"• {device}")

        # 게시판 통계
        if st.session_state.posts:
            st.markdown("---")
            st.subheader("📝 게시판 현황")
            st.write(f"• 총 게시글: {len(st.session_state.posts)}개")
            posts_with_images = len([post for post in st.session_state.posts if post.get('image')])
            st.write(f"• 사진 게시글: {posts_with_images}개")
            st.write(f"• 최근 게시글: {st.session_state.posts[0]['title'][:15]}...")

    # 메인 콘텐츠를 탭으로 구성
    # 반별 데이터와 전체 기능을 함께 제공
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"📊 {group_info['emoji']} {current_class}반 데이터",
        "🔄 반별 비교",
        "📈 상세 분석",
        "⚙️ 시스템",
        "📝 커뮤니티"
    ])

    with tab1:
        # 선택된 반의 실시간 데이터 표시
        display_weather_data(current_class)
        st.markdown("---")
        display_soil_data(current_class)

    with tab2:
        # 반별 비교 탭
        st.subheader("🔄 1반 vs 2반 비교")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🌱 1반 데이터")
            display_soil_data(1)

        with col2:
            st.markdown("### 🌿 2반 데이터")
            display_soil_data(2)

    with tab3:
        st.subheader("📈 상세 데이터 분석")
        st.info(f"이 섹션에서는 {group_info['name']}의 시간별 트렌드, 일별 통계, 센서 비교 분석 등의 기능을 추가할 예정입니다.")

        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"{group_info['name']} 평균 온도", "23.5°C", "↑2.1°C")
        with col2:
            st.metric(f"{group_info['name']} 평균 습도", "65.2%", "↓3.4%")

    with tab4:
        display_system_status()

    with tab5:
        display_bulletin_board()

    # 자동 새로고침 기능
    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()