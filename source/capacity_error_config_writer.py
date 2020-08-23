import json
import os

def main():
    """
    A config writer for the CapacityError object in the capacity_error library.
    Writes to a .txt file in json format.
    Returns
    -------
    None

    """

    domestic_count = 964926
    non_domestic_count = 33315

    config = {}

    config["decommissioned"] = {}
    config["decommissioned"]["domestic"] = {}
    config["decommissioned"]["domestic"]["p1"] = (
        "normal", [1000 / domestic_count, 300 / domestic_count]
    )

    config["decommissioned"]["domestic"]["p2"] = ("uniform", [-1])
    config["decommissioned"]["non_domestic"] = {}
    config["decommissioned"]["non_domestic"]["p1"] = (
        "normal", [100 / non_domestic_count, 30 / non_domestic_count]
    )
    config["decommissioned"]["non_domestic"]["p2"] = ("uniform", [-1])

    config["unreported"] = {}
    config["unreported"]["domestic"] = {}
    config["unreported"]["domestic"]["p1"] = (
        "uniform", [182530 / domestic_count]
    )
    config["unreported"]["non_domestic"] = {}
    config["unreported"]["non_domestic"]["p1"] = ("uniform", [9081 / 32872])
    config["revised_up"] = {}
    config["revised_up"]["domestic"] = {}
    config["revised_up"]["domestic"]["p1"] = (
        "normal",
        [10000 / domestic_count, 3000 / domestic_count]
    )
    config["revised_up"]["domestic"]["p2"] = ("normal", [0.4, 0.1])
    config["revised_up"]["non_domestic"] = {}
    config["revised_up"]["non_domestic"]["p1"] = (
        "normal", [1000 / non_domestic_count, 300 / non_domestic_count]
    )
    config["revised_up"]["non_domestic"]["p2"] = ("normal", [0.4, 0.1])

    config["revised_down"] = {}
    config["revised_down"]["domestic"] = {}
    config["revised_down"]["domestic"]["p1"] = (
        "normal", [10000 / domestic_count,3000 / domestic_count]
    )
    config["revised_down"]["domestic"]["p2"] = ("normal", [-0.2, 0.1])
    config["revised_down"]["non_domestic"] = {}
    config["revised_down"]["non_domestic"]["p1"] = (
        "normal", [1000 / non_domestic_count, 300 / non_domestic_count]
    )
    config["revised_down"]["non_domestic"]["p2"] = ("normal", [-0.2, 0.1])

    config["site_uncertainty"] = {}
    config["site_uncertainty"]["domestic"] = {}
    config["site_uncertainty"]["domestic"]["p1"] = ("uniform", [1])
    config["site_uncertainty"]["domestic"]["p2"] = ("normal", [0.5, 0.2])
    config["site_uncertainty"]["non_domestic"] = {}
    config["site_uncertainty"]["non_domestic"]["p1"] = ("uniform", [437 / 705])
    config["site_uncertainty"]["non_domestic"]["p2"] = (
        "johnson_su", [0.245073, 0.6974654, 3.6488511, 8.3220805, (-100, 100)]
    ) # shape, shape, location, scale

    config["offline"] = {}
    config["offline"]["domestic"] = {}
    config["offline"]["domestic"]["p1"] = ("normal", [0.1, 0.03])
    config["offline"]["domestic"]["p2"] = ("uniform",  [-1])
    config["offline"]["non_domestic"] = {}
    config["offline"]["non_domestic"]["p1"] = ("normal", [0.015, 0.006])
    config["offline"]["non_domestic"]["p2"] = ("uniform", [-1])

    config["network_outage"] = {}
    config["network_outage"]["domestic"] = {}
    config["network_outage"]["domestic"]["p1"] = ("normal", [0.002, 0.001])
    config["network_outage"]["domestic"]["p2"] = ("uniform", [-1])
    config["network_outage"]["non_domestic"] = {}
    config["network_outage"]["non_domestic"]["p1"] = ("normal", [0.02, 0.01])
    config["network_outage"]["non_domestic"]["p2"] = ("uniform", [-1])

    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'Config/capacity_error.txt'), 'w') as jsonconfigfile:
        json.dump(config, jsonconfigfile, indent=4, sort_keys=True)


if __name__ == "__main__":
    main()