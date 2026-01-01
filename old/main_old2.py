import streamlit as st
import psycopg2
import pandas as pd
import os
import time
from datetime import date

# ==========================================
# ⚙️ 基本設定
# ==========================================
PAR_DATA = {
    1: 4, 2: 3, 3: 4, 4: 4, 5: 4, 6: 5, 7: 3, 8: 5, 9: 4,
    10: 5, 11: 4, 12: 3, 13: 4, 14: 4, 15: 4, 16: 3, 17: 4, 18: 5
}
CLUB_LIST = ["DR", "5W", "7W", "5U", "6U", "6I", "7I", "8I", "9I", "PW", "50", "56", "58", "PT"]
DIST_LIST_DISP = ["~100", "100~", "120~", "140~", "160~", "180~"]

DIST_MAP = {"~100": "under_100", "100~": "100-120", "120~": "120-140", "140~": "140-160", "160~": "160-180", "180~": "over_180"}
DIR_MAP = {"手前": "SHORT", "奥": "OVER", "右": "RIGHT", "左": "LEFT", "NONE": "NONE"}
LIE_MAP = {"フェアウェイ": "FAIRWAY", "ラフ弱": "ROUGH_LIGHT", "ラフ強": "ROUGH_DEEP", "バンカー": "BUNKER", "NONE": "NONE"}

# --- 🔌 データベース接続機能（クラウド対応版） ---
def get_connection():
    """
    接続先を自動判定します。
    1. st.secrets に 'DATABASE_URL' があればそれを使う (Streamlit Cloud / Neon用)
    2. なければローカルのDocker設定を使う
    """
    # StreamlitのSecrets（秘密鍵管理）からURLを取得
    if "DATABASE_URL" in st.secrets:
        # NeonなどのクラウドDBはSSL接続が必須の場合が多いです
        return psycopg2.connect(st.secrets["DATABASE_URL"], sslmode='require')
    
    # フォールバック（ローカルDocker用）
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "golf_db"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", "password")
    )

def init_db():
    """初回起動時にテーブルがなければ作成する"""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS approach_logs (
        id SERIAL PRIMARY KEY,
        round_date DATE,
        course_name TEXT,
        hole_no INTEGER,
        par INTEGER,
        dist_range TEXT,
        club TEXT,
        is_green_on BOOLEAN,
        miss_dir TEXT,
        lie_type TEXT,
        recovery_strokes INTEGER,
        hole_score INTEGER,
        green_type TEXT,
        putts INTEGER
    );
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(create_table_query)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"DB初期化エラー: {e}")

st.set_page_config(page_title="Golf Log Cloud", page_icon="⛳", layout="centered")

# アプリ起動時にテーブル存在確認を実行
init_db()

# --- 🔄 セッション状態の初期化 ---
if 'hole_index' not in st.session_state:
    st.session_state.hole_index = int(st.query_params.get("hole", 0))
if 'course_name' not in st.session_state:
    st.session_state.course_name = st.query_params.get("course", "掛川GH")
if 'start_side' not in st.session_state:
    st.session_state.start_side = st.query_params.get("start", "OUT (1→18)")
if 'green_type' not in st.session_state:
    st.session_state.green_type = st.query_params.get("green", "A")
if 'last_registered_hole' not in st.session_state:
    st.session_state.last_registered_hole = -1
if 'on_status_res' not in st.session_state:
    st.session_state.on_status_res = "パーオン成功"
if 'is_finished' not in st.session_state:
    st.session_state.is_finished = False
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

def sync_params():
    st.query_params["hole"] = str(st.session_state.hole_index)
    st.query_params["course"] = st.session_state.course_name
    st.query_params["start"] = st.session_state.start_side
    st.query_params["green"] = st.session_state.green_type

def next_hole():
    """次のホールへ進む共通処理"""
    if st.session_state.hole_index == 17:
        st.session_state.is_finished = True
    else:
        st.session_state.hole_index += 1
        st.session_state.on_status_res = "パーオン成功"
    sync_params()
    st.rerun()

