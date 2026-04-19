import random
import pandas as pd
import streamlit as st


def already_matched(a, b, historical_pairs):
    return f"{a}-{b}" in historical_pairs or f"{b}-{a}" in historical_pairs


def create_matches(mentors, mentees, historic_matches, random_seed=42):
    """
    Match mentors to mentees (then mentees to mentees for leftovers).
    Avoids historical pairs. Prioritises same-region matches.
    Returns a DataFrame with columns: mentor, mentee, type.
    """
    random.seed(random_seed)

    historical_pairs = set(historic_matches["pairs"].values)

    # Shuffle for variety
    mentors = mentors.copy()
    mentees = mentees.copy()
    random.shuffle(mentors)
    random.shuffle(mentees)

    pairs = []
    unmatched_mentors = list(mentors)
    unmatched_mentees = list(mentees)

    # --- Pass 1: Same-region mentor-mentee ---
    remaining_mentors, remaining_mentees = [], []
    used_mentees = set()

    for mentor in unmatched_mentors:
        matched = False
        for i, mentee in enumerate(unmatched_mentees):
            if i in used_mentees:
                continue
            if mentor["region"] == mentee["region"] and not already_matched(
                mentor["full_name"], mentee["full_name"], historical_pairs
            ):
                pairs.append((mentor["full_name"], mentee["full_name"], "mentor-mentee"))
                used_mentees.add(i)
                matched = True
                break
        if not matched:
            remaining_mentors.append(mentor)

    remaining_mentees = [m for i, m in enumerate(unmatched_mentees) if i not in used_mentees]

    # --- Pass 2: Cross-region mentor-mentee ---
    still_unmatched_mentors = []
    used_mentees2 = set()

    for mentor in remaining_mentors:
        matched = False
        for i, mentee in enumerate(remaining_mentees):
            if i in used_mentees2:
                continue
            if not already_matched(mentor["full_name"], mentee["full_name"], historical_pairs):
                pairs.append((mentor["full_name"], mentee["full_name"], "mentor-mentee"))
                used_mentees2.add(i)
                matched = True
                break
        if not matched:
            still_unmatched_mentors.append(mentor)

    remaining_mentees = [m for i, m in enumerate(remaining_mentees) if i not in used_mentees2]

    # --- Pass 3: Mentee-mentee (same region first) ---
    # Sort: put same-region pairs together by grouping on region
    remaining_mentees.sort(key=lambda x: x["region"])
    used_mm = set()

    for i, m1 in enumerate(remaining_mentees):
        if i in used_mm:
            continue
        for j, m2 in enumerate(remaining_mentees):
            if j <= i or j in used_mm:
                continue
            if m1["region"] == m2["region"] and not already_matched(
                m1["full_name"], m2["full_name"], historical_pairs
            ):
                pairs.append((m1["full_name"], m2["full_name"], "mentee-mentee"))
                used_mm.add(i)
                used_mm.add(j)
                break

    # Pass 4: Cross-region mentee-mentee for any still unmatched
    leftover = [m for i, m in enumerate(remaining_mentees) if i not in used_mm]
    used_lo = set()

    for i, m1 in enumerate(leftover):
        if i in used_lo:
            continue
        for j, m2 in enumerate(leftover):
            if j <= i or j in used_lo:
                continue
            if not already_matched(m1["full_name"], m2["full_name"], historical_pairs):
                pairs.append((m1["full_name"], m2["full_name"], "mentee-mentee"))
                used_lo.add(i)
                used_lo.add(j)
                break

    matched_names = {name for p in pairs for name in p[:2]}
    unmatched_mentors = [m["full_name"] for m in mentors if m["full_name"] not in matched_names]
    unmatched_mentees = [m["full_name"] for m in mentees if m["full_name"] not in matched_names]

    if len(unmatched_mentors)>0:
        st.markdown(f"Unmatched mentors: {unmatched_mentors}")
    if len(unmatched_mentees)>0:
        st.markdown(f"Unmatched mentees: {unmatched_mentees}")
 


    return pd.DataFrame(pairs, columns=["mentor", "mentee", "type"])


def add_contact_details(pairs_df, email_list):
    """Merge email/job/org details onto the pairs DataFrame."""
    cols = ["full_name", "region", "Email Address", "Job Title", "Organisation"]
    rename = {"Email Address": "email_address", "Job Title": "job_title", "Organisation": "organisation"}
    ref = email_list[cols].rename(columns=rename)

    df = pairs_df.merge(ref, left_on="mentor", right_on="full_name").rename(
        columns={c: f"{c}_mentor" for c in ["region", "email_address", "job_title", "organisation"]}
    ).drop(columns="full_name")

    df = df.merge(ref, left_on="mentee", right_on="full_name").rename(
        columns={c: f"{c}_mentee" for c in ["region", "email_address", "job_title", "organisation"]}
    ).drop(columns="full_name")

    df.fillna("(unknown)", inplace=True)
    df["within_region"] = df["region_mentor"] == df["region_mentee"]

    return df[["mentor", "mentee",
               "email_address_mentor", "email_address_mentee",
               "region_mentor", "region_mentee",
               "job_title_mentor", "job_title_mentee",
               "organisation_mentor", "organisation_mentee",
               "within_region", "type"]]


def append_to_historic(new_matches, historic_matches, latest_round, date_str):
    """Format new matches and append to the historic matches DataFrame."""
    df = new_matches.copy()
    df["round"] = latest_round + 1
    df["date"] = date_str
    df["pairs"] = df["mentor"] + " - " + df["mentee"]
    df["mentee_type"] = df["type"].str.split("-").str[1]
    df.rename(columns={"mentee": "mentee_name", "mentor": "mentor_name"}, inplace=True)
    keep = ["mentee_name", "mentor_name", "within_region", "round", "date", "pairs", "mentee_type", "type"]
    return pd.concat([historic_matches, df[keep]], ignore_index=True)


def build_mailchimp_upload(new_matches, email_list, date_str):
    """Build the Mailchimp re-upload DataFrame."""
    base_cols = ["Email Address", "First Name", "Last Name", "Region - closest to you",
                 "Do you want to join Coffee Catchup as a Mentee?",
                 "Do you want to join Coffee Catchup as a Mentor?"]

    def make_half(match_col, email_col, name_col, job_col, org_col, match_type_fn):
        half = new_matches[[email_col, name_col, job_col, org_col, "within_region", "type"]].copy()
        half.rename(columns={
            name_col: "full_name_match",
            email_col: "email_address_match",
            job_col: "job_title_match",
            org_col: "organisation_match",
            "within_region": "within_region_match",
        }, inplace=True)
        half["match_type"] = half["type"].apply(match_type_fn)
        half["match_round"] = date_str
        half["_join_email"] = new_matches[match_col]
        return pd.merge(email_list, half, how="inner",
                        left_on="Email Address", right_on="_join_email").drop(columns="_join_email")

    part1 = make_half(
        "email_address_mentor",
        "email_address_mentee", "mentee", "job_title_mentee", "organisation_mentee",
        lambda t: "mentee",
    )
    part2 = make_half(
        "email_address_mentee",
        "email_address_mentor", "mentor", "job_title_mentor", "organisation_mentor",
        lambda t: "mentor" if t == "mentor-mentee" else "mentee",
    )

    out = pd.concat([part1, part2])
    out["Region - closest to you"] = out["region"].str.capitalize()

    return out[base_cols + ["full_name_match", "email_address_match",
                            "job_title_match", "organisation_match",
                            "within_region_match", "type", "match_type", "match_round"]]