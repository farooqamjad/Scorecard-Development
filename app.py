
import streamlit as st
import warnings
import logging
import io
import re
import time
import contextlib
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.api as sm
from xlsx2csv import Xlsx2csv
from streamlit_tags import st_tags
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from scorecardpy import woebin, woebin_ply, scorecard, scorecard_ply
import scorecardpy as sc
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import roc_curve,roc_auc_score,confusion_matrix
from scipy.stats import binomtest
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.metrics import mutual_info_score
import plotly.express as px
from streamlit_extras.customize_running import center_running
import plotly.graph_objects as go
logging.getLogger("scorecardpy").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
import streamlit_authenticator as stauth
import importlib.metadata


FIXED_PASSWORD = "Delta007"

def require_login():
    if st.session_state.get("auth", False):
        with st.sidebar:
            st.markdown(
                f"""
                <style>
                .logout-btn button {{
                    width: 100%;
                    background: linear-gradient(135deg, #ff4b5c, #ff6f61);
                    color: white !important;
                    border: none;
                    border-radius: 12px;
                    padding: 0.6rem;
                    font-size: 16px;
                    font-weight: 600;
                    box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
                    transition: all 0.3s ease-in-out;
                }}
                .logout-btn button:hover {{
                    background: linear-gradient(135deg, #e63946, #ff4b5c);
                    transform: scale(1.05);
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(f"👋 Welcome **{st.session_state.username}**")
            if st.button("🚪 Logout", key="logout", help="Click to logout", type="primary"):
                st.session_state.auth = False
                st.session_state.username = None
                st.rerun()
        return

    st.markdown(
        """
        <style>
        .login-card {
            max-width: 420px;
            margin: 100px auto;
            padding: 2rem;
            border-radius: 18px;
            background: linear-gradient(270deg, #e0f7fa, #c8e6c9, #b2dfdb, #a5d6a7);
            background-size: 600% 600%;
            animation: gradientMove 12s ease infinite;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            text-align: center;
            font-family: 'Segoe UI', sans-serif;
            animation: fadeIn 0.8s ease-in-out;
        }

        .login-title {
            font-size: 30px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #004d40;
        }
        .login-subtitle {
            font-size: 16px;
            color: #00695c;
            margin-bottom: 25px;
        }
        .stTextInput label, .stTextInput input {
            font-size: 15px;
        }
        .stButton button {
            width: 100%;
            border-radius: 10px;
            padding: 0.6rem;
            font-size: 16px;
            background: #00796b;
            color: white;
            font-weight: 600;
            transition: all 0.3s ease-in-out;
        }
        .stButton button:hover {
            background: #004d40;
            transform: scale(1.05);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ✅ Gradient move animation */
        @keyframes gradientMove {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🔐 Secure Login</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Welcome back! Please enter your credentials to continue.</div>', unsafe_allow_html=True)

        username = st.text_input("👤 Username")
        password = st.text_input("🔑 Password", type="password")
        submitted = st.form_submit_button("Login")

        st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if password == FIXED_PASSWORD:
            st.session_state.auth = True
            st.session_state.username = username or "User"
            st.success(f"✅ Welcome {st.session_state.username} 👋")
            st.rerun()
        else:
            st.error("❌ Password is incorrect")
            st.stop()
    st.stop()

require_login()

st.markdown("""
    <style>
        .center-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin-top: 30px;
        }

        .scorecard-title {
            font-size: 42px;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 20px;
            font-family: 'Segoe UI', sans-serif;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            text-align: center;
        }

        @media (prefers-color-scheme: light) {
            .scorecard-title {
                color: #0d3b66;
            }
        }

        @media (prefers-color-scheme: dark) {
            .scorecard-title {
                color: #f0f4f8;
            }
        }
    </style>

    <div class="center-wrapper">
        <h1 class="scorecard-title">Credit Risk Scorecard</h1>
    </div>
""", unsafe_allow_html=True)

_, col, _ = st.columns([1, 2, 1])
with col:
    st.image("Scorecard.png", width=400)


session_defaults = {
    "original_data": None,
    "cdata": None,
    "selected_tags": [],
    "show_tag_selector": False,
    "show_processed_data": False,
    "show_original_data": False,
    "show_custom_var_ui": False,
    "created_variables": {},
    "bin_rules": {},
    "source_vars_for_last_derived": [],
    "derived_source_vars": {},
    "show_missing_ui": False,
    "show_preview": False,
    "source_mapping": {}
}

for key, default_value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

def style_expander_header():
    st.markdown("""
        <style>
        /* 🔵 Default Blue Theme */
        div[data-testid="stExpander"] > details > summary {
            background-color: #e3f2fd;
            color: #0d47a1;
            border: 1px solid #1976d2;
            border-radius: 6px;
            padding: 6px;
            font-weight: 600;
            cursor: pointer;
        }
        div[data-testid="stExpander"] > details > summary:hover {
            background-color: #bbdefb;
        }
        </style>
    """, unsafe_allow_html=True)


def load_excel_fast(file):
    ext = file.name.split(".")[-1].lower()
    if ext == "xlsx":
        return pd.read_excel(file, engine="openpyxl")
    elif ext == "xls":
        return pd.read_excel(file, engine="xlrd")
    elif ext == "xlsb":
        return pd.read_excel(file, engine="pyxlsb")
    else:
        raise ValueError("Unsupported Excel format")

def clean_names(data):
    data.columns = data.columns.str.strip().str.lower().str.replace(' ', '_')
    data.rename(columns={data.columns[-1]: "target"}, inplace=True)
    return data

def style_threshold_table(df, threshold, value_column, format_map=None):
    def highlight_column(val):
        return "background-color: #ffcccc" if val >= threshold else ""

    styled_df = (
        df.style
        .applymap(highlight_column, subset=[value_column])
        .background_gradient(subset=[value_column], cmap='Reds')
        .format(format_map or {})
        .set_properties(**{
            'text-align': 'center',
            'border': '1px solid #ddd',
            'border-radius': '4px',
            'padding': '6px'
        })
        .set_table_styles([
            {'selector': 'thead th', 'props': [('font-weight', 'bold'), ('background-color', '#f7f7f7')]},
            {'selector': 'tbody tr:hover', 'props': [('background-color', '#f0f0f0')]},
            {'selector': 'td', 'props': [('font-size', '14px')]},
            {'selector': 'th', 'props': [('font-size', '14px')]}
        ])
    )
    return styled_df

def get_missing_summary(df, threshold):
    df_summary = df.copy()
    if 'target' in df_summary.columns:
        df_summary = df_summary.drop(columns=['target'])

    missing_values = df_summary.isnull().sum()
    missing_percent = round((missing_values / len(df_summary)) * 100, 5)

    mdt = pd.DataFrame({
        'Variable': missing_percent.index,
        'Missing Count': missing_values.values,
        'Missing %': missing_percent.values
    }).sort_values(by='Missing %', ascending=False).reset_index(drop=True)

    styled_mdt = style_threshold_table(
        mdt,
        threshold=threshold,
        value_column='Missing %',
        format_map={'Missing %': '{:.2f}%'}
    )

    return mdt, styled_mdt

def classify_iv_status(iv):
    if iv < 0.02:
        return 'Not useful for prediction'
    elif iv < 0.1:
        return 'Weak predictor'
    elif iv < 0.3:
        return 'Medium predictor'
    elif iv < 0.5:
        return 'Strong predictor'
    else:
        return 'Suspicious'

def iv_color(status):
    return {
        'Not useful for prediction': 'background-color: #f8d7da; color: #721c24',
        'Weak predictor': 'background-color: #fff3cd; color: #856404',
        'Medium predictor': 'background-color: #d1ecf1; color: #0c5460',
        'Strong predictor': 'background-color: #d4edda; color: #155724',
        'Suspicious': 'background-color: #e2e3e5; color: #6c757d'
    }[status]

def build_breaks(df, target_col, manual_breaks):
    breaks_list = manual_breaks.copy()

    for col in df.columns:
        if col == target_col or col in breaks_list:
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            try:
                bin_result = sc.woebin(df[[col, target_col]], y=target_col)
                if bin_result[col]['bin'].nunique() <= 1:
                    breaks_list[col] = [1]
            except:
                continue

        elif df[col].dtype == 'object' or isinstance(df[col].dtype, pd.CategoricalDtype):
            try:
                categories = df[col].dropna().unique().tolist()
                if len(categories) > 1:
                    breaks_list[col] = categories
            except:
                continue

    return breaks_list

def run_woe_iv_with_progress(df, target_col, manual_breaks):
    breaks_list = build_breaks(df, target_col, manual_breaks)
    total_vars = len([col for col in df.columns if col != target_col])

    bins = {}
    iv_list = []

    for i, col in enumerate(df.columns):
        if col == target_col:
            continue
        brks = {col: breaks_list.get(col)} if breaks_list.get(col) else None

        binned = sc.woebin(df[[col, target_col]], y=target_col, breaks_list=brks)
        bins.update(binned)
        iv_value = binned[col]['total_iv'].iloc[0]
        iv_list.append({'Variable': col, 'Information Value': round(iv_value, 5)})

        yield {
            "progress": int((i + 1) / total_vars * 100),
            "variable": col,
            "iv_entry": iv_list[-1],
            "bins": binned,
            "breaks": breaks_list.get(col)
        }

    iv_summary = pd.DataFrame(iv_list).sort_values(by='Information Value', ascending=False).reset_index(drop=True)
    iv_summary['IV Status'] = iv_summary['Information Value'].apply(classify_iv_status)

    yield {
        "done": True,
        "bins": bins,
        "iv_summary": iv_summary,
        "breaks_list": breaks_list
    }

def _round_numeric_bounds(bin_label, decimals=2):
    try:
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", bin_label)
        rounded = [str(round(float(num), decimals)) for num in numbers]
        return re.sub(r"[-+]?\d*\.\d+|\d+", lambda m: rounded.pop(0), bin_label).replace(',', ' – ')
    except:
        return bin_label

def round_bin_labels(bins_dict, decimals=2):
    cleaned_bins = {}
    for var, df in bins_dict.items():
        df = df.copy()
        df['bin'] = df['bin'].astype(str).apply(lambda x: _round_numeric_bounds(x, decimals))
        cleaned_bins[var] = df
    return cleaned_bins

def clean_varname(name: str) -> str:
    """Readable variable name"""
    return name.replace("_", " ").title()

def sync_final_woe_data(removed_vars):
    if "final_woe_data" in st.session_state and st.session_state.final_woe_data is not None:
        st.session_state.final_woe_data = st.session_state.final_woe_data.drop(columns=removed_vars, errors='ignore')
    else:
        st.warning("⚠️ WOE-transformed data not found. Cannot sync removal.")

def style_vif_table(df, threshold):
    def highlight_vif(val):
        try:
            val = float(val)
            if val >= threshold:
                return "background-color: #ffcccc; color: #b30000; font-weight: bold;"  # red tone
            else:
                return "background-color: #ffe5cc; color: #663300; font-weight: bold;"  # skin/peach tone
        except:
            return ""

    styled_df = (
        df.style
        .applymap(highlight_vif, subset=["VIF"])
        .set_properties(**{
            'text-align': 'center',
            'border': '1px solid #ddd',
            'padding': '6px'
        })
        .set_table_styles([
            {'selector': 'thead th', 'props': [('font-weight', 'bold'), ('background-color', '#f7f7f7')]},
            {'selector': 'tbody tr:hover', 'props': [('background-color', '#f0f0f0')]},
            {'selector': 'td', 'props': [('font-size', '14px')]},
            {'selector': 'th', 'props': [('font-size', '14px')]}
        ])
        .format({"VIF": "{:.2f}", "IV": "{:.4f}"})
    )
    return styled_df

def get_expanded_corr_vars(vif_data, df_for_vif, vif_threshold=5.0, corr_threshold=0.5):

    high_vif_vars = vif_data[vif_data["VIF"] > vif_threshold]["Features"].tolist()
    corr_matrix_full = df_for_vif.corr()
    expanded_vars = set(high_vif_vars)

    for var in high_vif_vars:
        if var in corr_matrix_full.columns:
            correlated = corr_matrix_full.loc[var][
                abs(corr_matrix_full.loc[var]) > corr_threshold
            ].index.tolist()
            expanded_vars.update(correlated)

    return [v for v in expanded_vars if v in df_for_vif.columns]

def iv_based_backward_selection(df_woe, iv_table, target_col, sig_level=0.05):
    variable_map = {
        var: f"{var}_woe"
        for var in iv_table["Variable"]
        if f"{var}_woe" in df_woe.columns
    }

    iv_table = iv_table.loc[iv_table["IV"] > 0.02].copy()
    iv_table = iv_table.sort_values(by="IV", ascending=True)

    selected_vars = [variable_map[v] for v in iv_table["Variable"] if v in variable_map]
    df_model = df_woe[selected_vars + [target_col]].copy()

    removed_vars = []

    while True:
        X = df_model.drop(columns=[target_col])
        y = df_model[target_col]

        X_const = sm.add_constant(X)
        model = sm.Logit(y, X_const).fit(disp=False)
        pvalues = model.pvalues.drop("const")

        removal_candidate = None
        for var in iv_table["Variable"]:
            woe_var = variable_map.get(var)
            if woe_var in pvalues.index and pvalues[woe_var] > sig_level:
                removed_vars.append({
                    "Variable": var,
                    "IV": iv_table.loc[iv_table["Variable"] == var, "IV"].values[0],
                    "p-value": pvalues[woe_var]
                })
                removal_candidate = woe_var
                break

        if removal_candidate:
            df_model = df_model.drop(columns=[removal_candidate])
            iv_table = iv_table[iv_table["Variable"] != removal_candidate.split("_woe")[0]]
        else:
            break

    return df_model, model, removed_vars

def style_removal_table(df):
    styled = df.style.set_table_styles([{
        "selector": "th",
        "props": [("text-align", "center")]
    }])
    return styled


st.sidebar.title("📌 Navigation")
menu = st.sidebar.radio(
    "Go to section:",
    ["🧰 Data Preparation", "🎯 Variables Selection", "🛠️ Scorecard Development"]
)

if menu == "🧰 Data Preparation":
    style_expander_header()
    with st.expander("📂 Upload Data", expanded=True):
        file_type = st.selectbox(
            "Select File Type",
            ["Excel (.xlsx / .xls / .xlsb)", "CSV (.csv)"]
        )
        uploaded_file = st.file_uploader(
            "Upload your dataset",
            type=["xlsx", "xls", "xlsb"] if file_type.startswith("Excel") else ["csv"]
        )

        spinner_placeholder = st.empty()
        progress_bar = st.empty()

        if uploaded_file and st.session_state.get("original_data") is None:
            spinner_placeholder.markdown(
                """
                <div style="display: flex; justify-content: center; align-items: center; height: 60px;">
                    <span style="font-size: 16px;">⏳ <strong>Processing your file... Please wait.</strong></span>
                    <div class="loader" style="margin-left: 10px;"></div>
                </div>
                <style>
                .loader {
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #3498db;
                    border-radius: 50%;
                    width: 18px;
                    height: 18px;
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            if file_type.startswith("Excel"):
                progress = progress_bar.progress(0.5)  # Simulated mid-progress
                st.session_state.original_data = load_excel_fast(uploaded_file)
                progress.progress(1.0)
            else:
                progress = progress_bar.progress(0.5)
                st.session_state.original_data = pd.read_csv(uploaded_file, low_memory=False)
                progress.progress(1.0)


            progress_bar.empty()
            spinner_placeholder.empty()
            st.session_state.selected_tags = st.session_state.original_data.columns.tolist()
            st.success("✅ File uploaded successfully!")

    if st.session_state.original_data is not None:
        data = st.session_state.original_data
        st.session_state.data = st.session_state.original_data.copy()
        style_expander_header()
        with st.expander("👁️ View & Select Data", expanded=True):
            if st.checkbox("📄 Preview Uploaded Data"):
                st.dataframe(data.head(), use_container_width=True)

            if "confirmed_tags" not in st.session_state:
                st.session_state.confirmed_tags = False

            if not st.session_state.confirmed_tags:
                st.info("📌 Select Variables for Analysis")
                st.session_state.show_tag_selector = st.checkbox(
                    "🧠 Select Explanatory & Target Variables"
                )
                st.caption("⚠️ **Only select scoring and target variables — remove all others**")
                if st.session_state.show_tag_selector:
                    selected_tags = st_tags(
                        label='',
                        value=st.session_state.selected_tags,
                        suggestions=data.columns.tolist(),
                        key='column_tags',
                        maxtags=len(data.columns),
                    )

                    if not selected_tags:
                        st.warning("Please select at least one column.")
                    else:
                        st.session_state.selected_tags = selected_tags

                    if st.button("✅ Confirm Selection",type="primary"):
                        st.session_state.confirmed_tags = True
                        st.session_state.show_processed_data = True
                        st.success("✅ Variables selected successfully!")

        if st.session_state.show_processed_data:
            with st.expander("🧹 Clean & Process Data", expanded=True):
                cdata = st.session_state.original_data[st.session_state.selected_tags].copy()
                cdata = clean_names(cdata)
                for var_name, var_series in st.session_state.created_variables.items():
                    cdata[var_name] = var_series
                st.session_state.cdata = cdata
                st.dataframe(cdata.head(), use_container_width=True)

                if st.checkbox("➕ Create Custom Variable"):
                    st.session_state.show_custom_var_ui = True

                if st.session_state.get("show_custom_var_ui", False):
                    cdata = st.session_state.cdata
                    cat_vars = [col for col in cdata.select_dtypes(include=['object', 'category']).columns if col != 'target']
                    num_vars = [col for col in cdata.select_dtypes(include=['int', 'float']).columns if col != 'target']

                    if cat_vars and num_vars:
                        st.subheader("🧮 Custom Variable Binning")
                        st.caption("👇 Select Categorical & Numeric Variable")

                        categorical_col = st.selectbox(
                            "Select Categorical Variable",
                            options=["— Select option —"] + cat_vars,
                            index=0,
                            key="cat_var_select"
                        )
                        numeric_col = st.selectbox(
                            "Select Numeric Variable",
                            options=["— Select option —"] + num_vars,
                            index=0,
                            key="num_var_select"
                        )

                        if categorical_col != "— Select option —" and numeric_col != "— Select option —":
                            categories = cdata[categorical_col].dropna().unique()
                            new_var_name = st.text_input(
                                "Enter New Variable Name",
                                value=f"{categorical_col}_wise_{numeric_col}"
                            )

                            for cat in categories:
                                with st.expander(f"Category: {cat}", expanded=False):
                                    subset = cdata[cdata[categorical_col] == cat]
                                    if subset.empty:
                                        st.warning(f"No data for category {cat}")
                                        continue

                                    create_bins = st.checkbox(
                                        f"Create bins for '{cat}'?", value=True, key=f"{cat}_createbins"
                                    )
                                    if not create_bins:
                                        label = st.text_input(
                                            f"Label for category '{cat}' (no binning)",
                                            value=f"{cat}",
                                            key=f"{cat}_nobin_label"
                                        )
                                        st.session_state.bin_rules[(cat, categorical_col, numeric_col)] = [{
                                            "min": None,
                                            "max": None,
                                            "label": label,
                                            "no_bin": True
                                        }]
                                        continue

                                    min_val = subset[numeric_col].min()
                                    max_val = subset[numeric_col].max()

                                    num_bins = st.number_input(
                                        f"How many bins for '{cat}'?",
                                        min_value=1, max_value=10, value=1, step=1,
                                        key=f"{cat}_numbins"
                                    )

                                    default_bps = [
                                        float(min_val + (max_val - min_val) * (i + 1) / num_bins)
                                        for i in range(num_bins - 1)
                                    ]

                                    bp_text = st.text_input(
                                        f"Breakpoints for {cat} (comma separated)",
                                        value=",".join([f"{bp:.0f}" for bp in default_bps]),
                                        key=f"{cat}_breakpoints"
                                    )

                                    try:
                                        middle_points = sorted(set([float(x.strip()) for x in bp_text.split(",") if x.strip() != ""]))
                                    except ValueError:
                                        st.error("⚠️ Please enter valid numeric breakpoints (comma separated).")
                                        middle_points = []

                                    bin_edges = [min_val] + middle_points + [max_val]

                                    bin_labels = []
                                    for i in range(len(bin_edges) - 1):
                                        default_label = f"{cat}({bin_edges[i]:.0f} - {bin_edges[i+1]:.0f})"
                                        label = st.text_input(
                                            f"Label for Bin {i+1} ({cat})",
                                            value=default_label,
                                            key=f"{cat}_label_{i}"
                                        )
                                        bin_labels.append(label)

                                    st.session_state.bin_rules[(cat, categorical_col, numeric_col)] = [
                                        {"min": bin_edges[i], "max": bin_edges[i+1], "label": bin_labels[i], "no_bin": False}
                                        for i in range(len(bin_edges) - 1)
                                    ]

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Finish and Create Variable"):
                                    if new_var_name:
                                        def assign_bin(row):
                                            seg = row[categorical_col]
                                            val = row[numeric_col]
                                            rules = st.session_state.bin_rules.get((seg, categorical_col, numeric_col), [])
                                            for rule in rules:
                                                if rule["no_bin"]:
                                                    return rule["label"] if seg == seg else None
                                                if rule["min"] <= val <= rule["max"]:
                                                    return rule["label"]
                                            return None

                                        st.session_state.cdata[new_var_name] = st.session_state.cdata.apply(assign_bin, axis=1)
                                        st.session_state.created_variables[new_var_name] = st.session_state.cdata[new_var_name]

                                        st.session_state.cdata_aligned = st.session_state.cdata.copy()
                                        st.session_state.cdata_cleaned = st.session_state.cdata.copy()

                                        if "source_mapping" not in st.session_state:
                                            st.session_state.source_mapping = {}
                                        st.session_state.source_mapping[new_var_name] = [categorical_col, numeric_col]

                                        st.success(f"Custom variable '{new_var_name}' created!")
                                        st.session_state.show_custom_var_ui = False
                            with col2:
                                if st.button("❌ Cancel"):
                                    st.session_state.show_custom_var_ui = False
                                    st.info("Custom variable creation cancelled.")

                if 'removed_derived_vars' not in st.session_state:
                    st.session_state.removed_derived_vars = []

                if st.session_state.get("source_mapping") and st.session_state.get("cdata") is not None:
                    all_sources = set()
                    for sources in st.session_state.source_mapping.values():
                        all_sources.update(sources)
                    to_remove = [v for v in all_sources if v in st.session_state.cdata.columns]
                    if to_remove:
                        st.session_state.to_remove_derived = to_remove
                        st.info(f"Variables available for removal: {', '.join(to_remove)}")

                    remove_button = st.button(
                        "🗑 Remove Variables Used for Derived Variable Creation", key="btn_remove_derived_vars"
                    )
                    if remove_button:
                        removed = [v for v in st.session_state.to_remove_derived if v in st.session_state.cdata.columns]
                        if removed:
                            st.session_state.cdata.drop(columns=removed, inplace=True, errors='ignore')
                            for v in removed:
                                st.session_state.created_variables.pop(v, None)
                            st.session_state.removed_derived_vars = removed

                        st.session_state.cdata_cleaned = st.session_state.cdata.copy()
                        st.session_state.cdata_aligned = st.session_state.cdata.copy()

                        if st.session_state.removed_derived_vars:
                            st.success(f"🚮 Variables Removed : {', '.join(removed)}")

                st.session_state.missing_expander_open = st.session_state.get("remove_missing_vars_expander", False)

                if "missing_expander_open" not in st.session_state:
                    st.session_state.missing_expander_open = False

                with st.expander("🧹 Missing Value Treatment", expanded=st.session_state.missing_expander_open):
                    if "cdata_cleaned" not in st.session_state:
                        st.session_state.cdata_cleaned = st.session_state.get("cdata", pd.DataFrame()).copy()

                    threshold = st.number_input(
                        "Allowed Missing % Threshold",
                        min_value=0.0, max_value=100.0, value=10.0, step=0.1,
                        key="missing_threshold_expander"
                    )

                    mdt, _ = get_missing_summary(st.session_state.cdata_cleaned, threshold)
                    mdt.index = range(1, len(mdt) + 1)

                    styled_mdt = style_threshold_table(
                        mdt, threshold=threshold, value_column='Missing %', format_map={'Missing %': '{:.2f}%'}
                    )
                    st.dataframe(styled_mdt, use_container_width=True)

                    over_threshold = mdt[mdt['Missing %'] >= threshold]
                    if not over_threshold.empty:
                        st.warning(f"🚨 Variables exceeding threshold: {', '.join(over_threshold['Variable'])}")

                    remove_vars = st.checkbox("🗑 Remove Variables Above Threshold", key="remove_missing_vars_expander")

                    if remove_vars:
                        to_keep = mdt[mdt['Missing %'] < threshold]['Variable'].tolist()
                        removed_vars = mdt[mdt['Missing %'] >= threshold]['Variable'].tolist()

                        if 'target' in st.session_state.cdata_cleaned.columns and 'target' not in to_keep:
                            to_keep.append('target')

                        cleaned = st.session_state.cdata_cleaned[to_keep].copy()
                        for col in cleaned.select_dtypes(include='object').columns:
                            cleaned[col] = cleaned[col].astype('category')

                        st.session_state.cdata_cleaned = cleaned
                        st.session_state.cdata_aligned = cleaned

                        if removed_vars:
                            st.session_state.missing_vars_removed = True
                            st.success(f"🚮 Variables Removed : {', '.join(removed_vars)}")
                        else:
                            st.session_state.missing_vars_removed = False
                            st.info("✅ No variables exceeded the missing value threshold.")

                    if st.session_state.get("missing_vars_removed", False):
                        st.caption("📄 Final Cleaned & Aligned Data")
                        st.dataframe(st.session_state.cdata_aligned.head(), use_container_width=True)
                        st.success("🎉 Data is ready for modeling! 🚀 Moving on to Variable Selection")
                        st.divider()

elif menu == "🎯 Variables Selection":

    @contextlib.contextmanager
    def suppress_stdout():
        with contextlib.redirect_stdout(io.StringIO()):
            yield

    if st.session_state.get("cdata_aligned") is not None:
        style_expander_header()
        with st.expander("📊 WOE Binning & IV Analysis", expanded=False):

            for key in ["manual_breaks", "woe_iv_result", "woe_transformed", "cdata_filtered", "edit_var", "show_filtered_after_removal"]:
                if key not in st.session_state:
                    st.session_state[key] = {} if key == "manual_breaks" else None

            st.markdown("#### ✏️ Define Manual Breaks")
            all_vars = [c for c in st.session_state.cdata_aligned.columns if c != "target"]

            selected_var = st.selectbox(
                "Select variable to define breaks if required",
                options=[""] + all_vars,
                index=([""] + all_vars).index(st.session_state.get("edit_var", "")) if st.session_state.get("edit_var") in all_vars else 0,
                key="var_select"
            )

            if selected_var:
                default_breaks = st.session_state.manual_breaks.get(selected_var, [])
                user_input = st.text_input(
                    f"Enter breakpoints for {selected_var} (comma-separated)",
                    value=",".join(map(str, default_breaks)),
                    key=f"breaks_input_{selected_var}"
                )

                if st.button(f"💾 Save Breaks for {selected_var}", key=f"save_{selected_var}"):
                    try:
                        if pd.api.types.is_numeric_dtype(st.session_state.cdata_aligned[selected_var]):
                            breaks = [float(x.strip()) for x in user_input.split(",") if x.strip()]
                        else:
                            breaks = [x.strip() for x in user_input.split(",") if x.strip()]
                        st.session_state.manual_breaks[selected_var] = breaks
                        st.success(f"✅ Manual breaks updated for {selected_var}")
                        st.session_state.edit_var = ""
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing breaks: {e}")

            if st.session_state.manual_breaks:
                st.info("#### 📋 Current Manual Breaks")
                for var, brks in st.session_state.manual_breaks.copy().items():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{var}** → {brks}")
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_{var}"):
                            st.session_state.edit_var = var
                            st.rerun()
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_{var}"):
                            st.session_state.manual_breaks.pop(var)
                            st.warning(f"🗑️ Deleted manual breaks for `{var}`")
                            st.rerun()

            if st.button("⚙️ Run WOE Transformation", type="primary", key="btn_run_iv"):
                progress_text = "🔄 Processing WOE Transformation"
                my_bar = st.progress(0, text=progress_text)
                for col in st.session_state.cdata_aligned.select_dtypes(include=["category", "object"]).columns:
                    st.session_state.cdata_aligned[col] = (
                        st.session_state.cdata_aligned[col]
                        .astype("string")
                        .fillna("missing")
                    )
                bins = {}
                iv_entries = []
                breaks_list = {}

                with st.spinner("🧪 Transforming Data to WOE"):
                    for update in run_woe_iv_with_progress(
                        st.session_state.cdata_aligned,
                        target_col="target",
                        manual_breaks=st.session_state.manual_breaks
                    ):
                        if update.get("done"):
                            st.session_state.final_woe_data = sc.woebin_ply(st.session_state.cdata_aligned, update["bins"])
                            st.session_state.woe_iv_result = (update["bins"], update["iv_summary"], update["breaks_list"])
                            break

                        bins.update(update["bins"])
                        iv_entries.append(update["iv_entry"])
                        breaks_list[update["variable"]] = update["breaks"]
                        my_bar.progress(update["progress"], text=f"{progress_text} ({update['variable']})")

                my_bar.empty()
                st.session_state.breaks_list = breaks_list
                st.success(f"✅ WOE transformation completed for {len(bins)} variables!")

            if st.session_state.woe_transformed is not None:
                if st.button("👀 View WOE Transformed Data", key="btn_view_woe"):
                    st.info("#### 📘 WOE Transformed Dataset")
                    st.dataframe(st.session_state.woe_transformed.head(), use_container_width=True)

            for key, default in {
                'show_iv_table': False,
                'iv_df': None,
                'iv_sorted': None
            }.items():
                if key not in st.session_state:
                    st.session_state[key] = default

            if st.session_state.get('woe_iv_result') is not None:

                if st.button("📊 Show IV Table", key="btn_show_iv"):
                    _, iv_df, _ = st.session_state.woe_iv_result

                    if iv_df is not None and not iv_df.empty:
                        iv_df['IV Status'] = iv_df['Information Value'].apply(classify_iv_status)
                        iv_df.index = range(1, len(iv_df) + 1)
                        iv_sorted = iv_df.sort_values(by='Information Value', ascending=False)

                        st.session_state.iv_df = iv_df
                        st.session_state.iv_sorted = iv_sorted
                        st.session_state.show_iv_table = True

                if st.session_state.show_iv_table and st.session_state.iv_df is not None:
                    def style_iv_status(s):
                        return [iv_color(val) if s.name == 'IV Status' else '' for val in s]

                    styled_iv = (
                        st.session_state.iv_df.style
                        .apply(style_iv_status, axis=0)
                        .format({'Information Value': '{:.4f}'})
                        .set_properties(**{
                            'text-align': 'center',
                            'padding': '6px',
                            'border': '1px solid #ddd',
                            'font-size': '13px'
                        })
                        .set_table_styles([
                            {'selector': 'thead th', 'props': [('font-weight', 'bold'), ('background-color', '#f1f1f1')]},
                            {'selector': 'tbody tr:hover', 'props': [('background-color', '#f9f9f9')]},
                            {'selector': 'td', 'props': [('border', '1px solid #eee')]},
                            {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]}
                        ])
                    )

                    st.markdown("### 🧾 IV Summary", unsafe_allow_html=True)
                    st.dataframe(styled_iv, use_container_width=True)

                    csv = st.session_state.iv_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download IV Summary",
                        data=csv,
                        file_name="iv_summary.csv",
                        mime="text/csv"
                    )

                    show_chart = st.toggle("📈 Show IV Chart", value=False)

                    if show_chart and st.session_state.iv_sorted is not None and not st.session_state.iv_sorted.empty:

                        fig = px.bar(
                            st.session_state.iv_sorted,
                            x='Variable',
                            y='Information Value',
                            color='IV Status',
                            title='📊 Information Value by Variable',
                            color_discrete_map={
                                'Not useful for prediction': '#FF4C4C',
                                'Weak predictor': '#FFC300',
                                'Medium predictor': '#00BFFF',
                                'Strong predictor': '#28A745',
                                'Suspicious': '#9B59B6'
                            },
                            hover_data={'Information Value': ':.4f', 'IV Status': True},
                            height=400
                        )

                        fig.update_traces(
                            marker_line_width=0,
                            width=0.5
                        )

                        fig.update_layout(
                            xaxis=dict(
                                title="Variable",
                                tickangle=-45,
                                tickfont=dict(size=11),
                                automargin=True
                            ),
                            yaxis=dict(
                                title="Information Value",
                                tickfont=dict(size=11)
                            ),
                            font=dict(size=13),
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            margin=dict(t=60, b=100),
                            title_x=0.0
                        )
                        st.caption("📢 **Tip:** For better visualization, use the **↗️ Fullscreen** icon in the top-right corner of the graph.")
                        st.plotly_chart(fig, use_container_width=True)

            if st.session_state.woe_iv_result is not None:
                if st.checkbox("🗑️ Remove Variables with IV < 0.02", key="chk_remove_iv"):
                    bins, iv, _ = st.session_state.woe_iv_result
                    rvar = iv[iv['Information Value'] < 0.02]['Variable'].tolist()

                    st.session_state.cdata_aligned = st.session_state.cdata_aligned.drop(columns=rvar, errors='ignore')
                    st.session_state.cdata_aligned = st.session_state.cdata_aligned.copy()
                    rvar_woe = [f"{col}_woe" for col in rvar]

                    if "final_woe_data" in st.session_state and st.session_state.final_woe_data is not None:
                        st.session_state.final_woe_data = st.session_state.final_woe_data.drop(columns=rvar_woe, errors='ignore')
                    else:
                        st.warning("⚠️ WOE-transformed data not found. Cannot sync removal.")

                    st.success(f"✅ Removed {len(rvar)} variable(s) with IV < 0.02:\n{rvar}")

                    if st.button("📄 View Dataset"):
                        st.caption("📘 Dataset after IV Removal")
                        st.dataframe(st.session_state.cdata_aligned.head(), use_container_width=True)
                        st.session_state.show_filtered_after_removal = True


    if st.session_state.get("woe_iv_result") is not None:
        style_expander_header()
        with st.expander("📈 Trend Analysis", expanded=False):
            bins_rounded = round_bin_labels(st.session_state.woe_iv_result[0], decimals=2)
            vars_to_plot = list(st.session_state.cdata_aligned.columns)
            if "vars_with_xtick_rotation" not in st.session_state:
                st.session_state.vars_with_xtick_rotation = []

            col1, col2, col3 = st.columns([1, 2, 2])
            with col1:
                show_graphs = st.button("👀 View WOE Trend Graphs")
            with col2:
                rotation_vars = st.multiselect(
                    "Rotate X-ticks for:",
                    options=vars_to_plot,
                    default=st.session_state.get("vars_with_xtick_rotation", []),
                    key="rotate_xticks"
                )
            with col3:
                rotation_angle = st.slider("↪️ Angle", 20, 90, 30, 5)
            if show_graphs:
                st.caption("⚠️ Must exclude variables that are counterintuitive")
                for var in vars_to_plot:
                    if var not in bins_rounded:
                        continue

                    bdf = bins_rounded[var]
                    sc.woebin_plot({var: bdf})
                    fig = plt.gcf()

                    bin_count = bdf['bin'].nunique()
                    fig.set_size_inches(7, 4) if bin_count <= 3 else fig.set_size_inches(8, 4)

                    for ax in fig.axes:
                        y_values = [p.get_height() for p in ax.patches]
                        if y_values:
                            ax.set_ylim(top=max(y_values) * 1.15)

                        labels = ax.get_xticklabels()
                        fig.canvas.draw()

                        overlaps = (
                            bin_count > 4 and any(
                                label.get_window_extent().width >
                                (ax.get_xlim()[1] - ax.get_xlim()[0]) / len(labels)
                                for label in labels
                            )
                        )

                        if overlaps or var in st.session_state.vars_with_xtick_rotation:
                            for label in labels:
                                label.set_rotation(rotation_angle)
                                label.set_ha('right')

                    plt.tight_layout()
                    st.pyplot(fig)

        if st.session_state.get("woe_iv_result") is not None:
            style_expander_header()
            with st.expander("🧭 Counter-Intuitive & Business POV Removal", expanded=False):
                current_cols = [
                    col for col in st.session_state.cdata_aligned.columns
                    if col != 'target'
                ]

                if st.session_state.get("trigger_reset", False):
                    st.session_state.rem_con_int_selection = []
                    st.session_state.rem_var_bv_selection = []
                    st.session_state.trigger_reset = False

                with st.form("removal_form"):
                    st.caption("👇 Select variables to remove based on business logic or intuition")
                    rem_con_int_selection = st.multiselect(
                        "Variables (Counter-Intuitive)",
                        options=current_cols,
                        default=[
                            x for x in st.session_state.get("rem_con_int_selection", [])
                            if x in current_cols
                        ],
                        key="rem_con_int_selection"
                    )

                    rem_var_bv_selection = st.multiselect(
                        "Variables (Business POV)",
                        options=current_cols,
                        default=[
                            x for x in st.session_state.get("rem_var_bv_selection", [])
                            if x in current_cols
                        ],
                        key="rem_var_bv_selection"
                    )

                    reset_sel = st.form_submit_button("♻️ Reset Selection")
                    submit_rem = st.form_submit_button("🧹 Apply Removal")

                if reset_sel:
                    st.session_state.trigger_reset = True
                    st.rerun()

                if submit_rem:
                    removed = []

                    all_selected = rem_con_int_selection + rem_var_bv_selection

                    if all_selected:
                        st.session_state.cdata_aligned = st.session_state.cdata_aligned.drop(columns=all_selected, errors='ignore')
                        removed.extend(all_selected)

                        woe_cols_to_remove = [f"{col}_woe" for col in all_selected]

                        if "final_woe_data" in st.session_state and st.session_state.final_woe_data is not None:
                            st.session_state.final_woe_data = st.session_state.final_woe_data.drop(columns=woe_cols_to_remove, errors='ignore')
                        st.session_state.cdata_filtered = st.session_state.cdata_aligned.copy()
                        st.success(f"Removed Variables: {', '.join(removed)}")

                    st.session_state.show_filtered_after_removal = True
                    st.session_state.trigger_view_filtered = True

                if st.session_state.get("trigger_view_filtered"):
                    if st.button("🧾 View Filtered Dataset", key="btn_view_filtered_after_removal"):
                        st.dataframe(st.session_state.cdata_aligned.head(), use_container_width=True)

        for key, default in {
            "vif_expander_open": False,
            "show_corr": False,
            "vif_data": None,
            "df_for_vif": None,
            "iv_map": None
        }.items():
            if key not in st.session_state:
                st.session_state[key] = default

        if st.session_state.get("woe_iv_result") is not None:
            @st.cache_data(show_spinner=False)
            def calculate_vif_cached(df_for_vif, iv_map):
                from statsmodels.stats.outliers_influence import variance_inflation_factor

                results = []
                my_bar = st.progress(0, text="⚙️ Calculating VIF...")

                for i, col in enumerate(df_for_vif.columns):
                    vif = variance_inflation_factor(df_for_vif.values, i)
                    results.append((col, vif))
                    my_bar.progress((i + 1) / len(df_for_vif.columns), text=f"⚙️ Calculating VIF... ({col})")

                my_bar.empty()

                vif_data = pd.DataFrame(results, columns=["Features", "VIF"])
                vif_data["VIF"] = vif_data["VIF"].replace([np.inf, -np.inf], np.nan).fillna(999)
                vif_data["Clean Feature"] = vif_data["Features"].str.replace("_woe", "", regex=False)
                vif_data["IV"] = vif_data["Clean Feature"].map(iv_map).fillna("N/A")
                vif_data = vif_data.sort_values(by="VIF", ascending=False).reset_index(drop=True)
                vif_data.index = vif_data.index + 1

                return vif_data
            style_expander_header()
            with st.expander("🧮 VIF & Correlation Analysis", expanded=st.session_state.vif_expander_open):

                vif_threshold = st.slider("⚠️ VIF Threshold", 0.0, 30.0, 5.0, 0.5)

                if "final_woe_data" not in st.session_state:
                    st.warning("⚠️ Please apply variable removal first using the '🧹 Apply Removal' button.")
                else:
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        if st.button("🚀 Run VIF Analysis", type="primary", key="btn_calculate_vif"):
                            st.session_state.vif_expander_open = True
                            try:
                                df_for_vif = st.session_state.final_woe_data.drop(columns=['target'], errors='ignore')
                                df_for_vif.rename(columns=lambda x: x.replace("_woe", "") if "_woe" in x else x, inplace=True)
                                df_for_vif = df_for_vif.replace([np.inf, -np.inf], np.nan).dropna()

                                iv_df = st.session_state.woe_iv_result[1]
                                iv_map = dict(zip(iv_df["Variable"], iv_df["Information Value"]))

                                st.session_state.vif_data = calculate_vif_cached(df_for_vif, iv_map)
                                st.session_state.df_for_vif = df_for_vif
                                st.session_state.iv_map = iv_map

                            except Exception as e:
                                st.error(f"❌ Error during VIF analysis: {e}")

                    with col2:
                        st.session_state.show_corr = st.toggle(
                            "🔗 Show Correlation View",
                            value=st.session_state.get("show_corr", False)
                        )

                    if st.session_state.vif_data is not None:
                        vif_df = st.session_state.vif_data.copy()

                        required_cols = ["Clean Feature", "VIF", "IV"]
                        if not all(col in vif_df.columns for col in required_cols):
                            st.error("❌ Missing columns in VIF DataFrame")
                        else:
                            display_df = vif_df[required_cols].rename(columns={"Clean Feature": "Variable"})
                            styled_vif = style_vif_table(display_df, threshold=vif_threshold)

                            st.caption("**📋 VIF Table with IV**")
                            st.dataframe(styled_vif, use_container_width=True)

                            rem_vars = st.multiselect(
                                "🗑️ Select variables to remove (based on VIF):",
                                options=vif_df["Clean Feature"].tolist(),
                                key="rem_vif_vars"
                            )

                            if st.button("♻️ Recalculate VIF after Removal", key="btn_recalc_vif"):
                                rem_vars = st.session_state.get("rem_vif_vars", [])

                                st.session_state.final_woe_data = st.session_state.final_woe_data.drop(
                                    columns=[v + "_woe" if v + "_woe" in st.session_state.final_woe_data.columns else v
                                            for v in rem_vars],
                                    errors="ignore"
                                )
                                st.session_state.cdata_aligned = st.session_state.cdata_aligned.drop(columns=rem_vars, errors='ignore')

                                st.success(f"✅ Removed {len(rem_vars)} variable(s): {', '.join(rem_vars) if rem_vars else 'None'}")

                                df_for_vif = st.session_state.final_woe_data.drop(columns=["target"], errors="ignore")
                                df_for_vif.rename(columns=lambda x: x.replace("_woe", "") if "_woe" in x else x, inplace=True)
                                df_for_vif = df_for_vif.replace([np.inf, -np.inf], np.nan).dropna()

                                st.session_state.vif_data = calculate_vif_cached(df_for_vif, st.session_state.iv_map)
                                st.session_state.df_for_vif = df_for_vif
                                st.session_state.vif_expander_open = True

                                st.session_state.vif_removal_triggered = True

                                st.rerun()
                            elif not st.session_state.get("vif_removal_triggered", False):
                                st.warning("⚠️ Select variables based on VIF to remove or press Recalculate button to move forward.")

                            if st.session_state.show_corr and st.session_state.vif_data is not None:
                                with st.expander("🔗 Correlation View", expanded=True):

                                    iv_map = st.session_state.get("iv_map", {})

                                    corr_threshold = st.slider("📈 Correlation Threshold (|r|)", 0.0, 1.0, 0.5, 0.05)

                                    filtered_vars = get_expanded_corr_vars(
                                        st.session_state.vif_data,
                                        st.session_state.df_for_vif,
                                        vif_threshold=vif_threshold,
                                        corr_threshold=corr_threshold
                                    )

                                    if filtered_vars:
                                        corr_matrix = st.session_state.df_for_vif[filtered_vars].corr()

                                        view_mode = st.radio("Choose view mode:", ["Heatmap", "Clustermap"], horizontal=True)
                                        num_vars = len(corr_matrix.columns)
                                        fig_width = max(18, num_vars * 0.8)
                                        fig_height = max(14, num_vars * 0.6)

                                        if view_mode == "Heatmap":
                                            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
                                            sns.heatmap(
                                                corr_matrix, annot=True, cmap='PuBuGn',
                                                fmt=".2f", linewidths=0.5, annot_kws={"size": 14},
                                                cbar_kws={"shrink": 0.8}
                                            )
                                            ax.set_title("Correlation Heatmap (For High VIF Variables)", loc='left', fontsize=16, pad=30)
                                            ax.tick_params(axis="x", labelsize=14)
                                            ax.tick_params(axis="y", labelsize=14)
                                            plt.tight_layout()
                                            st.caption("📢 **Tip:** For better visualization, use the **↗️ Fullscreen** icon in the top-right corner of the graph.")
                                            st.pyplot(fig)

                                        elif view_mode == "Clustermap":
                                            if not corr_matrix.empty and corr_matrix.isnull().sum().sum() == 0:
                                                cluster_fig = sns.clustermap(
                                                    corr_matrix, cmap="PuBuGn", annot=True, fmt=".2f",
                                                    figsize=(fig_width, fig_height), annot_kws={"size": 14}
                                                )
                                                plt.setp(cluster_fig.ax_heatmap.get_xticklabels(), fontsize=14)
                                                plt.setp(cluster_fig.ax_heatmap.get_yticklabels(), fontsize=14)
                                                st.caption("📢 **Tip:** For better visualization, use the **↗️ Fullscreen** icon in the top-right corner of the graph.")
                                                st.pyplot(cluster_fig.fig)
                                            else:
                                                st.warning("⚠️ Clustermap cannot be generated due to insufficient or invalid correlation data.")

                                        st.info(f"ℹ️ Correlation Insights for High VIF Variables (|r| > {corr_threshold})")

                                        summary = []
                                        full_corr_matrix = st.session_state.df_for_vif.corr()

                                        high_vif_vars = st.session_state.vif_data[
                                            st.session_state.vif_data["VIF"] > vif_threshold
                                        ]["Features"].tolist()

                                        for var in full_corr_matrix.columns:
                                            if var in high_vif_vars:
                                                correlated_vars = [
                                                    f"{other} (IV={iv_map.get(other.replace('_woe',''), 'N/A'):.4f})"
                                                    for other in full_corr_matrix.columns
                                                    if other != var and abs(full_corr_matrix.loc[var, other]) > corr_threshold
                                                ]
                                                if correlated_vars:
                                                    summary.append({
                                                        "Variables": f"{var} (IV={iv_map.get(var.replace('_woe',''), 'N/A'):.4f})",
                                                        "Correlated With Variables": " | ".join(correlated_vars)
                                                    })

                                        if summary:
                                            summary_df = pd.DataFrame(summary)
                                            summary_df.index = range(1, len(summary_df) + 1)
                                            st.caption("📢 **Tip:** For better visualization, use the **↗️ Fullscreen** icon in the top-right corner of the table.")
                                            st.dataframe(summary_df, use_container_width=True)
                                        else:
                                            st.info(f"✅ No variable pairs found with correlation > {corr_threshold} among high VIF variables")
                                    else:
                                        st.info("✅ No valid high VIF variables or correlated partners found for correlation view.")

        if st.session_state.get("vif_removal_triggered", False):
            if st.button("👁️ View Aligned Data", key="btn_view_aligned"):
                st.caption("📘 Aligned Data After VIF-Based Removal")
                st.dataframe(st.session_state.cdata_aligned.head(), use_container_width=True)

        if st.session_state.get("vif_removal_triggered", False):
            style_expander_header()
            with st.expander("🧬 Significance Testing", expanded=False):
                st.caption("**👇 Use logistic regression to iteratively remove low-IV variables with high p-values (p > 0.05)**")

                if st.session_state.get("iv_sorted") is None:
                    if st.session_state.get("woe_iv_result") is not None:
                        _, iv_df, _ = st.session_state.woe_iv_result
                        if iv_df is not None and not iv_df.empty:
                            iv_df['IV Status'] = iv_df['Information Value'].apply(classify_iv_status)
                            iv_df.index = range(1, len(iv_df) + 1)
                            st.session_state.iv_df = iv_df
                            st.session_state.iv_sorted = iv_df.sort_values(by='Information Value', ascending=False)
                            st.session_state.show_iv_table = True
                        else:
                            st.error("❌ IV DataFrame is empty. Please run IV analysis first.")
                            st.stop()
                    else:
                        st.error("❌ woe_iv_result not found. Run WOE binning and IV analysis first.")
                        st.stop()

                sig_level = st.slider("Select significance level (p-value threshold):", 0.01, 0.10, 0.05, step=0.01)

                if st.button("✂️ Trim Insignificant Variables", type ="primary", key="btn_iv_backward"):
                    iv_table = st.session_state.iv_sorted.rename(columns={"Information Value": "IV"})

                    df_filtered, final_model, removed_vars = iv_based_backward_selection(
                        df_woe=st.session_state.final_woe_data,
                        iv_table=iv_table,
                        target_col="target",
                        sig_level=sig_level
                    )
                    removed_var_names = [item["Variable"] for item in removed_vars if isinstance(item, dict)]
                    woe_removed_vars = [var + "_woe" for var in removed_var_names]
                    st.session_state.final_woe_data = st.session_state.final_woe_data.drop(
                        columns=woe_removed_vars,
                        errors="ignore"
                    )

                    st.session_state.cdata_aligned = st.session_state.cdata_aligned.drop(
                        columns=removed_var_names,
                        errors="ignore"
                    )

                    st.session_state.iv_selection_result = {
                        "df_filtered": df_filtered,
                        "final_model": final_model,
                        "removed_vars": removed_vars,
                        "sig_level": sig_level
                    }

                if "iv_selection_result" in st.session_state:
                    result = st.session_state.iv_selection_result

                    if st.button("👁️ View Iteration Log", key="btn_view_iteration"):
                        removed_vars = result["removed_vars"]
                        if removed_vars:
                            removed_df = pd.DataFrame(removed_vars)
                            removed_df.index = [f"Step {i+1}" for i in range(len(removed_df))]

                            st.caption("🗑️ **Iterative Removal Log:**")
                            styled_log = style_removal_table(removed_df)
                            st.dataframe(styled_log, use_container_width=True)
                        else:
                            st.info("✅ No variables removed — all passed significance threshold.")

                    st.info("📊 Final Logistic Regression Summary")
                    st.code(result["final_model"].summary().as_text(), language="text")
                    st.success(f"✅ Remaining Variables: {', '.join(result['df_filtered'].drop(columns=['target']).columns)}")

                    if st.toggle("🧾 Show Dataset", value=False, key="toggle_raw_view"):
                        st.caption("**✅ Selected variables after triming insignificant variables**")
                        st.dataframe(st.session_state.cdata_aligned.head(), use_container_width=True)


        if "iv_selection_result" in st.session_state and st.session_state.iv_sorted is not None:
            style_expander_header()
            with st.expander("🎯 Select Top IV Variables", expanded=False):
                st.caption("**👇 Choose how many top-IV variables to retain for modeling**")

                iv_sorted = st.session_state.iv_sorted.copy()
                iv_filtered = iv_sorted[
                    iv_sorted['Variable'].isin(st.session_state.cdata_aligned.columns)
                ].sort_values(by='Information Value', ascending=False).reset_index(drop=True)

                iv_filtered['IV Status'] = iv_filtered['Information Value'].apply(classify_iv_status)
                iv_filtered.index = range(1, len(iv_filtered) + 1)

                max_vars = st.number_input(
                    "Allowed number of top-IV variables",
                    min_value=1,
                    max_value=len(iv_filtered),
                    value=len(iv_filtered),
                    step=1,
                    key="num_top_iv_vars"
                )

                top_iv_df = iv_filtered.head(max_vars)
                top_vars = top_iv_df['Variable'].tolist()
                st.session_state.cdata_filtered = st.session_state.cdata_aligned[top_vars + ['target']]
                woe_vars = [var + "_woe" for var in top_vars if var + "_woe" in st.session_state.final_woe_data.columns]

                st.session_state.cdata_woe_filtered = st.session_state.final_woe_data[woe_vars + ['target']]
                st.session_state.iv_selection_updated = True

                styled_iv = (
                    top_iv_df.style
                    .apply(lambda s: [iv_color(val) if s.name == 'IV Status' else '' for val in s], axis=0)
                    .format({'Information Value': '{:.4f}'})
                    .set_properties(**{
                        'text-align': 'center',
                        'padding': '6px',
                        'border': '1px solid #ddd',
                        'font-size': '13px'
                    })
                    .set_table_styles([
                        {'selector': 'thead th', 'props': [('font-weight', 'bold'), ('background-color', '#f1f1f1')]},
                        {'selector': 'tbody tr:hover', 'props': [('background-color', '#f9f9f9')]},
                        {'selector': 'td', 'props': [('border', '1px solid #eee')]},
                        {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%')]}
                    ])
                )

                st.caption("**🧾 Selected Variables**")
                st.dataframe(styled_iv, use_container_width=True)

                st.caption("**👇 Final selected variables for developing scorecard**")
                st.dataframe(st.session_state.cdata_filtered.head(), use_container_width=True)

                if st.toggle("📊 Show Selected Variable Graphs", value=False, key="toggle_selected_iv_graphs"):
                    st.caption("**📈 WOE Trend Graphs for Selected Variables**")

                    if st.session_state.get("woe_iv_result") is not None:
                        bins_rounded = round_bin_labels(st.session_state.woe_iv_result[0], decimals=2)
                        selected_vars = st.session_state.cdata_filtered.drop(columns=['target']).columns.tolist()

                        col1, col2 = st.columns([1, 3])
                        with col1:
                            rotation_angle = st.slider("↪️ X-tick Angle", 20, 90, 30, 5)
                        with col2:
                            rotation_vars = st.multiselect(
                                "🔄 Rotate X-ticks for:",
                                options=selected_vars,
                                default=st.session_state.get("vars_with_xtick_rotation", []),
                                key="rotate_xticks_selected"
                            )

                        for var in selected_vars:
                            if var not in bins_rounded:
                                continue
                            bdf = bins_rounded[var]
                            sc.woebin_plot({var: bdf})
                            fig = plt.gcf()
                            bin_count = bdf['bin'].nunique()
                            fig.set_size_inches(7, 4) if bin_count <= 3 else fig.set_size_inches(8, 4)

                            for ax in fig.axes:
                                y_values = [p.get_height() for p in ax.patches]
                                if y_values:
                                    ax.set_ylim(top=max(y_values) * 1.15)
                                labels = ax.get_xticklabels()
                                fig.canvas.draw()
                                overlaps = (
                                    bin_count > 4 and any(
                                        label.get_window_extent().width > (ax.get_xlim()[1] - ax.get_xlim()[0]) / len(labels)
                                        for label in labels
                                    )
                                )
                                if overlaps or var in rotation_vars:
                                    for label in labels:
                                        label.set_rotation(rotation_angle)
                                        label.set_ha('right')
                            plt.tight_layout()
                            st.pyplot(fig)

                st.success("🎉 Variables Selected! 🚀 Moving on to Scorecard Development")
                st.divider()

@st.cache_data(show_spinner="⏳ Generating scorecard bins...")
def generate_scorecard(data_filtered, breaks_list, points0, odds0, pdo):
    svar = sc.woebin(data_filtered, y="target", breaks_list=breaks_list)
    cdata_woe = sc.woebin_ply(data_filtered, bins=svar)

    # Logistic regression
    X = cdata_woe.drop(columns='target')
    y = cdata_woe['target']
    X_const = sm.add_constant(X)
    glm_fit = sm.GLM(y, X_const, family=sm.families.Binomial()).fit()

    # Scorecard
    card = sc.scorecard(svar, glm_fit, X.columns, points0=points0, odds0=odds0, pdo=pdo)
    scores = scorecard_ply(data_filtered, card)
    scores['target'] = data_filtered['target'].values

    return card, scores, glm_fit, svar, cdata_woe


if menu == "🛠️ Scorecard Development":
    if "iv_selection_result" in st.session_state and st.session_state.iv_sorted is not None:

        expander_state = True if "card" in st.session_state else False
        style_expander_header()
        with st.expander("🛠️ Scorecard Development", expanded=expander_state):

            st.subheader("⚙️ Scorecard Parameters")
            col1, col2, col3 = st.columns(3)
            with col1:
                points0 = st.number_input("🎯 Base Score (points0)", value=1060, step=1)
            with col2:
                odds0 = st.number_input("⚖️ Base Odds (odds0)", value=1/10.0, format="%.4f")
            with col3:
                pdo = st.number_input("📈 Points to Double Odds (PDO)", value=20, step=1)

            run_scorecard = st.button("⚙️ Generate Scorecard", type="primary", key="generate_scorecard_btn")

            if run_scorecard:
                st.session_state.iv_selection_updated = False
                breaks_list = st.session_state.get("breaks_list", None)

                card, scores, glm_fit, svar, cdata_woe = generate_scorecard(
                    st.session_state.cdata_filtered, breaks_list, points0, odds0, pdo
                )

                # Save in session state
                st.session_state.card = card
                st.session_state.scores = scores
                st.session_state.glm_fit = glm_fit
                st.session_state.svar_final = svar
                st.session_state.final_cdata_woe = cdata_woe

            if "card" in st.session_state and "scores" in st.session_state and "glm_fit" in st.session_state:
                card = st.session_state.card
                scores = st.session_state.scores
                glm_fit = st.session_state.glm_fit
                svar = st.session_state.svar_final
                cdata = st.session_state.cdata_filtered
                data = st.session_state.data.copy()

                st.info("📊 Logistic Regression Summary")
                st.code(glm_fit.summary().as_text(), language="text")

                st.subheader("🧾 Scorecard Table")
                selected_var = st.selectbox(
                    "📌 Choose variable to view scorecard bins:",
                    options=list(card.keys()),
                    key="scorecard_var_select"
                )
                if selected_var:
                    st.caption(f"🧾 Scorecard bins for `{selected_var}`")
                    st.dataframe(card[selected_var], use_container_width=True)

                output = io.BytesIO()
                merged_card = {}
                for var in svar.keys():
                    df_svar = svar[var]
                    df_points = card[var][['bin', 'points']]
                    df_merged = pd.merge(df_svar, df_points, on='bin', how='left')
                    merged_card[var] = df_merged

                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for var, df in merged_card.items():
                        df.to_excel(writer, sheet_name=var[:31], index=False)
                    if 'basepoints' in card:
                        pd.DataFrame(card['basepoints'], index=[0]).to_excel(writer, sheet_name='basepoints', index=False)

                output.seek(0)
                st.download_button(
                    label="📥 Download Scorecard Excel",
                    data=output,
                    file_name="Scorecard_with_points.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                def acc_func(probs, labels):
                    auc = roc_auc_score(labels, probs)
                    gini = 2 * auc - 1
                    return abs(gini) * 100

                def test_acc(data, target_col='target', score_col='score'):
                    acc = []
                    n = data.shape[0]
                    for i in range(1, 11):
                        np.random.seed(i)
                        sample_indices = np.random.choice(n, size=int(0.4 * n), replace=False)
                        sample = data.iloc[sample_indices]
                        gini_score = acc_func(sample[score_col], sample[target_col])
                        acc.append(gini_score)
                    return np.mean(acc), acc

                st.info("📈 Model Accuracy")
                col_dev, col_test = st.columns(2)

                with col_dev:
                    if st.button("🚀 Show Development Accuracy", type= "primary", key="dev_acc_btn"):
                        dev_acc = acc_func(scores['score'], cdata['target'])
                        st.metric("📊 Development Gini (%)", f"{dev_acc:.2f}%")

                with col_test:
                    if st.button("🧪 Show Testing Accuracy", type= "primary", key="test_acc_btn"):
                        test_gini, gini_list = test_acc(scores)
                        st.metric("🧪 Testing Gini (avg over 10 samples)", f"{test_gini:.2f}%")

                        gini_df = pd.DataFrame({
                            "Sample #": [f"Sample {i}" for i in range(1, 11)],
                            "Gini Score (%)": gini_list
                        })

                        st.caption("📊 Individual Gini scores across 10 random samples (40% each)")
                        st.dataframe(gini_df.style.format({"Gini Score (%)": "{:.2f}%"}), use_container_width=True)

                target_numeric = cdata['target'].cat.codes if hasattr(cdata['target'], 'cat') else cdata['target'].astype(int)
                bp = target_numeric.mean()
                basepoints_value = card['basepoints'].loc[0, 'points']
                adjusted_baseline_score = (np.log(bp / (1 - bp)) * 20 / np.log(2)) + basepoints_value

                min_score = scores["score"].min()
                max_score = scores["score"].max()

                    # Show in one line
                col1, col2, col3 = st.columns(3)
                col1.metric("⚖️ Adjusted Baseline Score", f"{adjusted_baseline_score:.2f}")
                col2.metric("⬇️ Minimum Score", f"{min_score:.2f}")
                col3.metric("⬆️ Maximum Score", f"{max_score:.2f}")

                if "show_graphs" not in st.session_state:
                    st.session_state.show_graphs = False

                if st.button("📈 Show Evaluation Graphs", key="show_graphs_btn"):
                    st.session_state.show_graphs = True
                if st.session_state.show_graphs:
                    X = st.session_state.final_cdata_woe.drop(columns="target")
                    X_const = sm.add_constant(X)
                    probs = st.session_state.glm_fit.predict(X_const)
                    y_true = st.session_state.final_cdata_woe["target"]

                    plot_choice = st.radio(
                        "📌 Choose curve to display:",
                        ["ROC Curve", "CAP Curve", "KS Curve"],
                        horizontal=True
                    )

                    # --- ROC Curve ---
                    if plot_choice == "ROC Curve":
                        fpr, tpr, _ = roc_curve(y_true, probs)
                        roc_auc = roc_auc_score(y_true, probs)

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=fpr,
                            y=tpr,
                            mode="lines+markers",
                            name=f"AUC = {roc_auc:.3f}",
                            marker=dict(
                                size=1.5,
                                color=tpr,
                                colorscale="Rainbow",
                                showscale=True,
                                colorbar=dict(thickness=8)
                            )
                        ))

                        fig.add_trace(go.Scatter(
                            x=[0, 1],
                            y=[0, 1],
                            mode="lines",
                            name="Random",
                            line=dict(dash="dash", color="gray", width=1.2)
                        ))

                        fig.update_layout(
                            title="📉 ROC Curve",
                            xaxis_title="False Positive Rate",
                            yaxis_title="True Positive Rate",
                            template="plotly_white",
                            width=980,
                            height=560,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            )
                        )

                        st.plotly_chart(fig, use_container_width=True)

                    # --- CAP Curve ---
                    elif plot_choice == "CAP Curve":
                        df_cap = pd.DataFrame({"y": y_true, "probs": probs}).sort_values(by="probs", ascending=False).reset_index(drop=True)
                        cum_pos = np.cumsum(df_cap["y"]) / df_cap["y"].sum()
                        pct_sample = np.arange(1, len(df_cap) + 1) / len(df_cap)

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=pct_sample, y=cum_pos,
                            mode="lines+markers", name="Model",
                            marker=dict(size=1.5, color=cum_pos, colorscale="Rainbow", showscale=True, colorbar=dict(thickness=8))
                        ))
                        fig.add_trace(go.Scatter(
                            x=[0, 1], y=[0, 1],
                            mode="lines", name="Random",
                            line=dict(dash="dash", color="gray", width=1.2)
                        ))
                        perfect_x = [0, df_cap["y"].sum()/len(df_cap), 1]
                        perfect_y = [0, 1, 1]
                        fig.add_trace(go.Scatter(
                            x=perfect_x, y=perfect_y,
                            mode="lines", name="Perfect",
                            line=dict(dash="dot", color="red", width=1.5)
                        ))
                        fig.update_layout(
                            title="📈 CAP Curve",
                            xaxis_title="Proportion of Sample",
                            yaxis_title="Proportion of Positives",
                            template="plotly_white",
                            width=980, height=560,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    elif plot_choice == "KS Curve":
                        df_ks = pd.DataFrame({"y": y_true, "p": probs}).sort_values("p", ascending=False).reset_index(drop=True)

                        n = len(df_ks)
                        total_bad = df_ks["y"].sum()
                        total_good = n - total_bad

                        cum_bad = np.cumsum(df_ks["y"]) / max(total_bad, 1)
                        cum_good = np.cumsum(1 - df_ks["y"]) / max(total_good, 1)

                        x = np.arange(1, n + 1) / n
                        x = np.insert(x, 0, 0.0)
                        cum_bad = np.insert(cum_bad, 0, 0.0)
                        cum_good = np.insert(cum_good, 0, 0.0)

                        ks_diff = np.abs(cum_bad - cum_good)
                        ks_idx = int(ks_diff.argmax())
                        ks_val = float(ks_diff[ks_idx])
                        ks_x = float(x[ks_idx])

                        fig = go.Figure()

                        fig.add_trace(go.Scatter(
                            x=x, y=cum_good, name="Cumulative Goods (y=0)",
                            line=dict(color="red", width=1.6)
                        ))
                        fig.add_trace(go.Scatter(
                            x=x, y=cum_bad, name="Cumulative Bads (y=1)",
                            line=dict(color="blue", width=1.6)
                        ))

                        fig.add_trace(go.Scatter(
                            x=[ks_x, ks_x],
                            y=[cum_good[ks_idx], cum_bad[ks_idx]],
                            mode="lines+text",
                            name=f"KS = {ks_val:.3f}",
                            line=dict(color="purple", width=2, dash="dot"),
                            text=[f"KS={ks_val:.3f}", ""],
                            textposition="top center"
                        ))

                        fig.add_trace(go.Scatter(
                            x=[ks_x], y=[cum_good[ks_idx]],
                            mode="markers", showlegend=False,
                            marker=dict(size=8, color="red", symbol="circle")
                        ))
                        fig.add_trace(go.Scatter(
                            x=[ks_x], y=[cum_bad[ks_idx]],
                            mode="markers", showlegend=False,
                            marker=dict(size=8, color="blue", symbol="circle")
                        ))

                        fig.update_layout(
                            title=f"📊 KS Curve (Max KS = {ks_val:.3f})",
                            xaxis_title="Proportion of Sample (sorted by prob. of BAD)",
                            yaxis_title="Cumulative Rate",
                            template="plotly_white",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            margin=dict(l=40, r=20, t=50, b=40),
                            width=980, height=560
                        )

                        st.plotly_chart(fig, use_container_width=True)

                    st.success("✅ Scorecard Developed Successfully!")

        def tb_func_dynamic(scores, labels, pred_probs, num_bins=10, min_score=None, max_score=None):
            tb = pd.DataFrame({
                'score': scores['score'],
                'pd': pred_probs,
                'target': labels.astype(int)
            })

            # Agar user custom min/max de to use karein warna auto
            if min_score is None:
                min_score = tb['score'].min()
            if max_score is None:
                max_score = tb['score'].max()

            # Create bin edges dynamically (equal-width bins)
            bin_edges = np.linspace(min_score, max_score, num_bins + 1)

            # Assign bins
            tb['Bins'] = pd.cut(tb['score'], bins=bin_edges, include_lowest=True)

            # Aggregate stats
            tot = tb.groupby('Bins')['target'].count().reset_index().rename(columns={'target': 'Total'})
            bads = tb.groupby('Bins')['target'].sum().reset_index().rename(columns={'target': 'Bads'})
            minpd = tb.groupby('Bins')['pd'].min().reset_index().rename(columns={'pd': 'Min_PD'})
            maxpd = tb.groupby('Bins')['pd'].max().reset_index().rename(columns={'pd': 'Max_PD'})

            tbf = tot.merge(bads, on='Bins').merge(minpd, on='Bins').merge(maxpd, on='Bins')
            tbf['Goods'] = tbf['Total'] - tbf['Bads']
            tbf['Avg_Default_Rate'] = tbf['Bads'] / tbf['Total']

            tbf = tbf[['Bins', 'Goods', 'Bads', 'Total', 'Avg_Default_Rate', 'Min_PD', 'Max_PD']]
            return tbf

        if "card" in st.session_state and "scores" in st.session_state and "glm_fit" in st.session_state:
            with st.expander("📐 Model Calibration", expanded=False):
                st.subheader("📊 Binning Analysis")

                # Step 1: Number of bins
                num_bins = st.number_input(
                    "Number of Bins", 
                    min_value=3, 
                    max_value=20, 
                    value=10, 
                    step=1
                )

                # Step 2: Auto bin edges
                min_score = st.session_state.scores['score'].min()
                max_score = st.session_state.scores['score'].max()
                auto_breaks = list(np.linspace(min_score, max_score, num_bins + 1))

                st.markdown("### ✂️ Adjust Bin Breaks")
                user_breaks = st.text_area(
                    "Enter bin edges (comma separated):",
                    value=", ".join([str(round(x, 2)) for x in auto_breaks])
                )

                # Step 3: Parse user breaks
                try:
                    breaks = [float(x.strip()) for x in user_breaks.split(",")]
                    breaks = sorted(list(set(breaks)))
                except:
                    st.error("⚠️ Please enter valid numeric breaks separated by commas.")
                    breaks = auto_breaks

                if len(breaks) < 2:
                    st.error("⚠️ At least 2 breaks are required.")
                else:
                    if st.button("Generate Binning Table"):
                        pd_train = st.session_state.glm_fit.predict(
                            sm.add_constant(st.session_state.final_cdata_woe.drop(columns=['target']))
                        )

                        tb = pd.DataFrame({
                            'score': st.session_state.scores['score'],
                            'pd': pd_train,
                            'target': st.session_state.cdata_filtered['target'].astype(int)
                        })

                        # Assign bins
                        tb['Bins'] = pd.cut(tb['score'], bins=breaks, include_lowest=True)
                        tb['Bins'] = tb['Bins'].astype(str)

                        # Aggregations
                        tot   = tb.groupby('Bins')['target'].count().reset_index().rename(columns={'target': 'Total'})
                        bads  = tb.groupby('Bins')['target'].sum().reset_index().rename(columns={'target': 'Bads'})
                        minpd = tb.groupby('Bins')['pd'].min().reset_index().rename(columns={'pd': 'Min_PD'})
                        maxpd = tb.groupby('Bins')['pd'].max().reset_index().rename(columns={'pd': 'Max_PD'})

                        # Merge
                        tbf = tot.merge(bads, on='Bins').merge(minpd, on='Bins').merge(maxpd, on='Bins')
                        tbf['Goods'] = tbf['Total'] - tbf['Bads']
                        tbf['Avg_Default_Rate'] = tbf['Bads'] / tbf['Total']

                        # Reorder columns
                        tbf = tbf[['Bins', 'Goods', 'Bads', 'Total', 'Avg_Default_Rate', 'Min_PD', 'Max_PD']]

                        # ✅ Sort bins descending (higher score → lower score)
                        tbf['bin_lower'] = tbf['Bins'].str.extract(r'\((.*),')[0].astype(float)
                        tbf = tbf.sort_values(by='bin_lower', ascending=False).drop(columns=['bin_lower'])
                        tbf.reset_index(drop=True, inplace=True)
                        tbf.index = tbf.index + 1
                        tbf.index.name = "S.No"

                        # Show table
                        st.dataframe(tbf, use_container_width=True)

                        # 📈 Line chart Total vs Bins
                        fig = px.line(
                            tbf, 
                            x="Bins", 
                            y="Total", 
                            markers=True,
                            title="📈 Total Count per Bin"
                        )
                        fig.update_layout(
                            xaxis_title="Bins (Score Ranges)",
                            yaxis_title="Total Count",
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Save in session
                        st.session_state.final_breaks = breaks
                        st.session_state.binning_table = tbf

        

        if "final_breaks" in st.session_state and "binning_table" in st.session_state:

            with st.expander("📊 Model Diagnostics", expanded=False):

                if "original_data" in st.session_state and not st.session_state.original_data.empty:
                    df = st.session_state.original_data.copy()

                    st.markdown("""
                    ⚠️ **Important:** Please select the following columns in this exact order:  
                    1️⃣ Loan Number (Unique ID)  
                    2️⃣ Limit  
                    3️⃣ M+6 (Observation Window column)  
                    4️⃣ Target Variable  
                    """)

                    selected_cols = st.multiselect(
                        "Select 4 columns in order (Loan Number, Limit, M+6, Target):",
                        options=df.columns.tolist(),
                        default=None
                    )

                    if len(selected_cols) != 4:
                        st.warning("⚠️ Please select exactly 4 columns in the correct order.")
                    else:
                        xdt1 = df[selected_cols].copy()
                        xdt1 = xdt1.rename(columns={selected_cols[3]: "target"})  # ✅ rename last col to target

                        xdt1['score'] = st.session_state.scores['score']
                        xdt1['pd'] = st.session_state.glm_fit.predict(
                            sm.add_constant(st.session_state.final_cdata_woe.drop(columns=['target']))
                        )

                        st.session_state.xdt = xdt1
                        st.session_state.selected_cols = selected_cols  # ✅ save here

                        st.success("✅ Dataframe `xdt` created successfully!")
                        st.write("📊 Preview of `xdt`")
                        st.dataframe(xdt1.head(), use_container_width=True)

                if "binning_table" in st.session_state and "final_breaks" in st.session_state and "xdt" in st.session_state:
                    xdt = st.session_state.xdt.copy()
                    breaks = st.session_state.final_breaks
                    tb = st.session_state.binning_table

                    # Get observation window column dynamically
                    obs_col = st.session_state.selected_cols[2].lower()  # 3rd col from user selection

                    bin_labels = list(range(len(breaks)-1, 0, -1))  

                    # Temporary bin rating
                    xdt['bin_rating'] = pd.cut(
                        xdt['score'],
                        bins=breaks,
                        labels=bin_labels,
                        include_lowest=True
                    ).astype(float)

                    # Final dataframe with single `rating`
                    xdft2 = (
                        xdt
                        .rename(columns=lambda c: c.lower())
                        .dropna(subset=[obs_col])
                        .assign(
                            rating=lambda df: np.select(
                                [
                                    df[obs_col] >= 89,
                                    df[obs_col] == 59,
                                    df[obs_col] == 29,
                                ],
                                [9, 8, 7],
                                default=df['bin_rating']
                            )
                        )
                        .drop(columns=['bin_rating'])   # ✅ remove extra column
                        .loc[lambda df: df['rating'] <= 6]
                    )

                    st.session_state.xdft2 = xdft2
                    st.success(f"✅ Rating assigned based on Final Binning Table + `{obs_col}` rules")
                    st.dataframe(xdft2.head(), use_container_width=True)

                if "xdft2" in st.session_state:
                    xdft2 = st.session_state.xdft2.copy()

                    # ✅ Rename target column (ensure 4th col is target)
                    xdft2 = xdft2.rename(columns={xdft2.columns[3]: "target"})

                    # Aggregations
                    a = xdft2.groupby('rating', as_index=False)['target'].count()
                    b = xdft2.groupby('rating', as_index=False)['limit'].sum()

                    f = pd.merge(a, b, on='rating')

                    # Distributions
                    f['count_distr'] = (f['target'] / f['target'].sum()) * 100
                    f['limit_distr'] = (f['limit'] / f['limit'].sum()) * 100

                    # Format numbers
                    f['limit'] = f['limit'].round(0).astype(int)
                    f['limit'] = f['limit'].map('{:,}'.format)
                    f['count_distr'] = f['count_distr'].round(2)
                    f['limit_distr'] = f['limit_distr'].round(2)

                    # ✅ UI Display
                    st.subheader("📊 Rating-wise Distribution")
                    st.dataframe(f, use_container_width=True)

                    # ✅ Optional: Bar chart visualization
                    fig = px.bar(
                        f, 
                        x="rating", 
                        y=["count_distr", "limit_distr"], 
                        barmode="group",
                        title="📈 Distribution of Count and Limit by Rating"
                    )
                    fig.update_layout(
                        xaxis_title="Rating",
                        yaxis_title="Distribution (%)"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                if "xdft2" in st.session_state:
                    bt = st.session_state.xdft2.copy()

                    if st.button("📌 Run Binomial Test"):
                        # ---------------- Table 1 ----------------
                        avg_pd = bt.groupby('rating', as_index=False)['pd'].mean()
                        avg_pd.rename(columns={'rating': 'Ratings', 'pd': 'avg_pd'}, inplace=True)

                        N, D = [], []
                        for i in range(1, 7):
                            N.append(len(bt[bt['rating'] == i]))
                            D.append(len(bt[(bt['rating'] == i) & (bt['target'] == 1)]))

                        table1 = avg_pd.copy()
                        table1['N'] = N
                        table1['D'] = D
                        table1 = table1.sort_values('Ratings').reset_index(drop=True)

                        # ---------------- Table 2 ----------------
                        pv = []
                        for i in range(1, 7):
                            n = len(bt[bt['rating'] == i])
                            d = len(bt[(bt['rating'] == i) & (bt['target'] == 1)])
                            pd_val = avg_pd.loc[avg_pd['Ratings'] == i, 'avg_pd'].values[0]

                            if d > 0:
                                btest = binomtest(d - 1, n, pd_val, alternative="less")
                                pval = 1 - btest.pvalue
                            else:
                                pval = 1.0  

                            pv.append(pval)

                        table2 = pd.DataFrame({
                            "Ratings": range(1, 7),
                            "p-value": [round(v, 5) for v in pv]
                        })
                        table2["Result"] = table2["p-value"].apply(lambda x: "TRUE" if x <= 0.01 else "FALSE")
                        table2 = table2.reset_index(drop=True)

                        # ---------------- Merge Tables ----------------
                        merged_table = pd.merge(table1, table2, on="Ratings", how="inner")

                        # ---------------- Show Merged Table ----------------
                        st.subheader("📊 Binomial Test with Counts & Avg PD")
                        st.dataframe(merged_table, use_container_width=True)
