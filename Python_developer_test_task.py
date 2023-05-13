import argparse
import json
import os.path
from datetime import datetime, timedelta
import numpy as np

DRIVER_SUFFIX = "(Driver)"
DRIVER_SLEEP_TIME = 6
TIME_FORMAT = "%H:%M"
INPUT_END_LINE = "END"


def get_input(file_path: str) -> str:
    """
    Get the input from the user either from a file or via the command line
    :param file_path: if manually, user has to insert the path
    :return input_text: the result of either file data or manual insert
    """
    if file_path is not None:
        if not os.path.isfile(file_path):
            print(f"File {file_path} doesn't exist")
            return None
        with open(file_path, "r") as f:
            input_text = f.read()
    else:
        print(f"Enter the input below (to stop enter \"{INPUT_END_LINE}\"):")
        lines = []
        line = input()
        while line != INPUT_END_LINE:
            lines.append(line)
            line = input()
        input_text = "\n".join(lines)

    return input_text


def parse_input(input_text: str) -> (datetime, datetime, list):
    """
    Function to appropriately store data and separate time from soldiers
    :param input_text: str, the list of soldiers separated by new line, any number of squads
    :return time: datatime, beginning and end of the timeframe, within which the duties should be distributed
    :return squads: the list of soldiers in separated squads
    """
    soldiers = input_text.strip().split("\n")
    time_strings = soldiers.pop(0).split(" to ")
    start_time = datetime.strptime(time_strings[0], TIME_FORMAT)
    end_time = datetime.strptime(time_strings[1], TIME_FORMAT)
    if start_time > end_time:
        end_time += timedelta(days=1)

    squads = []
    squad = []
    for soldier in soldiers:
        # Since there is always a new line separating the squads, we can split by it
        if soldier == "":
            squads.append(squad)
            squad = []
            continue

        is_driver = DRIVER_SUFFIX in soldier
        squad.append({
            "name": soldier,
            "is_driver": is_driver
        })

    squads.append(squad)
    return start_time, end_time, squads


def get_active_hours_distribution(squad: list, night_hours, active_hours: int) -> list:
    """
    The function summarize available active hours for every soldier in the squad
    :param squad: list of soldiers for the same squad
    :param night_hours: the duration of the duties timeframe
    :param active_hours: how many active (non-sleep) hours soldier has
    :return: list of nominal hours, for which soldier can take on duties
    """
    member_active_hours = [len(actions) for actions in np.array_split(range(active_hours), len(squad))]

    # redistribute if any driver gets more than they can handle and still sleep 6 hours
    drivers_cnt = 0
    max_driver_active_hours = night_hours - DRIVER_SLEEP_TIME
    redistribute = False
    for i, member in enumerate(squad):
        if member["is_driver"]:
            drivers_cnt += 1
            if member_active_hours[i] > max_driver_active_hours:
                redistribute = True

    if redistribute:
        # put drivers first
        squad.sort(key=lambda x: not x["is_driver"])
        for i in range(drivers_cnt):
            member_active_hours[i] = max_driver_active_hours
        redistributed = get_active_hours_distribution(squad[drivers_cnt:], night_hours,
                                                      active_hours - max_driver_active_hours * drivers_cnt)
        member_active_hours = member_active_hours[:drivers_cnt] + redistributed

    return member_active_hours


def get_next_member(squad: list, start_t: datetime, end_t: datetime, cur_t: datetime, *ignore_id: int) -> int:
    """
    Function finds the most appropriate soldier in terms of active hours for duties
    :param squad: list of soldiers for the same squad
    :param start_t: the beginning of the duties timeframe
    :param end_t: the end of the duties timeframe
    :param cur_t: current time
    :param ignore_id: list of exception to avoid the overlap
    :return: soldier "index"
    """
    i = 0
    start_sleep = cur_t - timedelta(hours=DRIVER_SLEEP_TIME)
    while squad[i]["active_hours"] == 0 or \
            i in ignore_id or (
            squad[i]["is_driver"] and
            start_sleep < start_t and
            (cur_t + timedelta(hours=DRIVER_SLEEP_TIME + squad[i]["active_hours"])) >= end_t
    ):
        i += 1
    squad[i]["active_hours"] -= 1
    return i


def allocate_duties(start_t: datetime, end_t: datetime, squads: list) -> dict:
    """
    Function covers both patrol and stove-watch duties for passed squads
    :param start_t: the beginning of the duties timeframe
    :param end_t: the end of the duties timeframe
    :param squads: the list of soldiers in separated squads
    :return: dictionary of time, names, and duties
    """
    squads_duties = {}
    num_of_squads = len(squads)
    night_hours = (end_t - start_t).seconds // 3600
    squads_patrol_hours = [len(actions) for actions in np.array_split(range(night_hours), num_of_squads)]

    patrol_end_time = start_t
    for i, squad in enumerate(squads):
        patrol_hours = squads_patrol_hours[i]
        active_hours = night_hours + patrol_hours * 2
        patrol_start_time = patrol_end_time
        patrol_end_time = patrol_start_time + timedelta(hours=patrol_hours)
        squad_duties = [
            {"time": (start_t + timedelta(hours=hour)).strftime(TIME_FORMAT)} for hour in range(night_hours)
        ]

        member_active_hours = get_active_hours_distribution(squad, night_hours, active_hours)

        for j, member in enumerate(squad):
            member["active_hours"] = member_active_hours[j]
        squad.sort(key=lambda x: (not x["is_driver"], x["active_hours"]))

        # calculating patrol duties
        patrols = [[]] * night_hours
        for hour in range(night_hours):
            cur_time = start_t + timedelta(hours=hour)
            if cur_time < patrol_start_time or cur_time >= patrol_end_time:
                squad_duties[hour]["patrol"] = "-"
                continue

            first = get_next_member(squad, start_t, end_t, cur_time)
            second = get_next_member(squad, start_t, end_t, cur_time, first)
            patrols[hour] = [first, second]
            squad_duties[hour]["patrol"] = ", ".join([
                squad[first]["name"],
                squad[second]["name"]
            ])

        # calculating stove-watch duties
        for hour in range(night_hours):
            cur_time = start_t + timedelta(hours=hour)
            cur_member = get_next_member(squad, start_t, end_t, cur_time, *patrols[hour])
            member = squad[cur_member]
            squad_duties[hour]["stove-watch"] = member["name"]

        squads_duties[f"squad {i + 1}"] = squad_duties

    return squads_duties


def generate_output(schedules: dict):
    """
    Generates the output in JSON format
    :param schedules: dictionary of time, names, and duties
    :return: json file
    """
    print(json.dumps(schedules, indent=4))

    save_output = input("\n\nDo you want to save the output as a file? (y/n) ")
    if save_output.lower() == "y":
        file_name = input("Enter the file name: ")
        with open(file_name, "w") as output_file:
            json.dump(schedules, output_file, indent=4)
    return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", nargs="?")
    args = parser.parse_args()

    input_text = get_input(args.file_path)
    if input_text is None:
        return

    start_time, end_time, squads = parse_input(input_text)
    schedules = allocate_duties(start_time, end_time, squads)
    generate_output(schedules)


if __name__ == "__main__":
    main()
