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
        email_list['LAST_CHANGED'] = pd.to_datetime(email_list.LAST_CHANGED, format='mixed')
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

        # MANUALLY MATCH

        # Initialization of forced lists
        # mentors
        if 'forced_mentor_list' not in st.session_state:
            st.session_state['forced_mentor_list'] = []
            forced_mentor_list = []
        else:
            forced_mentor_list = st.session_state['forced_mentor_list']
        # mentees
        if 'forced_mentee_list' not in st.session_state:
            st.session_state['forced_mentee_list'] = []
            forced_mentee_list = []
        else:
            forced_mentee_list = st.session_state['forced_mentee_list']
        
        # submit changes
        with st.form("OPTIONAL: manually match mentors-mentees"):
            forced_mentor = st.selectbox('Select mentor',mentor_name_list)
            forced_mentee = st.selectbox('Select mentee',mentee_name_list)
            submitted = st.form_submit_button("Submit")
            if submitted:
                forced_mentor_list.append(forced_mentor)
                forced_mentee_list.append(forced_mentee)
                st.markdown(f'Mentor list: {forced_mentor_list}')
                st.markdown(f'Mentee list: {forced_mentee_list}')
                st.session_state['forced_mentor_list'] = forced_mentor_list
                st.session_state['forced_mentee_list'] = forced_mentee_list
        
        clear_lists = st.button('Clear lists')
        if clear_lists:
            st.session_state['forced_mentor_list'] = []
            forced_mentor_list = st.session_state['forced_mentor_list']
            st.markdown(f'Mentor list: {forced_mentor_list}')
            st.session_state['forced_mentee_list'] = []
            forced_mentee_list = st.session_state['forced_mentee_list']
            st.markdown(f'Mentee list: {forced_mentee_list}')
                

        #TO DO: FILTER FORCED MENTEES/MENTORS FROM THE EMAIL LIST AND MANUALLY MATCH THEM
        #CONTINUE THE REST OF THE REGULAR MATCHING PROCESS
        #CONCAT THE TWO RESULTS

        
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

        #save the data
        st.markdown("Save the new and historic matches (sample table of only most recent matches):")  
    
        #Note: the code prioritises being matched by region rather than mentor-mentee (to prioritise in person meet ups)
        new_matches = func.add_data_to_new_matches(all_pairs_regional,email_list) 
        current_date = datetime.today().strftime('%Y%m%d')
        new_and_historic = func.save_new_matches_into_historic(current_date,latest_round,new_matches,historic_matches)
        st.dataframe(new_and_historic[new_and_historic['round'] == new_and_historic['round'].max()])
        st.download_button(label = 'Download new and historic matches csv',data = new_and_historic.to_csv(index=False),file_name=f'all_matches_{current_date}.csv')
      

        # join new_matches back onto email list (for upload into mailchimp)
        # first join on mentor email address to get information about their mentees
        mentor_match_df = new_matches[['email_address_mentor','mentee_name','email_address_mentee','job_title_mentee','organisation_mentee','within_region','type']]
        mentor_match_df = mentor_match_df.rename(columns={'mentee_name':'full_name_match',
                                                          'email_address_mentee':'email_address_match',
                                                          'job_title_mentee':'job_title_match',
                                                          'organisation_mentee':'organisation_match',
                                                          'within_region':'within_region_match',
                                                          })
        
        # since this is the df for mentors, it will always be mentee
        mentor_match_df['match_type'] = 'mentee'
        mentor_match_df['match_round'] = current_date
        mailchimp_upload_part_1 = pd.merge(email_list,
                                    mentor_match_df,
                                    how='inner',left_on=['Email Address'],right_on=['email_address_mentor']).drop(columns=['email_address_mentor'])
        # then join on mentee email address to get information about their mentors (or mentees if it's a mentee-mentee match)
        mentee_match_df = new_matches[['email_address_mentee','mentor_name','email_address_mentor','job_title_mentor','organisation_mentor','within_region','type']]
        mentee_match_df = mentee_match_df.rename(columns={'mentor_name':'full_name_match',
                                                          'email_address_mentor':'email_address_match',
                                                          'job_title_mentor':'job_title_match',
                                                          'organisation_mentor':'organisation_match',
                                                          'within_region':'within_region_match',
                                                          })
        # since this is the match for mentees, it can be mentor OR mentee (if it is a mentee-mentee match)
        mentee_match_df['match_type'] = mentee_match_df.type.apply(lambda x: 'mentor' if x == 'mentor-mentee' else 'mentee' if x == 'mentee-mentee' else '')
        mentee_match_df['match_round'] = current_date

        mailchimp_upload_part_2 = pd.merge(email_list,
                                    mentee_match_df,
                                    how='inner',left_on=['Email Address'],right_on=['email_address_mentee']).drop(columns=['email_address_mentee'])
        
        mailchimp_upload = pd.concat([mailchimp_upload_part_1,mailchimp_upload_part_2])

        # re-capitalise the first letter
        mailchimp_upload['region'] = mailchimp_upload.region.str.capitalize()
        # rename region back to Region - closest to you
        mailchimp_upload = mailchimp_upload.rename(columns={'region':'Region - closest to you'})

       # drop any columns that could be mis-formatted and aren't necessary
        mailchimp_upload = mailchimp_upload[['Email Address','First Name','Last Name','Region - closest to you',
                                       'Do you want to join Coffee Catchup as a Mentee?','Do you want to join Coffee Catchup as a Mentor?',
                                       'full_name_match','email_address_match','job_title_match','organisation_match','within_region_match','type','match_type','match_round']]

        st.markdown('File to re-upload to Mailchimp')
        st.dataframe(mailchimp_upload)
        # download mailchimp upload file
        st.download_button(label = 'Download csv to re-upload to Mailchimp',data = mailchimp_upload.to_csv(index=False),file_name=f'mailchimp_reupload_{current_date}.csv')


