from __future__ import annotations

import secrets
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from auth import (
    authenticate_user,
    create_employee_user,
    is_valid_email,
    is_valid_employee_id,
    validate_password_strength,
)
from model import (
    ATTENDANCE_HISTORY_COLUMNS,
    DATA_FILE,
    WEIGHTS,
    build_reward_analysis,
    export_powerbi_results,
)


LOGIN_ROUTE = "/login"
SIGNUP_ROUTE = "/employee/signup"
MANAGER_DASHBOARD_ROUTE = "/manager/dashboard"
EMPLOYEE_DASHBOARD_ROUTE = "/employee/dashboard"
SESSION_TTL_SECONDS = 45 * 60


st.set_page_config(
    page_title="AI HR Reward System",
    layout="wide",
)


@st.cache_data
def get_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    return build_reward_analysis(DATA_FILE)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1180px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #0f766e;
            letter-spacing: 0;
        }
        div[data-testid="stSidebar"] {
            border-right: 1px solid #d9e8e2;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.7rem 0.85rem;
        }
        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 8px;
            transition: all 0.2s;
        }
        .auth-shell {
            max-width: 460px;
            margin: 0 auto;
            padding-top: 2rem;
        }
        .auth-title {
            font-size: 1.65rem;
            font-weight: 700;
            color: #14b8a6;
            margin-bottom: 0.15rem;
        }
        .auth-subtitle {
            color: #94a3b8;
            margin-bottom: 1rem;
        }
        @media (max-width: 640px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .auth-shell {
                padding-top: 0.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_score(value: float) -> str:
    return f"{value:.2f}"


def get_route() -> str:
    route = st.query_params.get("route", LOGIN_ROUTE)
    if isinstance(route, list):
        return route[0] if route else LOGIN_ROUTE
    return route or LOGIN_ROUTE


def set_route(route: str) -> None:
    st.query_params["route"] = route
    st.session_state["route"] = route
    st.rerun()


def queue_toast(message: str) -> None:
    st.session_state["toast_message"] = message


def show_queued_toast() -> None:
    message = st.session_state.pop("toast_message", None)
    if message:
        st.toast(message)


def start_session(user: dict[str, object]) -> None:
    st.session_state["auth_session"] = {
        "token": secrets.token_urlsafe(32),
        "user": user,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }


def get_current_user() -> dict[str, object] | None:
    session = st.session_state.get("auth_session")
    if not session:
        return None

    if time.time() > session.get("expires_at", 0):
        st.session_state.pop("auth_session", None)
        queue_toast("Session expired. Please sign in again.")
        return None

    session["expires_at"] = time.time() + SESSION_TTL_SECONDS
    return session["user"]


def logout() -> None:
    st.session_state.pop("auth_session", None)
    queue_toast("Signed out successfully.")
    set_route(LOGIN_ROUTE)


def show_auth_header(subtitle: str) -> None:
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">AI HR Reward System</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="auth-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def close_auth_header() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def show_login_page() -> None:
    show_auth_header("Secure login for managers and employees")

    with st.container(border=True):
        st.subheader("Login")
        
        show_password = st.toggle("Show password", key="login_show_pwd")
        
        with st.form("login_form", border=False):
            email = st.text_input(
                "Email",
                value=st.session_state.pop("prefill_email", ""),
                placeholder="name@company.com",
            )
            password = st.text_input(
                "Password",
                type="default" if show_password else "password",
                placeholder="Enter password",
            )

            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                email_ok = is_valid_email(email)
                password_ok = bool(password)
                login_ready = email_ok and password_ok

                if not login_ready:
                    if not email_ok:
                        st.error("Use a valid company email format.")
                    if not password_ok:
                        st.error("Password is required.")
                else:
                    with st.spinner("Signing in..."):
                        user = authenticate_user(email, password)
                        time.sleep(0.35)

                    if not user:
                        st.toast("Login failed. Check your email and password.")
                        st.error("Invalid email or password.")
                    else:
                        start_session(user)
                        route = (
                            MANAGER_DASHBOARD_ROUTE
                            if user["role"] == "manager"
                            else EMPLOYEE_DASHBOARD_ROUTE
                        )
                        queue_toast("Login successful.")
                        set_route(route)

        st.divider()
        if st.button("New employee sign up", use_container_width=True):
            set_route(SIGNUP_ROUTE)

        with st.expander("Demo accounts"):
            st.write("Manager: manager@company.com / Manager@123")
            st.write("Employee: aarav.sharma@company.com / Employee@123")

    close_auth_header()


def show_signup_page() -> None:
    show_auth_header("New employee account setup")

    with st.container(border=True):
        st.subheader("Employee Sign-Up")
        
        show_password = st.toggle("Show password", key="signup_show_pwd")
        
        with st.form("signup_form", border=False):
            full_name = st.text_input("Full Name", placeholder="Aditi Sharma")
            employee_id = st.text_input("Employee ID", placeholder="EMP031")
            email = st.text_input("Email", placeholder="employee@company.com")
            department = st.selectbox(
                "Department",
                [
                    "Select department",
                    "Engineering",
                    "Sales",
                    "HR",
                    "Operations",
                    "Finance",
                    "Marketing",
                    "Customer Success",
                ],
            )
            
            pwd_type = "default" if show_password else "password"
            password = st.text_input("Password", type=pwd_type, placeholder="Minimum 8 characters")
            confirm_password = st.text_input("Confirm Password", type=pwd_type, placeholder="Re-enter password")

            submitted = st.form_submit_button("Create employee account", type="primary", use_container_width=True)

            if submitted:
                password_issues = validate_password_strength(password) if password else []
                full_name_ok = len(full_name.strip()) >= 2
                employee_id_ok = is_valid_employee_id(employee_id)
                email_ok = is_valid_email(email)
                department_ok = department != "Select department"
                password_ok = bool(password) and not password_issues
                passwords_match = password == confirm_password

                signup_ready = (
                    full_name_ok
                    and employee_id_ok
                    and email_ok
                    and department_ok
                    and password_ok
                    and passwords_match
                )

                if not signup_ready:
                    if not full_name_ok:
                        st.error("Full name must be at least 2 characters.")
                    if not employee_id_ok:
                        st.error("Employee ID must be 3-20 letters, numbers, or hyphens.")
                    if not email_ok:
                        st.error("Use a valid email address.")
                    if not department_ok:
                        st.error("Please select a department.")
                    if password_issues:
                        st.error("Password needs " + ", ".join(password_issues) + ".")
                    elif not password_ok:
                        st.error("Password is required.")
                    if not passwords_match:
                        st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating secure account..."):
                        ok, message, _ = create_employee_user(
                            full_name=full_name,
                            employee_id=employee_id,
                            email=email,
                            department=department,
                            password=password,
                        )
                        time.sleep(0.35)

                    if ok:
                        st.session_state["prefill_email"] = email
                        queue_toast(message)
                        set_route(LOGIN_ROUTE)
                    else:
                        st.toast(message)
                        st.error(message)

        st.divider()
        if st.button("Already have an account? Back to login", use_container_width=True):
            set_route(LOGIN_ROUTE)

        st.caption("Manager accounts are admin-created only and cannot be made here.")

    close_auth_header()


def render_sidebar(user: dict[str, object]) -> None:
    st.sidebar.title("AI HR Reward System")
    st.sidebar.write(user["full_name"])
    st.sidebar.caption(f"{str(user['role']).title()} | {user['email']}")
    st.sidebar.divider()

    if user["role"] == "manager":
        if st.sidebar.button("Manager Dashboard", use_container_width=True):
            set_route(MANAGER_DASHBOARD_ROUTE)
    else:
        if st.sidebar.button("Employee Dashboard", use_container_width=True):
            set_route(EMPLOYEE_DASHBOARD_ROUTE)

    st.sidebar.divider()
    st.sidebar.caption("Scoring weights")
    st.sidebar.write(f"Attendance: {WEIGHTS['attendance_percent']:.0%}")
    st.sidebar.write(f"Performance: {WEIGHTS['project_completion_rate']:.0%}")
    st.sidebar.write(f"Peer feedback: {WEIGHTS['peer_feedback_score']:.0%}")
    st.sidebar.divider()

    if st.sidebar.button("Sign out", use_container_width=True):
        logout()


def employee_dashboard(df: pd.DataFrame, user: dict[str, object]) -> None:
    st.title("Employee Dashboard")

    employee_id = str(user["employee_id"]).upper()
    matched = df[df["employee_id"].str.upper() == employee_id]

    if matched.empty:
        st.subheader(str(user["full_name"]))
        st.info("Your account is active. Reward data will appear after HR imports your first performance cycle.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Full Name": user["full_name"],
                        "Employee ID": user["employee_id"],
                        "Email": user["email"],
                        "Department": user["department"],
                        "Role": user["role"],
                    }
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        return

    employee = matched.iloc[0]

    st.subheader(f"{employee['employee_name']} | {employee['role']}")
    st.caption(f"Department: {employee['department']} | Employee ID: {employee['employee_id']}")

    score_col, points_col, badge_col, cluster_col = st.columns(4)
    score_col.metric("Total Score", format_score(employee["total_score"]))
    points_col.metric("Reward Points", int(employee["reward_points"]))
    badge_col.metric("Badge Earned", employee["badge_earned"])
    cluster_col.metric("Fairness Group", employee["fairness_group"])

    st.divider()

    chart_col, logic_col = st.columns([1.1, 0.9])

    with chart_col:
        st.subheader("Historical Attendance")
        attendance_history = pd.DataFrame(
            {
                "month": ["Jan", "Feb", "Mar", "Apr"],
                "attendance_percent": [
                    employee[column] for column in ATTENDANCE_HISTORY_COLUMNS
                ],
            }
        )
        st.line_chart(
            attendance_history,
            x="month",
            y="attendance_percent",
            height=260,
        )

        st.subheader("Current Reward Decision")
        st.write(employee["reward_action"])
        st.info(employee["motivation_trigger"])

    with logic_col:
        st.subheader("Reward Logic")
        st.write(
            "Total Score = "
            f"({WEIGHTS['attendance_percent']} x Attendance) + "
            f"({WEIGHTS['project_completion_rate']} x Performance) + "
            f"({WEIGHTS['peer_feedback_score']} x Feedback)"
        )

        components = pd.DataFrame(
            [
                {
                    "Metric": "Attendance",
                    "Raw Score": employee["attendance_percent"],
                    "Weight": WEIGHTS["attendance_percent"],
                    "Weighted Points": employee["attendance_component"],
                },
                {
                    "Metric": "Performance",
                    "Raw Score": employee["project_completion_rate"],
                    "Weight": WEIGHTS["project_completion_rate"],
                    "Weighted Points": employee["performance_component"],
                },
                {
                    "Metric": "Peer Feedback",
                    "Raw Score": employee["peer_feedback_score"],
                    "Weight": WEIGHTS["peer_feedback_score"],
                    "Weighted Points": employee["feedback_component"],
                },
            ]
        )
        st.dataframe(components, use_container_width=True, hide_index=True)

        st.subheader("Fairness Check")
        st.write(employee["fairness_note"])
        st.write(f"Peer-group average score: {employee['cluster_average_score']:.2f}")
        st.write(f"Difference from peer group: {employee['score_vs_peer_group']:+.2f}")

        if employee["needs_manager_review"]:
            st.warning(employee["anomaly_flags"])
        else:
            st.success("No anomaly flags for this record.")

    st.divider()
    st.subheader("Canva AI Certificate and Badge Placeholders")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Asset Type": "Badge",
                    "Placeholder": employee["canva_badge_placeholder"],
                },
                {
                    "Asset Type": "Certificate",
                    "Placeholder": employee["canva_certificate_placeholder"],
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


def managerial_view(df: pd.DataFrame, cluster_summary: pd.DataFrame) -> None:
    st.title("Managerial View")

    average_score = df["total_score"].mean()
    gold_count = (df["badge_earned"] == "Gold Performance Badge").sum()
    review_count = df["needs_manager_review"].sum()
    average_points = df["reward_points"].mean()

    metric_cols = st.columns(4)
    metric_cols[0].metric("Average Score", f"{average_score:.2f}")
    metric_cols[1].metric("Average Reward Points", f"{average_points:.0f}")
    metric_cols[2].metric("Gold Badges", int(gold_count))
    metric_cols[3].metric("Review Cases", int(review_count))

    st.subheader("AI Productivity Clusters")
    scatter = (
        alt.Chart(df)
        .mark_circle(size=120, opacity=0.78)
        .encode(
            x=alt.X("attendance_percent:Q", title="Attendance %"),
            y=alt.Y("project_completion_rate:Q", title="Project Completion %"),
            color=alt.Color("fairness_group:N", title="Fairness Group"),
            size=alt.Size("peer_feedback_score:Q", title="Peer Feedback"),
            tooltip=[
                "employee_id",
                "employee_name",
                "department",
                "total_score",
                "badge_earned",
                "fairness_group",
                "anomaly_flags",
            ],
        )
        .properties(height=380)
        .interactive()
    )
    st.altair_chart(scatter, use_container_width=True)

    st.subheader("Cluster Summary")
    st.dataframe(cluster_summary, use_container_width=True, hide_index=True)

    st.subheader("Reward Decisions")
    st.dataframe(
        df[
            [
                "employee_id",
                "employee_name",
                "department",
                "total_score",
                "reward_points",
                "badge_earned",
                "bonus_amount",
                "fairness_group",
                "needs_manager_review",
                "fairness_note",
            ]
        ].sort_values("total_score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Challenge Review: Technical Issues and Outliers")
    review_cases = df[df["needs_manager_review"]][
        [
            "employee_id",
            "employee_name",
            "department",
            "attendance_percent",
            "project_completion_rate",
            "peer_feedback_score",
            "anomaly_flags",
            "fairness_note",
        ]
    ]
    if review_cases.empty:
        st.success("No technical issues or outliers detected.")
    else:
        st.warning("Automatic rewards are paused for these records until a manager reviews them.")
        st.dataframe(review_cases, use_container_width=True, hide_index=True)

    st.subheader("Department Transparency")
    department_summary = (
        df.groupby("department")
        .agg(
            employees=("employee_id", "count"),
            average_score=("total_score", "mean"),
            average_points=("reward_points", "mean"),
            review_cases=("needs_manager_review", "sum"),
        )
        .reset_index()
    )
    department_summary[["average_score", "average_points"]] = department_summary[
        ["average_score", "average_points"]
    ].round(2)
    st.dataframe(department_summary, use_container_width=True, hide_index=True)


def export_and_assets_view(df: pd.DataFrame) -> None:
    st.title("Power BI Export and Canva AI Assets")

    output_path = Path(__file__).with_name("powerbi_reward_export.csv")
    if st.button("Create Power BI Export", type="primary"):
        export_powerbi_results(df, output_path)
        st.toast("Power BI export created.")
        st.success(f"Export created: {output_path}")

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Current Analysis CSV",
        data=csv_bytes,
        file_name="powerbi_reward_export.csv",
        mime="text/csv",
    )

    st.subheader("Power BI Ready Columns")
    export_preview = df[
        [
            "employee_id",
            "employee_name",
            "department",
            "total_score",
            "reward_points",
            "badge_earned",
            "bonus_amount",
            "fairness_group",
            "needs_manager_review",
            "anomaly_flags",
            "motivation_trigger",
        ]
    ]
    st.dataframe(export_preview, use_container_width=True, hide_index=True)

    st.subheader("Replaceable Canva AI Placeholders")
    asset_table = (
        df[
            [
                "badge_earned",
                "canva_badge_placeholder",
                "canva_certificate_placeholder",
            ]
        ]
        .drop_duplicates()
        .sort_values("badge_earned")
    )
    st.dataframe(asset_table, use_container_width=True, hide_index=True)


def show_manager_dashboard() -> None:
    df, cluster_summary = get_analysis()
    dashboard_tab, export_tab = st.tabs(["Dashboard", "Power BI and Canva Assets"])
    with dashboard_tab:
        managerial_view(df, cluster_summary)
    with export_tab:
        export_and_assets_view(df)


def show_employee_dashboard(user: dict[str, object]) -> None:
    df, _ = get_analysis()
    employee_dashboard(df, user)


def protect_route(route: str, user: dict[str, object] | None) -> None:
    if route in {LOGIN_ROUTE, SIGNUP_ROUTE}:
        return

    if not user:
        queue_toast("Please sign in to continue.")
        set_route(LOGIN_ROUTE)

    if route == MANAGER_DASHBOARD_ROUTE and user["role"] != "manager":
        queue_toast("Manager access is restricted.")
        set_route(EMPLOYEE_DASHBOARD_ROUTE)

    if route == EMPLOYEE_DASHBOARD_ROUTE and user["role"] != "employee":
        queue_toast("Employee dashboard is restricted to employee accounts.")
        set_route(MANAGER_DASHBOARD_ROUTE)


def main() -> None:
    apply_theme()
    show_queued_toast()

    route = get_route()
    user = get_current_user()
    protect_route(route, user)

    if route == LOGIN_ROUTE:
        if user:
            target = (
                MANAGER_DASHBOARD_ROUTE
                if user["role"] == "manager"
                else EMPLOYEE_DASHBOARD_ROUTE
            )
            set_route(target)
        show_login_page()
        return

    if route == SIGNUP_ROUTE:
        if user:
            logout()
        show_signup_page()
        return

    if not user:
        show_login_page()
        return

    render_sidebar(user)

    if route == MANAGER_DASHBOARD_ROUTE:
        show_manager_dashboard()
    elif route == EMPLOYEE_DASHBOARD_ROUTE:
        show_employee_dashboard(user)
    else:
        target = (
            MANAGER_DASHBOARD_ROUTE
            if user["role"] == "manager"
            else EMPLOYEE_DASHBOARD_ROUTE
        )
        set_route(target)


if __name__ == "__main__":
    main()
