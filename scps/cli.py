import argparse
import logging
import json

from scps.scraper import get_select_options, master_table

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def master_table_func(args):
    for _type in ["incidence", "mortality"]:
        logger.info("Getting %s data", _type)
        df = master_table(_type=_type)
        logger.info("Saving %s data with shape: %s", _type, str(df.shape))
        df.to_csv(
            f"state_cancer_profiles_{_type}.csv.gz", index=False, compression="gzip"
        )


def select_options_func(args):
    select_options = get_select_options()
    with open(args.output, "w") as f:
        f.write(json.dumps(select_options, indent=4))


def main():
    parser = argparse.ArgumentParser(description="State Cancer Profiles Scraper")

    # add a subcommand to get the select options
    subparsers = parser.add_subparsers()

    sel_options = subparsers.add_parser(
        "select_options",
        help="Get the select options from the state cancer profiles website",
    )
    sel_options.add_argument(
        "-o",
        "--output",
        help="Output file name",
        default="state_cancer_profiles_select_options.json",
    )
    sel_options.set_defaults(
        func=select_options_func
    )  # Set the default function for this subcommand

    # add a subcommand to get the master table
    master_table = subparsers.add_parser(
        "master_table",
        help="Get the master table from the state cancer profiles website",
    )
    master_table.set_defaults(
        func=master_table_func
    )  # Set the default function for this subcommand

    args = parser.parse_args()

    if "func" in args:
        args.func(args)  # Call the function associated with the chosen subcommand
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
