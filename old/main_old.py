import streamlit as st
import psycopg2
import pandas as pd
import os
import time
from datetime import date

# ==========================================
# ⚙️ コース設定
# ==========================================
PAR_DATA = {
    1: 4, 2: 3, 3: 4, 4: 4, 5: 4, 6: 5, 7: 3, 8: 5, 9: 4,   # OUT
    10: 5, 11: 4, 12: 3, 13: 4, 14: 4, 15: 4, 16: 3, 17: 4, 18: 5 # IN
}

CLUB_LIST = ["DR", "5W", "7W", "5U", "6U", "6I", "7I", "8I", "9I", "PW", "50", "56", "58", "PT"]

# ==========================================
# 🛠️ システム設定
# ==========================================
def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "golf_db"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", "password")
    )

st.set_page_config(page_title="Golf Log v13", page_icon="⛳", layout="centered")

# --- CSS設定 ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 3rem !important;
            padding-left: 0.2rem !important;
            padding-right: 0.2rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.2rem !important;
            align-items: end !important;
            margin-bottom: 0rem !important;
        }
        div[data-testid="column"] {
            min-width: 0 !important;
            flex: 1 !important;
            padding: 0 !important;
        }
        div[data-baseweb="select"] > div {
            font-size: 0.85rem !important;
            min-height: 2.2rem !important;
            padding: 0 0.2rem !important;
            background-color: #f8f9fa;
        }
        .stCaption {
            font-size: 0.7rem !important;
            text-align: center;
            margin-bottom: 0rem !important;
            height: 1.1rem !important;
            line-height: 1.1rem !important;
            white-space: nowrap;
        }
        div[data-testid="stCheckbox"] {
            min-height: 0 !important;
            height: auto !important;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            margin-top: -0.8rem !important;
            margin-bottom: -1.2rem !important;
        }
        div[data-testid="stCheckbox"] label {
            font-size: 0.75rem !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="element-container"]:has(div[data-testid="stCheckbox"]) {
            margin-bottom: 0 !important;
        }
        div.stButton > button {
            width: 100%;
            height: 3.5rem;
            font-weight: bold;
            margin-top: 0.5rem;
        }
        .hole-info {
            font-size: 1rem;
            font-weight: bold;
            text-align: center;
            background-color: #e6e6fa;
            padding: 0.3rem;
            border-radius: 5px;
            margin-bottom: 0.2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔄 リロード対策 & 連打防止ロジック
# ==========================================
if 'hole_index' not in st.session_state:
    try:
        saved_hole = st.query_params.get("hole", 0)
        st.session_state.hole_index = int(saved_hole)
    except:
        st.session_state.hole_index = 0

if 'last_registered_hole' not in st.session_state:
    st.session_state.last_registered_hole = -1

def move_hole(delta):
    new_index = max(0, min(17, st.session_state.hole_index + delta))
    st.session_state.hole_index = new_index
    st.query_params["hole"] = str(new_index)

HOLES_OUT = list(range(1, 19))
HOLES_IN = list(range(10, 19)) + list(range(1, 10))

# --- サイドバー ---
with st.sidebar:
    st.header("⚙️ 設定")
    round_date = st.date_input("日付", date.today())
    course = st.text_input("コース名", value="掛川GH")
    start_side = st.radio("スタート", ["OUT (1→18)", "IN (10→9)"])
    green_type = st.radio("グリーン", ["A", "B"], horizontal=True)
    current_order = HOLES_OUT if "OUT" in start_side else HOLES_IN
    
    st.markdown("---")
    c_prev, c_next = st.columns(2)
    with c_prev:
        st.button("◀ 前へ", on_click=move_hole, args=(-1,))
    with c_next:
        st.button("次へ ▶", on_click=move_hole, args=(1,))

# --- メイン画面 ---
tab1, tab2 = st.tabs(["⛳ 入力", "📝 履歴"])

with tab1:
    if st.session_state.hole_index > 17:
        st.success("終了")
        if st.button("最初から"):
            move_hole(-100)
            st.rerun()
    else:
        current_hole_no = current_order[st.session_state.hole_index]
        current_par = PAR_DATA.get(current_hole_no, 4)

        st.markdown(f"<div class='hole-info'>{current_hole_no}H (Par{current_par} / {green_type})</div>", unsafe_allow_html=True)

        with st.form("shot_input", clear_on_submit=True):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.caption("距離")
                dist_range = st.selectbox("dist", ["~100", "100-120", "120-140", "140-160", "160-180", "180~"], index=2, label_visibility="collapsed")
            with c2:
                st.caption("クラブ")
                club = st.selectbox("club", CLUB_LIST, index=6, label_visibility="collapsed")

            is_on = st.checkbox("パーオン (Green ON)", value=False)
            miss_dir = "NONE"
            lie_type = "NONE"
            
            if not is_on:
                c3, c4 = st.columns([1, 1])
                with c3:
                    st.caption("方向")
                    miss_dir = st.selectbox("dir", ["手前", "奥", "右", "左"], label_visibility="collapsed")
                with c4:
                    st.caption("ライ")
                    lie_type = st.selectbox("lie", ["花道", "ラフ浅", "ラフ深", "バンカー"], label_visibility="collapsed")

            st.markdown("") 
            c5, c6, c7 = st.columns([1, 1, 1])
            with c5:
                st.caption("パット")
                putts = st.selectbox("putts", list(range(6)), index=2, label_visibility="collapsed")
            with c6:
                st.caption("スコア")
                score_options = list(range(1, 15))
                default_idx = max(0, current_par - 1)
                hole_score = st.selectbox("score", score_options, index=default_idx, label_visibility="collapsed")
            with c7:
                st.caption("リカバリ")
                recovery = st.selectbox("recovery", list(range(1, 6)), index=1, label_visibility="collapsed")

            submitted = st.form_submit_button("登録 ➡ 次へ", type="primary")

            if submitted:
                # ★修正ポイント：もし「登録済み」の場合でも、強制的に次へ進める処理を追加
                if st.session_state.last_registered_hole == current_hole_no:
                    st.toast("⚠️ 登録済みです。次のホールへ進みます。", icon="⏭️")
                    time.sleep(1.0)
                    move_hole(1)  # ここで強制移動！
                    st.rerun()
                else:
                    try:
                        dist_map = {"~100": "under_100", "100-120": "100-120", "120-140": "120-140", "140-160": "140-160", "160-180": "160-180", "180~": "over_180"}
                        dir_map = {"手前": "SHORT", "奥": "OVER", "右": "RIGHT", "左": "LEFT"}
                        lie_map = {"花道": "HANAMICHI", "ラフ浅": "ROUGH_LIGHT", "ラフ深": "ROUGH_DEEP", "バンカー": "BUNKER"}
                        
                        db_dist = dist_map.get(dist_range, "140-160")
                        db_dir = dir_map.get(miss_dir, "NONE")
                        db_lie = lie_map.get(lie_type, "NONE")
                        green_val = "A" if green_type == "A" else "B"

                        conn = get_connection()
                        cur = conn.cursor()
                        sql = """
                            INSERT INTO approach_logs 
                            (round_date, course_name, hole_no, par, dist_range, club, is_green_on, miss_dir, lie_type, recovery_strokes, hole_score, green_type, putts)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cur.execute(sql, (
                            round_date, course, current_hole_no, current_par, db_dist, club, 
                            is_on, db_dir, db_lie, recovery, hole_score, green_val, putts
                        ))
                        conn.commit()
                        cur.close()
                        conn.close()
                        
                        # 登録成功マーク
                        st.session_state.last_registered_hole = current_hole_no
                        
                        msg = f"⛳ {current_hole_no}H 登録完了！\n(スコア: {hole_score} / パット: {putts})"
                        st.toast(msg, icon="✅")
                        
                        time.sleep(1.0)
                        
                        move_hole(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"エラー: {e}")

with tab2:
    try:
        conn = get_connection()
        df = pd.read_sql(f"SELECT id, hole_no as H, par as P, hole_score as Sc, putts as Pt, club FROM approach_logs WHERE round_date = '{round_date}' ORDER BY id DESC", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, hide_index=True, use_container_width=True)
            if st.button("最新1打を削除"):
                last_id = df.iloc[0]['id']
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM approach_logs WHERE id = %s", (int(last_id),))
                conn.commit()
                conn.close()
                st.warning("削除しました")
                
                # 削除したら連打防止ロック解除
                st.session_state.last_registered_hole = -1
                
                move_hole(-1)
                st.rerun()
    except:
        st.write("履歴なし")