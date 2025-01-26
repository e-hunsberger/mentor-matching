import streamlit as st
import pandas as pd
import functions as func
st.header('YEPN Coffe Catch Up Matching ☕')


#user upload historic matches file
uploaded_file = st.file_uploader("Upload historic matches csv")

if uploaded_file is not None:
    # Read the uploaded CSV file into a DataFrame
    historic_matches = pd.read_csv(uploaded_file)
    
    # Display the DataFrame in the Streamlit app
    st.markdown("Historic matches:")
    st.dataframe(historic_matches)

    
    uploaded_file2 = st.file_uploader("Upload email listerv data")

    if uploaded_file2 is not None:
        # Read the uploaded CSV file into a DataFrame
        email_list = pd.read_csv(uploaded_file2).rename(columns={'Region - closest to you':'region'})
        #fill any na in the region column with 'Unknown'
        email_list["region"] = email_list["region"].fillna('Unknown')
        #rename columns, sort and only store the latest entry for duplicate names
        email_list['full_name'] = email_list['First Name'] + ' ' + email_list['Last Name']
        email_list['LAST_CHANGED'] = pd.to_datetime(email_list.LAST_CHANGED, format='%m/%d/%Y %H:%M')
        email_list = email_list.sort_values(by='LAST_CHANGED',ascending=False)
        #drop duplicates of the same full name by sorting by the last date they changed their info and taking the first entry
        email_list = email_list.drop_duplicates(subset='full_name', keep='first')

        #since duplicates have been removed, this will take the latest mentor/mentee status selected by the participant
        mentees = email_list[email_list['Do you want to join Coffee Catchup as a Mentee?'] == 'Yes'].copy()
        #store the region 
        mentee_data_list = mentees[['full_name','region']].to_dict(orient="records")
        mentee_name_list = mentees.full_name.unique()
        mentors = email_list[email_list['Do you want to join Coffee Catchup as a Mentor?'] == 'Yes'].copy()
        mentor_data_list = mentors[['full_name','region']].to_dict(orient="records")
        mentor_name_list = mentors.full_name.unique()
        
        # Display the DataFrame in the Streamlit app
        st.markdown("Email listserv data:")
        st.dataframe(email_list)

        #get a unique list of the regions to match people by region 
        region_list = email_list.region.unique()
        #get the latest round number for tracking 
        latest_round = historic_matches['round'].max()
        
        #create the matches 
        all_pairs_regional = func.create_matches(latest_round,historic_matches,region_list,mentee_data_list,mentor_data_list)
        st.markdown("New matches:")
        st.dataframe(all_pairs_regional)

        #save the data
        st.markdown("Save the new matches:")  
    
        #Note: the code prioritises being matched by region rather than mentor-mentee (to prioritise in person meet ups)
        new_matches = func.add_data_to_new_matches(all_pairs_regional,email_list)      
        date_input = int(st.number_input(label='Input the date label (eg 202501010201 for Jan to Feb of 2025)'))
        st.download_button(label = 'Download matches',data = new_matches.to_csv(index=False),file_name=f"new_matches_{date_input}.csv")

        #add date and concatenate with historic matches
        #give an error if the user hasn't changed the date yet
        if date_input == 0:
            st.warning("Set the date before downloading!")

        new_and_historic = func.save_new_matches_into_historic(date_input,latest_round,new_matches,historic_matches)
        st.download_button(label = 'Download new and historic matches csv',data = new_and_historic.to_csv(index=False),file_name=f'all_matches_{date_input}.csv')
    



