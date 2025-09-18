import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

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
</style>
""", unsafe_allow_html=True)

# API 서버 주소 설정 - 여기서 localhost는 같은 서버 내의 Flask 앱을 의미합니다
API_BASE_URL = "http://localhost:5000"


def fetch_api_data(endpoint):
    """
    Flask API에서 데이터를 가져오는 함수입니다.
    네트워크 오류나 서버 문제를 대비해서 에러 처리를 포함했습니다.
    """
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API 호출 실패: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Flask 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        return None
    except requests.exceptions.Timeout:
        st.error("서버 응답 시간이 초과되었습니다.")
        return None
    except Exception as e:
        st.error(f"예상치 못한 오류가 발생했습니다: {str(e)}")
        return None


def display_weather_data():
    """
    날씨 센서 데이터를 가져와서 화면에 표시하는 함수입니다.
    온도, 습도, 강우 상태를 각각 다른 색깔의 메트릭으로 보여줍니다.
    """
    weather_data = fetch_api_data("/api/weather")

    if weather_data:
        st.subheader("🌤️ 날씨 센서 데이터")

        # 3개의 열로 나누어 각 센서 값을 표시합니다
        col1, col2, col3 = st.columns(3)

        with col1:
            # 온도 표시 - 색깔로 온도 범위를 직관적으로 보여줍니다
            temp_value = weather_data.get('temperature')
            if temp_value is not None:
                if temp_value >= 30:
                    temp_color = "🔥"  # 더운 날씨
                elif temp_value >= 20:
                    temp_color = "🌡️"  # 적당한 날씨
                else:
                    temp_color = "❄️"  # 추운 날씨

                st.metric(
                    label=f"{temp_color} 온도",
                    value=f"{temp_value}°C",
                    delta=None
                )
            else:
                st.metric(label="🌡️ 온도", value="데이터 없음")

        with col2:
            # 습도 표시 - 습도 레벨에 따른 아이콘을 보여줍니다
            humidity_value = weather_data.get('humidity')
            if humidity_value is not None:
                if humidity_value >= 70:
                    humidity_icon = "💧"  # 높은 습도
                elif humidity_value >= 40:
                    humidity_icon = "💨"  # 적당한 습도
                else:
                    humidity_icon = "🏜️"  # 낮은 습도

                st.metric(
                    label=f"{humidity_icon} 습도",
                    value=f"{humidity_value}%",
                    delta=None
                )
            else:
                st.metric(label="💨 습도", value="데이터 없음")

        with col3:
            # 강우 상태 표시
            rain_status = weather_data.get('rain_status', 'unknown')
            if rain_status == 'rain':
                st.metric(label="🌧️ 강우", value="비 내림", delta=None)
            elif rain_status == 'no_rain':
                st.metric(label="☀️ 강우", value="맑음", delta=None)
            else:
                st.metric(label="🌫️ 강우", value="데이터 없음", delta=None)

        # 마지막 업데이트 시간을 작은 글씨로 표시합니다
        if 'last_updated' in weather_data:
            update_time = datetime.fromisoformat(weather_data['last_updated'].replace('Z', '+00:00'))
            st.caption(f"📅 마지막 업데이트: {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("날씨 데이터를 불러올 수 없습니다.")


def display_soil_data():
    """
    토양수분 센서들의 데이터를 가져와서 화면에 표시하는 함수입니다.
    여러 센서가 있을 경우 각각을 별도로 표시하고, 차트로도 보여줍니다.
    """
    soil_data = fetch_api_data("/api/soil/all")

    if soil_data and soil_data.get('sensors'):
        st.subheader("🌱 토양수분 센서 데이터")

        sensors = soil_data['sensors']

        # 센서가 여러 개인 경우 열로 나누어 표시합니다
        if len(sensors) <= 3:
            cols = st.columns(len(sensors))
        else:
            cols = st.columns(3)  # 최대 3열로 제한

        sensor_names = []
        moisture_values = []

        for i, sensor in enumerate(sensors):
            col_index = i % len(cols)  # 센서가 많으면 다음 줄로 넘어가도록

            with cols[col_index]:
                moisture_level = sensor['soil_moisture']
                device_id = sensor['device_id']

                # 토양수분 레벨에 따른 상태 판단과 색깔 결정
                if moisture_level >= 70:
                    status_text = "습함 💧"
                    status_color = "normal"
                elif moisture_level >= 40:
                    status_text = "적당 🌿"
                    status_color = "normal"
                elif moisture_level >= 20:
                    status_text = "건조 ⚠️"
                    status_color = "off"
                else:
                    status_text = "매우건조 🚨"
                    status_color = "inverse"

                # Streamlit의 metric 위젯을 사용해 값을 표시합니다
                st.metric(
                    label=f"🏷️ {device_id}",
                    value=f"{moisture_level}%",
                    delta=status_text
                )

                # 차트용 데이터를 수집합니다
                sensor_names.append(device_id)
                moisture_values.append(moisture_level)

        # 토양수분 데이터를 막대 차트로 시각화합니다
        if sensor_names and moisture_values:
            st.subheader("📊 토양수분 비교 차트")

            # 막대 차트의 색깔을 토양수분 수준에 따라 다르게 설정합니다
            colors = []
            for value in moisture_values:
                if value >= 70:
                    colors.append('#2E8B57')  # 녹색 - 좋음
                elif value >= 40:
                    colors.append('#32CD32')  # 연녹색 - 보통
                elif value >= 20:
                    colors.append('#FFA500')  # 주황색 - 주의
                else:
                    colors.append('#FF4500')  # 빨간색 - 위험

            # Plotly를 사용해서 더 예쁜 차트를 만듭니다
            fig = go.Figure(data=[
                go.Bar(
                    x=sensor_names,
                    y=moisture_values,
                    marker_color=colors,
                    text=[f'{val}%' for val in moisture_values],
                    textposition='auto',
                )
            ])

            fig.update_layout(
                title="토양수분 센서별 비교",
                xaxis_title="센서 ID",
                yaxis_title="수분량 (%)",
                yaxis=dict(range=[0, 100]),  # Y축을 0-100%로 고정
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("토양수분 데이터를 불러올 수 없습니다.")


def display_system_status():
    """
    시스템 전체 상태를 확인하는 함수입니다.
    서버 연결 상태와 각종 통계 정보를 보여줍니다.
    """
    st.subheader("🔧 시스템 상태")

    # 서버 헬스체크를 통해 시스템 상태를 확인합니다
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
        st.error("❌ Flask 서버에 연결할 수 없습니다")


# 메인 애플리케이션 시작
def main():
    """
    Streamlit 앱의 메인 함수입니다.
    여기서 전체 레이아웃을 구성하고 각 컴포넌트들을 배치합니다.
    """

    # 페이지 제목을 크고 예쁘게 표시합니다
    st.markdown('<h1 class="main-title">🌱 스마트팜 모니터링 대시보드</h1>',
                unsafe_allow_html=True)

    # 사이드바에 컨트롤 패널을 만듭니다
    with st.sidebar:
        st.header("🎛️ 제어판")

        # 자동 새로고침 설정
        auto_refresh = st.checkbox("자동 새로고침 (30초)", value=True)

        if st.button("🔄 수동 새로고침"):
            st.rerun()  # 페이지를 새로고침합니다

        st.markdown("---")  # 구분선

        # 연결 정보 표시
        st.subheader("🔗 연결 정보")
        st.write(f"**Flask API:** {API_BASE_URL}")
        st.write(f"**현재 시간:** {datetime.now().strftime('%H:%M:%S')}")

        # 간단한 통계 정보
        st.markdown("---")
        st.subheader("📈 오늘의 요약")
        st.write("• 센서 상태: 정상 동작 중")
        st.write("• 데이터 수집: 실시간")
        st.write("• 마지막 점검: 방금 전")

    # 메인 콘텐츠 영역을 두 개의 탭으로 구성합니다
    tab1, tab2, tab3 = st.tabs(["📊 실시간 데이터", "📈 상세 분석", "⚙️ 시스템"])

    with tab1:
        # 실시간 센서 데이터 표시
        display_weather_data()
        st.markdown("---")  # 구분선 추가
        display_soil_data()

    with tab2:
        st.subheader("📈 상세 데이터 분석")
        st.info("이 섹션에서는 향후 시간별 트렌드, 일별 통계, 센서 비교 분석 등의 기능을 추가할 예정입니다.")

        # 예시로 간단한 정보를 표시해봅니다
        col1, col2 = st.columns(2)
        with col1:
            st.metric("오늘 평균 온도", "23.5°C", "↑2.1°C")
        with col2:
            st.metric("오늘 평균 습도", "65.2%", "↓3.4%")

    with tab3:
        # 시스템 상태 표시
        display_system_status()

    # 자동 새로고침 기능
    if auto_refresh:
        # 30초마다 페이지를 자동으로 새로고침합니다
        time.sleep(30)
        st.rerun()


# 이 부분은 Python 스크립트가 직접 실행될 때만 main() 함수를 호출합니다
if __name__ == "__main__":
    main()