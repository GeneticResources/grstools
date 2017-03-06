"""
Multiple utilities to manipulate computed GRS.
"""

import logging
import argparse

import pandas as pd
import numpy as np
import scipy.stats
import matplotlib.pyplot as plt


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


plt.style.use("ggplot")


def _read_grs(filename):
    return pd.read_csv(filename, sep=",", index_col="sample")


def histogram(args):
    out = args.out if args.out else "grs_histogram.png"
    data = _read_grs(args.grs_filename)

    plt.hist(data["grs"], bins=args.bins)
    plt.xlabel("GRS")
    logger.info("WRITING histogram to file '{}'.".format(out))
    if args.out.endswith(".png"):
        plt.savefig(out, dpi=300)
    else:
        plt.savefig(out)


def quantiles(args):
    out = args.out if args.out else "grs_discretized.csv"
    data = _read_grs(args.grs_filename)

    q = float(args.k) / args.q
    low, high = data.quantile([q, 1-q]).values.T[0]

    data["group"] = np.nan
    data.loc[data["grs"] <= low, "group"] = 0
    data.loc[data["grs"] >= high, "group"] = 1

    if not args.keep_unclassified:
        data = data.dropna(axis=0, subset=["group"])

    logger.info("WRITING discretized GRS using k={}; q={} to file '{}'."
                "".format(args.k, args.q, out))

    data[["group"]].to_csv(out)


def standardize(args):
    out = args.out if args.out else "grs_standardized.csv"
    data = _read_grs(args.grs_filename)

    data["grs"] = (data["grs"] - data["grs"].mean()) / data["grs"].std()
    data.to_csv(out)


def correlation(args):
    grs1 = _read_grs(args.grs_filename)
    grs1.columns = ["grs1"]

    grs2 = _read_grs(args.grs_filename2)
    grs2.columns = ["grs2"]

    grs = pd.merge(grs1, grs2, left_index=True, right_index=True, how="inner")

    if grs.shape[0] == 0:
        raise ValueError("No overlapping samples between the two GRS.")

    linreg = scipy.stats.linregress
    slope, intercept, r_value, p_value, std_err = linreg(grs["grs1"],
                                                         grs["grs2"])

    plt.scatter(grs["grs1"], grs["grs2"], marker=".", s=1, c="#444444",
                label="data")

    xmin = np.min(grs["grs1"])
    xmax = np.max(grs["grs1"])

    x = np.linspace(xmin, xmax, 2000)
    y = slope * x + intercept

    plt.plot(
        x, y,
        label=("GRS2 = {:.2f} GRS1 + {:.2f} ($R^2={:.2f}$)"
               "".format(slope, intercept, r_value ** 2))
    )

    plt.xlabel("GRS1")
    plt.ylabel("GRS2")

    plt.legend()
    plt.show()


def main():
    args = parse_args()

    command_handlers = {
        "histogram": histogram,
        "quantiles": quantiles,
        "standardize": standardize,
        "correlation": correlation,
    }

    command_handlers[args.command](args)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Utilities to manipulated computed GRS."
    )

    parent = argparse.ArgumentParser(add_help=False)

    # General arguments.
    parent.add_argument(
        "grs_filename",
        help="Path to the file containing the computed GRS."
    )

    parent.add_argument(
        "--out", "-o",
        default=None
    )

    subparser = parser.add_subparsers(
        dest="command",
    )

    subparser.required = True

    # Histogram
    histogram_parse = subparser.add_parser(
        "histogram",
        help="Plot the histogram of the computed GRS.",
        parents=[parent]
    )

    histogram_parse.add_argument("--bins", type=int, default=60)

    # Quantiles
    quantiles = subparser.add_parser(
        "quantiles",
        help=(
            "Dichotomize the GRS using quantiles. Takes two parameters: "
            "k and q where q is the number of quantiles and k is the cutoff "
            "to be used for the discretization. For example, if the 1st "
            "quintile is to be compared to the 5th, use -q 5 -k 1. "
            "By default -k=1 and -q=2 which means the median is used."
        ),
        parents=[parent]
    )

    quantiles.add_argument("-k", default=1, type=int)
    quantiles.add_argument("-q", default=2, type=int)
    quantiles.add_argument("--keep-unclassified", action="store_true")

    # Standardize
    subparser.add_parser(
        "standardize",
        help="Standardize the GRS (grs <- (grs - mean) / std).",
        parents=[parent]
    )

    # Correlation
    correlation = subparser.add_parser(
        "correlation",
        help="Plot the correlation between two GRS.",
        parents=[parent]
    )

    correlation.add_argument(
        "grs_filename2",
        help="Filename of the second GRS."
    )

    return parser.parse_args()
