import datetime
import functools
import random

import gspread
import praw
import requests

from config import reddit_client_id
from config import reddit_client_secret
from config import reddit_user_agent

from config import bot_info


# DECORATORS #

def retry_gspread_func(f):
    """
    Retries the function that uses gspread until it completes without throwing an HTTPError
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        while True:
            try:
                f(*args, **kwargs)
            # Gspread doesn't handle errors very well
            # Sometimes it tries to index an error object, which it can't, which causes a type error.
            # I'd submit a patch, but the last time I tried to do that I had to harangue the author for literally
            # months to get my well tested, documented, all tests passing PR accepted. So I'm not doing that again.
            except (gspread.exceptions.GSpreadException, TypeError):
                continue
            break

    return wrapper


def mod_only(f):
    f._mod_only = True
    return f


def private_message_allowed(f):
    f._private_message_allowed = True
    return f


def public_message_disallowed(f):
    f._public_message_disallowed = True
    return f

# END DECORATORS #


def get_live_time():
    """
    Uses the kraken API to fetch the start time of the current stream.
    Computes how long the stream has been running, returns that value in a dictionary.
    """
    channel = bot_info['channel']
    url = 'https://api.twitch.tv/kraken/streams/{}'.format(channel.lower())
    for attempt in range(5):
        try:
            r = requests.get(url, headers={"Client-ID": bot_info['twitch_api_client_id']})
            r.raise_for_status()
            start_time_str = r.json()['stream']['created_at']
            start_time_dt = datetime.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%SZ')
            now_dt = datetime.datetime.utcnow()
            time_delta = now_dt - start_time_dt
            time_dict = {'hour': None,
                         'minute': None,
                         'second': None}

            time_dict['hour'], remainder = divmod(time_delta.seconds, 3600)
            time_dict['minute'], time_dict['second'] = divmod(remainder, 60)
            for time_var in time_dict:
                if time_dict[time_var] == 1:
                    time_dict[time_var] = "{} {}".format(time_dict[time_var], time_var)
                else:
                    time_dict[time_var] = "{} {}s".format(time_dict[time_var], time_var)
            time_dict['stream_start'] = start_time_dt
            time_dict['now'] = now_dt
        except requests.exceptions.HTTPError:
            continue
        except TypeError:
            raise RuntimeError("Sorry, the channel doesn't seem to be live at the moment.")
        except ValueError:
            continue
        else:
            return time_dict
    else:
        raise RuntimeError("Sorry, there was a problem talking to the twitch api. Maybe wait a bit and retry your command?")


def get_creation_date(user):
    """
    Returns the creation date of a given twitch user.
    """
    url = 'https://api.twitch.tv/kraken/users/{}'.format(user)
    for attempt in range(5):
        try:
            r = requests.get(url, headers={"Client-ID": bot_info['twitch_api_client_id']})
            creation_date = r.json()['created_at']
            cut_creation_date = creation_date[:10]
        except ValueError:
            continue
        except TypeError:
            continue
        else:
            return cut_creation_date
    else:
        raise RuntimeError(
            "Sorry, there was a problem talking to the twitch api. Maybe wait a bit and retry your command?")


def fetch_random_reddit_post_title(subreddit, time_filter='day', limit=10):
    """
    Fetches a random title from the specified subreddit
    """
    reddit_specific_words = ['reddit', 'karma', 'repost', 'vote', '/r/']
    valid_thoughts = []
    r = praw.Reddit(client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    user_agent=reddit_user_agent)

    submissions = r.subreddit(subreddit).top(time_filter=time_filter, limit=limit)
    for entry in submissions:
        if len([word for word in reddit_specific_words if word in entry.title.lower()]) == 0:
            valid_thoughts.append(entry.title)
    return random.choice(valid_thoughts)