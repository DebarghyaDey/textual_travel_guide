import os
import time

import openai
import googlemaps

import streamlit as st

openai.api_key = st.secrets['OPENAI_API_KEY']
googlemaps_api_key = st.secrets['GOOGLEMAPS_API_KEY']

gmaps = googlemaps.Client(googlemaps_api_key)

max_distance = 3000
min_buildings = 5
BUILDING_CATEGORIES = [['bank', 'atm'], ['hospital', 'pharmacy'], ['lodging'], ['restaurant', 'cafe'],
                       ['shopping_mall', 'supermarket'], ['store'], ['amusement_park', 'park', 'zoo'],
                       ['bar', 'liquor_store']]
BUILDING_CATEGORIES_PLURAL = [' banks or ATMs', ' hospitals or medical shops', ' hotels', ' restaurants or cafes',
                              ' shopping places', ' stores', ' parks or zoo', ' bars or liquor stores']


def format_building_counts(building_counts: list[list[str]]):
    building_summary = ""
    # printing first summary
    for i in range(3):
        if not building_counts[i]: continue
        if i == 0:
            building_summary += f"Within a distance of 1 km, we have "
        elif i == 1:
            building_summary += f"Increasing the search space to 2 km yields in extra establishments such as "
        else:
            building_summary += f"Overall within 3 km, in addition to previously discovered buildings, one can come across "
        for j in range(len(building_counts[i])):
            if len(building_counts[i]) == 1:
                building_summary += f"{building_counts[i][j]}.\n\n"
            elif j == len(building_counts[i]) - 1:
                building_summary += f"and {building_counts[i][j]}.\n\n"
            elif j == len(building_counts[i]) - 2:
                building_summary += f"{building_counts[i][j]} "
            else:
                building_summary += f"{building_counts[i][j]}, "
                
    return building_summary


def initial_summary(location: tuple):
    building_counts = [[], [], []]
    for i in range(len(BUILDING_CATEGORIES)):
        count = 0
        distance = 0

        # find distance where we get more than 5 items
        while count < min_buildings and distance < max_distance:
            count = 0
            distance += 1000
            for building_type in BUILDING_CATEGORIES[i]:
                response = gmaps.places_nearby(
                    location=location,
                    radius=distance,
                    type=building_type
                )
                count += len(response['results'])

        if count < 5:
            continue

        # find total count using 'next_page_token'
        count = 0
        for building_type in BUILDING_CATEGORIES[i]:
            response = gmaps.places_nearby(
                location=location,
                radius=distance,
                type=building_type
            )
            count += len(response['results'])

            while 'next_page_token' in response:
                time.sleep(2)
                response = gmaps.places_nearby(
                    location=location,
                    radius=distance,
                    type=building_type,
                    page_token=response['next_page_token']
                )
                count += len(response['results'])

        building_counts[(int)(distance / 1000) - 1].append(str(count) + BUILDING_CATEGORIES_PLURAL[i])

    return format_building_counts(building_counts)


def format_summary(summary: str, popular_buildings: list[any], building_category: int):
    formatted_summary = ""
    if len(popular_buildings) < 3:
        formatted_summary += f"Very little information is available about the {BUILDING_CATEGORIES_PLURAL[building_category]} at this place. "

    formatted_summary += f"Some popular {BUILDING_CATEGORIES_PLURAL[building_category]} found nearby are "
    for j in range(min(2, len(popular_buildings))):
        formatted_summary += f"{popular_buildings[j]}{',  and ' if j == 0 and len(popular_buildings) > 1 else '. '}"

    formatted_summary += "\n" + summary.lstrip(":-\n\t ")

    return formatted_summary[:formatted_summary.rindex(".") + 1]


def summarize_location_for_building_category(location: tuple, building_category: int):
    count = 0
    distance = 0

    # find distance where we get more than 5 buildings
    while count < min_buildings and distance < max_distance:
        count = 0
        distance += 1000
        for building_type in BUILDING_CATEGORIES[building_category]:
            response = gmaps.places_nearby(
                location=location,
                radius=distance,
                type=building_type
            )
            count += len(response['results'])

    if count < 5:
        return ""

    # find all the buildings within this distance using 'next_page_token'
    buildings = []
    for building_type in BUILDING_CATEGORIES[building_category]:
        response = gmaps.places_nearby(
            location=location,
            radius=distance,
            type=building_type
        )
        buildings.extend(response['results'])

        while 'next_page_token' in response:
            time.sleep(2)
            response = gmaps.places_nearby(
                location=location,
                radius=distance,
                type=building_type,
                page_token=response['next_page_token']
            )
            buildings.extend(response['results'])

    # reviews array contains concatenated reviews for each building
    reviews = []
    for j in range(len(buildings)):
        place_details = gmaps.place(buildings[j]['place_id'])
        reviews.append("")
        if 'reviews' in place_details['result']:
            for review in place_details['result']['reviews']:
                if review['text'] != '':
                    reviews[j] = reviews[j] + " " + review['text']

    buildings = sorted(zip(buildings, reviews), key=lambda pair: len(pair[1]), reverse=True)

    # summarize the reviews for each building and add the building to popular_buildings if it has enough reviews
    index = 0
    summarised_reviews = []
    popular_buildings = []
    while len(buildings[index][1]) > 300:
        popular_buildings.append(buildings[index][0]['name'])
        response = openai.Completion.create(
            model="babbage",
            prompt=buildings[index][1][0:1500] + "\n\nTL;DR",
            temperature=0.7,
            max_tokens=60,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        summarised_reviews.append(buildings[index][0]['name'].upper() + ": " + response["choices"][0]['text'])
        index += 1

    # summarize the reviews for all the buildings belonging to a particular building category eg: ['bank','atm']
    to_summarize = "This place has several " + BUILDING_CATEGORIES_PLURAL[
        building_category] + ". Details about some of those are given.\n" + "\n".join(summarised_reviews)[
                                                                            :1800] + "\nREQUIRED: Give me a summary about this place in 100 words. DO NOT list the building names in the summary."
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=to_summarize + "\n\nTL;DR",
        temperature=0.5,
        max_tokens=100,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    summary = response['choices'][0]['text']
    print(summary)

    return format_summary(summary, popular_buildings, building_category)


def summarize_location(location: tuple):
    summaries = []

    for i in range(len(BUILDING_CATEGORIES)):
        summaries.append(summarize_location_for_building_category(location, i))

    return "\n\n".join(summaries)
