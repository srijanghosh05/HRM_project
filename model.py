from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "2")

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


DATA_FILE = Path(__file__).with_name("data.csv")
POWER_BI_EXPORT_FILE = Path(__file__).with_name("powerbi_reward_export.csv")

FEATURE_COLUMNS = [
    "attendance_percent",
    "project_completion_rate",
    "peer_feedback_score",
]

ATTENDANCE_HISTORY_COLUMNS = [
    "attendance_jan",
    "attendance_feb",
    "attendance_mar",
    "attendance_apr",
]

WEIGHTS = {
    "attendance_percent": 0.40,
    "project_completion_rate": 0.40,
    "peer_feedback_score": 0.20,
}


@dataclass(frozen=True)
class RewardRule:
    minimum_score: float
    badge: str
    reward_action: str
    bonus_amount: str
    canva_badge_placeholder: str
    canva_certificate_placeholder: str


REWARD_RULES = [
    RewardRule(
        90,
        "Gold Performance Badge",
        "Annual performance bonus and public recognition",
        "15 percent bonus",
        "assets/badge_gold.png",
        "assets/certificate_gold.png",
    ),
    RewardRule(
        80,
        "Silver Performance Badge",
        "Quarterly spot bonus and manager appreciation note",
        "10 percent bonus",
        "assets/badge_silver.png",
        "assets/certificate_silver.png",
    ),
    RewardRule(
        70,
        "Bronze Performance Badge",
        "Learning credit and team recognition",
        "5 percent bonus",
        "assets/badge_bronze.png",
        "assets/certificate_bronze.png",
    ),
    RewardRule(
        60,
        "Progress Badge",
        "Skill-building plan with monthly review",
        "Recognition points",
        "assets/badge_progress.png",
        "assets/certificate_progress.png",
    ),
    RewardRule(
        0,
        "Coaching Support Badge",
        "Personalized improvement plan",
        "No bonus yet",
        "assets/badge_support.png",
        "assets/certificate_support.png",
    ),
]


def load_hr_data(path: Path | str = DATA_FILE) -> pd.DataFrame:
    """Load the simulated HR reward dataset."""
    return pd.read_csv(path)


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def clean_hr_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize numeric HR metrics into a 0-100 scale."""
    cleaned = df.copy()
    _require_columns(cleaned, FEATURE_COLUMNS + ATTENDANCE_HISTORY_COLUMNS)

    for column in FEATURE_COLUMNS + ATTENDANCE_HISTORY_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0)
        cleaned[column] = cleaned[column].clip(lower=0, upper=100)

    cleaned["reward_history_points"] = pd.to_numeric(
        cleaned.get("reward_history_points", 0),
        errors="coerce",
    ).fillna(0)
    return cleaned


def calculate_reward_points(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the transparent weighted reward formula."""
    scored = clean_hr_data(df)
    scored["attendance_component"] = (
        scored["attendance_percent"] * WEIGHTS["attendance_percent"]
    )
    scored["performance_component"] = (
        scored["project_completion_rate"] * WEIGHTS["project_completion_rate"]
    )
    scored["feedback_component"] = (
        scored["peer_feedback_score"] * WEIGHTS["peer_feedback_score"]
    )
    scored["total_score"] = (
        scored["attendance_component"]
        + scored["performance_component"]
        + scored["feedback_component"]
    ).round(2)
    scored["reward_points"] = (scored["total_score"] * 10).round().astype(int)

    reward_details = scored["total_score"].apply(_select_reward_rule)
    scored["badge_earned"] = reward_details.apply(lambda rule: rule.badge)
    scored["reward_action"] = reward_details.apply(lambda rule: rule.reward_action)
    scored["bonus_amount"] = reward_details.apply(lambda rule: rule.bonus_amount)
    scored["canva_badge_placeholder"] = reward_details.apply(
        lambda rule: rule.canva_badge_placeholder
    )
    scored["canva_certificate_placeholder"] = reward_details.apply(
        lambda rule: rule.canva_certificate_placeholder
    )
    scored["motivation_trigger"] = scored.apply(generate_motivation_message, axis=1)
    return scored


def _select_reward_rule(score: float) -> RewardRule:
    for rule in REWARD_RULES:
        if score >= rule.minimum_score:
            return rule
    return REWARD_RULES[-1]


