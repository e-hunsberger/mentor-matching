import streamlit as st
import pandas as pd
import functions as func
from datetime import datetime

st.header('YEPN Coffe Catch Up Matching ☕')


#user upload historic matches file
uploaded_file = st.file_uploader("Upload historic matches csv")


if uploaded_file is not None:
    try:
        # Read the file as a CSV
        historic_matches = pd.read_csv(uploaded_file)
        # Display the DataFrame in the Streamlit app
        st.markdown("Historic matches (sample of last 10 entries):")
        st.dataframe(historic_matches.tail(10))
    except Exception as e:
        st.error(f"Error reading file: {e}")

    
    uploaded_file2 = st.file_uploader("Upload email listerv data")

    if uploaded_file2 is not None:
        # Read the uploaded CSV file into a DataFrame
        email_list = pd.read_csv(uploaded_file2).rename(columns={'Region - closest to you':'region'})

        #remove anyone who has selected 'Yes' for pause coffee catch up 
        email_list = email_list[email_list['Pause Coffee Catch-up'] != 'Yes']


        #remove any whitespace in the region
        email_list['region'] = email_list['region'].str.strip()
        #convert to lowercase
        email_list['region'] = email_list['region'].str.lower()

        #fill any na in the region column with 'Unknown'
        email_list["region"] = email_list["region"].fillna('Unknown')
        #rename columns, sort and only store the latest entry for duplicate names
        email_list['full_name'] = email_list['First Name'] + ' ' + email_list['Last Name']
        email_list['LAST_CHANGED'] = pd.to_datetime(email_list.LAST_CHANGED, format='%Y-%m-%d %H:%M:%S')
        email_list = email_list.sort_values(by='LAST_CHANGED',ascending=False)
        #drop duplicates of the same full name by sorting by the last date they changed their info and taking the first entry
        email_list = email_list.drop_duplicates(subset='full_name', keep='first')

        # #TEMP FOR MISTAKE: ONE OFF REMOVE EVERYONE FROM ROUND 11 FROM the email list
        # remove_list1 = historic_matches[historic_matches['round'] == 11].mentee_name.values
        # remove_list2 = historic_matches[historic_matches['round'] == 11].mentor_name.values
        # email_list = email_list[~email_list.full_name.isin(remove_list1)]
        # email_list = email_list[~email_list.full_name.isin(remove_list2)]
        # st.markdown(remove_list1)
        # st.markdown(remove_list2)


        #select mentors and mentees
        #since duplicates have been removed, this will take the latest mentor/mentee status selected by the participant
        #select mentors
        mentors = email_list[email_list['Do you want to join Coffee Catchup as a Mentor?'] == 'Yes'].copy()
        mentor_data_list = mentors[['full_name','region']].to_dict(orient="records")
        mentor_name_list = mentors.full_name.unique()
        #select mentees
        mentees = email_list[email_list['Do you want to join Coffee Catchup as a Mentee?'] == 'Yes'].copy()
        #DECISION POINT: remove anyone who selected to be a mentor AND a mentee. Force them to be a mentee ONLY (otherwise they would get two emails)
        #remove mentees that are in the mentor list from the mentee list
        mentees = mentees[~mentees.full_name.isin(mentors.full_name)]

        #store the region 
        mentee_data_list = mentees[['full_name','region']].to_dict(orient="records")
        mentee_name_list = mentees.full_name.unique()

        
        # Display the DataFrame in the Streamlit app
        st.markdown("Email listserv data:")
        st.dataframe(email_list)

        #get a unique list of the regions to match people by region 
        region_list = email_list.region.unique()
        #get the latest round number for tracking 
        latest_round = historic_matches['round'].max()

        #slider for random seed
        random_seed = st.number_input(label='Random seed',value=42, step=1, format="%d")
        
        #create the matches 
        all_pairs_regional = func.create_matches(latest_round,historic_matches,region_list,mentee_data_list,mentor_data_list,random_seed)
        
        #validation: check that for mentee-mentee matches, if someone is in the mentee column, they are not in the mentor column
        check_mentee = all_pairs_regional[all_pairs_regional.type == 'mentee-mentee']
        assert len(set(check_mentee.mentee).intersection(set(check_mentee.mentor))) == 0

        st.markdown("New matches:")
        st.dataframe(all_pairs_regional)

        #save the data
        st.markdown("Save the new matches:")  
    
        #Note: the code prioritises being matched by region rather than mentor-mentee (to prioritise in person meet ups)
        new_matches = func.add_data_to_new_matches(all_pairs_regional,email_list)      
        current_date = datetime.today().strftime('%Y%m%d')
        #first download mentor-mentee matches
        st.download_button(label = 'Download new mentor-mentee matches',
                           data = new_matches[new_matches.type == 'mentor-mentee']
                           .to_csv(index=False),file_name=f"new_mentor-mentee_matches_{current_date}.csv")
        #then download mentee-mentee matches (for a separate email)
        st.download_button(label = 'Download new mentee-mentee matches',
                           data = new_matches[new_matches.type == 'mentee-mentee']
                           .to_csv(index=False),file_name=f"new_mentee-mentee_matches_{current_date}.csv")

        new_and_historic = func.save_new_matches_into_historic(current_date,latest_round,new_matches,historic_matches)
        st.download_button(label = 'Download new and historic matches csv',data = new_and_historic.to_csv(index=False),file_name=f'all_matches_{current_date}.csv')
    



