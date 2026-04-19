import streamlit as st
import pandas as pd
from datetime import datetime
import functions_AI as func

st.header("YEPN Coffee Catch Up Matching ☕")

# --- Step 1: Upload historic matches ---
historic_file = st.file_uploader("Upload historic matches CSV")
if not historic_file:
    st.stop()

historic_matches = pd.read_csv(historic_file)
st.markdown("**Historic matches** (last 10 entries):")
st.dataframe(historic_matches.tail(10))

# --- Step 2: Upload email listserv ---
email_file = st.file_uploader("Upload email listserv CSV")
if not email_file:
    st.stop()

email_list = pd.read_csv(email_file).rename(columns={"Region - closest to you": "region"})

# Clean up
email_list = email_list[email_list["Pause Coffee Catch-up"] != "Yes"]
email_list["region"] = email_list["region"].str.strip().str.lower().fillna("unknown")
email_list["full_name"] = email_list["First Name"] + " " + email_list["Last Name"]
email_list["LAST_CHANGED"] = pd.to_datetime(email_list["LAST_CHANGED"], format="mixed")
email_list = (email_list
              .sort_values("LAST_CHANGED", ascending=False)
              .drop_duplicates(subset="full_name", keep="first"))

# Split into mentors and mentees
# If someone selected both, they become mentor only (one email)
mentors_df = email_list[email_list["Do you want to join Coffee Catchup as a Mentor?"] == "Yes"]
mentees_df = email_list[
    (email_list["Do you want to join Coffee Catchup as a Mentee?"] == "Yes") &
    (~email_list["full_name"].isin(mentors_df["full_name"]))
]

mentor_list = mentors_df[["full_name", "region"]].to_dict(orient="records")
mentee_list = mentees_df[["full_name", "region"]].to_dict(orient="records")

st.markdown(f"**{len(mentor_list)} mentors** and **{len(mentee_list)} mentees** found.")

# --- Step 3: Settings and run ---
random_seed = st.number_input("Random seed", value=42, step=1, format="%d")

latest_round = historic_matches["round"].max()
current_date = datetime.today().strftime("%Y%m%d")

pairs_df = func.create_matches(mentor_list, mentee_list, historic_matches, random_seed)

# Validation: no one appears on both sides of a mentee-mentee match
mm = pairs_df[pairs_df["type"] == "mentee-mentee"]
assert len(set(mm["mentor"]).intersection(set(mm["mentee"]))) == 0, "Duplicate in mentee-mentee pairs!"

st.markdown(f"**{len(pairs_df)} pairs created** "
            f"({len(pairs_df[pairs_df.type=='mentor-mentee'])} mentor-mentee, "
            f"{len(pairs_df[pairs_df.type=='mentee-mentee'])} mentee-mentee)")
st.dataframe(pairs_df)

# --- Step 4: Enrich and download ---
new_matches = func.add_contact_details(pairs_df, email_list)
new_and_historic = func.append_to_historic(new_matches, historic_matches, latest_round, current_date)
mailchimp_df = func.build_mailchimp_upload(new_matches, email_list, current_date)

st.markdown("**New + historic matches** (current round only):")
st.dataframe(new_and_historic[new_and_historic["round"] == new_and_historic["round"].max()])

st.download_button(
    "Download new & historic matches CSV",
    data=new_and_historic.to_csv(index=False),
    file_name=f"all_matches_{current_date}.csv",
)

st.markdown("**Mailchimp re-upload file:**")
st.dataframe(mailchimp_df)

st.download_button(
    "Download Mailchimp re-upload CSV",
    data=mailchimp_df.to_csv(index=False),
    file_name=f"mailchimp_reupload_{current_date}.csv",
)