def generate_motivation_message(row: pd.Series) -> str:
    """Rule-based Copilot-style coaching message for low or dropping scores."""
    score = float(row["total_score"])
    metrics = {
        "attendance": float(row["attendance_percent"]),
        "project completion": float(row["project_completion_rate"]),
        "peer feedback": float(row["peer_feedback_score"]),
    }
    lowest_metric = min(metrics, key=metrics.get)
    strongest_metric = max(metrics, key=metrics.get)

    if score >= 70:
        return (
            f"Keep the momentum: your strongest area is {strongest_metric}. "
            "Maintain consistency to move toward the next reward tier."
        )

    if score >= 60:
        return (
            f"You are close to the Bronze tier. Focus on {lowest_metric} this month "
            f"while using your strength in {strongest_metric} to rebuild points."
        )

    return (
        f"Motivation trigger: your reward score needs support. Start with "
        f"{lowest_metric}, schedule a manager check-in, and set one weekly target."
    )


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Flag technical issues and outliers that require manager review."""
    reviewed = df.copy()
    anomaly_flags: list[list[str]] = []

    z_scores = (
        reviewed[FEATURE_COLUMNS] - reviewed[FEATURE_COLUMNS].mean()
    ) / reviewed[FEATURE_COLUMNS].std(ddof=0)

    for idx, row in reviewed.iterrows():
        flags: list[str] = []

        if row["attendance_percent"] <= 5 and row["project_completion_rate"] >= 85:
            flags.append("Technical issue: high performance with near-zero attendance")

        if row["attendance_percent"] >= 90 and row["project_completion_rate"] < 65:
            flags.append("Review needed: high attendance but low completion")

        if row["project_completion_rate"] >= 80 and row["peer_feedback_score"] < 55:
            flags.append("Review needed: performance-feedback mismatch")

        statistical_outliers = [
            column.replace("_", " ")
            for column in FEATURE_COLUMNS
            if abs(float(z_scores.loc[idx, column])) >= 2.25
        ]
        if statistical_outliers:
            flags.append(
                "Statistical outlier in " + ", ".join(statistical_outliers)
            )

        anomaly_flags.append(flags)

    reviewed["anomaly_flags"] = [
        "; ".join(flags) if flags else "Clear" for flags in anomaly_flags
    ]
    reviewed["needs_manager_review"] = reviewed["anomaly_flags"] != "Clear"
    return reviewed


def cluster_for_fairness(
    df: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cluster employees so reward decisions can be compared within peer groups."""
    clustered = df.copy()
    if len(clustered) < 2:
        clustered["fairness_cluster"] = 0
        clustered["fairness_group"] = "Single employee review group"
        summary = _build_cluster_summary(clustered)
        return clustered, summary

    cluster_count = min(n_clusters, len(clustered))
    scaler = StandardScaler()
    features = scaler.fit_transform(clustered[FEATURE_COLUMNS])
    model = KMeans(n_clusters=cluster_count, random_state=random_state, n_init=10)
    clustered["fairness_cluster"] = model.fit_predict(features)

    cluster_rank = (
        clustered.groupby("fairness_cluster")["total_score"]
        .mean()
        .sort_values(ascending=False)
    )
    names = [
        "High productivity peer group",
        "Consistent productivity peer group",
        "Growth support peer group",
    ]
    label_map = {
        cluster_id: names[min(position, len(names) - 1)]
        for position, cluster_id in enumerate(cluster_rank.index)
    }
    clustered["fairness_group"] = clustered["fairness_cluster"].map(label_map)
    clustered["cluster_average_score"] = clustered.groupby("fairness_cluster")[
        "total_score"
    ].transform("mean").round(2)
    clustered["score_vs_peer_group"] = (
        clustered["total_score"] - clustered["cluster_average_score"]
    ).round(2)
    clustered["fairness_note"] = clustered.apply(_fairness_note, axis=1)
    return clustered, _build_cluster_summary(clustered)


def _fairness_note(row: pd.Series) -> str:
    if row["needs_manager_review"]:
        return "Pause automatic reward until the anomaly is reviewed."

    if row["score_vs_peer_group"] >= 5:
        return "Above peer-group average; strong candidate for recognition."

    if row["score_vs_peer_group"] <= -5:
        return "Below peer-group average; use coaching before reward escalation."

    return "Aligned with peer-group average; reward decision is consistent."


def _build_cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["fairness_cluster", "fairness_group"])
        .agg(
            employees=("employee_id", "count"),
            average_score=("total_score", "mean"),
            average_attendance=("attendance_percent", "mean"),
            average_completion=("project_completion_rate", "mean"),
            average_feedback=("peer_feedback_score", "mean"),
            review_cases=("needs_manager_review", "sum"),
        )
        .reset_index()
        .sort_values("average_score", ascending=False)
    )
    numeric_columns = [
        "average_score",
        "average_attendance",
        "average_completion",
        "average_feedback",
    ]
    summary[numeric_columns] = summary[numeric_columns].round(2)
    return summary


def build_reward_analysis(path: Path | str = DATA_FILE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the full scoring, AI clustering, anomaly, and fairness pipeline."""
    raw = load_hr_data(path)
    scored = calculate_reward_points(raw)
    reviewed = detect_anomalies(scored)
    clustered, cluster_summary = cluster_for_fairness(reviewed)
    return clustered, cluster_summary


def export_powerbi_results(
    df: pd.DataFrame,
    output_path: Path | str = POWER_BI_EXPORT_FILE,
) -> Path:
    """Export the analyzed reward data in a flat CSV format for Power BI."""
    output = Path(output_path)
    export_columns = [
        "employee_id",
        "employee_name",
        "department",
        "role",
        "attendance_percent",
        "project_completion_rate",
        "peer_feedback_score",
        "total_score",
        "reward_points",
        "badge_earned",
        "bonus_amount",
        "reward_action",
        "fairness_group",
        "cluster_average_score",
        "score_vs_peer_group",
        "needs_manager_review",
        "anomaly_flags",
        "fairness_note",
        "motivation_trigger",
        "canva_badge_placeholder",
        "canva_certificate_placeholder",
    ]
    df.to_csv(output, columns=export_columns, index=False)
    return output


if __name__ == "__main__":
    analysis, summary = build_reward_analysis()
    export_path = export_powerbi_results(analysis)
    print("Reward analysis completed.")
    print(f"Employees analyzed: {len(analysis)}")
    print(f"Manager review cases: {int(analysis['needs_manager_review'].sum())}")
    print(f"Power BI export: {export_path}")
    print("\nCluster summary:")
    print(summary.to_string(index=False))