# --- 🎨 CSS ---
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem !important; max-width: 500px !important; margin: auto; }
        .hole-header {
            background-color: #212529; color: white; padding: 12px 15px; border-radius: 10px;
            text-align: center; margin-bottom: 15px; display: flex; 
            justify-content: space-between; align-items: center;
        }
        .stCaption { font-weight: bold !important; margin-top: 12px !important; }
        div.stButton > button { width: 100%; font-weight: bold; height: 3.5rem; border-radius: 8px; }
        .btn-reg > div > button { background-color: #28a745 !important; color: white !important; }
        hr { margin: 12px 0 !important; border-top: 1px solid #ddd !important; }
    </style>
""", unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    st.header("⚙️ 設定 Cloud")
    with st.form(key="sidebar_form"):
        round_date = st.date_input("日付", date.today())
        course_in = st.text_input("コース名", value=st.session_state.course_name)
        start_in = st.radio("スタート", ["OUT (1→18)", "IN (10→9)"], index=0 if "OUT" in st.session_state.start_side else 1)
        green_in = st.radio("グリーン", ["A", "B"], horizontal=True, index=0 if st.session_state.green_type == "A" else 1)
        if st.form_submit_button("反映"):
            st.session_state.course_name, st.session_state.start_side, st.session_state.green_type = course_in, start_in, green_in
            st.session_state.hole_index = 0
            st.session_state.is_finished = False
            st.session_state.show_history = False
            st.session_state.on_status_res = "パーオン成功"
            sync_params(); st.rerun()

    st.markdown("---")
    if st.button("📝 履歴を表示"):
        st.session_state.show_history = True
        st.rerun()

    current_order = list(range(1, 19)) if "OUT" in st.session_state.start_side else list(range(10, 19)) + list(range(1, 10))
    
    st.markdown("---")
    c_prev, c_next = st.columns(2)
    with c_prev:
        if st.button("◀ 前へ"):
            st.session_state.hole_index = max(0, st.session_state.hole_index - 1)
            st.session_state.is_finished = False
            sync_params(); st.rerun()
    with c_next:
        if st.button("次へ ▶"):
            st.session_state.hole_index = min(17, st.session_state.hole_index + 1)
            sync_params(); st.rerun()

# --- メインエリア ---

if st.session_state.show_history:
    st.subheader("📝 本日の履歴")
    if st.button("◀ 入力に戻る"):
        st.session_state.show_history = False
        st.rerun()
    try:
        conn = get_connection()
        # データベースが空の場合の対応
        df = pd.read_sql(f"SELECT hole_no as H, par as P, hole_score as Score, putts as Putt, club FROM approach_logs WHERE round_date = '{round_date}' ORDER BY id DESC", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, hide_index=True, use_container_width=True)
            if st.button("最新1打を削除"):
                conn = get_connection(); cur = conn.cursor()
                cur.execute(f"DELETE FROM approach_logs WHERE id = (SELECT max(id) FROM approach_logs WHERE round_date = '{round_date}')")
                conn.commit(); conn.close()
                st.session_state.hole_index = max(0, st.session_state.hole_index - 1)
                st.session_state.last_registered_hole = -1
                st.rerun()
        else:
            st.info("まだデータがありません。")
    except Exception as e:
        st.error(f"履歴取得エラー: {e}")

elif st.session_state.is_finished:
    st.balloons()
    st.success(f"🏆 ラウンド終了！")
    if st.button("新しいラウンドを開始", type="primary"):
        st.session_state.is_finished = False
        st.session_state.hole_index = 0
        st.session_state.last_registered_hole = -1
        sync_params(); st.rerun()

else:
    hole_no = current_order[st.session_state.hole_index]
    par = PAR_DATA.get(hole_no, 4)

    st.markdown(f"""<div class='hole-header'>
        <span>{hole_no}H</span><span style='color:#ffc107; font-size:1.4rem;'>Par {par}</span><span>{st.session_state.green_type} Green</span>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("残り距離")
        dist_raw = st.selectbox("dist", DIST_LIST_DISP, index=2, label_visibility="collapsed")
    with col2:
        st.caption("クラブ")
        club = st.selectbox("club", CLUB_LIST, index=6, label_visibility="collapsed")

    st.caption("結果")
    on_status = st.radio("on_check", ["パーオン成功", "失敗"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.on_status_res == "パーオン成功" else 1)
    st.session_state.on_status_res = on_status
    
    miss_dir_raw, lie_raw = "NONE", "NONE"
    if on_status == "失敗":
        st.caption("外した方向")
        miss_dir_raw = st.radio("dir", ["左", "手前", "奥", "右"], horizontal=True, label_visibility="collapsed")
        st.caption("ライの状態")
        lie_raw = st.radio("lie", ["フェアウェイ", "ラフ弱", "ラフ強", "バンカー"], horizontal=True, label_visibility="collapsed")

    with st.form("score_form", clear_on_submit=True):
        st.markdown("<hr>", unsafe_allow_html=True)
        st.caption("パット数")
        putts = st.radio("putts", [0, 1, 2, 3, 4, 5, 6], index=2, horizontal=True, label_visibility="collapsed")
        st.caption(f"ホールスコア (Par {par})")
        score_opts = [1, 2, 3, 4, 5, 6, 7, 8, "9~"]
        score_disp = st.radio("score", score_opts, index=min(len(score_opts)-1, par-1), horizontal=True, label_visibility="collapsed")
        st.caption("リカバリ数")
        recovery = st.radio("recovery", [0, 1, 2, 3, 4, 5, 6], index=0, horizontal=True, label_visibility="collapsed")

        st.markdown("<div class='btn-reg'>", unsafe_allow_html=True)
        submitted = st.form_submit_button("登録 ➡ 次のホールへ")
        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if st.session_state.last_registered_hole == hole_no:
                st.warning(f"⚠️ {hole_no}Hは既に登録済みです。次のホールへ進みます。")
                time.sleep(1)
                next_hole()
            else:
                try:
                    final_score = 9 if score_disp == "9~" else int(score_disp)
                    conn = get_connection(); cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO approach_logs (round_date, course_name, hole_no, par, dist_range, club, is_green_on, miss_dir, lie_type, recovery_strokes, hole_score, green_type, putts)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (round_date, st.session_state.course_name, hole_no, par, DIST_MAP.get(dist_raw), club, (on_status=="パーオン成功"), DIR_MAP.get(miss_dir_raw), LIE_MAP.get(lie_raw), recovery, final_score, st.session_state.green_type, putts))
                    conn.commit(); cur.close(); conn.close()
                    
                    st.toast(f"✅ {hole_no}H 登録完了", icon="⛳")
                    st.session_state.last_registered_hole = hole_no
                    time.sleep(0.5)
                    next_hole()
                except Exception as e:
                    st.error(f"エラー: {e}")