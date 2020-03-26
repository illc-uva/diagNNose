import json
from argparse import ArgumentParser
from datetime import datetime
from functools import reduce
from pprint import pprint
from typing import Set

import numpy as np
import torch

import diagnnose.typedefs.config as config
from diagnnose.typedefs.activations import ActivationNames
from diagnnose.typedefs.config import ArgDict, ConfigDict, RequiredArgs
from diagnnose.utils.misc import merge_dicts


def create_config_dict(
    argparser: ArgumentParser, required_args: RequiredArgs, validate: bool = True
) -> ConfigDict:
    """ Sets up the configuration for extraction.

    Config can be provided from a json file or the commandline. Values
    in the json file can be overwritten by providing them from the
    commandline. Will raise an error if a required argument is not
    provided in either the json file or as a commandline arg.

    Commandline args should be provided as dot-separated values, where
    the first dot indicates the arg group the arg belongs to.
    For example, setting the `state_dict` of a `model` can be done as
    `--model.state_dict ...`.

    Parameters
    ----------
    argparser : ArgumentParser
        argparser that reads in the provided arguments
    required_args : RequiredArgs
        Set of arguments that should be at least provided in either the
        config file or as commandline argument.
    validate : bool
        Toggle to validate the provided config on required args and arg
        groups. Defaults to True.

    Returns
    -------
    config_dict : ConfigDict
        Dictionary mapping each arg group to their config values.
    """
    cmd_args = vars(argparser.parse_args())

    # Load arguments from config
    config_dict: ArgDict = {}
    if cmd_args["config"] is not None:
        with open(cmd_args["config"]) as f:
            config_dict.update(json.load(f))

    config_dict = add_cmd_args(config_dict, cmd_args)

    if validate:
        validate_config(required_args, argparser, config_dict)

    activation_config = config_dict.get("activations", {})
    activation_dtype = activation_config.get("dtype", None)
    if activation_dtype is not None:
        config.DTYPE = getattr(torch, activation_dtype)
        config.DTYPE_np = getattr(np, activation_dtype)
    activation_names = activation_config.get("activation_names", [])
    if len(activation_names) == 0:
        activation_names = config_dict.get("train_dc", {}).get("activation_names", [])
    if len(activation_names) > 0:
        cast_activation_names(activation_names)

    print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    pprint(config_dict)

    return config_dict


def validate_config(
    required_args: Set[str], argparser: ArgumentParser, config_dict: ArgDict
) -> None:
    """ Check if all required args are provided """
    config_args = set(f"{g}.{k}" for g, v in config_dict.items() for k in v.keys())
    for arg in required_args:
        assert arg in config_args, argparser.error(f"--{arg} should be provided")


def add_cmd_args(config_dict: ArgDict, cmd_args: ArgDict) -> ArgDict:
    """ Update provided config values with cmd args. """
    cdm_arg_dicts = []
    for arg, val in cmd_args.items():
        if val is not None and arg != "config":
            cmd_arg = arg.split(".")[::-1]
            cmd_arg_dict = val
            for key in cmd_arg:
                cmd_arg_dict = {key: cmd_arg_dict}
            cdm_arg_dicts.append(cmd_arg_dict)

    return reduce(merge_dicts, (config_dict, *cdm_arg_dicts))


def cast_activation_names(activation_names: ActivationNames) -> None:
    """ Cast activation names to (layer, name) format. """
    for i, name in enumerate(activation_names):
        activation_names[i] = (int(name[-1]), name[0:-1])
