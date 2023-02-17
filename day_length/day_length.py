import streamlit as st
import pandas as pd

from astral import Observer
from astral.sun import sunrise, sunset, sun

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder


@st.cache
def get_locator(city):
    geolocator = Nominatim(user_agent="MyApp")
    return geolocator.geocode(city)


def get_day_light_info(latitude, longitude, day=None):
    def get_polar_day_or_night():
        polar_day = {'dawn': None, 'sunrise': None, 'noon': None, 'sunset': None, 'dusk': None,
                     'day_length': 24 * 60 * 60 + 59 * 60 + 59}
        polar_night = {'dawn': None, 'sunrise': None, 'noon': None, 'sunset': None, 'dusk': None, 'day_length': 0}
        if day.month in [10, 11, 12, 1, 2, 3, 4]:
            return polar_night
        else:
            return polar_day

    day = day or pd.Timestamp.today().date()

    try:
        data = sun(Observer(latitude=latitude, longitude=longitude), date=day)
        data['day_length'] = (data['sunset'] - data['sunrise']).seconds
    except ValueError:
        try:
            sunrise = sunrise(Observer(latitude=latitude, longitude=longitude), date=day)
        except:
            sunrise = None
        try:
            sunset = sunset(Observer(latitude=latitude, longitude=longitude), date=day)
        except:
            sunset = None
        data = get_polar_day_or_night()
        data['sunrise'], data['sunset'] = sunrise, sunset
        if sunrise and data['day_length']:
            data['day_length'] -= (sunrise.hour * 60 * 60 + sunrise.minute * 60 + sunrise.second)
        if sunset and data['day_length']:
            data['day_length'] = (sunset.hour * 60 * 60 + sunset.minute * 60 + sunset.second)

    return data


def seconds_to_time(seconds):
    sec = seconds % 60
    min = seconds // 60
    hours = min // 60
    return f'{hours}:{min % 60}:{sec}'


def time_to_number(time):
    return time.hour + time.minute / 60


def get_timezone(lat, lng):
    tf = TimezoneFinder()
    return tf.timezone_at(lng=lng, lat=lat)


def get_data_frame(city):
    locator = get_locator(city)

    # Add a placeholder
    latest_iteration = st.empty()
    bar = st.progress(0)

    date_range = pd.date_range(start='2023-01-01', end='2023-12-31')
    result = {}
    for i, date in enumerate(date_range):
        result[date.date()] = get_day_light_info(locator.latitude,
                                                 locator.longitude,
                                                 date.date())
        # Update the progress bar with each iteration.
        latest_iteration.text(f'Wait for calculating data!!! Iteration {i + 1} for {date.date()}')
        bar.progress((i + 1) / len(date_range))
    latest_iteration.text(f'Calculating data complete!!!')

    result = {key: val for key, val in result.items() if val is not None}
    df = pd.DataFrame(result).T

    t_zone = get_timezone(locator.latitude, locator.longitude)

    for column in df.columns:
        if column != 'day_length':
            df[column] = pd.to_datetime(df[column]).dt.tz_convert(t_zone).dt.time
    df['sun_set'] = df.sunset.apply(time_to_number)
    df['sun_rise'] = df.sunrise.apply(time_to_number)

    return df


st.set_page_config(page_title='🌞Day length!',
                   page_icon=None,
                   layout="wide",
                   initial_sidebar_state="auto",
                   menu_items=None)

st.title('Day length program!!!')

with st.sidebar:
    st.text_input("City: ", key="city")
    city = st.session_state.city.title()
    city_locator = get_locator(city)

    if city:
        st.write(f'Latitude: {city_locator.latitude} Longitude: {city_locator.longitude}')

        time_zone = get_timezone(city_locator.latitude, city_locator.longitude)
        st.write(f'Timezone {time_zone}')

        st.text_input("Compare with city: ", key="city_two")
        city_two = st.session_state.city_two.title()

if st.session_state.city:
    if city_two and not city:
        st.session_state.city_two = ''
        city_two = ''

    with st.expander("See map"):
        st.map(pd.DataFrame({'lat': [city_locator.latitude], 'lon': [city_locator.longitude]}))

    df = get_data_frame(city)

    col1, col2 = st.columns(2)

    with col1:
        st.header(f'The earliest:')
        st.write(f'Sunrise is {min(df.sunrise.dropna()):%H:%M:%S} '
                 f'on {df[df.sunrise == min(df.sunrise.dropna())].index.format()}')
        st.write(f'Sunset is {min(df.sunset.dropna()):%H:%M:%S} '
                 f'on {df[df.sunset == min(df.sunset.dropna())].index.format()}')

    with col2:
        st.header(f'The latests')
        st.write(f'Sunrise is {max(df.sunrise.dropna()):%H:%M:%S} '
                 f'on {df[df.sunrise == max(df.sunrise.dropna())].index.format()}')
        st.write(f'Sunset is {max(df.sunset.dropna()):%H:%M:%S} '
                 f'on {df[df.sunset == max(df.sunset.dropna())].index.format()}')

    with st.sidebar:
        date = st.date_input("Choose date", pd.Timestamp.today().date(),
                             min_value=pd.Timestamp(2023, 1, 1).date(),
                             max_value=pd.Timestamp(2023, 12, 31).date())
        st.write(f'Sunrise: {df.loc[date].sunrise}')
        st.write(f'Sunset: {df.loc[date].sunset}')
        st.write(f'Day length: {df.loc[date].day_length}')

    st.line_chart(df[['sun_set', 'sun_rise']])

    longest_day = df[df.day_length == max(df.day_length)].day_length.values[0]
    shortest_day = df[df.day_length == min(df.day_length)].day_length.values[0]
    st.write(f'The longest day is {df[df.day_length == longest_day].index.format()} - '
             f'{longest_day} seconds {seconds_to_time(longest_day)}')
    st.write(f'The shortest day is {df[df.day_length == shortest_day].index.format()} - '
             f'{shortest_day} seconds {seconds_to_time(shortest_day)}')

    st.write('Day length:')
    st.area_chart(pd.to_numeric(df.day_length))

    st.write('Day length changing:')
    df['day_length_chng'] = df.day_length.rolling(window=2).apply(lambda x: x[1] - x[0])
    st.area_chart(df.day_length_chng)

    if city_two:
        df_two = get_data_frame(city_two)
        df[f'{city_two}_rise'] = df_two.sun_rise
        df[f'{city_two}_set'] = df_two.sun_set
        st.line_chart(df[['sun_rise', 'sun_set', f'{city_two}_rise', f'{city_two}_set']])

    st.dataframe(df)
