import os
import io
import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf

# 0. 檔案管理與資料夾結構建立
IMAGE_DIR = "images"
DATA_DIR = "data"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# 1. 基本設定
plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
}

try:
    print("⏳ 1. 抓取期交所 Put/Call Ratio...")
    url_pcr = "https://openapi.taifex.com.tw/v1/PutCallRatio"
    res_pcr = requests.get(url_pcr, headers=headers, timeout=10)
    df_pcr = pd.read_json(io.StringIO(res_pcr.text))

    df_pcr["Date_Clean"] = pd.to_datetime(df_pcr["Date"].astype(str))
    df_pcr["PCRatio"] = (
        pd.to_numeric(
            df_pcr["PutCallOIRatio%"].astype(str).str.replace(",", ""),
            errors="coerce",
        )
        / 100
    )

    print("⏳ 2. 抓取台股加權指數...")
    twii = yf.Ticker("^TWII")
    df_taiex = twii.history(period="3mo").reset_index()

    df_taiex["Date_Clean"] = pd.to_datetime(
        df_taiex["Date"].dt.strftime("%Y-%m-%d")
    )
    df_taiex["TAIEX"] = df_taiex["Close"]

    print("⏳ 3. 合併並鎖定最近 30 個交易日...")
    df_merged = pd.merge(
        df_pcr[["Date_Clean", "PCRatio"]],
        df_taiex[["Date_Clean", "TAIEX"]],
        on="Date_Clean",
        how="inner",
    )

    df_merged = df_merged.sort_values("Date_Clean").tail(30).reset_index(drop=True)
    df_merged["Display_Date"] = df_merged["Date_Clean"].dt.strftime("%m/%d")

    # ==========================================
    # 4. 繪製上下合一的兩張圖表 (共用同一個 fig)
    # ==========================================
    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # --- 上圖：加權指數 vs. Put/Call Ratio (雙 Y 軸複合圖) ---
    ax2 = ax_top.twinx()
    bars = ax2.bar(
        df_merged.index,
        df_merged["TAIEX"],
        color="skyblue",
        edgecolor="steelblue",
        alpha=0.6,
        width=0.6,
        label="加權指數收盤點數",
    )

    line = ax_top.plot(
        df_merged.index,
        df_merged["PCRatio"],
        color="crimson",
        linewidth=2,
        marker="o",
        markersize=4,
        label="Put/Call Ratio (未平倉比率)",
    )

    # 圖層調整與範圍設定
    ax_top.set_zorder(ax2.get_zorder() + 1)
    ax_top.set_facecolor("none")
    ax_top.set_ylim(0, 1.8)
    taiex_min = df_merged["TAIEX"].min() * 0.98
    taiex_max = df_merged["TAIEX"].max() * 1.02
    ax2.set_ylim(taiex_min, taiex_max)

    ax_top.set_xlim(-1, len(df_merged))

    # 標籤與圖例 (上圖)
    ax_top.set_ylabel(
        "Put/Call Ratio (未平倉)", color="crimson", fontsize=12, fontweight="bold"
    )
    ax2.set_ylabel(
        "加權指數點數", color="steelblue", fontsize=12, fontweight="bold"
    )

    lines1, labels1 = ax_top.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax_top.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    ax_top.set_title(
        "加權指數 (長條) vs. Put/Call Ratio 未平倉 (折線) (最近一個月)",
        fontsize=14,
        pad=15,
    )
    ax_top.grid(True, linestyle="--", alpha=0.3)

    # --- 下圖：P/C Ratio 警戒值長條圖 ---
    ax_bottom.bar(
        df_merged.index,
        df_merged["PCRatio"],
        label="P/C Ratio (未平倉)",
        color="gray",
        alpha=0.6,
        width=0.6,
    )
    ax_bottom.axhline(
        1.3, color="orange", linestyle="--", label="Panic Threshold (1.3)"
    )
    ax_bottom.axhline(
        0.8, color="green", linestyle="--", label="Optimistic Threshold (0.8)"
    )

    ax_bottom.set_ylim(0, 1.6)
    ax_bottom.set_xlim(-1, len(df_merged))
    ax_bottom.set_title(
        "選擇權買賣權比率情緒指標（最近 1 個月）", fontsize=14, pad=15
    )
    ax_bottom.set_ylabel("P/C Ratio (未平倉)", fontsize=12, fontweight="bold")
    ax_bottom.legend(loc="upper left")
    ax_bottom.grid(True, linestyle="--", alpha=0.3)

    # 統一設定 X 軸日期刻度 (共用 X 軸)
    ax_bottom.set_xticks(range(0, len(df_merged)))
    ax_bottom.set_xticklabels(
        df_merged["Display_Date"],
        rotation=30,
        ha="right",
        fontsize=9,
    )

    plt.tight_layout()

    # --- 自動儲存圖表至 images/ 資料夾 ---
    plt.savefig(
        os.path.join(IMAGE_DIR, "taiex_pcr_analysis.png"),
        dpi=300,
        bbox_inches="tight",
    )

    plt.show()

    # --- 自動儲存清理後的數據至 data/ 資料夾 ---
    df_merged.to_csv(
        os.path.join(DATA_DIR, "taiex_pcr_recent.csv"),
        index=False,
        encoding="utf-8-sig",
    )

    print("🎉 最近上下雙圖完整繪製成功！")

except Exception as e:
    print(f"❌ 處理失敗：{e}")