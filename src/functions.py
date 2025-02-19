import random
import pandas as pd
import streamlit as st

def match_pairs_from_lists(primary_list, secondary_list, historical_matches):
    """
    Match items from two lists while avoiding historical matches. 
    Returns a list of new pairs and unmatched items from both lists.
    """
    historical_pairs = set(historical_matches['pairs'].values)
    new_pairs = []
    unmatched_primary = set(primary_list)
    unmatched_secondary = set(secondary_list)

    for primary, secondary in zip(primary_list, secondary_list):
        pair_key = f"{primary}-{secondary}"
        if pair_key not in historical_pairs and (primary != secondary):
            new_pairs.append((primary, secondary))
            unmatched_primary.discard(primary)
            unmatched_secondary.discard(secondary)
            #in the case it's a mentee-mentee match, try discarding the name from both the primary and secondary 
            #otherwise mentees may get selected twice
            try:
                unmatched_primary.discard(secondary)
                unmatched_secondary.discard(primary)
            except:
                st.markdown('error')
    
    return new_pairs, list(unmatched_primary), list(unmatched_secondary)

def split_list(lst):
    mid = len(lst) // 2
    return lst[:mid], lst[mid:]

def create_matches(latest_round,matches,region_list,mentee_data_list,mentor_data_list):
    
    #Shuffle lists
    random.shuffle(mentee_data_list)
    random.shuffle(mentor_data_list)

    #prioritise mentees that were last in a mentee-mentee match
    priority_mentees = set(matches[(matches['type'] == 'mentee-mentee') & (matches['round'] == latest_round)]['mentee_name'].values)

    all_pairs_regional = pd.DataFrame()
    unmatched_mentees_regional = []
    unmatched_mentors_regional = []
    remaining_mentees_final = []
    mentee_count = 0 
    #loop through the regions to prioritise grouping by region first 
    for region in region_list:
        #filter the prioritised mentees and mentors by region
        mentee_name_list = [item['full_name'] for item in mentee_data_list if item['region'] == region]
        mentor_name_list = [item['full_name'] for item in mentor_data_list if item['region'] == region]
        #find the mentee-mentee matches in the latest round
        # Separate mentees into priority and non-priority lists
        priority_mentee_list = [mentee for mentee in mentee_name_list if mentee in priority_mentees]
        non_priority_mentee_list = [mentee for mentee in mentee_name_list if mentee not in priority_mentees]

        # Mentor-Mentee Matching
        # Match priority mentees first
        mentor_mentee_pairs_priority, remaining_mentors, remaining_priority_mentees = match_pairs_from_lists(
            mentor_name_list, priority_mentee_list, matches,
        )

        # Match non-priority mentees next
        mentor_mentee_pairs_regular, remaining_mentors, remaining_non_priority_mentees = match_pairs_from_lists(
            remaining_mentors, non_priority_mentee_list, matches, 
        )

        # Combine mentor-mentee pairs
        mentor_mentee_pairs = mentor_mentee_pairs_priority + mentor_mentee_pairs_regular

        # Combine remaining mentees into mentee-mentee matches
        remaining_mentees = remaining_priority_mentees + remaining_non_priority_mentees

        # Mentee-Mentee Matching
        # divide the list into two (otherwise people may get matched twice)
        remaining_mentees_1, remaining_mentees_2 = split_list(remaining_mentees)
        # # Create a shuffled copy of remaining mentees for pairing
        # remaining_mentees_shuffled = remaining_mentees.copy()
        # random.shuffle(remaining_mentees_shuffled)

        mentee_mentee_pairs, _, unmatched_mentees = match_pairs_from_lists(
            remaining_mentees_1, remaining_mentees_2, matches, 
        )
        
        mentee_count = mentee_count + ((len(mentee_mentee_pairs)*2) + len(mentor_mentee_pairs))


        # Collect mentees and mentors unmatched by region
        unmatched_mentees_regional = unmatched_mentees_regional + unmatched_mentees
        unmatched_mentors_regional = unmatched_mentors_regional + remaining_mentors

        # Combine results
        all_pairs = mentor_mentee_pairs + mentee_mentee_pairs

        # Convert to DataFrame
        pairs_df = pd.DataFrame(all_pairs, columns=["mentor", "mentee"])
        pairs_df["type"] = (
            ["mentor-mentee"] * len(mentor_mentee_pairs) + ["mentee-mentee"] * len(mentee_mentee_pairs)
        )

        # Store the results
        all_pairs_regional = pd.concat([all_pairs_regional,pairs_df])

    #at the end, match the mentors and mentees from different regions and add them to the dataframe
    for i,mentor in enumerate(unmatched_mentors_regional):
        if i < len(unmatched_mentees_regional):
            row = [mentor,unmatched_mentees_regional[i],'mentor-mentee']
            all_pairs_regional = pd.concat([all_pairs_regional,pd.DataFrame(columns= ['mentor','mentee','type'],data = [row])])


    #update unmatched_mentees
    for mentee in mentee_data_list:
        if mentee['full_name'] not in all_pairs_regional.mentee.values:
            if mentee['full_name'] not in all_pairs_regional.mentor.values:
                remaining_mentees_final = remaining_mentees_final + [mentee['full_name']]
                
    # Validation
    assert len(mentee_data_list) - mentee_count <= 1 #0 if even, 1 if odd


    return all_pairs_regional

def add_data_to_new_matches(all_pairs_regional,email_list):
    email_list_columns = ['full_name','region','Email Address','Job Title','Organisation']
    column_dict = {'Email Address':'email_address','Job Title':'job_title','Organisation':'organisation'}
    #add email and region data to the matches
    df = pd.merge(all_pairs_regional,
                  email_list[email_list_columns]
                  .rename(columns=column_dict),
                  left_on='mentor',right_on='full_name',suffixes=("_mentor", "_mentor"))
    df = pd.merge(df,email_list[email_list_columns]
                  .rename(columns=column_dict),
                  left_on='mentee',right_on='full_name',suffixes=("_mentor", "_mentee"))
    #replace any NANs with (we don't know sorry!)
    df.fillna("(we don't know sorry, you'll have to ask them!)",inplace=True)
    st.dataframe(df)
    return df[['mentee','mentor','email_address_mentee','email_address_mentor','region_mentee','region_mentor','job_title_mentee','job_title_mentor','organisation_mentee','organisation_mentor','type']]

def save_new_matches_into_historic(date_input,latest_round,new_matches,historic_matches):
    #format the new matches to fit the historic matches df and combine them
    new_matches['within_region'] = new_matches.region_mentor == new_matches.region_mentee
    new_matches['round'] = latest_round + 1 
    new_matches['date'] = date_input
    new_matches['pairs'] = new_matches.mentor + ' - ' + new_matches.mentee
    new_matches['mentee_type'] = new_matches['type'].str.split('-').str[1]
    new_matches.rename(columns={'mentee':'mentee_name','mentor':'mentor_name'},inplace=True)
    new_matches = pd.concat([historic_matches,new_matches[['mentee_name','mentor_name','within_region','round','date','pairs','mentee_type','type']]])
    return new_matches

